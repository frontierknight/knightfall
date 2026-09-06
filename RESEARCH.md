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
