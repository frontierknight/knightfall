# Knightfall — Deliverable ① : ROS 2 comms + security sample

**Goal (acceptance):** a minimal secured ROS 2 graph where **legitimate communication
succeeds and forbidden communication is rejected.** This is the foundation of the range —
proof that the access-control mechanism actually works — and the seed of scenario
`01-diagnostic-leak`.

## What it does
Uses **SROS2 / DDS-Security** (Enforce mode) on a `/diagnostics` topic:
- **Case A (legit):** a secured diagnostics publisher + an **authorized maintenance**
  listener (both with valid keystore enclaves) → the maintenance listener **receives**.
- **Case B (forbidden):** an **unauthorized** listener with no credentials on the same
  secured domain → **receives nothing** (rejected by DDS-Security under Enforce).

Access control is defined by [`policy/knightfall_diag.policy.xml`](policy/knightfall_diag.policy.xml):
the diagnostics publisher and the maintenance role are granted; no enclave is granted to an
attacker.

## Run
On Ubuntu 22.04 with ROS 2 Humble + `ros-humble-sros2` installed:
```bash
bash run_acceptance.sh
```
Expected:
```
authorized listener heard: N msgs   (N > 0)
unauthorized listener heard: 0 msgs
PASS ✅  legit comms succeed · unauthorized denied
```

## Validated
- 2026-09-06, ROS 2 **Humble** on Ubuntu **22.04.5** (WSL2). Authorized heard 4 msgs;
  unauthorized heard 0. **PASS.**
- Known benign warning during `generate_artifacts`: `failed to validate namespace: error
  not set` — artifacts still generate correctly; to be cleaned when the policy is refined.

## Env (version record for reproducibility)
- ROS 2 Humble · Ubuntu 22.04 · RMW rmw_fastrtps_cpp (default) · `ROS_SECURITY_STRATEGY=Enforce`
- (scenario `env` in `../scenarios/01-diagnostic-leak.yaml` pinned to match.)

## Next (Deliverable ②)
Wrap this into the full run loop: task briefing → attacker attempt (human + agent) →
trustworthy scoring → destroy-and-recreate reset. See `../DESIGN.md` §11.
