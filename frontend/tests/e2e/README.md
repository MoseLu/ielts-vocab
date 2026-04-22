# E2E Tests Documentation

## Prerequisites

1. **Install dependencies:**
   ```bash
   pnpm install
   ```

2. **Install Playwright browsers:**
   ```bash
   pnpm --dir frontend exec playwright install chromium
   ```

3. **Start split backend:**
   ```bash
   powershell -ExecutionPolicy Bypass -File .\start-microservices.ps1
   ```

4. **Start frontend server:**
   ```bash
   pnpm dev
   ```

## Running Tests

### Run all tests:
```bash
pnpm test:e2e
```

`frontend/playwright.config.ts` now auto-starts only the frontend dev server. Keep the split backend running on `gateway-bff:8000` before launching the suite.

### Run the CI smoke subset:
```bash
pnpm --dir frontend exec playwright test tests/e2e/smoke.spec.ts
```

### Run specific test file:
```bash
pnpm --dir frontend exec playwright test auth.spec.ts
```

### Run tests in headed mode (show browser):
```bash
pnpm --dir frontend exec playwright test --headed
```

### Run tests with UI:
```bash
pnpm --dir frontend exec playwright test --ui
```

### Run tests in debug mode:
```bash
pnpm --dir frontend exec playwright test --debug
```

### View test report:
```bash
pnpm --dir frontend exec playwright show-report
```

## Test Coverage

### Test Files:

1. **auth.spec.ts** - Authentication flow (login, register, validation)
2. **navigation.spec.ts** - Route navigation and redirects
3. **vocab-books.spec.ts** - Vocabulary books and chapters
4. **practice.spec.ts** - Practice page controls and UI
5. **practice-modes.spec.ts** - All practice modes (smart, listening, meaning, dictation, radio, quickmemory)
6. **errors.spec.ts** - Wrong words/Errors page
7. **stats.spec.ts** - Statistics and analytics
8. **profile.spec.ts** - User profile and settings
9. **ai-chat.spec.ts** - AI chat assistant panel
10. **admin.spec.ts** - Admin dashboard
11. **settings.spec.ts** - Practice settings and preferences
12. **integration.spec.ts** - Full user journey integration tests
13. **smoke.spec.ts** - CI smoke subset for login page, redirect, register, and logout

### Routes Covered:

- `/login` - Login/Register page
- `/` - Home/Vocabulary books page
- `/plan` - Learning plan page
- `/practice` - Practice page (all modes)
- `/errors` - Wrong words page
- `/stats` - Statistics page
- `/profile` - User profile page
- `/vocab-test` - Vocabulary test page
- `/journal` - Learning journal page
- `/admin` - Admin dashboard

### Features Tested:

- ✅ User authentication (login, register, logout)
- ✅ CI smoke path (login page, unauthenticated redirect, register -> shell -> logout)
- ✅ Route navigation and redirects
- ✅ Vocabulary book and chapter selection
- ✅ Practice modes (smart, listening, meaning, dictation, radio, quickmemory)
- ✅ Practice controls (pause, resume, skip, go back)
- ✅ Word list panel
- ✅ Settings panel and persistence
- ✅ Wrong words management
- ✅ Learning statistics and analytics
- ✅ User profile management
- ✅ AI chat assistant
- ✅ Admin dashboard (admin users only)
- ✅ Integration workflows

## Configuration

Edit `frontend/playwright.config.ts` to change:
- Base URL (`baseURL`)
- Test directory (`testDir`)
- Browser options
- Timeout settings

## Troubleshooting

### Tests fail with "Cannot find element":
- Ensure frontend and backend are running
- Check base URL in `frontend/playwright.config.ts`
- Use `--headed` flag to see what's happening

### Authentication issues:
- Tests use mock tokens for authentication
- For real auth tests, update auth.spec.ts with real credentials

### Browser not found:
- Run `pnpm --dir frontend exec playwright install chromium`
- Ensure you have enough disk space

## CI/CD Integration

Add to your CI pipeline:

```yaml
- name: Install dependencies
  run: pnpm install --frozen-lockfile

- name: Install Playwright
  run: pnpm --dir frontend exec playwright install --with-deps chromium

- name: Run E2E tests
  run: pnpm test:e2e

- name: Upload test results
  if: always()
  uses: actions/upload-artifact@v3
  with:
    name: playwright-report
    path: playwright-report/
```

The Windows split-runtime smoke path in this repository uses:

- `scripts/ci/windows-split-runtime-smoke.ps1`
- `frontend/tests/e2e/smoke.spec.ts`
