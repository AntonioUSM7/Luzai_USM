# Proposal

## Why

Currently, the frontend stores the authenticated `Usuario` object only in React component state (`useState` in `App.tsx`). Every browser refresh (`F5`) clears the session and forces the user back to the login screen, which interrupts workflows (such as checking RAG indexing status or demonstrating the platform live).

## What Changes

- Persist the authenticated `Usuario` object in `localStorage` on login and restore it on application mount.
- Clear the persisted session from `localStorage` on explicit logout (`onCerrarSesion`) or if stored data is malformed/invalid.

## Capabilities

### New Capabilities
- `frontend-session-persistence`: Client-side persistence and restoration of the active user session across browser reloads, with safe fallback on invalid storage data and explicit cleanup on logout.

### Modified Capabilities

## Impact

- Affected code: `frontend/src/App.tsx` (session initialization, login handler, and logout handler).
- No backend, API, or dependency changes required.
