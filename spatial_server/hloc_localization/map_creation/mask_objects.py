import argparse
import os
from pathlib import Path

from ultralytics import YOLO
import numpy as np
import cv2

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


# Find and remove masked 3D points from the reconstruction
def remove_masked_points3d(model_path, output_path=None):
    model_path = Path(model_path)
    cameras, images, points3D = read_write_model.read_model(model_path)

    seg_model = YOLO('yolov8x-seg.pt')  

    point3D_ids_to_mask = set()

    # Iterate though all images in the reconstruction
    for image_id, image in images.items():
        image_path = os.path.join(os.path.dirname(os.path.dirname(model_path)), 'ns_data', 'images', image.name)
        img = cv2.imread(image_path)
        (height, width) = np.shape(img)[:2]

        # Get mask using YOLO segmentation
        seg_result = seg_model.predict(source=image_path, conf=0.40)
        masks, union_mask = extract_masks(seg_result)
        if len(masks) == 0: continue # skip to next iteration if no masks found

        resized_mask = cv2.resize(union_mask, (width, height), interpolation=cv2.INTER_NEAREST)

        # Find 3D points that correspond to 2D points behind mask
        for point2D_idx, (x, y) in enumerate(image.xys):
            if resized_mask[int(np.round(y)), int(np.round(x))]:
                point3D_id = image.point3D_ids[point2D_idx]
                if point3D_id != -1:
                    point3D_ids_to_mask.add(point3D_id)
    
    point3D_ids_to_mask = list(point3D_ids_to_mask)

    # Create new Points3D excluding masked points
    new_points3D = {}
    for id, point in points3D.items():
        if id not in point3D_ids_to_mask: 
            new_points3D[id] = point

    if output_path is None:
        output_path = model_path
    if not output_path.exists():
        output_path.mkdir(parents=True)
    read_write_model.write_model(cameras, images, new_points3D, output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Remove 3D points in the map corresponding to masked (frequently moving) objects.')
    parser.add_argument("--model_path", type=str, help='The path to the COLMAP model file.')
    parser.add_argument('--output_path', type=str, help='The path to the output destination', default=None)
    args = parser.parse_args()
    remove_masked_points3d(args.model_path, args.output_path)
    