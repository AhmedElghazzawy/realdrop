# ADR 0014: Style profile stored on the device at launch

- **Status:** Accepted
- **Date:** 2026-11-14

## Context

Accounts add friction, KVKK obligations and build time; the launch window is 13 days.

## Decision

The style profile (styles, fits, colours, sizes, budget, brands) lives in the browser's localStorage and is sent with requests that need it. No user table at launch.

## Consequences

No cross-device sync until an optional login (UC-10). The API stays stateless per visitor, which also simplifies scaling and deletion (clearing the browser deletes the profile).
