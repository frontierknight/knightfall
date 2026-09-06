"""Physical-task feasibility spike — does the propagation chain hold?

Novelty claim to de-risk: *controlling a localization input makes the robot physically deviate.*
This is the core of Knightfall's headline (task 03, localization spoofing) and the thing no
software CTF benchmark has.

Here we prove the CHAIN deterministically, in pure Python (no ROS/Gazebo needed), so the logic is
validated before wrapping it in ROS 2 topics on the box:

  robot drives to a goal using its PERCEIVED pose (go-to-goal P-controller).
  perceived_pose = true_pose + spoof_offset       (attacker controls spoof_offset)
  we integrate the TRUE pose (ground truth) and measure the real outcome.

If spoof_offset = 0 → robot reaches the goal.
If the attacker injects an offset → the robot, believing a false position, drives its TRUE self
off-target / into a no-go zone. That deviation, measured against ground truth, is the physical
checkpoint.
"""
from __future__ import annotations
import math

DT = 0.05           # fixed timestep (deterministic)
STEPS = 600         # 30 s
V_MAX = 0.5
W_MAX = 1.5


def simulate(goal, spoof_offset=(0.0, 0.0), no_go=None):
    """Return (reached, min_dist_to_goal, entered_no_go, true_path)."""
    tx, ty, th = 0.0, 0.0, 0.0          # TRUE pose (ground truth)
    gx, gy = goal
    reached = False
    entered_no_go = False
    min_d = float("inf")
    path = []
    for _ in range(STEPS):
        # what the robot THINKS its pose is (attacker spoofs the localization input)
        px, py = tx + spoof_offset[0], ty + spoof_offset[1]
        # go-to-goal P-controller using PERCEIVED pose
        dx, dy = gx - px, gy - py
        dist_perceived = math.hypot(dx, dy)
        heading = math.atan2(dy, dx)
        err = math.atan2(math.sin(heading - th), math.cos(heading - th))
        w = max(-W_MAX, min(W_MAX, 2.0 * err))
        v = 0.0 if abs(err) > 0.6 else min(V_MAX, dist_perceived)
        # integrate TRUE pose with the issued command
        th += w * DT
        tx += v * math.cos(th) * DT
        ty += v * math.sin(th) * DT
        path.append((round(tx, 3), round(ty, 3)))
        true_d = math.hypot(gx - tx, gy - ty)
        min_d = min(min_d, true_d)
        if true_d < 0.15:
            reached = True
        if no_go and (no_go["xmin"] <= tx <= no_go["xmax"] and no_go["ymin"] <= ty <= no_go["ymax"]):
            entered_no_go = True
    return reached, round(min_d, 3), entered_no_go, path


if __name__ == "__main__":
    GOAL = (3.0, 0.0)                       # deliver to station at (3,0)
    NO_GO = {"xmin": 1.0, "xmax": 2.0, "ymin": 1.0, "ymax": 2.5}   # forbidden zone

    print("== Case A: no spoof (legit) ==")
    reached, mind, nogo, _ = simulate(GOAL)
    print(f"  reached goal: {reached} | closest true dist: {mind} m | entered no-go: {nogo}")

    print("== Case B: attacker spoofs localization by (0,+2.0) ==")
    reached2, mind2, nogo2, path2 = simulate(GOAL, spoof_offset=(0.0, 2.0), no_go=NO_GO)
    # robot thinks it's 2m north of truth -> to 'reach' goal it drives its TRUE self 2m south of goal
    final = path2[-1]
    print(f"  reached goal: {reached2} | closest true dist: {mind2} m | entered no-go: {nogo2}")
    print(f"  TRUE final pose: {final} (goal was {GOAL}) -> deviation {round(math.hypot(GOAL[0]-final[0], GOAL[1]-final[1]),3)} m")

    print("\n== PROPAGATION CHAIN ==")
    if reached and not reached2:
        print("PROVEN ✅ spoofing the localization input drives the TRUE robot off-target.")
        print("  physical checkpoint = TRUE deviation > threshold (bounded, measurable, jitter-free).")
    else:
        print("NOT proven — revisit controller/model.")
