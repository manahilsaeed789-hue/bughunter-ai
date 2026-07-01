# Permission check bypass in api/auth.py

Severity: critical
Confidence: 94%

## Impact
Privileged data or actions can be exposed to authenticated users without the required role.

## Root Cause
The authorization guard was widened from a role/permission check to a simple authenticated-user check.

## Trigger Scenario
A non-admin authenticated account calls the affected endpoint after the commit is deployed.

## Minimal Fix
Restore the explicit permission predicate and add a negative authorization test for ordinary users.

## Validation Steps
- Run the endpoint test as an authenticated non-admin user.
- Confirm the request returns 403 and no sensitive payload is produced.

