# Deferred Work

## DW-F009-01

Feature: 009 Notifications
Reason: Real Web Push permission and delivery require HTTPS staging, a supported browser/device, user permission, and provider configuration that cannot be proven by CI fake transport tests.
Prerequisites: HTTPS staging deployment, configured Web Push secrets, supported browser with notifications enabled, test MANAGER and HELPDESK accounts.
Steps:
1. Login as HELPDESK in the supported browser.
2. Enable Web Push from the Notifications screen and grant browser permission.
3. Login as MANAGER in another session and assign a Task to that HELPDESK user.
4. Confirm the in-app Notification appears for the HELPDESK user.
5. Confirm the browser/device push arrives.
6. Inspect the lock-screen/browser notification preview.
Expected:
- In-app notification is present and complete.
- Push payload is generic.
- No employee, Task detail, GPS coordinate, photo, map URL, signed URL, token, or private evidence data appears in the push preview.
Related requirement/R-xx: R-97.
Status: PENDING
