# Knightfall — Research Notes (traditional range/benchmark practice ⊕ ROS 2 specifics)

North star: a **publishable benchmark**. This file records the established practice we build on
and the gap we fill, so the design is grounded (not invented) and the paper's related-work +
novelty are ready.

## A. How agent-CTF benchmarks & cyber ranges are built (traditional — adopt this)

| Work | What to reuse |
|---|---|
| **NYU CTF Bench** (NeurIPS'24, [2406.05590](https://arxiv.org/abs/2406.05590)) | first CTF benchmark for cyber agents; scalable dataset + per-task metadata from real competitions |
| **Cybench** ([2408.08926](https://arxiv.org/pdf/2408.08926)) | 40 pro CTF tasks; **subtasks = fine-grained / gradated evaluation** (not just binary) |
| **InterCode-CTF** ([2306.14898](https://arxiv.org/pdf/2306.14898)) | structured triplet `<instruction, assets, hidden flag>`; **Docker-isolated per instance**; explicit reproducible eval protocol |
| **DeepRed — "Do Agents Dream of Root Shells?"** ([2604.19354](https://arxiv.org/abs/2604.19354)) | **partial-credit via checkpoints from writeups** + **records full execution traces** + **Kali attacker env over a private network to the target**. Almost exactly our three-zone + graded design — but for software. |
| **Cyber-range reference architectures** ([ScienceDirect S2214212624002199](https://www.sciencedirect.com/science/article/pii/S2214212624002199), [2307.04416](https://arxiv.org/pdf/2307.04416)) | virtualized/emulated + **hypervisor isolation per segment**; **reset to a known fixed state in minutes via stored templates**; a score-computation engine |

**Consensus we adopt (all already in DESIGN.md):**
1. **Per-challenge isolation** (Docker/VM), private attacker↔target network, separate judge/scoring plane.
2. **Reproducibility**: templated environments, reset-to-known-state, pinned versions.
3. **Graded / checkpoint scoring** beats binary (Cybench subtasks, DeepRed checkpoints) — our 4 layers = checkpoints.
4. **Full trajectory (execution-trace) logging** is standard (DeepRed) → this is exactly our "agent run = trajectory", and it's what makes it RL-ready.
5. Task unit as `<briefing, assets, success/flag>` → our scenario YAML.

## B. ROS 2 / embodied specifics + THE GAP (our novelty)

- **ROS 2 attack surface is real & current**: RIPA — sensory-vector prompt injection on LLM-controlled
  ROS 2 robots ([2606.28649](https://arxiv.org/pdf/2606.28649)); SROS2/DDS-Security weaknesses (CCS'22);
  ROS 2 official threat model (design.ros2.org).
- **Embodied-AI security is surveyed but under-benchmarked**: Awesome-Embodied-AI-Safety (500+ papers),
  "Towards Robust and Secure Embodied AI" survey (ACM Comput. Surv., [10.1145/3806048](https://dl.acm.org/doi/10.1145/3806048));
  RoboJailBench ([2605.19328](https://arxiv.org/html/2605.19328v1)) benchmarks attacks on the robot's *AI*,
  not a security **range**.
- **The gap, quotable for the paper's motivation** (from the embodied-AI security survey):
  > "Creating standardized, reproducible environments to test contextual and integration vulnerabilities
  > like **sensor spoofing** in embodied agents remains a paramount challenge … there remains a **gap in a
  > standardized, comprehensive benchmark** that systematically evaluates adversarial attacks and defenses
  > in embodied AI systems."

**What's special about ROS 2 (vs a software CTF) — must be designed in:**
- Comms is **DDS pub/sub + discovery**, access control is **SROS2 policies** (not TCP/HTTP + firewalls).
- There is a **sensing → decision → physical-action chain**: an attack can move a *robot*, not just read a flag.
- Therefore scoring needs a **physical-impact layer** (perceived pose vs sim ground truth) that no
  software CTF has — and it must be **jitter-robust** (bounded thresholds, multiple trials).

## C. Novelty / contribution (the paper's claim)

**Knightfall = the first standardized, reproducible, auto-scored ROS 2 / embodied-robot security range
that is simultaneously a human CTF and an AI-agent benchmark, with a physical-impact scoring layer
(perceived vs ground-truth) absent from software CTF benchmarks — filling the explicitly-stated gap in
standardized embodied-AI security evaluation.**

Contributions to claim:
1. A shared-robot, scenario-driven range (roles-first permission model; DDS/SROS2-grounded flaws).
2. A **4-layer graded scoring** (interface → accept → mission → physical) extending checkpoint-style
   partial credit to embodied impact, with ground-truth isolation from the attacker.
3. **Fix-oracles** per challenge (attack blocked ∧ mission still works) → measures defense, not just attack.
4. A reproducible harness that logs full **trajectories** (RL-ready), scoring humans and agents alike.

## D. Related work to cite (starter list)
NYU CTF Bench · Cybench · InterCode-CTF · DeepRed (partial-credit CTF) · cyber-range reference
architecture (ScienceDirect'24; 2307.04416) · RIPA (ROS 2 prompt injection) · CCS'22 (In)Security of
Secure ROS2 · ROS 2 threat model · embodied-AI security surveys (ACM CSUR 3806048; Awesome-Embodied-AI-Safety)
· CTF-Dojo / RANDOM-CRYPTO (for the later RL/data angle).

## E. How this changes the build (feeds DESIGN.md)
- Keep the three-zone + destroy-and-recreate + graded scoring (now citation-backed — good).
- Frame each challenge as `<briefing, assets, checkpoints, flag/event, fix-oracle>` (checkpoints = the
  4 layers) — aligns with DeepRed/Cybench, and the **physical checkpoint is our differentiator**.
- Log full trajectories from day one (execution traces) — matches DeepRed and is the RL unit.
- v1 scope stays small (3 tasks) but **the physical-impact task is the headline** — it's what no prior
  benchmark has; prioritize proving its propagation path (DESIGN §12 open question).

## F. Prior ranges surveyed for the v2 architecture (2026-09-25)

Goal of this pass: learn how existing ranges are *built and delivered* (containers, networks,
visualization, reset, agent interface), to shape Knightfall's environment. Infrastructure only.

| Range | Kind | What we take from it |
|---|---|---|
| **GRFICSv3** ([GitHub](https://github.com/Fortiphyd/GRFICSv3); v1: [USENIX ASE'18](https://www.usenix.org/conference/ase18/presentation/formby)) | ICS / chemical-plant cyber-physical lab | **Closest precedent.** Fully Docker-compose'd: 3D process sim, PLC, HMI, engineering workstation, player workstation, router/firewall each a container. **Two segmented zones** (process / enterprise) with a router controlling traffic. **The physical process is visualized in the browser** — the learner *sees* the physical consequence. Reset = `docker compose down --volumes`. Optional services behind compose profiles. |
| **RCTF** — Robotics CTF, Alias Robotics ([GitHub](https://github.com/aliasrobotics/RCTF); [arXiv 1810.02690](https://arxiv.org/abs/1810.02690)) | Robot CTF (ROS / ROS 2) | The only direct robotics precedent. Scenarios in a **linear difficulty progression**, one repo + Docker image per scenario. **Archived (read-only) as of 2026-07** — there is currently no maintained open robotics range. No graded scoring, no agent interface, no physical-impact judging. |
| **CTFd + ctfd-whale** ([GitHub](https://github.com/frankli0324/ctfd-whale)) | General CTF platform | **Per-player instance on demand**, **dynamic per-instance flag**, admin panel managing instance lifecycle. |
| **CybORG / CAGE Challenge 4** ([CybORG](https://github.com/cage-challenge/CybORG); [CC4](https://github.com/cage-challenge/cage-challenge-4)) | Autonomous cyber-operations gym | **Agent-first interface** (PettingZoo), structured observation / action / reward, fixed episode length (500 steps), **evaluation over 100 randomized episodes**, public leaderboard. |
| **Lichtblick** ([GitHub](https://github.com/lichtblick-suite/lichtblick)) | Open-source ROS visualization (Foxglove Studio fork) | Candidate off-the-shelf viewer via `foxglove_bridge`; kept as an option, but it cannot by itself enforce the judge/player data split (see DESIGN §13). |

**Common pattern across these (the "standard parts" of a range):**
1. **Zones on separate networks** — player, target, and judge/management are isolated by the
   network, not by convention.
2. **Visible physical process** (GRFICS) — seeing the consequence is the core learning experience
   for cyber-physical ranges.
3. **One-command up / one-command reset** (compose + volume teardown).
4. **Independent instance + dynamic flag per player/run** (ctfd-whale).
5. **Standard agent interface + multi-episode randomized evaluation** (CybORG).

**Knightfall v1 vs this pattern:** 4 and 5 exist in embryo (per-round random flag; the uniform
`Session` console). 1–3 are missing: everything runs in one container, and there is no
visualization. DESIGN §13 closes this gap.

**Positioning:** GRFICS proves the "containerized cyber-physical range + visible physics" model for
ICS; RCTF proved robotics demand but is archived and never had graded / agent / physical-truth
scoring. Knightfall = GRFICS-style delivery × RCTF's domain × CybORG-style agent evaluation, plus the
physical-impact checkpoint.
