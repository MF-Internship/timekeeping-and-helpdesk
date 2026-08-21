# Data Model: Release Hardening Evidence

Feature 016 introduces no business or database model. Its engineering evidence has the following logical records.

## Canonical Check

- `id`: stable check name
- `owner`: frontend manifest, backend project, or repository script
- `mode`: check-only or write/fix
- `prerequisites`: runtime, locked dependencies, service, and scoped environment
- `command`: one canonical repository-root invocation
- `mutates_source`: false for every CI/release check
- `result`: pass or fail; no optional required state

## Workflow Job Record

- `workflow`, `job`, `purpose`, and `triggers`
- `runtime_versions`, `dependencies`, and `services`
- `required_configuration` and `canonical_commands`
- `security_boundary` and `status_problem`

Each workflow/job pair is unique and maps to one or more Canonical Checks.

## Failure Record

- `failure`: command/job and diagnostic symptom
- `root_cause`: mechanism producing the failure
- `fix`: smallest behavior-preserving correction
- `verification`: targeted command/result
- `final_gate_status`: pass or fail

A failure cannot transition to resolved until targeted verification passes. “A test failed” is not a valid root cause.

## Generated Contract Pair

- `backend_source`, `committed_openapi`, and `generated_frontend_schema`
- `operation_ids` and `generation_command`
- `drift_status` and `compatibility_status`

The pair is valid only when generation is deterministic, both artifacts match their owners, operation identifiers remain explicit/unique/stable, and compatibility passes.

## Deferred Verification

- `id`
- `feature`: fixed to `016`
- `reason`, `environment`, and `prerequisites`
- `steps` and `expected_result`
- `status`: fixed to `PENDING` until real evidence exists

Deferred Verification records never satisfy a machine release category or convert production readiness to pass by documentation alone.
