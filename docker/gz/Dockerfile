# Knightfall Gazebo tier — the single simulation tier (CORE.md §3).
# ROS 2 Jazzy + Gazebo Harmonic (vendored via ros_gz) + Nav2 + the TurtleBot3 sim world.
# Runs headless: sensors render in software (Mesa llvmpipe) under Xvfb, no GPU needed.
#
#   docker build -f docker/gz/Dockerfile -t knightfall-gz .
#   docker run --rm knightfall-gz                    # headless smoke: sim + lidar + Nav2 + ground truth
#
# CI builds this image and publishes it to ghcr.io/frontierknight/knightfall-gz, so environments that
# cannot reach packages.ros.org pull the prebuilt image instead of building it.
ARG BASE=ros:jazzy-ros-base
FROM ${BASE}

SHELL ["/bin/bash", "-c"]
RUN apt-get update && apt-get install -y --no-install-recommends \
      ros-jazzy-ros-gz \
      ros-jazzy-navigation2 \
      ros-jazzy-nav2-bringup \
      ros-jazzy-nav2-minimal-tb3-sim \
      ros-jazzy-nav2-simple-commander \
      ros-jazzy-sros2 \
      xvfb xauth libgl1-mesa-dri libegl-mesa0 \
    && rm -rf /var/lib/apt/lists/*

# Provenance: every trajectory records what produced it.
ARG KNIGHTFALL_GIT_SHA=unknown
ENV KNIGHTFALL_GIT_SHA=${KNIGHTFALL_GIT_SHA}
LABEL org.opencontainers.image.source="https://github.com/frontierknight/knightfall"
LABEL org.opencontainers.image.description="Knightfall Gazebo tier: ROS 2 Jazzy + Gazebo Harmonic + Nav2 + TurtleBot3"

WORKDIR /knightfall
COPY . /knightfall

CMD ["bash", "tools/gz/smoke.sh"]
