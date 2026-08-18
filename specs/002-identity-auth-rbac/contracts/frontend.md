# Frontend Contract: Identity Session and User Administration

## Session state

`AuthProvider` exposes:

| State | Meaning |
|---|---|
| `bootstrapping` | Attempting cookie refresh after page load; no protected UI is rendered. |
| `anonymous` | No usable refresh/access; login screen is available. |
| `authenticated` | In-memory access plus current SelfUser/capabilities. |
| `password_change_required` | Authenticated but only password-change UI is allowed. |
| `inactive` | Current account is inactive; access cleared and refresh retries stopped. |

Access value and session/account objects live only in JavaScript memory. They are absent from localStorage, sessionStorage, IndexedDB, URL/query/hash, logs, error messages, analytics, and component debug output.

## Bootstrap and request behavior

1. On application load, call refresh through the one transport.
2. If refresh succeeds, hold the returned access in memory and GET `/me/`.
3. If `/me/` reports forced change, transition to password_change_required and route to change-password.
4. If refresh is INVALID_TOKEN, clear session and become anonymous.
5. If any request is ACCOUNT_INACTIVE, clear access, become inactive, stop retries, and display the canonical locked-account message.
6. If bootstrap refresh returns PASSWORD_CHANGE_REQUIRED while no access remains in memory, become anonymous and route to login with forced-change guidance; after login restores access, route to change-password.

`authenticatedFetch` behavior:

- accepts only relative `/api/v1/` targets;
- includes cookies and no-store as it does today;
- attaches `Authorization: Bearer <memory access>` only when present and appropriate;
- on one protected request receiving INVALID_TOKEN, joins/starts one refresh promise;
- retries the original request once after successful refresh, using a non-user-visible retry marker;
- never refreshes recursively for login/refresh or repeatedly retries a replay;
- never refreshes for ACCOUNT_INACTIVE, PASSWORD_CHANGE_REQUIRED, PERMISSION_DENIED, SERVER_OWNED_FIELD, or ordinary validation failures;
- concurrent failures share one refresh rotation and all resume from its result.

The Next.js proxy preserves the caller's exact path. It does not append a slash: slashless auth/change-password and slashed `/me/`/user routes reach matching backend routes without redirects or duplicate contracts.

## Route behavior

| Route | Guard / behavior |
|---|---|
| `/login` | Anonymous only; success stores access in memory, then routes to forced change or authorized landing. |
| `/change-password` | Authenticated; available even in password_change_required state. Success replaces access and refreshes `/me/`. |
| `/users` | Requires effective `user.view`; Manager only under canonical map. Direct backend denial remains authoritative. |

Leader and Helpdesk have no user-directory UI entry. Manager-target action controls are absent/disabled based on the visible target role, but forged requests remain blocked by backend target permission.

## User directory state

- Query state contains q, optional role, optional is_active, and page.
- Empty filter sends no is_active default, so inactive and Manager accounts remain visible.
- Assignment-picker behavior is not implemented here; a later Task screen must reuse this API with explicit role=HELPDESK and is_active=true.
- Create/edit/role/status/reset use distinct typed API wrappers and forms over the handwritten thin shared client and generated schema.
- Mutations are not automatically replayed by UI retry; the transport's sole replay is the original request after one successful authentication refresh.

## Generated-password lifecycle

`GeneratedPasswordDialog` is opened only from a successful create/reset response.

- Plaintext is held in component state only.
- It is not copied into directory cache, global auth state, toast history, URL, browser storage, logs, or error objects.
- Dismiss, unmount, logout, and account switch clear the value.
- Reopening the target later cannot recover it; UI instructs Manager to reset again.
- Network retry must not claim it can recover a committed but lost response; after uncertainty, reload target state and use a deliberate reset if a new password is required.

## Capability presentation

- Backend login and `/me/` supply effective action strings.
- UI checks exact strings; it does not infer a role hierarchy or recreate PERMISSION_IMPLIES.
- Unknown future capability strings are retained/ignored safely by the client and do not break parsing.
- Backend authorization is always final; hidden buttons are usability, not security.

## Canonical error handling

Extend the shared authorized-code parser/messages for:

| Code | UI action |
|---|---|
| INVALID_CREDENTIALS | Stay on login and show the same credential message. |
| INVALID_TOKEN | Run at most one refresh; otherwise become anonymous. |
| ACCOUNT_INACTIVE | Stop refresh, clear session, show locked-account guidance. |
| PASSWORD_CHANGE_REQUIRED | Preserve current access, route to change-password, do not replay business request. |
| PERMISSION_DENIED | Show insufficient permission; update visible capabilities after `/me/` if appropriate. |
| SERVER_OWNED_FIELD | Show contract/form error and do not retry unchanged. |
| VALIDATION_FAILED | Bind field details to the owning form. |

Request IDs remain visible for support on canonical errors. Unexpected/network failures continue using the existing AsyncState behavior.

## Frontend verification

- Token strings never appear in storage APIs or rendered DOM.
- Ten simultaneous INVALID_TOKEN responses trigger exactly one refresh call and each original request runs at most twice total.
- Reused/failed refresh clears state once without loops.
- Forced-change state cannot render user admin or other business pages.
- Capability matrix renders only expected controls for Leader/Manager/Helpdesk.
- Manager targets remain visible while all four admin mutations are unavailable in UI.
- Generated password disappears after every lifecycle boundary.
- All calls use generated types and the existing API transport/client boundaries; architecture check finds no alternate fetch path.
- Logout sends the in-memory bearer access and protected refresh cookie when present; with valid access every cookie state receives `204`, so the client clears local session state without inspecting or retrying the cookie.
- `429 THROTTLED` displays the server-provided wait and does not retry before `Retry-After`; `503 SERVICE_UNAVAILABLE` presents a temporary-service failure and does not bypass the failed-closed throttle boundary.
