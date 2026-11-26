# Tasks

## 1. Frontend Session Persistence

- [x] 1.1 Update `frontend/src/App.tsx` to initialize `usuario` from `localStorage` (`luzai_usuario`) with JSON parsing and structural validation (`nombre` string and `rol` in `['alumno', 'docente']`), clearing corrupted entries safely and falling back to `null`. Verify TypeScript compilation succeeds (`npm run build` or `npx tsc --noEmit` in `frontend/`).
- [x] 1.2 Update login and logout handlers in `frontend/src/App.tsx` so login writes the `Usuario` JSON to `localStorage` and `onCerrarSesion` removes `luzai_usuario` from `localStorage` before resetting state. Verify via browser reload (`F5`) that an authenticated session persists and that clicking logout returns to the login view and stays logged out on reload.
