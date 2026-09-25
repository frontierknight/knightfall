# Threat-model mapping

Each challenge is grounded in a real mechanism, not a vague "attack". This maps the three
challenges to the ROS 2 security threat model (design.ros2.org), to a MITRE technique, to the CIA
property they violate, and to the concrete DDS/SROS2 mechanism involved — the taxonomy backbone
RESEARCH.md §A calls for. The MITRE ids are the ones each scenario declares (indicative; ATT&CK for
Enterprise `T1xxx` and ATT&CK for ICS `T0xxx`).

| Challenge | ROS 2 threat-model element | Category | MITRE (declared) | CIA | Mechanism |
|---|---|---|---|---|---|
| **01 diagnostic leak** | Unauthorized subscription to a topic (no access-control policy on a DDS topic) | access-control | T1530 (data from repositories), T1602 (data from config) | **C**onfidentiality | SROS2 / DDS-Security: a topic published with no `permissions.xml` grant is readable by any participant on the domain |
| **02 maintenance over-privilege** | A role granted more than its intended permissions issues an unauthorized command | access-control | T0855 (unauthorized command message), T0879 (damage to property) | **I**ntegrity (of mission state) | RBAC policy misconfig: the maintenance role holds a state-changing permission (`cancel`/`redirect`) that should belong to dispatch |
| **03 localization spoofing** | A trusted data source is spoofed; downstream lacks a consistency check (sensing→action chain) | data-integrity | T0856 (spoof reporting message), T0832 (manipulation of view) | **I**ntegrity (of perception) → physical safety | The controller consumes `/localization/pose` with no integrity/authenticity check, so a spoofed pose drives the TRUE robot off-target |

## Coverage and the physical layer
The three cover the ROS 2 threat model's two load-bearing surfaces — **access control on the DDS
graph** (who may read/write which topic, tasks 01–02) and **integrity of the sensing→decision→action
chain** (task 03) — and progress in difficulty (easy → medium). Task 03 is the differentiator: its
impact is not information disclosure or a changed record but the **physical** deviation of a real
robot, measured against ground truth the attacker cannot see or forge. This is the layer no software
CTF benchmark scores (PAPER.md §1, RESEARCH.md §B).

## What is deliberately out of scope (stated for the paper's threat model)
- **Cryptographic identity spoofing** beyond task 01's SROS2 boundary: task 02 models identity as a
  policy-governed role rather than a forged DDS-Security credential; an SROS2-enforced-identity
  variant is future work.
- **Discovery/transport attacks** (DDS discovery flooding, participant impersonation at the wire
  level) are not yet a challenge; the range pins one discovery mode per scenario (`env.discovery`).
- **Attacks on the agent's own model** (prompt injection via sensor data, e.g. RIPA): Knightfall
  scores attacks *by* an agent on the robot, not attacks on the agent — noted as adjacent work in
  RESEARCH.md §B.

Each row's mechanism is exactly what the challenge's fix-oracle closes (`challenges/oracles.py`):
tightening the SROS2 policy (01), removing the over-granted permission (02), and adding a
localization integrity check (03).
