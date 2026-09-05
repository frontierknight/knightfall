# Knightfall 🤖

**A ROS 2 security CTF range for both humans and AI agents** — a [Frontier Knight Labs](https://github.com/frontierknight) benchmark.

One warehouse delivery robot + switchable security scenarios + independent attack / scoring / reset
infrastructure. Every challenge is the same robot exposing a different security flaw under a
different deployment condition — so results stay comparable, and the same range benchmarks both
human players and AI security agents ([Crimson Knight](https://github.com/frontierknight/crimson) /
[Azure Knight](https://github.com/frontierknight/azure)).

> Status: **design / pre-implementation.** Versions & parameters lock after deployment validation.

## Contents
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
