# spatial-server

An instance of a localization server. This server is maintained by a "Cartographer". The spatial-server provides support for the following functions:

- Map creation and storage. Maps can be downloaded from this server by content developers.
- Localization against stored maps.
- Registration with the server disocvery service.

This repository contains submodules. Clone the repo using:
```
git clone --recurse-submodules https://github.com/SagarB-97/spatial-server.git
```

## Install dependencies

### Docker-based installation (Recommended)

1. Install docker engine. For Ubuntu, use instructions [from here](https://docs.docker.com/engine/install/ubuntu/#install-using-the-repository).
2. Install nvidia-container-toolkit. For Ubuntu, use instructions [from here](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html#installing-with-apt).
3. Run `nvidia-smi --query-gpu=compute_cap --format=csv` to get the CUDA Architecture. Change the `CUDA_ARCHITECTURES` ARG in the Dockerfile (without the dot).
3. `cd spatial-server` and run `docker compose up`.


### Conda-based installation (OLD)

- Install COLMAP and ffmpeg. Make sure COLMAP can use your GPU.
- After cloning, `cd spatial-server` 
- Create and activate `conda` environment: 

    ```
    conda env create -f environment.yaml
    conda activate spatial-server
    ```
- Install the correct versions of torch, torch vision etc.: 
    ```
    pip uninstall torch torchvision functorch tinycudann
    pip install torch==2.0.1+cu118 torchvision==0.15.2+cu118 --extra-index-url https://download.pytorch.org/whl/cu118
    ```
- Install `cuda-toolkit`:
    ```
    conda install -c "nvidia/label/cuda-11.8.0" cuda-toolkit
    ```
- Install nerfstudio (only used for its `ns-process-data` command as it conveniently combines `ffmpeg` and `colmap` commands).
    ```
    pip install nerfstudio
    ```
- Install `hloc` requirements: 
    ```
    pip install -r third_party/hloc/requirements.txt
    ```


## Start the server
From the root of this repository, run:
```
flask --debug --app spatial_server/server run --host 0.0.0.0 --port 8001
```

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

SfM is inherently scale ambiguous. Maps created using images or video frames needs to to be explicitly scaled to match the real-world. So we need some real world measurements to scale it. In project, we provide a way to scale the SfM reconstruction using camera pose matrices collected from an a-frame spatial client. Use the scripts in `hloc_localization/scale_adjustment` to adjust scale of the reconstruction.

Commands:
```
python -m spatial_server.hloc_localization.scale_adjustment.get_scale <path_to_query_dir>
python -m spatial_server.hloc_localization.scale_adjustment.scale_existing_model --model_path <path_to_SfMReconstruction>
```

(TODO: Write detailed instructions)

# Aligning the point cloud

The point cloud generated is not necessarily aligned with the gravity axis and may be randomly rotated. This makes it difficult to use the map. Use the following commands to align the model using Manhattan-world alignment.

```
python -m spatial_server.hloc_localization.map_aligner --model_path <path_to_colmap_model> --images_path <path_to_images_dir>
```
