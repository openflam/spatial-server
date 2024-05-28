import numpy as np
import pycolmap
import open3d as o3d
import os
from datetime import datetime
from pathlib import Path
from scipy import stats
from scale_adjustment import read_write_model

def pythonmapthing(model_path):
    # reconstruction = pycolmap.Reconstruction(model_path)
    # points3d = reconstruction.points3D

    # print(reconstruction.summary())
    # for image_id, image in reconstruction.images.items():
    #     print(image_id, image, [p.point3D_id for p in image.points2D])
    # for point3D_id, point3D in reconstruction.points3D.items():
    #     print(point3D_id, point3D)
    # for camera_id, camera in reconstruction.cameras.items():
    #     print(camera_id, camera)
    
    # pointids = np.array([point_id for point_id, point in points3d.items()])
    # points = np.array([point.xyz for point_id, point in points3d.items()])
    # colors = np.array([point.color for point_id, point in points3d.items()]) / 255.0
    # images = np.array([image for image_id, image in reconstruction.images.items()])

    cameras, images, points3D = read_write_model.read_model(model_path)
    pointids = np.array([point.id for point in points3D.values()])
    points = np.array([point.xyz for point in points3D.values()])

    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points)
    # o3d.visualization.draw_geometries([pcd])

    old_size = len(pcd.points)
    processed_pcd, _ = pcd.remove_statistical_outlier(nb_neighbors=100, std_ratio=1.5)
    new_size = len(processed_pcd.points)
    print(f"Total {new_size} points, pruned {old_size - new_size} outliers")
    # o3d.visualization.draw_geometries([processed_pcd])

    # old_size = len(pcd.points)
    # pcd, _ = pcd.remove_radius_outlier(nb_points=100, radius=0.5)
    # new_size = len(pcd.points)
    # print(f"Total {new_size} points, pruned {old_size - new_size} outliers")
    # o3d.visualization.draw_geometries([pcd])

    # Get the processed points, colors, and image associations
    processed_points = np.asarray(processed_pcd.points)
    zs = np.asarray([p[2] for p in list(processed_points)])

    boxdim = 0.5
    xmin = np.min(processed_points[:, 0])
    xmax = np.max(processed_points[:, 0])
    ymin = np.min(processed_points[:, 1])
    ymax = np.max(processed_points[:, 1])
    boxdim = np.asarray(boxdim)

    # # Flatten the grid for vectorized operations
    xbins = np.arange(xmin, xmax, boxdim)
    ybins = np.arange(ymin, ymax, boxdim)
    M, N = len(xbins), len(ybins)
    print(M, N)

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
            # print(f"{planecloud[idxs, :].shape} -> {bin.shape}")
            min_zs.append(np.min(bin[:, 2]))

    hist, bin_edges = np.histogram(min_zs, bins='auto', density=True)
    
    # Find the index of the bin with the highest probability
    max_prob_index = np.argmax(hist)
    
    # Get the corresponding bin edges for the most likely z coordinate
    most_likely_z = (bin_edges[max_prob_index] + bin_edges[max_prob_index + 1]) / 2
    
    # avg = 0 - np.average(np.asarray(min_zs))
    avg = 0 - most_likely_z
    print(f"Average: {avg}")

    mask = np.isin(points, processed_points).all(axis=1)
    processed_pointids = pointids[mask]
    new_points3D = {}
    
    for id in points3D:
        if id in processed_pointids:
            new_points3D[id] = points3D[id]
            # print(new_points3D[id])
            new_points3D[id].xyz[2] += avg
            # print(new_points3D[id])
            
    for id, image in images.items():
        image.point3D_ids
        for i in range(len(image.point3D_ids)):
            if (i != -1) or (image.point3D_ids[i] not in processed_pointids):
                image.point3D_ids[i] = -1

    model_path = Path(model_path)
    output_model_path = model_path.parent / 'cleaned_map6'
    os.makedirs(output_model_path, exist_ok=True)
    _ = read_write_model.write_model(cameras, images, new_points3D, output_model_path)

def main():
    pythonmapthing("/Users/michael/Desktop/Map-Thingy/map/point_cloud")
    pythonmapthing("/Users/michael/Desktop/Map-Thingy/Arena/point_cloud")
    pythonmapthing("/Users/michael/Desktop/Map-Thingy/Lobby/point_cloud")

if __name__ == "__main__":
    main()