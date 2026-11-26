# Spec Delta

## Purpose

Preserves the authenticated user's session across browser reloads so users remain signed in until they explicitly log out.

## ADDED Requirements

### Requirement: Persist active session across page reloads
The frontend SHALL persist the authenticated user session in browser `localStorage` upon login and restore it on application startup so reloading the page does not return the user to the login screen.

#### Scenario: User reloads page while signed in
- **WHEN** an authenticated user reloads the browser page
- **THEN** the application restores the stored user session and renders the authenticated portal instead of the login view

### Requirement: Clear session on explicit logout
The frontend SHALL remove the persisted session from `localStorage` when the user explicitly logs out.

#### Scenario: User clicks logout
- **WHEN** an authenticated user triggers logout
- **THEN** the persisted session is removed from `localStorage` and the application displays the login view

### Requirement: Safe fallback on corrupted or invalid stored session
The frontend SHALL treat missing, unparseable, or structurally invalid stored session data as unauthenticated and clear the invalid entry.

#### Scenario: Stored session JSON is malformed
- **WHEN** `localStorage` contains invalid JSON or a value missing required `nombre` or valid `rol` fields on startup
- **THEN** the application clears the invalid entry and renders the login view without throwing an unhandled error
