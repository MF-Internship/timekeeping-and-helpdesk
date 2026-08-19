# SC-001 / SC-002 / SC-015 User-Trial Results

**Feature**: 006 | **Branch**: `feature/006-location-geofence-guidance`
**Status**: ⛔ **NOT YET RUN — awaiting human observation sessions.**
**Deferred**: `2026-08-20` — registered with T116 in [evidence/deferred-work.md](evidence/deferred-work.md).

This file is the recording sheet for the trial protocol defined in
[spec.md](spec.md) §Measurable Outcomes. It is deliberately empty of results:
SC-001, SC-002, and SC-015 are measured by observing people, and no automated gate can
stand in for them. Feature 006 is not signed off until the tables below are
filled in and both criteria pass.

## Protocol (from spec.md §Measurable Outcomes)

- **Ten trials.** Each trial is one participant, under one scripted position and
  reference-data condition, asked to read the guidance aloud.
- **Coverage floors.** The ten trials MUST span **at least three distinct
  participants** and **at least three distinct device or browser combinations**.
- **Scoring.** A trial is a success only when **every** value the criterion names
  is stated correctly. A partially correct reading is a failure.
- **Threshold.** Each criterion passes at **≥ 9 of 10** successes.

### SC-001 — the reading is legible

Condition: an **accurate** reading (`accuracy_m` at or below
`Config.max_attendance_accuracy_m`).

The participant must state, within **15 seconds of the position being
displayed**, all four of:

1. their nearest registered Location,
2. their distance to it,
3. its radius,
4. whether they are inside it.

### SC-002 — a weak signal is not mistaken for a wrong place

Condition: a reading whose `accuracy_m` **exceeds**
`Config.max_attendance_accuracy_m`.

The participant must state that the punch will be rejected **for signal quality**
— not for being in the wrong place.

## Recording — SC-001

| # | Participant | Device / browser | Position & reference condition | Read time (s) | Nearest | Distance | Radius | Inside? | Pass |
|---|---|---|---|---|---|---|---|---|---|
| 1 |  |  |  |  |  |  |  |  |  |
| 2 |  |  |  |  |  |  |  |  |  |
| 3 |  |  |  |  |  |  |  |  |  |
| 4 |  |  |  |  |  |  |  |  |  |
| 5 |  |  |  |  |  |  |  |  |  |
| 6 |  |  |  |  |  |  |  |  |  |
| 7 |  |  |  |  |  |  |  |  |  |
| 8 |  |  |  |  |  |  |  |  |  |
| 9 |  |  |  |  |  |  |  |  |  |
| 10 |  |  |  |  |  |  |  |  |  |

**Result**: ___ / 10 (pass requires ≥ 9)

## Recording — SC-015

Condition: open the spatial disclosure with both the allowed Location radius
and GPS uncertainty represented, then remove color cues while retaining shape,
line treatment, legend text, and the textual alternative. Ask the participant
to identify both boundaries and explain their different meanings. Record only
aggregate-safe labels and pass/fail—never identity, coordinates, screenshots
containing coordinates, or identifying free-form responses.

| # | Participant code | Device / browser | Allowed radius identified | GPS uncertainty identified | Difference understood | Pass |
|---|---|---|---|---|---|---|
| 1 |  |  |  |  |  |  |
| 2 |  |  |  |  |  |  |
| 3 |  |  |  |  |  |  |
| 4 |  |  |  |  |  |  |
| 5 |  |  |  |  |  |  |
| 6 |  |  |  |  |  |  |
| 7 |  |  |  |  |  |  |
| 8 |  |  |  |  |  |  |
| 9 |  |  |  |  |  |  |
| 10 |  |  |  |  |  |  |

**Result**: ___ / 10 (pass requires ≥ 9; both meanings must be correct)

## Recording — SC-002

| # | Participant | Device / browser | `accuracy_m` vs threshold | Stated reason for rejection | Pass |
|---|---|---|---|---|---|
| 1 |  |  |  |  |  |
| 2 |  |  |  |  |  |
| 3 |  |  |  |  |  |
| 4 |  |  |  |  |  |
| 5 |  |  |  |  |  |
| 6 |  |  |  |  |  |
| 7 |  |  |  |  |  |
| 8 |  |  |  |  |  |
| 9 |  |  |  |  |  |
| 10 |  |  |  |  |  |

**Result**: ___ / 10 (pass requires ≥ 9)

## Coverage check

| Floor | Required | Observed | Met |
|---|---|---|---|
| Distinct participants | ≥ 3 |  |  |
| Distinct device / browser combinations | ≥ 3 |  |  |

## Sign-off

- [ ] SC-001 ≥ 9/10
- [ ] SC-002 ≥ 9/10
- [ ] SC-015 ≥ 9/10
- [ ] Both coverage floors met
- [ ] T116a marked `[X]` in [tasks.md](tasks.md)
- [ ] T204 marked `[X]` in [tasks.md](tasks.md)

Observer: ______________  Date: ______________
