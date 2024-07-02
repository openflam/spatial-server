import argparse
import os
from pathlib import Path

import numpy as np
import open3d as o3d

from .scale_adjustment import read_write_model
from ..localizer import _rot_from_qvec, _homogenize


def convert_colmap_to_pcd(points3D_colmap, downsample=True, crop_y=0.33):
    points_pcd = np.array([point.xyz for point in points3D_colmap.values()], dtype=np.float32)
    colors_pcd = (
        np.array([point.rgb for point in points3D_colmap.values()], dtype=np.uint8)
        / 255.0
    )  # Normalize colors to [0, 1]
    
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points_pcd)
    pcd.colors = o3d.utility.Vector3dVector(colors_pcd)
    # Swap Y and Z axes, Y is vertical in our coordinate space
    pcd.points = o3d.utility.Vector3dVector(np.array(pcd.points)[:, [1, 2, 0]])

    if downsample: # Downsample
        pcd = pcd.voxel_down_sample(voxel_size=0.08)
    
    if crop_y > 0: # Remove ceiling points
        aabb = pcd.get_axis_aligned_bounding_box()
        min_bound = np.array(aabb.min_bound)
        max_bound = np.array(aabb.max_bound)
        max_bound[1] -= crop_y  # Decrease the upper Y-bound

        # Crop off ceiling
        cropped_aabb = o3d.geometry.AxisAlignedBoundingBox(min_bound, max_bound)
        pcd = pcd.crop(cropped_aabb)
    
    return pcd

def _elevate_existing_reconstruction(model_path, avg):
    cameras, images, points3D = read_write_model.read_model(model_path)
    for id in points3D:
        points3D[id].xyz[2] += avg
    
    for id in images:
        tvec = images[id].tvec
        qvec = images[id].qvec
        camera_pose_matrix = np.linalg.inv(_homogenize(_rot_from_qvec(qvec).as_matrix(), tvec))
        camera_pose_matrix[2][3] += avg # Elevate z-axis of the camera pose
        tvec_new = np.linalg.inv(camera_pose_matrix)[:3,3]
        for i in range(3):
            images[id].tvec[i] = tvec_new[i]
    
    read_write_model.write_model(cameras, images, points3D, model_path)


def clean_map(model_path):
    """
    Clean the map by removing outliers and adjusting the z coordinate of the points.

    Parameters
    ----------
    model_path : str
        The path to the COLMAP model file.
    """
    cameras, images, points3D = read_write_model.read_model(model_path)
    pointids = np.array([point.id for point in points3D.values()])
    points = np.array([point.xyz for point in points3D.values()])

    # Clean the map by removing outliers
    print(f"Removing outliers...")
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points)
    # o3d.visualization.draw_geometries([pcd])

    old_size = len(pcd.points)
    processed_pcd, _ = pcd.remove_statistical_outlier(nb_neighbors=100, std_ratio=1.5)
    new_size = len(processed_pcd.points)
    print(f"Total {new_size} points, pruned {old_size - new_size} outliers")

    # Get the processed points, colors, and image associations
    processed_points = np.asarray(processed_pcd.points)

    # Remove references to points that were removed
    for id, image in images.items():
        for i in range(len(image.point3D_ids)):
            if (image.point3D_ids[i] != -1) or (image.point3D_ids[i] not in processed_points):
                image.point3D_ids[i] = -1

    # Elevate the map to the ground level
    print(f"\nElevating the map to the ground level...")
    boxdim = 0.5
    xmin = np.min(processed_points[:, 0])
    xmax = np.max(processed_points[:, 0])
    ymin = np.min(processed_points[:, 1])
    ymax = np.max(processed_points[:, 1])
    boxdim = np.asarray(boxdim)

    # Flatten the grid for vectorized operations
    xbins = np.arange(xmin, xmax, boxdim)
    ybins = np.arange(ymin, ymax, boxdim)
    M, N = len(xbins), len(ybins)
    print("Number of XY Bins: ", M, " X ", N)

    # Use digitize to assign each point to a bin
    x_bin_indices = np.digitize(processed_points[:, 0], xbins) - 1
    y_bin_indices = np.digitize(processed_points[:, 1], ybins) - 1

    # Calculate the grid cell indices for each point
    grid_cell_indices = x_bin_indices * N + y_bin_indices

    min_zs = []

    for bin_idx in range(M*N):
        idxs = np.where(grid_cell_indices == bin_idx)
        bin = processed_points[idxs, :][0]
        if bin.size > 0:
            min_zs.append(np.min(bin[:, 2]))

    hist, bin_edges = np.histogram(min_zs, bins='auto', density=True)
    
    # Find the index of the bin with the highest probability
    max_prob_index = np.argmax(hist)
    
    # Get the corresponding bin edges for the most likely z coordinate
    most_likely_z = (bin_edges[max_prob_index] + bin_edges[max_prob_index + 1]) / 2
    
    avg = 0 - most_likely_z
    print(f"Shift in z: {avg}")

    mask = np.isin(points, processed_points).all(axis=1)
    processed_pointids = pointids[mask]
    new_points3D = {}
    
    for id in points3D:
        if id in processed_pointids: # Only add the points that are in the processed point cloud
            new_points3D[id] = points3D[id]
            new_points3D[id].xyz[2] += avg # Adjust the z coordinate

    # Save in COLMAP format
    model_path = Path(model_path)
    output_model_path = model_path.parent / 'cleaned_map'
    os.makedirs(output_model_path, exist_ok=True)
    read_write_model.write_model(cameras, images, new_points3D, output_model_path)

    # Elevate existing reconstruction
    _elevate_existing_reconstruction(model_path, avg)

    # Save as PCD
    pcd = convert_colmap_to_pcd(new_points3D, downsample=True, crop_y=1)
    o3d.io.write_point_cloud(str(output_model_path.parent / 'points.pcd'), pcd)
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clean the map by removing outliers and adjusting the z coordinate of the points.")
    parser.add_argument("model_path", type=str, help="The path to the COLMAP model file.")
    args = parser.parse_args()
    clean_map(args.model_path)
