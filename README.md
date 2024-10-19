# spatial-server

An instance of a localization server. This server is maintained by a "Cartographer". The spatial-server provides support for the following functions:

- Map creation and storage. Maps can be downloaded from this server by content developers.
- Localization against stored maps.
- Registration with the server disocvery service.

This repository contains submodules. Clone the repo using:
```
git clone --recurse-submodules https://github.com/SagarB-97/spatial-server.git
```

# Install dependencies and run server

## Docker-based installation

1. Install docker engine. For Ubuntu, use instructions [from here](https://docs.docker.com/engine/install/ubuntu/#install-using-the-repository).
2. Install nvidia-container-toolkit. For Ubuntu, use instructions [from here](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html#installing-with-apt).
3. Run `nvidia-smi --query-gpu=compute_cap --format=csv` to get the CUDA Architecture. Change the `CUDA_ARCHITECTURES` ARG in the Dockerfile (without the dot).
3. `cd spatial-server`

## Running the server
Run `docker compose up --detach`. To print logs, run `docker compose logs`. To shutdown, `docker compose down`.

- If behind proxy, set the environment variable `BEHIND_PROXY` to `true`: `BEHIND_PROXY=true docker compose up --detach`.
- HTTPS is on by default. To turn off HTTPS, set the environment variable `HTTPS` to `false`: `HTTPS=false docker compose up --detach`.

**Note**: If you're making code changes, to ensure that the code changes are reflected in the docker, run: `docker compose up --detach --force-recreate --renew-anon-volumes`.

To run jupyter lab inside the docker container: 
- Get the container ID by running `docker ps`.
- Attach the terminal to the container bu running: `docker exec -it <container_id> bash`.
- Once inside the container, run: `jupyter lab --allow-root --ip 0.0.0.0`.

# Map creation, registration and localization

- **Map creation** (URL prefix: `/create_map`)
    - GET request to `/create_map/` renders a form that can be used to upload materials required for map creation. 
    - POST request to `create_map/video` (with the video file) starts the map creation process. Currently, we only support map creation from videos using hloc.

- **Registration** (URL prefix: `/register_with_discovery`)
    - GET request to `/register_with_discovery` renders a form to enter information about the URLs to be registered.
    - POST request to `/register_with_discovery` requests the server discovery service to update its database.

- **Download** (URL prefix: `/download_map`)
    - GET request to `/download_map/` renders a form to assist with download.
    - GET request to `/download_map/<map_name>` downloads the specified map.

- **Localization** (URL prefix: `/localize`)
    - POST request to `/localize/image/<map_name>` returns the pose corresponding to POSTed image against the map specified in `map_name`.

# Scaling SfM model

SfM is inherently scale ambiguous. Maps created using images or video frames needs to to be explicitly scaled to match the real-world. So we need some real world measurements to scale it. In project, we provide a way to scale the SfM reconstruction using camera pose matrices collected from an a-frame spatial client. 

## Application to collect images with pose

We have built an aframe-based application that can send camera images along with the camera pose to the server. On a phone browser, open `/save_image_pose` page and then select the map for which images along with the WebXR pose is to be collected. Click on "Collect Image" button. You will then be redirected to an application that can capture images and send them to the server.

Use the scripts in `hloc_localization/scale_adjustment` to adjust scale of the reconstruction.

Commands:
```
python -m spatial_server.hloc_localization.scale_adjustment.get_scale <path_to_query_dir> <dataset_name>
python -m spatial_server.hloc_localization.scale_adjustment.scale_existing_model --model_path <path_to_SfMReconstruction>
```

(TODO: Write detailed instructions)

# Aligning the point cloud

The point cloud generated is not necessarily aligned with the gravity axis and may be randomly rotated. This makes it difficult to use the map. Use the following commands to align the model using Manhattan-world alignment.

```
python -m spatial_server.hloc_localization.map_aligner --model_path <path_to_colmap_model> --images_path <path_to_images_dir>
```
# Map Cleaning

The point cloud created using the `map_creator` script generally has extraneous points. Use the script `map_cleaning` to automatically remove outliers and align the maps ground. It also saves the model as PCD file.

```
python spatial_server/hloc_localization/map_cleaning.py <path_to_colmap_model>
```

# Map transforms and conversion to PCD

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
