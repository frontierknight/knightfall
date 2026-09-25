# Reproducing Knightfall

Everything below runs from the range image; no ROS 2 install on the host is needed. This is the
artifact-evaluation path: one image, one command per claim.

## Build the image

```bash
git clone https://github.com/frontierknight/knightfall && cd knightfall
docker build -t knightfall .
```

In a network that blocks `packages.ros.org` (e.g. some CI/cloud egress), build with the helper,
which pulls the ROS base from a mirror and skips the blocked apt step (everything the range needs
ships in `ros-base`):

```bash
bash tools/cloud/docker-setup.sh
```

## Claims and the command that checks each

| Claim | Command | Expected |
|---|---|---|
| Challenges are solvable | `docker run --rm knightfall selftest all` | task01 1.0/1.0, task02 1.9/1.9, task03 2.5/2.5 |
| Defenses work and keep the mission | `docker run --rm knightfall oracle` | ALL FIX-ORACLES PASS |
| The range discriminates | `docker run --rm knightfall batch` | null 0 · random 0 · scripted pass, all tasks |
| The physical sim is deterministic | `docker run --rm knightfall measure 8` | deviation 2.0 m every run, sd 0.0 |
| Harness logic (no ROS) | `docker run --rm --entrypoint bash knightfall -lc "source /opt/ros/humble/setup.bash && python3 harness/test_session.py && python3 harness/validate_scenarios.py"` | all OK |

CI (`.github/workflows/ci.yml`) runs the same checks on every push, so `main` is always in a
reproducible state.

## Provenance

Every run writes a trajectory to `trajectories/` whose `meta` line records `git_sha`,
`image_digest`, `scenario_hash`, `seed` and the ROS distro (`harness/provenance.py`). Two runs of
the same image on the same scenario carry the same provenance, so a result can be traced to exactly
what produced it. The image bakes its source revision via the `KNIGHTFALL_GIT_SHA` build arg.

## Running an AI agent (needs a model key)

The agent adapter (`harness/agent_actor.py`) drives the same `Session` a human uses, from a
`policy(observation, context) -> action` callable. The model call and its API key live inside that
callable, which the caller builds **outside** the solving terminal (DESIGN §8) — the range never
sees the key. A keyless scripted policy is included and tested; a real LLM policy is a few lines in
the caller (sketch in the module docstring). Provide the key through environment secrets, not the
repo.

## Version record

Pinned in each scenario's `env` block and in the trajectory `meta`: ROS 2 Humble,
`rmw_fastrtps_cpp`, Fast DDS discovery server across containers (see DESIGN §13.4). The base image
is `ros:humble-ros-base`; pin it by digest for a citable artifact.
