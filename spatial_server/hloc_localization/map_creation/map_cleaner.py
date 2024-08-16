import argparse
import os
from pathlib import Path

import numpy as np
import open3d as o3d

from ..scale_adjustment import read_write_model
from ..localizer import _rot_from_qvec, _homogenize


def elevate_existing_reconstruction(model_path, output_path=None):
    """
    Changes the z-coordinate of the points (and camera locations) so that
    the ground is approximately at 0
    """
    model_path = Path(model_path)
    cameras, images, points3D = read_write_model.read_model(model_path)

    # Calculate the average z-coordinate of the points
    points = np.array([point.xyz for point in points3D.values()])

    boxdim = np.asarray(0.5)
    xmin, xmax = np.min(points[:, 0]), np.max(points[:, 0])
    ymin, ymax = np.min(points[:, 1]), np.max(points[:, 1])

    xbins = np.arange(xmin, xmax, boxdim)
    ybins = np.arange(ymin, ymax, boxdim)
    M, N = len(xbins), len(ybins)
    print("Number of XY Bins: ", M, " X ", N)

    # Use digitize to assign each point to a bin
    x_bin_indices = np.digitize(points[:, 0], xbins) - 1
    y_bin_indices = np.digitize(points[:, 1], ybins) - 1

    # Calculate the grid cell indices for each point
    grid_cell_indices = x_bin_indices * N + y_bin_indices

    min_zs = []

    for bin_idx in range(M * N):
        idxs = np.where(grid_cell_indices == bin_idx)
        bin = points[idxs, :][0]
        if bin.size > 0:
            min_zs.append(np.min(bin[:, 2]))

    hist, bin_edges = np.histogram(min_zs, bins="auto", density=True)

    # Find the index of the bin with the highest probability
    max_prob_index = np.argmax(hist)

    # Get the corresponding bin edges for the most likely z coordinate
    most_likely_z = (bin_edges[max_prob_index] + bin_edges[max_prob_index + 1]) / 2

    avg = 0 - most_likely_z
    print(f"Shift in z: {avg}")

    # Use the average to elevate the z-coordinate of the points
    for id in points3D:
        points3D[id].xyz[2] += avg

    for id in images:
        tvec = images[id].tvec
        qvec = images[id].qvec
        camera_pose_matrix = np.linalg.inv(
            _homogenize(_rot_from_qvec(qvec).as_matrix(), tvec)
        )
        camera_pose_matrix[2][3] += avg  # Elevate z-axis of the camera pose
        tvec_new = np.linalg.inv(camera_pose_matrix)[:3, 3]
        for i in range(3):
            images[id].tvec[i] = tvec_new[i]

    if output_path is None:
        output_path = model_path
    if not output_path.exists():
        output_path.mkdir(parents=True)
    read_write_model.write_model(cameras, images, points3D, output_path)


def clean_map(model_path, voxel_downsample=True, crop_y=0.33):
    """
    Clean the map by removing outliers and as pcd.

    Parameters
    ----------
    model_path : str
        The path to the COLMAP model file.
    """
    model_path = Path(model_path)
    # Convert colmap format to PCD
    cameras, images, points3D = read_write_model.read_model(model_path)
    points_pcd = np.array([point.xyz for point in points3D.values()], dtype=np.float32)
    colors_pcd = (
        np.array([point.rgb for point in points3D.values()], dtype=np.uint8) / 255.0
    )  # Normalize colors to [0, 1]

    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points_pcd)
    pcd.colors = o3d.utility.Vector3dVector(colors_pcd)

    # Clean the map by removing outliers
    print(f"Removing outliers...")
    processed_pcd, _ = pcd.remove_statistical_outlier(nb_neighbors=100, std_ratio=1.5)
    new_size, old_size = len(processed_pcd.points), len(pcd.points)
    print(f"Total {new_size} points, pruned {old_size - new_size} outliers")

    # Swap Y and Z axes, Y is vertical in aframe coordinate space
    processed_pcd.points = o3d.utility.Vector3dVector(
        np.array(processed_pcd.points)[:, [1, 2, 0]]
    )

    if voxel_downsample:  # Downsample
        processed_pcd = processed_pcd.voxel_down_sample(voxel_size=0.08)

    if crop_y > 0:  # Remove ceiling points
        aabb = processed_pcd.get_axis_aligned_bounding_box()
        min_bound = np.array(aabb.min_bound)
        max_bound = np.array(aabb.max_bound)
        max_bound[1] -= crop_y  # Decrease the upper Y-bound

        # Crop off ceiling
        cropped_aabb = o3d.geometry.AxisAlignedBoundingBox(min_bound, max_bound)
        processed_pcd = processed_pcd.crop(cropped_aabb)

    # Save as PCD
    o3d.io.write_point_cloud(str(model_path.parent / "points.pcd"), processed_pcd)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Clean the map by removing outliers and adjusting the z coordinate of the points."
    )
    parser.add_argument(
        "--model_path", type=str, help="The path to the COLMAP model file."
    )
    args = parser.parse_args()
    clean_map(args.model_path)
