# Manager user-administration usability evidence

- Date: 2026-08-18 (Asia/Ho_Chi_Minh)
- Environment: local PostgreSQL 17, controlled test identities
- Command: `uv run --project backend pytest backend/tests/integration/api/identity/test_identity_flows.py -q`
- Result: passed. The complete identity API scenario suite, including login and
  the Manager create, list/search contract, eligible profile/role/status actions,
  and password reset paths, completed in 2.05 seconds in the recorded run.
- Target: each Manager happy-path action completes within two minutes.
- Sensitive data: no generated plaintext password or token value was copied into
  this evidence. This is reproducible development usability evidence, not a
  production performance or readiness claim.

