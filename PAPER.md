# Knightfall: a reproducible ROS 2 robot-security range that scores humans and AI agents alike

> Working draft. This assembles the implemented system into a submittable structure. Sections
> marked _[pending]_ need experimental runs that are not yet done (real LLM agents need a model key;
> a human cohort needs recruiting — see `docs/HUMAN_BASELINE.md`). No results are invented here.

## Abstract _(draft)_

Security benchmarks for AI agents target software capture-the-flag; embodied robots, where an attack
can move a machine and not just read a flag, have no standardized, reproducible, auto-scored range.
Knightfall is that range for ROS 2. One warehouse delivery robot exposes a different security flaw
under each of a set of switchable scenarios; a single console scores humans and agents identically
and logs every run as a trajectory. Scoring is graded across four layers — interface, acceptance,
mission, physical — with the physical layer (perceived pose vs. ground truth) absent from software
CTF benchmarks. Each challenge ships a fix-oracle proving its defense blocks the attack while the
normal mission still completes, which makes the range a benchmark of defenses, not only of attacks.
Ground truth is held off the attacker's DDS graph, checkpoints are confirmed from events the
simulator records rather than from the attacker's commands, budgets are enforced, and every result
records its provenance, so scores are comparable and reproducible from a single container image.

## 1. Introduction

- The gap: embodied-AI security is surveyed but under-benchmarked; a standardized, reproducible
  environment for sensor-spoofing-class attacks is called out as missing (RESEARCH.md §B).
- The claim: Knightfall is the first standardized, reproducible, auto-scored ROS 2 robot-security
  range that is simultaneously a human CTF and an agent benchmark, with a physical-impact scoring
  layer and per-challenge fix-oracles (RESEARCH.md §C).
- Contributions: (1) a shared-robot, scenario-driven range with a roles-first permission model and
  DDS/SROS2-grounded flaws; (2) four-layer graded scoring that extends checkpoint-style partial
  credit to embodied impact, with ground-truth isolation; (3) fix-oracles per challenge; (4) a
  reproducible harness that logs RL-ready trajectories and scores humans and agents through one
  console.

## 2. Related work

From RESEARCH.md §A/§B/§F (cite there):
- Agent-CTF benchmarks and cyber ranges: NYU CTF Bench, Cybench (subtask/graded scoring),
  InterCode-CTF (Docker-isolated instances), DeepRed (checkpoint partial credit + execution traces),
  cyber-range reference architectures (segment isolation, reset-to-known-state).
- Robot/embodied security: RCTF (the prior robotics CTF, now archived and never graded/agent-scored),
  SROS2/DDS-Security weaknesses, the ROS 2 threat model, RIPA, embodied-AI security surveys.
- Range delivery: GRFICSv3 (containerized cyber-physical lab with a visualized process), CTFd-whale
  (per-player instances, dynamic flags), CybORG/CAGE (agent-first API, multi-episode evaluation).
- Positioning: GRFICS-style containerized delivery × RCTF's domain × CybORG-style agent evaluation,
  plus a physical-impact checkpoint and fix-oracles.

## 3. The range

### 3.1 Target and roles
One warehouse delivery robot; a roles-first permission model (dispatch, navigation/control,
sensors/localization, maintenance, external) written down before any flaw (DESIGN §3). Each scenario
names exactly which permission is misconfigured.

### 3.2 Three zones, isolated by network
Attack / target / judge zones (DESIGN §4). In v2 each zone is a container on its own Docker network;
the player shares no network with the judge, and ground truth is exported to the judge off the DDS
graph (DESIGN §13, §14 D2). E1 verified cross-container DDS discovery via a Fast DDS discovery server
and confirmed the player cannot reach the judge or the internet, with positive/negative controls
(`compose/e1_check.sh`).

### 3.3 Scenario spec
A single YAML per challenge is the source of truth (DESIGN §14 D4), validated in CI
(`harness/validate_scenarios.py`): attacker start, flaw mechanism and intended permission, budget,
layered scoring, fix-oracle, reset scope, readiness checks, and a pinned environment record.

## 4. Scoring

### 4.1 Four graded layers
interface_op → target_accept → mission_impact → physical_impact (DESIGN §6). The agent view is the
weighted sum (graded ratio); the human view is a binary pass on the scenario's final-condition layer.
Graded signal keeps later RL from being starved by sparse rewards.

