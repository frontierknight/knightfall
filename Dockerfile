# Knightfall — self-contained ROS 2 security CTF range in one image.
# Bundles ROS 2 Humble + SROS2 + the range code, so anyone runs it with one command,
# reproducibly, on any machine — no ROS 2 setup, no Gazebo. This is what makes it a
# shareable, citable benchmark.
#
#   docker build -t knightfall .
#   docker run --rm knightfall list
#   docker run --rm knightfall selftest all
#   docker run --rm -it knightfall play task01     # play it yourself
#   docker run --rm knightfall oracle              # check the defenses
FROM ros:humble-ros-base

SHELL ["/bin/bash", "-c"]
RUN apt-get update && apt-get install -y --no-install-recommends \
      ros-humble-sros2 ros-humble-demo-nodes-cpp python3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /knightfall
COPY . /knightfall
RUN chmod +x /knightfall/deliverable-01/run_acceptance.sh /knightfall/docker-entrypoint.sh 2>/dev/null || true

ENTRYPOINT ["/knightfall/docker-entrypoint.sh"]
CMD ["list"]
