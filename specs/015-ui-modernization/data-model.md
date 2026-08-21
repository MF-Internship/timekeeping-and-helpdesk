# Data Model: UI Modernization

Feature 015 adds no backend entity and changes no persisted business data.

## ThemePreference

- `mode`: `light | dark | system`
- Stored locally as non-sensitive presentation preference.
- Resolved theme follows `mode` and the current operating-system preference.

## NavigationItem

- `href`: canonical route
- `label`: Vietnamese user-facing label
- `icon`: Lucide icon component
- `capability`: optional existing presentation capability
- `group`: `primary | secondary | account`
- `mobileSlot`: optional `home | tasks | attendance | more`
- `activeMatch`: exact or route-prefix matching rule

Filtering affects presentation only and does not replace route or backend authorization.

## RouteCoverageRecord

- `route`
- `capabilityOrState`
- `existingPurpose`
- `existingMajorComponents`
- `modernizedComponents`
- `regressionEvidence`

The authoritative inventory is [contracts/route-coverage.md](./contracts/route-coverage.md).

## ChartDatum

- `key`: canonical response-map key
- `label`: safe localized label
- `value`: finite non-negative number from the response
- `colorToken`: centralized chart token

Transformation is deterministic: preserve canonical ordering where defined, convert missing known categories to zero, retain unknown categories in textual summaries, and never synthesize time buckets.

## NotificationGroup

- `period`: `today | yesterday | earlier`
- `items`: existing notification items sorted by `created_at`

Unread filtering and date grouping are client presentation transforms; read state continues to come from the notification contract.