### 4.2 Ground truth and event-based confirmation
Checkpoints are confirmed only from events the simulator/robot record and latch — a message on an
input with no legitimate publisher, the perceived-vs-true pose gap, the settled distance from the
goal — never from the attacker's command text (DESIGN §14 D2/D3). The judge's ground truth is on a
channel the attacker cannot see or forge.

### 4.3 Budget and provenance
The console enforces a step and wall-clock budget and excludes judge-side time from the player's
clock; every trajectory records git SHA, image digest, scenario hash and seed (DESIGN §14 D5).

## 5. Fix-oracles
Each challenge ships a corrective config; the oracle proves both that the same attack path now fails
and that the legitimate mission still completes (`harness/fix_oracle.py`, `challenges/oracles.py`).
This measures defense, not only attack.

## 5b. Threat-model mapping
Each challenge maps to a ROS 2 threat-model element, a MITRE technique, the CIA property it
violates, and the DDS/SROS2 mechanism its fix-oracle closes — see `docs/THREAT_MODEL.md`. The set
covers access control on the DDS graph (01–02) and integrity of the sensing→action chain (03).

## 6. Challenges (first three)
| # | Player role | Flaw class | Final condition |
|---|---|---|---|
| 01 diagnostic leak | network participant, no creds | access control (SROS2) on diagnostic data | interface_op (flag) |
| 02 maintenance over-privilege | maintenance identity | authorization: a role granted a permission it should not hold | mission_impact |
| 03 localization spoofing | controls a localization source | data integrity → physical motion | physical_impact |

Each is solvable (a scripted reference solver passes) and defended (its fix-oracle passes), enforced
in CI.

## 7. Reproducibility and evaluation harness
- One image; one command per claim (`REPRODUCE.md`), gated in CI (`.github/workflows/ci.yml`):
  build, `selftest all`, `oracle`, benchmark-discrimination sanity, cross-container isolation.
- Baselines via `run.py batch`: null and random score 0 on every challenge; the scripted reference
  passes — the range discriminates. Swept across seeds 0–2 (per-round variants), the result holds
  on every seed (null/random 0/3, scripted 3/3): see `results/baselines.md`.
- The physical sim is deterministic: task03's settled deviation was 2.0 m across repeated runs
  (sd 0.0), 1.0 m above threshold (`run.py measure`, DESIGN §14; audit M7).
- Human and agent runs share the console, budget and scoring; the human-baseline protocol is in
  `docs/HUMAN_BASELINE.md`.

## 8. Experiments _[pending]_
- Agent evaluation across models through the adapter (`harness/agent_actor.py`); needs a model key.
  Report graded ratio, pass rate, checkpoint reached, and step/time cost per challenge, over multiple
  randomized episodes, against null/random/scripted baselines.
- Human cohort on the same challenges (n ≥ 8), reported beside the agent condition.
- All rows carry provenance (image digest, scenario hash, seed) for reproducibility.
- The keyless baseline rows are already produced and committed (`results/baselines.md`); agent rows
  drop into the same table through `harness/agent_actor.py` once a model key is provided.

## 9. Limitations and threats to validity
- v1 single-container results are a machinery demo, not benchmark data, until challenges run on the
  hardened multi-container topology (DESIGN §14 D6; audit B2).
- Task02 models identity as a policy-governed role; cryptographic-identity enforcement (SROS2) is
  task01's domain and a future task02 variant.
- Seeded per-round randomization exists (task02 varies which command the misconfig grants;
  `challenges/variants.py`, held-out seeds >= 1000 kept out of the repo) and extends to the other
  challenges as future work; reference solutions for the public seeds are in-repo by design.
- Small challenge set (three); the contribution is the methodology and the physical-impact layer, not
  breadth.

## 10. Ethics and responsible use
Fully simulated and isolated; scenarios model misconfigurations for education and benchmarking. Runs
only within the range; not to be pointed at real robotic deployments (README).

## Appendix: mapping to the artifact
Every section above points to the file that implements it. A reviewer can rebuild the image and
reproduce §7's claims from `REPRODUCE.md`; §8's numbers are produced by `run.py batch` once agents
are plugged in.
