# Build and install COLMAP as a multi-stage docker build. In the final stage, the python dependencies are installed.

# Build COLMAP. From https://github.com/colmap/colmap/blob/main/docker/Dockerfile.
# The python dependecies use CUDA 11.8. The latest Colmap image from docker.io uses CUDA 12.3 and breaks dependencies.
ARG UBUNTU_VERSION=22.04
ARG NVIDIA_CUDA_VERSION=11.8.0

FROM nvidia/cuda:${NVIDIA_CUDA_VERSION}-devel-ubuntu${UBUNTU_VERSION} as builder

ARG COLMAP_GIT_COMMIT=main
ARG CUDA_ARCHITECTURES=89
ENV QT_XCB_GL_INTEGRATION=xcb_egl

# Prevent stop building ubuntu at time zone selection.
ENV DEBIAN_FRONTEND=noninteractive

# Prepare and empty machine for building.
RUN apt-get update && \
    apt-get install -y --no-install-recommends --no-install-suggests \
    git \
    cmake \
    ninja-build \
    build-essential \
    libboost-program-options-dev \
    libboost-filesystem-dev \
    libboost-graph-dev \
    libboost-system-dev \
    libeigen3-dev \
    libflann-dev \
    libfreeimage-dev \
    libmetis-dev \
    libgoogle-glog-dev \
    libgtest-dev \
    libsqlite3-dev \
    libglew-dev \
    qtbase5-dev \
    libqt5opengl5-dev \
    libcgal-dev \
    libceres-dev

# Build and install COLMAP.
RUN git clone https://github.com/colmap/colmap.git
RUN cd colmap && \
    git fetch https://github.com/colmap/colmap.git ${COLMAP_GIT_COMMIT} && \
    git checkout FETCH_HEAD && \
    mkdir build && \
    cd build && \
    cmake .. -GNinja -DCMAKE_CUDA_ARCHITECTURES=${CUDA_ARCHITECTURES} \
    -DCMAKE_INSTALL_PREFIX=/colmap_installed && \
    ninja install

#
# Docker runtime stage.
#
FROM nvidia/cuda:${NVIDIA_CUDA_VERSION}-runtime-ubuntu${UBUNTU_VERSION} as runtime

# Minimal dependencies to run COLMAP binary compiled in the builder stage.
# Note: this reduces the size of the final image considerably, since all the
# build dependencies are not needed.
RUN apt-get update && \
    apt-get install -y --no-install-recommends --no-install-suggests \
    libboost-filesystem1.74.0 \
    libboost-program-options1.74.0 \
    libc6 \
    libceres2 \
    libfreeimage3 \
    libgcc-s1 \
    libgl1 \
    libglew2.2 \
    libgoogle-glog0v5 \
    libqt5core5a \
    libqt5gui5 \
    libqt5widgets5

# Copy all files from /colmap_installed/ in the builder stage to /usr/local/ in
# the runtime stage. This simulates installing COLMAP in the default location
# (/usr/local/), which simplifies environment variables. It also allows the user
# of this Docker image to use it as a base image for compiling against COLMAP as
# a library. For instance, CMake will be able to find COLMAP easily with the
# command: find_package(COLMAP REQUIRED).
COPY --from=builder /colmap_installed/ /usr/local/

# Set working directory
WORKDIR /code

# Install ffmpeg
RUN apt install -y ffmpeg

# Install python, pip, git
RUN apt install -y python3 python3-pip git
RUN python3 -m pip install --upgrade pip

# Install python dependencies
RUN pip install flask flask-cors ffmpeg-python
RUN pip install torch==2.0.1+cu118 torchvision==0.15.2+cu118 --extra-index-url https://download.pytorch.org/whl/cu118
RUN pip install nerfstudio

RUN mkdir /dependencies
COPY ./third_party/hloc/requirements.txt /dependencies/requirements.txt
RUN pip install -r /dependencies/requirements.txt

# Uninstall numpy 2.0 and install numpy 1.26.4 as cv2 is not compatible with numpy 2.0
RUN pip uninstall numpy -y
RUN pip install numpy==1.26.4

# Install unzip
RUN apt install unzip -y

# Generate self-signed certificate
RUN mkdir /ssl
RUN openssl req -new -newkey rsa:4096 -days 365 -nodes -x509 \
    -subj "/C=US/ST=Pennsylvania/L=Pittsburgh/O=Sagar/CN=Sagar" \
    -keyout /ssl/key.pem  -out /ssl/cert.pem
