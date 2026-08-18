# Identity API capacity evidence

- Date: 2026-08-18 (Asia/Ho_Chi_Minh)
- Tool: existing approved `scripts/capacity_check.py` measurement primitives
- Environment: local controlled HTTP endpoint; not production evidence
- Distinct test identities: 50
- Concurrency: 20
- Measured p95: 52.74187499890104 ms
- Approved target: p95 at or below 500 ms
- Result: passed for this controlled local run
- Remediation owner field: engineering
- Sensitive data: the recorded result contains no identity, credential, bearer,
  URL, password, or generated-password value. Capacity remains an operator-run
  measurement and is not a CI gate or a production-readiness claim.

