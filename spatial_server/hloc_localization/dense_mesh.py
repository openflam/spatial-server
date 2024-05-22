"""
Uses colmap to create a dense mesh from a sparse point cloud.
"""
import argparse
import os
from pathlib import Path

def create_dense_mesh(images_path, sparse_sfm_path, output_path):
    print("Image undistortion using COLMAP..")
    os.system((
        f'colmap image_undistorter '
        f'--image_path {images_path} '
        f'--input_path {sparse_sfm_path} '
        f'--output_path {output_path} '
        f'--output_type COLMAP '
        f'--max_image_size 2000'
    ))

    print("Patch match stereo..")
    os.system((
        f'colmap patch_match_stereo '
        f'--workspace_path {output_path} '
        f'--workspace_format COLMAP '
        f'--PatchMatchStereo.geom_consistency true'
    ))

    print("Stereo fusion..")
    os.system((
        f'colmap stereo_fusion '
        f'--workspace_path {output_path} '
        f'--workspace_format COLMAP '
        f'--input_type geometric '
        f'--output_path {output_path}/fused.ply'
    ))

    print("Poisson mesher..")
    os.system((
        f'colmap poisson_mesher '
        f'--input_path {output_path}/fused.ply '
        f'--output_path {output_path}/meshed-poisson.ply'
    ))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--images_path', type=str, required=True)
    parser.add_argument('--sparse_sfm_path', type=str, required=True)
    parser.add_argument('--output_path', type=str, required=False, default=None)
    args = parser.parse_args()

    output_path = args.output_path
    if output_path is None:
        output_path = Path(args.sparse_sfm_path).parent / 'dense'
    create_dense_mesh(args.images_path, args.sparse_sfm_path, output_path)
