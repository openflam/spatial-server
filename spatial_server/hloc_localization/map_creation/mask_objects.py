import argparse
import os
from pathlib import Path

from ultralytics import YOLO
import numpy as np
import cv2
import pycolmap
import h5py

from ..scale_adjustment import read_write_model


# COCO class IDs to be extracted
TARGET_CLASS_IDS = [0, 1, 2, 3, 5, 7, 14, 15, 16, 24, 25, 26, 28, 36, 39, 40, 41, 42, 43, 44, 45, 56, 63, 64, 65, 66, 67]

# Get relevant masks from segmentation model prediction
# Returns mask (tuple of (class id, mask)) and union_mask (combined mask)
def extract_masks(results, target_class_ids=TARGET_CLASS_IDS):
    masks = []
    union_mask = 0
    for res in results:
        if hasattr(res, 'masks'):
            for i, cls in enumerate(res.boxes.cls):
                if int(cls) in target_class_ids:
                    mask = res.masks.data[i].cpu().numpy()
                    masks.append((int(cls), mask))

                    # Bitwise OR operation to get the union of all masks so far
                    union_mask = np.bitwise_or(union_mask, mask.astype(np.uint8))
    return masks, union_mask


def remove_masked_keypoints(model_path, features_path, image_dir):
    seg_model = YOLO('yolov8x-seg.pt')
    cameras, images, points3D = read_write_model.read_model(model_path)

    with h5py.File(features_path, 'r+') as f:
        for image_id, image in images.items():
            image_name = image.name
            image_path = os.path.join(image_dir, image_name)

            img = cv2.imread(image_path)
            height, width = np.shape(img)[:2]

            seg_result = seg_model.predict(source=image_path, conf=0.40)
            masks, union_mask = extract_masks(seg_result)
            if len(masks) == 0: continue

            resized_mask = cv2.resize(union_mask, (width, height), interpolation=cv2.INTER_NEAREST)

            if image_name in f:
                grp = f[image_name]
                keypoints = grp['keypoints'][:]
                descriptors = grp['descriptors'][:]
                scores = grp['scores'][:]

                # Filter out masked keypoints
                valid_keypoints = []
                valid_descriptors = []
                valid_scores = []
                for i, (x, y) in enumerate(keypoints):
                    if not (0 <= x < width and 0 <= y < height and resized_mask[int(np.round(y)), int(np.round(x))]):
                        valid_keypoints.append([x, y])
                        valid_descriptors.append(descriptors[:, i])
                        valid_scores.append(scores[i])

                valid_keypoints = np.array(valid_keypoints)
                valid_descriptors = np.array(valid_descriptors).T
                valid_scores = np.array(valid_scores)

                # Update the .h5 file
                del grp['keypoints']
                del grp['descriptors']
                del grp['scores']
                grp.create_dataset('keypoints', data=valid_keypoints)
                grp.create_dataset('descriptors', data=valid_descriptors)
                grp.create_dataset('scores', data=valid_scores)


# Find and remove masked 3D points from the reconstruction
def remove_masked_points3d(model_path, image_dir, output_path=None):
    seg_model = YOLO('yolov8x-seg.pt')
    cameras, images, points3D = read_write_model.read_model(model_path)

    point3D_ids_to_mask = set()

    # Iterate though all images in the reconstruction
    for image_id, image in images.items():
        image_path = os.path.join(image_dir, image.name)
        img = cv2.imread(image_path)
        (height, width) = np.shape(img)[:2]

        # Get mask using YOLO segmentation
        seg_result = seg_model.predict(source=image_path, conf=0.40)
        masks, union_mask = extract_masks(seg_result)
        if len(masks) == 0: continue # skip to next iteration if no masks found

        resized_mask = cv2.resize(union_mask, (width, height), interpolation=cv2.INTER_NEAREST)

        # Find 3D points that correspond to 2D points behind mask
        for point2D_idx, (x, y) in enumerate(image.xys):
            if 0 <= x < (width - 1) and 0 <= y < (height - 1) and resized_mask[int(np.round(y)), int(np.round(x))]:
                point3D_id = image.point3D_ids[point2D_idx]
                if point3D_id != -1:
                    point3D_ids_to_mask.add(point3D_id)
    
    point3D_ids_to_mask = list(point3D_ids_to_mask)

    # Delete 3D points from the reconstruction and all 2D correspondences in images
    reconstruction = pycolmap.Reconstruction(model_path)
    for id in point3D_ids_to_mask:
        reconstruction.delete_point3D(id)

    if output_path is None:
        output_path = model_path
    if not os.path.exists(output_path):
        os.mkdir(output_path)
    reconstruction.write(output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Remove 3D points in the map corresponding to masked (frequently moving) objects.')
    parser.add_argument("--model_path", type=str, help='The path to the COLMAP model file')
    parser.add_argument('--image_dir', type=str, help='The path to the image directory')
    parser.add_argument('--output_path', type=str, help='The path to the output destination', default=None)
    args = parser.parse_args()
    remove_masked_points3d(args.model_path, args.image_dir, args.output_path)
    