# Auth And Payments Checks

Use this reference when the app has login, roles, subscriptions, checkout, webhooks, credits, usage limits, teams, or admin features.

## Authentication

P0 examples:

- Protected pages only hide UI but do not protect server routes.
- Session or JWT verification is missing on sensitive API endpoints.
- Auth secret is hardcoded or missing in production.
- Password reset or magic link flow can be replayed or guessed.

Check for:

- Server-side protection for every private route.
- Secure cookie flags where cookies are used.
- Sensible session expiration.
- Clear handling for unauthenticated and expired sessions.

## Authorization

P0 examples:

- Users can access another user's records by changing an ID.
- Admin routes rely on client-side role checks only.
- Team/workspace membership is not checked on mutations.

Check for:

- Object-level access checks.
- Role checks on the server.
- Tenant scoping in queries.
- Safe defaults for new users.

## Payments

P0 examples:

- Webhooks are accepted without signature verification.
- Subscription status can be changed from the client.
- Paid features trust client-side plan flags.

Check for:

- Provider webhook signatures verified with raw request bodies.
- Idempotent webhook handling.
- Clear mapping between provider customer IDs and local users.
- Server-side entitlement checks.
- Trial, cancellation, failed payment, refund, and downgrade states.

## Usage, credits, and metering

Check for:

- Usage limits enforced server-side.
- Race conditions in credit deduction.
- Expensive AI/API calls protected by quotas.
- Admin or support adjustments are auditable.
