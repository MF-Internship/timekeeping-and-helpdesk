# Contract: Observability

No public HTTP contract is added.

Internal contracts:

- `emit_metric(sink, name, labels, value)` returns `False` for invalid metrics or sink failures.
- `emit_alert(reason, route_name)` returns `False` for sink failure and logs only sanitized strings.
- `prune_retention(repository, now, batch_size)` returns deleted counts per allowed category.
