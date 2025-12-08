# HOWTO — REQ-011 Web Console

## Prerequisites
- Node.js 20+
- npm 10+
- Backend API + OIDC auth stack reachable at `NEXT_PUBLIC_API_BASE_URL`.
- Browser session authenticated against backend (cookies reused by Next dev server).

## Local Setup
```bash
cd runs/kit/REQ-011/src/web
npm install
```

### Environment
Create `.env.local` (optional):
```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

## Developer Commands
- **Dev server:** `npm run dev`
- **Lint:** `npm run lint`
- **Tests:** `npm run test`
- **Build:** `npm run build`
- **Start (prod):** `npm run start`

## CI Runner (Enterprise/Jenkins)
1. Check out repo.
2. `cd runs/kit/REQ-011/src/web`
3. `npm ci`
4. Execute commands per LTC:
   - `npm run lint`
   - `npm run build`
   - `npm run test`
5. Archive `runs/kit/REQ-011/test/web/coverage`.

## Troubleshooting
- **Module path errors:** Ensure tests use Vitest config that sets alias `@ -> src/web`.
- **Fetch/auth failures:** verify backend CORS allows `http://localhost:3000` and cookies are shared.
- **Tailwind styles missing:** confirm `content` paths include `app`, `components`, `lib`; rerun `npm run dev`.