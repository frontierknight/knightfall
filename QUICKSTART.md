# Knightfall — Quickstart (self-check the v1)

The range runs on **winbox's WSL2 Ubuntu 22.04** (ROS 2 Humble already installed). From your Mac:

## 1. Get onto the box
```bash
ssh winbox
wsl -d Ubuntu-22.04            # enter the Ubuntu env
source /opt/ros/humble/setup.bash
cd ~/knightfall
```
(Or run any command below in one shot from the Mac, e.g.
`ssh winbox 'wsl -d Ubuntu-22.04 -u root -- bash -lc "source /opt/ros/humble/setup.bash; cd ~/knightfall && python3 run.py list"'`)

## 2. See the challenges
```bash
python3 run.py list
```

## 3. Run a challenge (reference solver attacks it → score + trajectory)
```bash
python3 run.py run task01     # SROS2 diagnostic leak  -> success, 1.0/1.0
python3 run.py run task03     # localization spoofing  -> success, 2.5/2.5 (physical_impact!)
```
Each run prints the outcome + score and writes an **RL-ready trajectory** to
`trajectories/task0X_reference.jsonl` (meta → steps(action,observation,checkpoints,reward) → result).

## 4. Check the defenses (fix-oracles)
```bash
python3 run.py oracle         # both challenges: attack BLOCKED and mission STILL WORKS
```
Expect `ALL FIX-ORACLES PASS ✅`.

## What "v1 OK" means (what's already here)
- Evaluation core (`harness/`): trajectory logger + graded checkpoint judge + lifecycle runner.
- Two challenges covering the two core dimensions: **access control** (task01, SROS2) and
  **physical impact** (task03, the differentiator — a real robot driven off-target).
- **Graded 4-layer scoring** + **RL-ready trajectory logging** + **destroy-and-recreate reset**.
- **Fix-oracles** (defense blocks attack ∧ mission still works) — this is what makes it a benchmark.
- One CLI (`run.py`) for humans/agents alike.

## What's next (after you're happy with v1)
More challenges plug into the same harness (task02 maintenance-over-privilege, etc.) — that's
*content expansion*, not new machinery. Then: human baseline + agent adapter (Crimson Knight) +
batch leaderboard → the paper's experiments. See `DESIGN.md` §11 and `RESEARCH.md`.

## To update the box after code changes (from Mac)
```bash
cd ~/Desktop/Frontier-Knight-Labs/knightfall
tar czf - run.py harness challenges deliverable-01 | ssh winbox 'wsl -d Ubuntu-22.04 -u root -- bash -lc "tar xzf - -C ~/knightfall"'
```
