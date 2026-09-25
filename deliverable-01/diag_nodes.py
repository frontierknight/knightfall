#!/usr/bin/env python3
"""Minimal talker / listener for the SROS2 acceptance test (replaces demo_nodes_cpp).

Only needs rclpy + std_msgs, both shipped in ros-humble-ros-base, so the task01 fix-oracle
runs anywhere the range image runs. Mirrors demo_nodes_cpp's behavior closely enough for
run_acceptance.sh: default topic `chatter` (remap it with `-r chatter:=<topic>`), node
name overridable with `-r __node:=<name>`, and the listener prints "I heard: [...]".

Usage:  python3 diag_nodes.py talker   --ros-args --enclave /diag_publisher -r __node:=diag_publisher -r chatter:=diagnostics
        python3 diag_nodes.py listener --ros-args --enclave /maintenance_listener -r __node:=maintenance_listener -r chatter:=diagnostics
"""
import sys

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import String


class Talker(Node):
    def __init__(self):
        super().__init__("talker")
        self._pub = self.create_publisher(String, "chatter", 10)
        self._n = 0
        self.create_timer(1.0, self._tick)

    def _tick(self):
        self._n += 1
        msg = String(data=f"Hello World: {self._n}")
        self._pub.publish(msg)
        print(f"Publishing: '{msg.data}'", flush=True)


class Listener(Node):
    def __init__(self):
        super().__init__("listener")
        self.create_subscription(String, "chatter", self._cb, 10)

    def _cb(self, msg):
        print(f"I heard: [{msg.data}]", flush=True)


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("talker", "listener"):
        print(__doc__)
        return 2
    rclpy.init(args=sys.argv)
    node = Talker() if sys.argv[1] == "talker" else Listener()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass  # SIGINT / SIGTERM from the acceptance script is the normal way to stop
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
