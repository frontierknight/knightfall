# Human-baseline protocol

An agent score means little without a human reference on the same challenges under the same rules.
This protocol collects that reference. It is designed so a human session and an agent session are
scored by the identical machinery (the uniform `Session` console), differing only in who emits the
actions — the property that makes the two numbers comparable.

## What we measure

For each `(participant, challenge)` attempt, the range already records a full trajectory. From it we
report, per challenge and aggregated:

- **graded ratio** — `graded_score / max_score` (the 4-layer partial credit).
- **binary pass** — did the scenario's `final_condition` layer fire.
- **budget used** — steps and player wall-clock (judge time excluded), and whether the budget was
  exhausted.
- **checkpoint reached** — the highest of interface_op → target_accept → mission_impact →
  physical_impact confirmed by the judge.

These are exactly the fields a baseline agent run produces, so human and agent rows share a schema.

## Participants

- Target n ≥ 8 per challenge for a first reference; report per-participant rows, not just the mean.
- Record each participant's self-rated ROS 2 familiarity (none / user / developer) and security-CTF
  experience (none / hobby / professional). These are covariates, not gates.
- Exclude a participant's challenge attempt from the aggregate only for a logged environment failure
  (startup_failure outcome), never for a low score.

## Conditions (identical to the agent condition)

- Same challenge versions (pinned by `scenario_hash` in the trajectory `meta`), same image digest.
- Same budget from the scenario YAML (steps primary, wall-clock secondary).
- Same briefing text the agent receives (`backend.briefing()`), shown once at the start.
- The participant plays through `run.py play <task>` — the same `Session` an agent drives. No hints,
  no writeups, no access to `selftest.py`/`QUICKSTART.md` (they contain solutions).
- One attempt per participant per challenge for the headline number; additional attempts, if any, are
  recorded separately and not pooled with first attempts.

## Procedure

1. Fresh round: the harness destroys and recreates the challenge before the clock starts (readiness
   gate). Confirm readiness passes.
2. Show the briefing. Start the budget clock on the first action.
3. The participant works at the console until they submit/`done` or the budget is exhausted.
4. The judge scores from ground truth; the trajectory is written to `trajectories/`.
5. Move the trajectory into a per-study folder named by an opaque participant id (no names/emails in
   the file). The `actor.name` field should be set to that id, not a login.

## Ethics and data

- Consent: participants are told the session is recorded as a trajectory (their commands and the
  observations) and used, in aggregate and de-identified, as a benchmark reference.
- De-identification: the only identifier stored is the opaque study id. Do not log usernames,
  hostnames, or IPs into the trajectory (`actor.name` is set explicitly; provenance records the image
  and scenario, not the person).
- Storage: keep raw trajectories access-controlled; publish only aggregates and, where a participant
  agreed, individual de-identified trajectories.

## Reporting (for the paper)

- Per challenge: human mean graded ratio and pass rate with n and spread, beside the agent condition
  and the null/random/scripted baselines from `run.py batch`.
- A trajectory-length and time distribution per challenge (humans vs agents) — cost, not just score.
- State the pinned versions once (image digest, ROS distro, discovery mode) from the trajectory
  `meta`, so the table is reproducible.

## Not in scope here

- Recruiting logistics and IRB/again-review requirements depend on the institution and are handled
  outside this repo.
- A web-hosted collection UI is future work; the terminal `run.py play` path is sufficient for a
  first reference set.
