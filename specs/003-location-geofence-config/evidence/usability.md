# Feature 003 Manager Usability Evidence

Date: 2026-08-18  
Status: PASS

The non-CI acceptance run used the local Django and Next.js applications, the PostgreSQL
acceptance data, an active Manager account, and the connected Chrome browser at
`http://localhost:3000`. All three Manager maintenance workflows completed in under the
two-minute SC-009 threshold.

| Workflow | Elapsed | Result | Observed acceptance evidence |
| --- | ---: | --- | --- |
| Location maintenance | 10.901 s | PASS | Located `HCM020129`, edited its name with an attributable reason, received `Đã lưu địa điểm.`, and restored the canonical name through the same UI. |
| Config maintenance | 0.379 s | PASS | Raised the attendance-accuracy threshold to 51 m and observed a structured warning containing affected code `HCM020129` plus `50.000m / 51.000m`; restored the threshold to 25 m. |
| Holiday maintenance | 5.963 s | PASS | Created `2027-12-26 — Acceptance T122 timed`, observed it in the list, accepted deletion, and observed its removal. |

The Location and Config values were restored and all acceptance Holiday rows were removed.
The temporary Manager was made inactive with an unusable password because protected audit
history correctly prevents deleting its identity. The browser reported no console errors, and
the final local location-reference readiness check reported `Location reference data ready`.

These are individual observed runs, not a latency sample, so no p95 usability claim is made.
