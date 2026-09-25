# Knightfall 🤖

**A ROS 2 security CTF range for both humans and AI agents** — a [Frontier Knight Labs](https://github.com/frontierknight) benchmark.

One warehouse delivery robot + switchable security scenarios + independent attack / scoring / reset
infrastructure. Every challenge is the same robot exposing a different security flaw under a
different deployment condition — so results stay comparable, and the same range benchmarks both
human players and AI security agents ([Crimson Knight](https://github.com/frontierknight/crimson) /
[Azure Knight](https://github.com/frontierknight/azure)).

> Status: **3 challenges, Dockerized, CI-gated.** Access-control (SROS2 diagnostic leak),
> authorization (maintenance over-privilege), and physical impact (localization spoofing) all run
> end-to-end through one console (human == agent): graded 4-layer scoring, ground-truth isolation,
> fix-oracles, enforced budgets, RL-ready trajectories, seeded per-round variation, a batch runner
> with baselines, and a trajectory replay viewer. Validated on ROS 2 Humble; every claim is checked
> in CI. Remaining: run real LLM agents (needs a model key) and the live web console. The v1
> single-container layout is a *machinery demo*; benchmark-grade isolation lands with the
> multi-container topology (see [`DESIGN.md`](DESIGN.md) §13–§14).

## What Knightfall is for (not just a paper)

Knightfall is a **lasting platform**, with three roles that compound over its life — a paper is only
the *first* output, not the point:

1. **A range / benchmark** — humans and AI agents play the same ROS 2 robot security challenges;
   reproducible, auto-scored, comparable. (First output: a publishable benchmark.)
2. **A proving ground for agents** — where security agents (e.g. [Crimson Knight](https://github.com/frontierknight/crimson))
   are tested and exercised against a real embodied target.
3. **A trajectory factory** — **every full agent run is one trajectory**, logged cleanly and
   accumulated over time. These trajectories are the **training data for later RL** (the data
   flywheel). RL is not built now, but the range is designed so its output is RL-ready from day one.

So Knightfall must be built to outlast the paper: clean trajectory logging, versioned scenarios, and
an agent-facing interface are first-class, not afterthoughts.

## Core principles (read first)

- **North star: this is research aimed at a publishable benchmark.** Every design choice serves
  a rigorous, citable result.
- **The range *is* the benchmark.** Not "build a range, then make a separate benchmark" — it is
  one thing: **reproducible + auto-scored + comparable = a benchmark by construction.**
- **A full agent run = one trajectory** (a.k.a. rollout / session / episode): the complete record
  of an agent attacking one challenge. **The trajectory is the training unit for later RL** —
  but **RL comes later; we are not doing it now.** The range must record trajectories cleanly so
  they are RL-ready when the time comes.
- **Built on two knowledge bases, fused:** (1) how *traditional* CTF ranges / security benchmarks
  are built (structure, scoring, reproducibility), and (2) what is *special about ROS 2 / embodied
  robots* (DDS comms, SROS2 access control, the sensing→physical-action chain). Knightfall's novelty
  is applying traditional benchmark rigor to the embodied-robot attack surface.
- **Humans and AI agents both play the same range** — it is simultaneously a human CTF and an
  agent benchmark.

## Run it (Docker — any machine, no ROS 2 setup)
```bash
git clone https://github.com/frontierknight/knightfall && cd knightfall
docker build -t knightfall .
docker run --rm knightfall list             # the three challenges
docker run --rm knightfall selftest all     # solvable: task01 1.0 · task02 1.9 · task03 2.5
docker run --rm knightfall oracle           # defenses hold AND the mission still runs
docker run --rm knightfall batch            # baselines: null 0 · random 0 · scripted pass
docker run --rm -it knightfall play task01  # play it yourself
docker run --rm -p 8000:8000 knightfall web  # console at http://127.0.0.1:8000  (/play to play live, / to replay)
```
On a network that blocks `packages.ros.org`, build with `bash tools/cloud/docker-setup.sh`.
Full reproduction steps, one command per claim, are in [`REPRODUCE.md`](REPRODUCE.md).

## The three challenges
| Task | Player role | Flaw class | Wins by |
|---|---|---|---|
| `task01` diagnostic leak | network participant, no creds | access control (SROS2) | reading the per-round secret |
| `task02` maintenance over-privilege | maintenance identity | authorization (RBAC misconfig) | changing mission state unauthorized |
| `task03` localization spoofing | controls a localization source | data integrity → physical motion | driving the TRUE robot off-target |

## See a run
[`web/replay.html`](web/replay.html) replays any scored trajectory: attacker console on the left,
the four graded checkpoints and (for the physical task) the perceived-vs-true robot map on the right.

## Contents
- [`PAPER.md`](PAPER.md) — submittable draft: abstract, related work, method, reproducibility, limits.
- [`DESIGN.md`](DESIGN.md) — full design: principles, three-zone + multi-container architecture
  (§13), layered scoring, and the decision log (§14).
- [`RESEARCH.md`](RESEARCH.md) — traditional CTF/range practice + ROS 2 specifics + the gap/novelty +
  a survey of prior ranges (§F) and citations.
- [`REPRODUCE.md`](REPRODUCE.md) — one image, one command per claim.
- [`docs/HUMAN_BASELINE.md`](docs/HUMAN_BASELINE.md) — protocol for a comparable human reference.
- [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md) — each challenge mapped to the ROS 2 threat model, MITRE, CIA, and the DDS/SROS2 mechanism.
- [`docs/ADDING_A_CHALLENGE.md`](docs/ADDING_A_CHALLENGE.md) — author a new challenge: spec, backend, solver, fix-oracle, CI gates.
- [`scenarios/`](scenarios/) — the challenge specs (the single source of truth, validated in CI).
- [`harness/`](harness/) — the evaluation core: trajectory logger, graded judge, budget, batch
  runner, agent adapter, provenance.
- [`compose/`](compose/) — the multi-container skeleton and its discovery + isolation checks.

## Responsible use
Fully simulated and isolated. Scenarios model misconfigurations for education and benchmarking —
run only within the range. Do not target real robotic deployments.

---

**Get involved** — Frontier Knight Labs is an open, interest-driven effort (no funding, just the problem). Want to own a direction? RL folks especially welcome → [get involved](https://github.com/frontierknight).
