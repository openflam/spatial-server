
import argparse
import copy
import json
import os
from pathlib import Path
import numpy as np
# import open3d as o3d
# from PIL import Image
from tqdm import tqdm
from scipy.spatial.transform import Rotation

# Lazy imports for hloc parts
# from . import map_creator
# from .polycam import build_map_from_polycam_output as build_map_original

def load_polycam_camera_params(json_path):
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    import open3d as o3d
    
    # Intrinsics
    w, h = data['width'], data['height']
    fx, fy = data['fx'], data['fy']
    cx, cy = data['cx'], data['cy']
    
    intrinsic = o3d.camera.PinholeCameraIntrinsic(w, h, fx, fy, cx, cy)
    
    # Extrinsics
    # Polycam stores a 4x4 matrix flattened or as t_ij
    # "t_00", "t_01", ... "t_33" (implied 0,0,0,1 for last row usually)
    
    c2w = np.eye(4)
    for i in range(3):
        for j in range(4):
            key = f"t_{i}{j}"
            if key in data:
                c2w[i, j] = data[key]
    
    # Polycam raw poses are often in a coordinate system where Y is Up, -Z is forward (GL style)
    # But sometimes they are different.
    # Open3D coordinate system: Y is Down, Z is Forward?
    # Actually Open3D PinholeCameraTrajectory uses Y down, Z forward.
    # Let's try to interpret the matrix as is first, but we might need conversion.
    # Usually, GL -> CV conversion involves flipping Y and Z axes.
    # Let's apply valid conversion:
    # Rotate 180 deg around X axis to convert from GL (Y up, -Z forward) to CV (Y down, Z forward)
    # This matrix M = [[1, 0, 0, 0], [0, -1, 0, 0], [0, 0, -1, 0], [0, 0, 0, 1]]
    # Open3D expects World-to-Camera (extrinsics) usually, but point cloud generation
    # typically uses Camera-to-World to place points in world.
    
    # Empirically, Polycam poses in raw export:
    # They seem to be Camera-to-World.
    # Let's create a point cloud in Camera frame and transform it by C2W.
    
    return intrinsic, c2w

