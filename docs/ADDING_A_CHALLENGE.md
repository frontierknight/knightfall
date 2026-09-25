# Adding a challenge

Knightfall is built so new challenges plug into the same harness — same console, scoring,
trajectories, and CI gates. A challenge is four things: a **scenario spec**, a **backend**, a
**reference solver**, and a **fix-oracle**. All four are required; CI enforces that the challenge is
both solvable and defended.

## 1. Scenario spec — `scenarios/NN-name.yaml`
The single source of truth (the registry loads it; `harness/validate_scenarios.py` checks it in CI).
Copy an existing one and fill every required field: `id`, `title`, `desc`, `version`, `category`,
`difficulty`, `normal_mission`, `attacker`, `flaw` (summary + mechanism + intended_permission),
`attack_goal`, `budget` (`steps`, `wall_clock_s`), `scoring`, `fix_oracle`, `reset_scope`,
`readiness_checks`, `env`. The validator requires `scoring.graded` to cover exactly the four layers
`interface_op, target_accept, mission_impact, physical_impact` and the `final_condition` layer to
have non-zero weight. Map the flaw to the threat model (`docs/THREAT_MODEL.md`).

## 2. Backend — `challenges/taskNN_name.py`
Implement `ChallengeBackend` (see `harness/runner.py`). The backend holds ground truth; the attacker
never sees it.

- `readiness_check() -> (ok, detail)` — bring the target up; return False before the budget clock
  starts if it isn't ready. Run this in the challenge's own ROS domain.
- `briefing() -> dict` — what the actor is told. **Never** include the secret/goal value, and don't
  name anything the challenge wants the attacker to discover (see seeded variation below).
- `exec_action(cmd) -> observation` — run one attacker command in the sandbox terminal.
- `confirm_checkpoints() -> set[str]` — **confirm layers only from recorded ground truth**, never
  from the attacker's command text. Read a judge-only channel (a file the player container never
  mounts, or mission state), and **latch** hits so a transient reading can't un-set them.
- `submit(value) -> bool` — optional, for flag-style challenges.
- `artifacts() -> dict | None` — optional ground-truth data to attach to the trajectory for
  replay/analysis (e.g. task03's pose trail); read it before `reset()` destroys state.
- `reset()` — destroy and recreate the round (nodes, creds, discovery cache, params, state, secret).

Ground-truth rule (audit B1/B3): keep truth off the DDS graph the player shares; export it over a
side channel the player cannot read or forge. Confirm impact from events the sim/robot record.

## 3. Register it — `challenges/registry.py`
Add one line to `_BACKENDS`: `"taskNN": ("NN-name", TaskNNBackend)`. The runtime view is projected
from the YAML automatically.

## 4. Reference solver — `harness/selftest.py`
Add `solve_taskNN(s)` and register it in `SOLVERS`. It must **discover**, not hardcode, anything the
seed varies (list topics, try both commands) so it passes any round. For impact that needs time to
develop, poll `s.backend.confirm_checkpoints()` up to a bounded deadline instead of a fixed sleep.

## 5. Fix-oracle — `challenges/oracles.py`
Implement `FixOracle` (`apply_patch`, `attack_blocked`, `mission_still_works`, `teardown`) and add it
to `harness/run_fix_oracles.py`. `apply_patch` applies the corrective config (tighten the SROS2
policy, remove the over-granted permission, add an integrity check); the oracle must show the same
attack now fails **and** the legitimate mission still completes.

## 6. Seeded variation (recommended) — `challenges/variants.py`
If the answer isn't visible in `ros2 topic list` (a secret, a granted command), vary it from a fixed
allowlist keyed on `KNIGHTFALL_SEED` so memorized solutions don't generalize. Keep the no-seed
default deterministic for CI and the reference sample. Public/demo seeds are 0–99; evaluation seeds
(>=1000) stay out of the repo.

## 7. Verify (what CI will run)
```bash
python3 harness/validate_scenarios.py            # spec is well-formed
docker run --rm knightfall selftest taskNN       # solvable
docker run --rm knightfall oracle                # defended + mission still works
docker run --rm knightfall batch --actors null,scripted --tasks taskNN   # null 0, scripted pass
```
A challenge that the null actor scores on, or that the reference solver cannot pass, fails the CI
gate (`harness/test_batch_sanity.py`). Keep code comments in English.
