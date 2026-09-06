# Knightfall 🤖

**A ROS 2 security CTF range for both humans and AI agents** — a [Frontier Knight Labs](https://github.com/frontierknight) benchmark.

One warehouse delivery robot + switchable security scenarios + independent attack / scoring / reset
infrastructure. Every challenge is the same robot exposing a different security flaw under a
different deployment condition — so results stay comparable, and the same range benchmarks both
human players and AI security agents ([Crimson Knight](https://github.com/frontierknight/crimson) /
[Azure Knight](https://github.com/frontierknight/azure)).

> Status: **design / pre-implementation.** Versions & parameters lock after deployment validation.

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

## Try it (self-check)
见 [`QUICKSTART.md`](QUICKSTART.md) — 在 winbox WSL 上 `python3 run.py list / run task01 / run task03 / oracle`。

## Contents
- [`RESEARCH.md`](RESEARCH.md) — 研究笔记：传统 CTF/range 做法 + ROS 2 特殊性 + 空白点/novelty + 引用清单（论文地基）。
- [`DESIGN.md`](DESIGN.md) — full design: principles, three-zone architecture, layered scoring,
  reset/timing, first three tasks, reuse stack, and the build order.
- [`schema/scenario.schema.yaml`](schema/scenario.schema.yaml) — machine-readable spec every
  challenge follows (attacker start · flaw · goal · budget · scoring · fix-oracle · reset · env).
- [`scenarios/`](scenarios/) — concrete challenges. First: `01-diagnostic-leak.yaml`.

## Build order (see DESIGN §11)
1. ROS 2 comms + security-config sample (legit comms succeed; forbidden rejected)
2. Task 1 + full run loop (human solves, agent attempts, scoring & reset trustworthy)
3. Reference delivery robot + maintenance-over-privilege task
4. Localization physical task + batch evaluation

## Responsible use
Fully simulated and isolated. Scenarios model misconfigurations for education and benchmarking —
run only within the range. Do not target real robotic deployments.