def generate_point_cloud_from_polycam(polycam_data_directory, voxel_size=0.05):
    import open3d as o3d
    from PIL import Image

    kf_dir = Path(polycam_data_directory) / "keyframes"
    images_dir = kf_dir / "images"
    depth_dir = kf_dir / "depth"
    
    # Check if corrected_cameras exists, else use cameras
    cameras_dir = kf_dir / "corrected_cameras"
    if not cameras_dir.exists():
        cameras_dir = kf_dir / "cameras"
        print(f"Using raw cameras from {cameras_dir} (corrected_cameras not found)")
    else:
        print(f"Using corrected cameras from {cameras_dir}")

    # List all timestamps (filenames without extension)
    # We assume matching filenames in images, depth, and cameras
    image_files = sorted(list(images_dir.glob("*.jpg")) + list(images_dir.glob("*.png")))
    
    pcd_combined = o3d.geometry.PointCloud()
    
    # Downsample frames to speed up (e.g. use every 10th frame)
    # adjust based on count
    stride = max(1, len(image_files) // 50) # Use around 50 frames max for speed
    
    print(f"Generating point cloud from {len(image_files)} frames (stride={stride})...")
    
    for i in tqdm(range(0, len(image_files), stride)):
        img_path = image_files[i]
        stem = img_path.stem
        
        depth_path = depth_dir / f"{stem}.png"
        cam_path = cameras_dir / f"{stem}.json"
        
        if not depth_path.exists() or not cam_path.exists():
            continue
            
        # Load images
        color = o3d.io.read_image(str(img_path))
        depth = o3d.io.read_image(str(depth_path))
        
        # Load params
        intrinsic, c2w = load_polycam_camera_params(cam_path)

        # Handle resolution mismatch
        color_w, color_h = np.asarray(color).shape[1], np.asarray(color).shape[0]
        depth_w, depth_h = np.asarray(depth).shape[1], np.asarray(depth).shape[0]
        
        if color_w != depth_w or color_h != depth_h:
            # Resize color to match depth (faster processing)
            scale_x = depth_w / color_w
            scale_y = depth_h / color_h
            
            # Using PIL for resizing as Open3D resize might be different or less control?
            # Open3D Image has no resize method in python binding easily? 
            # Actually it does in newer versions, but let's use PIL to be safe or convert to numpy.
            # Or just use Open3D legacy resize if available.
            # Let's use PIL which is imported.
            
            # Re-read as PIL to resize
            color_pil = Image.fromarray(np.asarray(color))
            color_pil = color_pil.resize((depth_w, depth_h), Image.BILINEAR)
            color = o3d.geometry.Image(np.array(color_pil))
            
            # Scale intrinsics
            intrinsic_matrix = intrinsic.intrinsic_matrix
            fx, fy = intrinsic_matrix[0, 0] * scale_x, intrinsic_matrix[1, 1] * scale_y
            cx, cy = intrinsic_matrix[0, 2] * scale_x, intrinsic_matrix[1, 2] * scale_y
            intrinsic = o3d.camera.PinholeCameraIntrinsic(depth_w, depth_h, fx, fy, cx, cy)

        # Create RGBD
        # Polycam depth is usually in millimeters? verify.
        # usually 1000 scale factor for png.
        # But wait, looking at the files, depth are .png. 
        # Typically Polycam depth maps are 16-bit PNGs where unit is millimeters -> scale=1000.
        rgbd = o3d.geometry.RGBDImage.create_from_color_and_depth(
            color, depth, 
            depth_scale=1000.0, 
            depth_trunc=10.0, 
            convert_rgb_to_intensity=False
        )
        
        # Create PointCloud
        pcd = o3d.geometry.PointCloud.create_from_rgbd_image(
            rgbd, intrinsic
        )
        
        # Transform to World
        # Polycam C2W is GL style (Y up). Open3D expects Y down for projection?
        # create_from_rgbd_image creates points in camera frame: +Z forward, +Y down, +X right.
        # If Polycam poses are Y up, -Z forward, we need to transform the camera frame points to that convention first?
        # actually, simply applying the C2W matrix (if it matches the camera frame convention) works.
        # If C2W is GL style, then the rotation part R transforms from GL-Cam to World.
        # We need to rotate our CV-Cam points to GL-Cam first.
        # CV (Open3D default) to GL conversion: Rotate 180 around X.
        
        # T_cv_to_gl
        T_fix = np.eye(4)
        T_fix[1,1] = -1
        T_fix[2,2] = -1
        
        # Full transform: C2W_gl * T_cv_to_gl
        pcd.transform(c2w @ T_fix)
        
        pcd_combined += pcd

    # Voxel downsample
    pcd_combined = pcd_combined.voxel_down_sample(voxel_size=voxel_size)
    
    return pcd_combined

def align_point_cloud_to_mesh(source_pcd, mesh_path):
    import open3d as o3d
    print(f"Loading target mesh from {mesh_path}...")
    target_mesh = o3d.io.read_triangle_mesh(str(mesh_path))
    target_pcd = target_mesh.sample_points_poisson_disk(number_of_points=len(source_pcd.points))
    
    # Initial alignment
    # We assume they are roughly aligned but maybe origin shifted?
    # Polycam's raw.glb and the poses *should* be in the same coordinate system relative to each other 
    # IF we interpret them validity.
    # However, sometimes raw.glb is centered or transformed.
    
    # Since we built source_pcd from the explicit poses, it represents the "Structure from Motion" world.
    # The raw.glb might be in that same world, OR it might be post-processed.
    # If they are already aligned, the identity transform should result in low error.
    
    # Let's perform ICP to refine/calculate transform.
    # Trans_init = Identity
    
    threshold = 1.0 # 1 meter distance threshold for correspondence
    trans_init = np.eye(4)
    
    print("Running ICP Registration...")
    reg_p2p = o3d.pipelines.registration.registration_icp(
        source_pcd, target_pcd, threshold, trans_init,
        o3d.pipelines.registration.TransformationEstimationPointToPoint(),
        o3d.pipelines.registration.ICPConvergenceCriteria(max_iteration=2000)
    )
    
    print(f"ICP Fitness: {reg_p2p.fitness}")
    print(f"ICP RMSE: {reg_p2p.inlier_rmse}")
    print(f"Transformation:\n{reg_p2p.transformation}")
    
    return reg_p2p.transformation, target_mesh

def calculate_mesh_info_fields(mesh):
    # vertexCount
    vertexCount = len(mesh.vertices)
    # faceCount
    faceCount = len(mesh.triangles)
    # bbox
    bbox = mesh.get_axis_aligned_bounding_box()
    min_bound = bbox.get_min_bound()
    max_bound = bbox.get_max_bound()
    bboxSize = (max_bound - min_bound).tolist()
    bboxCenter = bbox.get_center().tolist()
    
    # Area calculation involves iterating triangles
    # Approximation or full calc? Open3D has get_surface_area()
    totalArea = mesh.get_surface_area()
    
    return {
        "vertexCount": vertexCount,
        "faceCount": faceCount,
        "totalArea": totalArea,
        "bboxSize": bboxSize,
        "bboxCenter": bboxCenter,
        # Default/Dummy values for fields we might not strictly need or are complex to calc perfectly without more logic
        "xPlusArea": 0, "xMinusArea": 0,
        "yMinusArea": 0, # Floor area?
        "zPlusArea": 0, "zMinusArea": 0,
        "horizontalUpArea": 0,
        "georeferenceLatitude": 0, "georeferenceLongitude": 0, "georeferenceAltitude": 0,
        "georeferenceRotation": 0,
        "yAlignmentRotation": 0
    }

def generate_mesh_info_json(polycam_data_directory):
    polycam_dir = Path(polycam_data_directory)
    mesh_path = polycam_dir / "raw.glb"
    
    if not mesh_path.exists():
        print(f"Error: {mesh_path} does not exist.")
        return False
        
    print("Generating Point Cloud from Polycam data...")
    source_pcd = generate_point_cloud_from_polycam(polycam_dir)
    if not source_pcd.has_points():
        print("Error: Failed to generate point cloud.")
        return False
        
    print("Aligning Point Cloud to Mesh...")
    # Note: Source is our reconstructed PC, Target is the Mesh (raw.glb).
    # transform maps Source -> Target.
    # So if we apply 'transformation' to Source, it aligns with Target.
    # mesh_info.json 'alignmentTransform' usually maps the mesh to some canonical frame?
    # Wait, the description says:
    # "alignmentTransform: A 4×4 matrix ... describing how the mesh is aligned in space."
    # If the mesh is already in "space", maybe this is Identity?
    
    # Let's look at existing polycam.py usage.
    # In polycam.py: 
    # alignment_transform = np.array(mesh_info["alignmentTransform"]).reshape((4,4)).T
    # ...
    # _transform_hloc_reconstruction(hloc_data, alignment_transform ...)
    
    # This implies that the 'alignmentTransform' is used to move the HLoc reconstruction (which is in the same space as the images/SFM)
    # to the "Aligned" space (where the mesh presumably lives or the user wants it to be).
    
    # So if we have:
    # Frame S (SFM/Images) -> This is where HLoc reconstructs.
    # Frame M (Mesh/raw.glb) -> This is the target geometry.
    # We computed T_s2m (Source to Target) via ICP.
    # So T_s2m * P_s = P_m.
    # So 'alignmentTransform' should be T_s2m.
    
    transform, mesh = align_point_cloud_to_mesh(source_pcd, mesh_path)
    
    fields = calculate_mesh_info_fields(mesh)
    
    # Flatten transform
    # JSON uses column-major or row-major?
    # usage in polycam.py: alignment_transform.reshape((4,4)).T
    # This suggests the JSON list is a flattened ROW-MAJOR matrix?
    # If it was Column-Major, reshape((4,4)) would produce columns as rows, so .T would fix it to standard.
    # If it was Row-Major, reshape((4,4)) produces standard matrix, so .T would transpose it.
    
    # Let's verify standard webgl usage. usually column-major.
    # If it is column-major: [m00, m10, m20, m30, m01 ...]
    # np.array(list).reshape((4,4)) fills row by row:
    # row 0 becomes [m00, m10, m20, m30] (which is the first column)
    # So the resulting matrix M has M_rows = Original_Cols.
    # So M is the Transpose of the standard matrix.
    # So M.T gives the standard matrix.
    # So the JSON is likely Column-Major flattened.
    
    transform_list = transform.flatten('F').tolist() # 'F' for column-major
    
    fields["alignmentTransform"] = transform_list
    
    out_path = polycam_dir / "mesh_info.json"
    with open(out_path, 'w') as f:
        json.dump(fields, f, indent=4)
    print(f"Written mesh_info.json to {out_path}")
    return True

def run_polycam2(polycam_data_directory, log_filepath=None, negate_y_mesh_align=True):
    polycam_dir = Path(polycam_data_directory)
    mesh_info_path = polycam_dir / "mesh_info.json"
    
    if not mesh_info_path.exists():
        print("mesh_info.json not found. Generating it from raw data...")
        files_ok = generate_mesh_info_json(polycam_dir)
        if not files_ok:
            print("Failed to generate mesh_info.json. Aborting.")
            return
            
    # Now run standard pipeline
    build_map_original = None
    try:
        from .polycam import build_map_from_polycam_output as build_map_ref
        build_map_original = build_map_ref
    except ImportError as e:
        print(f"Could not import polycam pipeline: {e}")
        print("Required modules (hloc, etc) might be missing in this environment.")
        print("Please run the standard polycam.py pipeline in the correct environment now that mesh_info.json exists.")
        return

    print("Running original Polycam pipeline...")
    build_map_original(polycam_data_directory, log_filepath, negate_y_mesh_align)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process Polycam data with missing mesh_info.json")
    parser.add_argument("--data_dir", required=True, help="Path to polycam_data directory")
    parser.add_argument("--log_file", default=None, help="Path to log file")
    
    args = parser.parse_args()
    
    run_polycam2(args.data_dir, args.log_file)
