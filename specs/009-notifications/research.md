# Research: In-App Notifications and Web Push

- **Decision**: Do not create new notification types.
  **Rationale**: CHOT/R-97 approves exactly five events.
  **Alternatives considered**: Account lock/reset notifications; rejected as explicitly out of scope.

- **Decision**: In-app notifications remain authoritative and Web Push remains best-effort.
  **Rationale**: Push can be denied, revoked, delayed by quiet hours, or fail provider delivery.
  **Alternatives considered**: Push as delivery source of truth; rejected by CHOT/R-97.

- **Decision**: Real browser/device push verification is deferred.
  **Rationale**: It requires HTTPS staging, provider configuration, browser permission, and a supported device/browser.
  **Alternatives considered**: Mark fake transport tests as real delivery; rejected by deferred work policy.
