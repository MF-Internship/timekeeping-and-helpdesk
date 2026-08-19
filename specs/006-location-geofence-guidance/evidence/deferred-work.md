# Feature 006 Deferred Work

- Status: **DEFERRED — HUMAN VERIFICATION REQUIRED**
- Deferred on: `2026-08-20`, at the user's direction
- Scope of this register: the human observation work in **T116, T116a, and
  T204**. The product-supplied logo dependency was resolved on 2026-08-20.
- **Deferral is not a pass and not a waiver.** Feature 006 is not signed off
  until both records below read PASS.
- Privacy rule: record aggregate observations only. Never record GPS
  coordinates, credentials, participant identities, or screenshots containing
  either. This is not boilerplate here — the thing being verified is precisely
  that a coordinate never escapes the screen (FR-029a–FR-039, SC-003), so the
  evidence must not carry one either.

## Why these two cannot be self-certified

The UI extension now includes Playwright and axe as development-only verification
tools. They cover representative viewports, overflow, responsive navigation,
keyboard semantics, automated accessibility rules, reduced motion, touch-target
size, and progressive disclosure. What remains requires a **person**: inspecting
privacy-sensitive browser behavior under a real GPS override, observing whether
participants understand the operational guidance, and validating artwork that
product has not supplied. Automation narrows these checks; it does not replace
them.

The static counterparts that *can* be automated already exist and pass —
[gps-privacy.test.ts](../../../frontend/tests/architecture/gps-privacy.test.ts),
[guidance-boundary.test.ts](../../../frontend/tests/architecture/guidance-boundary.test.ts),
[test_guidance_reads_create_no_records.py](../../../backend/tests/integration/postgres/locations/test_guidance_reads_create_no_records.py)
and [test_geofence_distance_fixture.py](../../../backend/tests/contract/locations/test_geofence_distance_fixture.py).
They narrow the manual pass; they do not replace it.

---

## T116 — Manual quickstart walkthrough (FR-044)

- Status: **PARTIALLY COMPLETE** — executable half done, interactive half deferred
- Resume condition: backend and frontend both running, frontend served over
  HTTPS or `localhost`, the canonical 76-`Location` seed loaded, a `Config` row
  carrying `max_attendance_accuracy_m`, an account holding
  `attendance.check_in.self` / `attendance.check_out.self`, and a browser able to
  override geolocation

### Already done on 2026-08-20 — do not redo

Every command [quickstart.md](../quickstart.md) documents was run as written and
passed. Four steps had drifted from the implementation and were corrected in
place:

| Drift | Correction |
|---|---|
| `manage.py` commands died on `ConfigurationError: invalid configuration: APP_ENV` — `core/deployment.py` reads `os.environ` only and nothing autoloads a dotenv | `set -a && . ./.env && set +a` added to Prerequisites, Setup, Scenario 5 and Scenario 10 |
| Scenario 1 step 2 named a *Bật vị trí* trigger | the UI renders *Xem vị trí* (`shared/messages.ts` → `guidance.trigger`); text corrected |
| Scenario 8's static counterpart ran only `gps-privacy.test.ts` | step 5 (the external map link, FR-029a) is proven by `guidance-boundary.test.ts`; that file added to the documented command |
| — | every threshold, label and seed code the quickstart quotes re-checked against source: `STALE_AFTER_SECONDS = 60`, `ACQUISITION_TIMEOUT_MS = 15000`, `NEARBY_LIMIT = 5`, `COORDINATE_DECIMALS = 6`, coincident pair `HCM000079` / `HCM010005` — all match |

### Remaining — interactive, one row per scenario

| Scenario | What still needs a human | Result |
|---|---|---|
| 1 — acquire and read | no permission prompt before the trigger; six-decimal readout, accuracy, capture time, freshness within 15 s | _pending_ |
| 2 — browser failure modes | four forced conditions each give a distinct message and the right affordance; none names an Attendance code | _pending_ |
| 3 — overlap and coincidence | all containing Locations remain visible; nearest is the display-only focus and no Attendance candidate is selected | _pending_ |
| 4 — no distance filter | list still fills from a remote position | _pending_ |
| 5 — preview never authorizes | geolocation invoked **again** at press time; outgoing `captured_at` strictly newer than the preview's; attempt count unchanged by viewing and refreshing | _pending_ |
| 6 — server-attributed errors | each Attendance code rendered as a server decision; candidate chooser built from `details.location_candidates`, never from the preview | _pending_ |
| 7 — spatial diagram | geofence circle sized to `radius_m` and **not** modified by `accuracy_m`; scale bar present; coincident case renders sanely | _pending_ |
| 8 — privacy sweep | DevTools Network / Storage / Console / address bar all clean; position gone after navigating away | _pending_ |
| 9 — parity by hand | a UI preview distance matches the `distance_m` the server returns for the same position (the fixture half is already green in CI) | _pending_ |
| 10 — no migration | already verified: `makemigrations --check --dry-run` reports no changes | **PASS** |

### Execution record

- Run owner: _pending_
- Run date and environment: _pending_
- Browser / device used: _pending_
- Quickstart drift found during the interactive pass: _pending — correct `quickstart.md` in place and note it here_
- Result: **NOT YET EVALUATED — DEFERRAL IS NOT A PASS OR WAIVER**

---

## T116a — SC-001 / SC-002 user trials

- Status: **DEFERRED — NOT YET RUN**
- Resume condition: a scheduled test session with at least `3` representative
  participants and at least `3` distinct device or browser combinations
- Recording sheet: [trial-results.md](../trial-results.md) — the protocol, the
  scoring rules and the empty tables are already prepared there, and `tasks.md`
  names that path specifically. Record per-trial outcomes there; keep this file
  as the register.
- Required trials: `10`, each one participant under one scripted position and
  reference-data condition
- Passing threshold: at least `9` of `10` successes, **separately** for SC-001
  and for SC-002. A trial counts as a success only when every value the criterion
  names is stated correctly; partially correct is a failure.
- SC-001: within 15 seconds of display, the participant states their nearest
  registered Location, the distance to it, its radius, and whether they are inside
- SC-002: under a weak reading, the participant attributes the problem to signal
  quality rather than to being in the wrong place

### Execution record

- Run owner: _pending_
- Run dates and environment: _pending_
- Distinct participants: _pending_ (floor `3`)
- Distinct device/browser combinations: _pending_ (floor `3`)
- SC-001 successes: _pending_ / 10
- SC-002 successes: _pending_ / 10
- Result: **NOT YET EVALUATED — DEFERRAL IS NOT A PASS OR WAIVER**

---

## Resume checklist

1. Bring up the stack per [quickstart.md](../quickstart.md) §Setup, loading the
   root `.env` first.
2. Walk Scenarios 1–9 interactively; fill the T116 table above and correct
   `quickstart.md` in place if anything else has drifted.
3. Run the ten trials; fill [trial-results.md](../trial-results.md), then copy
   the counts into the T116a execution record above.
4. Run the SC-015 legend trial recorded in [trial-results.md](../trial-results.md).
5. Flip `T116`, `T116a`, and `T204` to `[X]` only after their evidence passes.
5. If either criterion falls below 9/10, that is a **finding against the
   feature**, not against the protocol — open the gap before sign-off.
