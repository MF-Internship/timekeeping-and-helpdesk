# Implementation Plan: Operational Telemetry, Health and Retention

- Extend logging config with formatter defaults and named loggers.
- Add `core.metrics` closed registry and safe emission helper.
- Add sanitized alert adapter.
- Add pure heartbeat evaluator and `JobHeartbeat` model.
- Add retention application service with persistence behind a port.
- Add thin `prune_retention` command.
- Verify with unit, PostgreSQL, and command-thinness tests.
