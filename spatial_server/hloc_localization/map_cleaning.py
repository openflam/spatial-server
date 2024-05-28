import numpy as np
import pycolmap
import open3d as o3d
import os
from datetime import datetime

def pythonmapthing(model_path):
    reconstruction = pycolmap.Reconstruction(model_path)
    points3d = reconstruction.points3D

    print(reconstruction.summary())
    # for image_id, image in reconstruction.images.items():
    #     print(image_id, image, [p.point3D_id for p in image.points2D])
    # for point3D_id, point3D in reconstruction.points3D.items():
    #     print(point3D_id, point3D)
    # for camera_id, camera in reconstruction.cameras.items():
    #     print(camera_id, camera)
    
    # import pdb; pdb.set_trace()

    pointids = np.array([point_id for point_id, point in points3d.items()])
    points = np.array([point.xyz for point_id, point in points3d.items()])
    colors = np.array([point.color for point_id, point in points3d.items()]) / 255.0
    images = np.array([image for image_id, image in reconstruction.images.items()])

    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points)
    pcd.colors = o3d.utility.Vector3dVector(colors)
    # o3d.visualization.draw_geometries([pcd])

    old_size = len(pcd.points)
    processed_pcd, _ = pcd.remove_statistical_outlier(nb_neighbors=1000, std_ratio=1)
    new_size = len(processed_pcd.points)
    print(f"Total {new_size} points, pruned {old_size - new_size} outliers")
    # import pdb; pdb.set_trace()
    # o3d.visualization.draw_geometries([processed_pcd])

    # old_size = len(pcd.points)
    # pcd, _ = pcd.remove_radius_outlier(nb_points=100, radius=0.5)
    # new_size = len(pcd.points)
    # print(f"Total {new_size} points, pruned {old_size - new_size} outliers")
    # o3d.visualization.draw_geometries([pcd])

    # for point_id, point in points.items():
    #     xyz = point.xyz
    #     print(xyz)
    #     color = point.color
    #     print(color)

    # Get the processed points, colors, and image associations
    processed_points = np.asarray(processed_pcd.points)
    mask = np.isin(points, processed_points).all(axis=1)
    processed_pointids = pointids[mask]
    # processed_colors = np.asarray(processed_pcd.colors) * 255.0
        


    # Create a new COLMAP reconstruction
    new_reconstruction = pycolmap.Reconstruction()



    # Save the new COLMAP reconstruction
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_folder = f"/Users/michael/Desktop/Map-Thingy/map/new_point_cloud_{timestamp}"
    os.makedirs(output_folder, exist_ok=True)

    # Save the new COLMAP reconstruction in the new folder
    new_reconstruction.write(output_folder)

def main():
    pythonmapthing("/Users/michael/Desktop/Map-Thingy/map/point_cloud")

if __name__ == "__main__":
    main()