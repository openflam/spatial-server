# Commands

Some of the following commands are executed when the corresponding options are selected on the landing page. They are included here for convenience.

## Jupyter Notebook
To run jupyter lab inside the docker container: 
- Get the container ID by running `docker ps`.
- Attach the terminal to the container bu running: `docker exec -it <container_id> bash`.
- Once inside the container, run: `jupyter lab --allow-root --ip 0.0.0.0`.

## Aligning the point cloud

The point cloud generated is not necessarily aligned with the gravity axis and may be randomly rotated. This makes it difficult to use the map. Use the following commands to align the model using Manhattan-world alignment.

```
python3 -m spatial_server.hloc_localization.map_aligner --model_path <path_to_colmap_model> --images_path <path_to_images_dir>
```
## Map Cleaning

The point cloud created using the `map_creator` script generally has extraneous points. Use the script `map_cleaning` to automatically remove outliers and align the maps ground. It also saves the model as PCD file.

```
python3 spatial_server/hloc_localization/map_cleaning.py <path_to_colmap_model>
```

## Map transforms and conversion to PCD

Use the `spatial_server.hloc_localization.map_creation.map_transforms` script to rotate, elevate and save map as a .pcd.

To rotate a map (elevate and save pcd is run automatically):
```
python3 -m spatial_server.hloc_localization.map_creation.map_transforms --rotation x180 --model_path <path_to_colmap_directory>
```

The format of argument to `--rotation` is: \[x/y/z\]\[degrees to rotate\].

To elevate the map 
```
python3 -m spatial_server.hloc_localization.map_creation.map_transforms --elevate --model_path <path_to_colmap_directory>
``` 

To create PCD: 
```
python3 -m spatial_server.hloc_localization.map_creation.map_transforms --create_pcd --model_path <path_to_colmap_directory>
```