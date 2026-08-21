# Visualization Data Contract

| Visualization | Endpoint | Source | Transform | Accessible equivalent |
|---|---|---|---|---|
| Task status | Task report | `status_counts` | Order TODO, IN_PROGRESS, BLOCKED, COMPLETED; missing to zero | Labeled count list |
| Completion method | Task report | `completion_method_counts` | Non-empty map entries with localized known labels | Labeled count list |
| Evidence GPS quality | Task report | `gps_quality_counts` | Non-empty map entries with localized known labels | Labeled count list |
| Attendance attempts | Attendance report | `attempt_counts` | Non-empty map entries; retain unknown keys in text | Labeled count list |
| Attendance anomalies | Attendance report | `anomaly_counts` | Non-empty map entries; retain unknown keys in text | Labeled count list |
| Failure rate | Attendance report | `failure_rate` | Direct percentage/numerator/denominator/excluded values | KPI text and supporting counts |

Prohibited transformations:

- No date/trend buckets because neither report endpoint returns a time series.
- No population pie from open-session and checked-out counts because those groups can overlap.
- No chart of `actual_completer_counts` because keys are raw user IDs and the response has no display names.
- No random, sample, interpolated, or client-inferred values.
