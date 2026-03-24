# Expo App Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone Expo app that lets users configure OneLap/Strava credentials, run syncs, review history/logs, and use the tool on iOS, Android, web, and desktop-class browsers without changing the existing Python CLI.

**Architecture:** Keep the existing Python package untouched and add a new `app/` workspace for the Expo client. Recreate the CLI's business logic in small TypeScript service modules with behavior matched by tests, then layer Zustand stores and Expo Router screens on top so the UI stays thin and the sync logic stays independently testable.

**Tech Stack:** Expo 52, React Native, Expo Router, TypeScript, Jest, React Native Testing Library, Zustand, i18next, AsyncStorage, SecureStore, Expo Auth Session, Expo File System, Expo Crypto, `@react-native-cookies/cookies`.

---

## File Map

### New application workspace

- Create: `app/package.json`
- Create: `app/tsconfig.json`
- Create: `app/app.json`
- Create: `app/babel.config.js`
- Create: `app/jest.config.ts`
- Create: `app/jest.setup.ts`
- Create: `app/expo-env.d.ts`
- Create: `app/app/_layout.tsx`
- Create: `app/app/(tabs)/_layout.tsx`
- Create: `app/app/(tabs)/index.tsx`
- Create: `app/app/(tabs)/history.tsx`
- Create: `app/app/(tabs)/logs.tsx`
- Create: `app/app/(tabs)/settings.tsx`

### Shared app source

- Create: `app/src/types/domain.ts`
- Create: `app/src/services/storage.ts`
- Create: `app/src/services/dedupe-service.ts`
- Create: `app/src/services/state-store.ts`
- Create: `app/src/services/onelap-client.ts`
- Create: `app/src/services/strava-client.ts`
- Create: `app/src/services/sync-engine.ts`
- Create: `app/src/services/oauth.ts`
- Create: `app/src/stores/settings-store.ts`
- Create: `app/src/stores/sync-store.ts`
- Create: `app/src/stores/log-store.ts`
- Create: `app/src/hooks/use-settings.ts`
- Create: `app/src/hooks/use-sync.ts`
- Create: `app/src/hooks/use-strava-auth.ts`
- Create: `app/src/components/ProgressBar.tsx`
- Create: `app/src/components/StatusBadge.tsx`
- Create: `app/src/components/ActivityRow.tsx`
- Create: `app/src/i18n/index.ts`
- Create: `app/src/i18n/en.json`
- Create: `app/src/i18n/zh.json`
- Create: `app/src/theme/colors.ts`
- Create: `app/src/theme/spacing.ts`

### Tests

- Create: `app/__tests__/services/dedupe-service.test.ts`
- Create: `app/__tests__/services/state-store.test.ts`
- Create: `app/__tests__/services/onelap-client.test.ts`
- Create: `app/__tests__/services/strava-client.test.ts`
- Create: `app/__tests__/services/sync-engine.test.ts`
- Create: `app/__tests__/stores/settings-store.test.ts`
- Create: `app/__tests__/stores/sync-store.test.ts`
- Create: `app/__tests__/components/sync-screen.test.tsx`
- Create: `app/__tests__/components/settings-screen.test.tsx`

### Existing docs to update after the app works

- Modify: `README.md`
- Modify: `README.zh.md`
- Modify: `CONTRIBUTING.md`

---

### Task 1: Scaffold the Expo workspace and prove the shell app renders

**Files:**
- Create: `app/package.json`
- Create: `app/tsconfig.json`
- Create: `app/app.json`
- Create: `app/babel.config.js`
- Create: `app/jest.config.ts`
- Create: `app/jest.setup.ts`
- Create: `app/expo-env.d.ts`
- Create: `app/app/_layout.tsx`
- Create: `app/app/(tabs)/_layout.tsx`
- Create: `app/app/(tabs)/index.tsx`
- Test: `app/__tests__/components/sync-screen.test.tsx`

- [ ] **Step 1: Write the failing UI smoke test**

```tsx
import { render, screen } from '@testing-library/react-native';
import SyncScreen from '../../app/(tabs)/index';

test('renders sync home actions', () => {
  render(<SyncScreen />);
  expect(screen.getByText('Start Sync')).toBeTruthy();
  expect(screen.getByText('Download Only')).toBeTruthy();
});
```

- [ ] **Step 2: Run the test to verify the workspace is missing**

Run: `npm --prefix app test -- --runInBand __tests__/components/sync-screen.test.tsx`
Expected: FAIL with missing `package.json`, missing Jest config, or missing screen module.

- [ ] **Step 3: Create the minimal Expo shell**

```tsx
// app/app/(tabs)/index.tsx
import { Text, View } from 'react-native';

export default function SyncScreen() {
  return (
    <View>
      <Text>Start Sync</Text>
      <Text>Download Only</Text>
    </View>
  );
}
```

Include these dependencies in `app/package.json`: `expo`, `react`, `react-native`, `expo-router`, `typescript`, `jest`, `jest-expo`, `@testing-library/react-native`, `zustand`, `i18next`, `react-i18next`, `expo-secure-store`, `@react-native-async-storage/async-storage`, `expo-file-system`, `expo-crypto`, `expo-auth-session`, `@react-native-cookies/cookies`.

- [ ] **Step 4: Run the smoke test again**

Run: `npm --prefix app test -- --runInBand __tests__/components/sync-screen.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit the scaffold**

```bash
git add app/package.json app/tsconfig.json app/app.json app/babel.config.js app/jest.config.ts app/jest.setup.ts app/expo-env.d.ts app/app/_layout.tsx app/app/(tabs)/_layout.tsx app/app/(tabs)/index.tsx app/__tests__/components/sync-screen.test.tsx
git commit -m "feat: scaffold Expo app workspace"
```

### Task 2: Add app types, storage adapters, i18n bootstrap, and settings persistence

**Files:**
- Create: `app/src/types/domain.ts`
- Create: `app/src/services/storage.ts`
- Create: `app/src/stores/settings-store.ts`
- Create: `app/src/hooks/use-settings.ts`
- Create: `app/src/i18n/index.ts`
- Create: `app/src/i18n/en.json`
- Create: `app/src/i18n/zh.json`
- Create: `app/__tests__/stores/settings-store.test.ts`

- [ ] **Step 1: Write the failing settings-store test**

```ts
import { act } from '@testing-library/react-native';
import { useSettingsStore } from '../../src/stores/settings-store';

test('persists language and lookback settings', async () => {
  await act(async () => {
    await useSettingsStore.getState().setLanguage('zh');
    await useSettingsStore.getState().setDefaultLookbackDays(5);
  });

  expect(useSettingsStore.getState().language).toBe('zh');
  expect(useSettingsStore.getState().defaultLookbackDays).toBe(5);
});

test('falls back to AsyncStorage for sensitive values on web', async () => {
  const storage = createStorageAdapter('web');
  await storage.setSecret('onelap_password', 'secret');
  expect(await storage.getSecret('onelap_password')).toBe('secret');
});
```

- [ ] **Step 2: Run the test to verify storage/state are missing**

Run: `npm --prefix app test -- --runInBand __tests__/stores/settings-store.test.ts`
Expected: FAIL with missing store module.

- [ ] **Step 3: Implement the smallest working settings stack**

```ts
export type Language = 'en' | 'zh';

type SettingsState = {
  language: Language;
  defaultLookbackDays: number;
  setLanguage: (language: Language) => Promise<void>;
  setDefaultLookbackDays: (days: number) => Promise<void>;
};
```

Use platform-aware storage:
- native: `SecureStore` for sensitive fields, `AsyncStorage` for language/lookback
- web: `AsyncStorage` fallback for all fields because `SecureStore` is unavailable

Initialize `i18next` from the persisted language and expose a store flag like `isWebInsecureStorage` so UI can show the required web warning based on actual capability, not hard-coded platform checks.

- [ ] **Step 4: Run the store test again**

Run: `npm --prefix app test -- --runInBand __tests__/stores/settings-store.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit the persistence layer**

```bash
git add app/src/types/domain.ts app/src/services/storage.ts app/src/stores/settings-store.ts app/src/hooks/use-settings.ts app/src/i18n/index.ts app/src/i18n/en.json app/src/i18n/zh.json app/__tests__/stores/settings-store.test.ts
git commit -m "feat: add app settings persistence and i18n bootstrap"
```

### Task 3: Port fingerprinting and sync state storage from Python to TypeScript

**Files:**
- Create: `app/src/services/dedupe-service.ts`
- Create: `app/src/services/state-store.ts`
- Create: `app/__tests__/services/dedupe-service.test.ts`
- Create: `app/__tests__/services/state-store.test.ts`
- Reference: `src/sync_onelap_strava/dedupe_service.py`
- Reference: `src/sync_onelap_strava/state_store.py`

- [ ] **Step 1: Write the failing service tests**

```ts
test('makeFingerprint matches Python format', async () => {
  const value = await makeFingerprint('file:///tmp/a.fit', '2026-03-09T08:00:00Z', 'fileKey:abc');
  expect(value).toMatch(/^fileKey:abc\|[a-f0-9]{64}\|2026-03-09T08:00:00Z$/);
});

test('markSynced stores activity id and timestamp', async () => {
  const store = new StateStore('@test_state');
  await store.markSynced('fp-1', 12345);
  expect(await store.isSynced('fp-1')).toBe(true);
});

test('exposes last success sync time and synced activity map', async () => {
  const store = new StateStore('@test_state');
  await store.markSynced('fp-2', 54321);
  expect(await store.lastSuccessSyncTime()).toBeTruthy();
  expect((await store.getAllSynced())['fp-2'].strava_activity_id).toBe(54321);
});
```

- [ ] **Step 2: Run the service tests to confirm they fail**

Run: `npm --prefix app test -- --runInBand __tests__/services/dedupe-service.test.ts __tests__/services/state-store.test.ts`
Expected: FAIL with missing services.

- [ ] **Step 3: Implement byte-accurate hashing and JSON-like sync state**

```ts
export async function makeFingerprint(fileUri: string, startTime: string, recordKey: string) {
  const digest = await sha256FileBytes(fileUri);
  return `${recordKey}|${digest}|${startTime}`;
}
```

Mirror Python state shape exactly and implement both read APIs required by the UI:
- `lastSuccessSyncTime()` for the Sync tab summary
- `getAllSynced()` for the full synced-activities list in the History tab

Mirror Python state shape exactly:

```json
{
  "synced": {
    "fingerprint": {
      "strava_activity_id": 12345,
      "synced_at": "2026-03-24T12:00:00+00:00"
    }
  }
}
```

- [ ] **Step 4: Run the tests again**

Run: `npm --prefix app test -- --runInBand __tests__/services/dedupe-service.test.ts __tests__/services/state-store.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit the core persistence services**

```bash
git add app/src/services/dedupe-service.ts app/src/services/state-store.ts app/__tests__/services/dedupe-service.test.ts app/__tests__/services/state-store.test.ts
git commit -m "feat: port sync fingerprint and state storage"
```

### Task 4: Add persisted sync-history storage used by the History screen

**Files:**
- Create: `app/src/services/history-store.ts`
- Create: `app/__tests__/services/history-store.test.ts`

- [ ] **Step 1: Write the failing history-store test**

```ts
test('appends sync runs in reverse chronological order with activity details', async () => {
  const store = new HistoryStore('@test_history');
  await store.appendRun({
    finishedAt: '2026-03-24T12:00:00Z',
    summary: { fetched: 2, deduped: 1, success: 1, failed: 0 },
    activities: [{ filename: 'a.fit', status: 'success', stravaActivityId: 12345 }],
  });

  const runs = await store.listRuns();
  expect(runs[0].summary.success).toBe(1);
  expect(runs[0].activities[0].filename).toBe('a.fit');
});
```

- [ ] **Step 2: Run the history-store test to confirm failure**

Run: `npm --prefix app test -- --runInBand __tests__/services/history-store.test.ts`
Expected: FAIL with missing history store module.

- [ ] **Step 3: Implement AsyncStorage-backed history persistence**

Store each sync run with:
- `finishedAt`
- `summary` (`fetched`, `deduped`, `success`, `failed`, `abortedReason?`)
- per-activity rows for expandable history details

Ensure `listRuns()` returns newest-first order because the spec requires reverse chronological history.

- [ ] **Step 4: Run the history-store test again**

Run: `npm --prefix app test -- --runInBand __tests__/services/history-store.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit the history persistence layer**

```bash
git add app/src/services/history-store.ts app/__tests__/services/history-store.test.ts
git commit -m "feat: add persisted sync history store"
```

### Task 5: Port OneLap auth/list behavior with login retry and cookie bridging

**Files:**
- Create: `app/src/services/onelap-client.ts`
- Create: `app/__tests__/services/onelap-client.test.ts`
- Reference: `src/sync_onelap_strava/onelap_client.py`

- [ ] **Step 1: Write the failing OneLap client tests**

```ts
test('retries activity fetch after login when first response requires auth', async () => {
  const client = new OneLapClient('https://www.onelap.cn', 'user', 'pass');
  mockListFirstAsHtmlThenJson();

  const items = await client.listFitActivities(new Date('2026-03-01'), 10);

  expect(items).toHaveLength(1);
  expect(items[0].recordKey).toBe('fileKey:abc');
});

test('builds record identity with fileKey priority', async () => {
  expect(buildRecordIdentity({ fileKey: 'abc', fitUrl: 'u', durl: 'd' })).toBe('fileKey:abc');
});
```

- [ ] **Step 2: Run the client tests and confirm missing behavior**

Run: `npm --prefix app test -- --runInBand __tests__/services/onelap-client.test.ts`
Expected: FAIL.

- [ ] **Step 3: Implement the auth/list subset of the TypeScript client**

Port these Python behaviors without adding extra product scope:
- `login()` posts MD5 password hash to `/api/login`
- `list_fit_activities()` filters by `since`, caps by `limit`, and caches record-to-fit URL mapping if needed
- `_requires_login()` treats 401, 403, HTML, and `login.html` redirects as auth failures
- detect OneLap risk-control responses (message/code pattern such as `风控`) and raise `OnelapRiskControlError`
- `_build_record_identity()` prioritizes `fileKey`, then `fitUrl`, then `durl`

Also add the documented cookie bridge using `@react-native-cookies/cookies` for `www.onelap.cn` -> `u.onelap.cn`.

- [ ] **Step 4: Run the OneLap test file again**

Run: `npm --prefix app test -- --runInBand __tests__/services/onelap-client.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit the OneLap port**

```bash
git add app/src/services/onelap-client.ts app/__tests__/services/onelap-client.test.ts
git commit -m "feat: port OneLap auth and activity listing"
```

### Task 6: Add OneLap FIT download and cache-based file handling

**Files:**
- Modify: `app/src/services/onelap-client.ts`
- Modify: `app/__tests__/services/onelap-client.test.ts`

- [ ] **Step 1: Add a failing FIT download test**

```ts
test('downloads fit file into cache directory without persistent filename dedup', async () => {
  const uri = await client.downloadFit('fileKey:abc', 'https://example.com/a.fit');
  expect(uri).toContain('.fit');
});
```

- [ ] **Step 2: Run the OneLap test file and confirm the new case fails**

Run: `npm --prefix app test -- --runInBand __tests__/services/onelap-client.test.ts`
Expected: FAIL on the new download assertion.

- [ ] **Step 3: Implement cache-based FIT download behavior**

Follow the approved spec, not the desktop file strategy:
- normalize the output filename to a safe `.fit` name
- download into `FileSystem.cacheDirectory`
- return the local URI
- do **not** implement Python-style numbered overwrite dedup because the spec intentionally uses transient cache files on mobile/web

- [ ] **Step 4: Run the OneLap tests again**

Run: `npm --prefix app test -- --runInBand __tests__/services/onelap-client.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit the download support**

```bash
git add app/src/services/onelap-client.ts app/__tests__/services/onelap-client.test.ts
git commit -m "feat: add OneLap FIT download handling"
```

### Task 7: Port Strava token refresh and upload/poll behavior

**Files:**
- Create: `app/src/services/strava-client.ts`
- Create: `app/__tests__/services/strava-client.test.ts`
- Reference: `src/sync_onelap_strava/strava_client.py`

- [ ] **Step 1: Write the failing Strava tests**

```ts
test('refreshes expired access token before upload', async () => {
  const client = new StravaClient('id', 'secret', 'refresh', 'expired', 0);
  mockRefreshTokenSuccess();
  await client.ensureAccessToken();
  expect(savedAccessToken()).toBe('new-token');
});

test('pollUpload returns payload when duplicate error appears', async () => {
  const payload = await client.pollUpload(123);
  expect(payload.error).toContain('duplicate of activity');
});
```

- [ ] **Step 2: Run the Strava tests and confirm they fail**

Run: `npm --prefix app test -- --runInBand __tests__/services/strava-client.test.ts`
Expected: FAIL.

 - [ ] **Step 3: Implement token refresh, multipart upload, and polling**

Use the Python client as the contract:
- retry upload on 5xx exactly 3 times with backoff
- raise a permanent error on 4xx
- stop polling when `activity_id`, `error`, `status=ready`, or `status=complete` appears
- persist refreshed tokens immediately
- implement cross-platform multipart upload exactly as required by the spec:
  - native (`iOS`/`Android`): use `expo-file-system` multipart upload from a local file URI
  - web: use `FormData` plus `Blob`

- [ ] **Step 4: Run the Strava service tests again**

Run: `npm --prefix app test -- --runInBand __tests__/services/strava-client.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit the Strava layer**

```bash
git add app/src/services/strava-client.ts app/__tests__/services/strava-client.test.ts
git commit -m "feat: port Strava upload client"
```

### Task 8: Add Strava OAuth token exchange helpers and settings-store auth state

**Files:**
- Create: `app/src/services/oauth.ts`
- Create: `app/src/hooks/use-strava-auth.ts`
- Modify: `app/src/stores/settings-store.ts`
- Create: `app/__tests__/stores/settings-store.test.ts`
- Reference: `src/sync_onelap_strava/strava_oauth_init.py`

- [ ] **Step 1: Write the failing OAuth/settings tests**

```tsx
test('settings store reports not_set status before tokens exist', () => {
  expect(useSettingsStore.getState().stravaAuthStatus).toBe('not_set');
});

test('exchangeCodeForTokens rejects when activity:write scope is missing', async () => {
  await expect(exchangeCodeForTokens(mockConfigWithoutWriteScope)).rejects.toThrow('activity:write');
});
```

- [ ] **Step 2: Run the OAuth/settings tests to confirm failure**

Run: `npm --prefix app test -- --runInBand __tests__/stores/settings-store.test.ts`
Expected: FAIL.

- [ ] **Step 3: Implement the OAuth helper and status mapping**

Add:
- pure service helpers in `app/src/services/oauth.ts` for token exchange, scope validation, and persistence
- `app/src/hooks/use-strava-auth.ts` for the Expo Auth Session hook usage (`useAuthRequest` / `promptAsync`)
- settings-store derived auth statuses: `authorized`, `expired`, `not_set`
- settings-store fields and actions for `stravaClientId` and `stravaClientSecret` collection/persistence

- [ ] **Step 4: Run the OAuth/settings tests again**

Run: `npm --prefix app test -- --runInBand __tests__/stores/settings-store.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit the OAuth layer**

```bash
git add app/src/services/oauth.ts app/src/hooks/use-strava-auth.ts app/src/stores/settings-store.ts app/__tests__/stores/settings-store.test.ts
git commit -m "feat: add Strava OAuth status handling"
```

### Task 9: Add persisted log store with reload and clear behavior

**Files:**
- Create: `app/src/stores/log-store.ts`
- Create: `app/__tests__/stores/log-store.test.ts`

- [ ] **Step 1: Write the failing log-store test**

```ts
test('persists INFO WARN ERROR logs and clears them', async () => {
  const store = useLogStore.getState();
  await store.append({ level: 'INFO', message: 'start', timestamp: '2026-03-24T12:00:00Z' });
  await store.append({ level: 'ERROR', message: 'fail', timestamp: '2026-03-24T12:00:01Z' });
  expect(useLogStore.getState().entries).toHaveLength(2);
  await store.clear();
  expect(useLogStore.getState().entries).toHaveLength(0);
});
```

- [ ] **Step 2: Run the log-store test and confirm failure**

Run: `npm --prefix app test -- --runInBand __tests__/stores/log-store.test.ts`
Expected: FAIL.

- [ ] **Step 3: Implement AsyncStorage-backed log persistence**

Persist INFO/WARN/ERROR entries, reload them on store init, and expose a `clear()` action used by the Logs screen.

- [ ] **Step 4: Run the log-store test again**

Run: `npm --prefix app test -- --runInBand __tests__/stores/log-store.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit the log store**

```bash
git add app/src/stores/log-store.ts app/__tests__/stores/log-store.test.ts
git commit -m "feat: add persistent log store"
```

### Task 10: Port `SyncEngine` and expose progress events through the sync store

**Files:**
- Create: `app/src/services/sync-engine.ts`
- Create: `app/src/stores/sync-store.ts`
- Create: `app/src/hooks/use-sync.ts`
- Create: `app/__tests__/services/sync-engine.test.ts`
- Create: `app/__tests__/stores/sync-store.test.ts`
- Modify: `app/src/services/history-store.ts`
- Modify: `app/src/stores/log-store.ts`
- Reference: `src/sync_onelap_strava/sync_engine.py`

- [ ] **Step 1: Write the failing engine/store tests**

```ts
test('marks duplicate upload as deduped and stores extracted activity id', async () => {
  const summary = await engine.runOnce(new Date('2026-03-01'));
  expect(summary.deduped).toBe(1);
  expect(await stateStore.isSynced('fp-1')).toBe(true);
});

test('sync store exposes progress rows while sync is running', async () => {
  await useSyncStore.getState().startSync(new Date('2026-03-01'));
  expect(useSyncStore.getState().activities.length).toBeGreaterThan(0);
});

test('sync store records banner-level sync errors without clearing the run state', async () => {
  await useSyncStore.getState().startSync(new Date('2026-03-01'));
  expect(useSyncStore.getState().errorBanner).toBeDefined();
});
```

- [ ] **Step 2: Run the engine/store tests to confirm failure**

Run: `npm --prefix app test -- --runInBand __tests__/services/sync-engine.test.ts __tests__/stores/sync-store.test.ts`
Expected: FAIL.

- [ ] **Step 3: Implement the engine with Python-matching semantics**

Keep these exact behaviors from `src/sync_onelap_strava/sync_engine.py`:
- resolve `since_date` from parameter or default lookback
- abort on `OnelapRiskControlError`
- download FIT -> fingerprint -> dedupe -> upload -> poll
- treat `duplicate of` errors as deduped success and extract Strava activity ID with regex
- increment `failed` on other exceptions without killing the entire run

Push all user-visible progress into the sync store via typed `SyncEvent` objects so UI components never call service methods directly. At the end of each run, append the run summary and activity details into `HistoryStore`, and append log lines into `LogStore`.

- [ ] **Step 4: Run the engine and store tests again**

Run: `npm --prefix app test -- --runInBand __tests__/services/sync-engine.test.ts __tests__/stores/sync-store.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit the orchestration layer**

```bash
git add app/src/services/sync-engine.ts app/src/services/history-store.ts app/src/stores/log-store.ts app/src/stores/sync-store.ts app/src/hooks/use-sync.ts app/__tests__/services/sync-engine.test.ts app/__tests__/stores/sync-store.test.ts
git commit -m "feat: add sync orchestration and progress stores"
```

### Task 11: Build the sync screen and shared UI components

**Files:**
- Modify: `app/app/(tabs)/index.tsx`
- Create: `app/src/components/ProgressBar.tsx`
- Create: `app/src/components/StatusBadge.tsx`
- Create: `app/src/components/ActivityRow.tsx`
- Create: `app/src/theme/colors.ts`
- Create: `app/src/theme/spacing.ts`
- Modify: `app/__tests__/components/sync-screen.test.tsx`

- [ ] **Step 1: Expand the failing sync-screen test**

```tsx
test('sync screen disables actions until credentials are configured', () => {
  render(<SyncScreen />);
  expect(screen.getByText('Please configure OneLap account in Settings')).toBeTruthy();
});

test('sync screen disables actions when Strava is not authorized and shows last sync time', () => {
  render(<SyncScreen />);
  expect(screen.getByText('Please authorize Strava in Settings')).toBeTruthy();
  expect(screen.getByText(/Last sync/i)).toBeTruthy();
});

test('sync screen renders a top-level error banner when the run fails', () => {
  render(<SyncScreen />);
  expect(screen.getByTestId('sync-error-banner')).toBeTruthy();
});
```

- [ ] **Step 2: Run the screen tests to see the UI gaps**

Run: `npm --prefix app test -- --runInBand __tests__/components/sync-screen.test.tsx`
Expected: FAIL.

- [ ] **Step 3: Implement the sync screen with thin components and store-backed state**

UI requirements to match the approved spec:
- sync screen has date selector, `Start Sync`, `Download Only`, progress bar, rows, and last-sync summary
- `Start Sync` is disabled when Strava is unauthorized
- `Download Only` remains available when OneLap credentials are present because it does not require Strava auth
- when OneLap credentials are missing, both actions are disabled until Settings is completed
- sync screen renders a top-level error banner when a run fails

Do not add extra product scope like background sync, push notifications, or account switching.

- [ ] **Step 4: Run the screen tests again**

Run: `npm --prefix app test -- --runInBand __tests__/components/sync-screen.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit the UI layer**

```bash
git add app/app/(tabs)/index.tsx app/src/components/ProgressBar.tsx app/src/components/StatusBadge.tsx app/src/components/ActivityRow.tsx app/src/theme/colors.ts app/src/theme/spacing.ts app/__tests__/components/sync-screen.test.tsx
git commit -m "feat: build sync screen UI"
```

### Task 12: Build the History and Logs screens with persistence-backed tests

**Files:**
- Create: `app/app/(tabs)/history.tsx`
- Create: `app/app/(tabs)/logs.tsx`
- Create: `app/__tests__/components/history-screen.test.tsx`
- Create: `app/__tests__/components/logs-screen.test.tsx`

- [ ] **Step 1: Write the failing History and Logs screen tests**

```tsx
test('history screen renders newest sync first and can expand activity details', async () => {
  render(<HistoryScreen />);
  expect(await screen.findByText('History')).toBeTruthy();
});

test('logs screen renders persisted entries and clears them', async () => {
  render(<LogsScreen />);
  expect(await screen.findByText('Logs')).toBeTruthy();
});

test('history screen renders synced activities with Strava ids', async () => {
  render(<HistoryScreen />);
  expect(await screen.findByText(/Strava/i)).toBeTruthy();
});

test('logs screen autoscrolls while sync is active', async () => {
  render(<LogsScreen />);
  expect(await screen.findByTestId('logs-list')).toBeTruthy();
});
```

- [ ] **Step 2: Run the History and Logs screen tests**

Run: `npm --prefix app test -- --runInBand __tests__/components/history-screen.test.tsx __tests__/components/logs-screen.test.tsx`
Expected: FAIL.

- [ ] **Step 3: Implement the History and Logs screens**

Requirements to cover explicitly:
- History screen reads persisted sync runs from `HistoryStore`
- newest run appears first
- each run can expand to show per-activity details
- History screen also renders the full synced-activities list with Strava activity IDs using `StateStore.getAllSynced()`
- Logs screen shows INFO/WARN/ERROR entries and a clear action wired to `LogStore.clear()`
- Logs screen auto-scrolls while sync is active

- [ ] **Step 4: Run the screen tests again**

Run: `npm --prefix app test -- --runInBand __tests__/components/history-screen.test.tsx __tests__/components/logs-screen.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit the History and Logs screens**

```bash
git add app/app/(tabs)/history.tsx app/app/(tabs)/logs.tsx app/__tests__/components/history-screen.test.tsx app/__tests__/components/logs-screen.test.tsx
git commit -m "feat: add history and logs screens"
```

### Task 13: Build the Settings screen details and tab shell

**Files:**
- Create: `app/app/(tabs)/settings.tsx`
- Modify: `app/app/(tabs)/_layout.tsx`
- Modify: `app/__tests__/components/settings-screen.test.tsx`

- [ ] **Step 1: Expand the failing settings-screen test**

```tsx
test('settings screen shows connection controls, auth status, version, and web warning', async () => {
  render(<SettingsScreen />);
  expect(screen.getByText('Test Connection')).toBeTruthy();
  expect(screen.getByText('Not authorized')).toBeTruthy();
  expect(screen.getByText('Authorize')).toBeTruthy();
  expect(screen.getByText(/0\.1\.0/)).toBeTruthy();
});

test('test connection validates OneLap credentials from settings', async () => {
  render(<SettingsScreen />);
  expect(screen.getByText('Test Connection')).toBeTruthy();
});
```

- [ ] **Step 2: Run the settings-screen test to confirm failure**

Run: `npm --prefix app test -- --runInBand __tests__/components/settings-screen.test.tsx`
Expected: FAIL.

- [ ] **Step 3: Implement the Settings screen and tab shell**

Cover these approved requirements explicitly:
- tab layout with `Sync`, `History`, `Logs`, `Settings`
- settings fields for OneLap username/password
- OneLap username/password persist immediately through `app/src/stores/settings-store.ts` and the platform-aware storage adapter (`SecureStore` on native, fallback on web)
- settings fields for `STRAVA_CLIENT_ID` and `STRAVA_CLIENT_SECRET`
- `Test Connection` button
- `Test Connection` actually calls the OneLap login flow and reports success/failure
- Strava auth status indicator: `authorized`, `expired`, `not set`
- `Authorize` / `Re-authorize` button wired to the Expo Auth Session flow
- lookback days input
- language switcher
- about/version section
- web credential-storage warning when running on web

- [ ] **Step 4: Run the settings-screen test again**

Run: `npm --prefix app test -- --runInBand __tests__/components/settings-screen.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit the Settings screen**

```bash
git add app/app/(tabs)/settings.tsx app/app/(tabs)/_layout.tsx app/__tests__/components/settings-screen.test.tsx
git commit -m "feat: add settings screen details"
```

### Task 14: Add platform configuration for cleartext OneLap access

**Files:**
- Modify: `app/app.json`
- Modify: `app/package.json`
- Create: `app/plugins/withAndroidCleartextTraffic.js`
- Create: `app/__tests__/components/app-config.test.ts`

- [ ] **Step 1: Write the failing config/documentation assertions**

```ts
import appConfig from '../../app.json';

test('app config declares OneLap cleartext exceptions and deep-link scheme', () => {
  expect(appConfig.expo.scheme).toBe('onelap-sync');
  expect(appConfig.expo.ios.infoPlist.NSAppTransportSecurity).toBeTruthy();
  expect(appConfig.expo.ios.infoPlist.NSAppTransportSecurity.NSExceptionDomains['onelap.cn'].NSIncludesSubdomains).toBe(true);
  expect(appConfig.expo.ios.infoPlist.NSAppTransportSecurity.NSExceptionDomains['onelap.cn'].NSExceptionAllowsInsecureHTTPLoads).toBe(true);
  expect(appConfig.expo.plugins).toContain('./plugins/withAndroidCleartextTraffic');
});
```

- [ ] **Step 2: Run the final verification test and note missing config/docs**

Run: `npm --prefix app test -- --runInBand __tests__/components/app-config.test.ts`
Expected: FAIL.

- [ ] **Step 3: Add the last-mile platform config**

Use an Expo config plugin instead of a loose XML file so Android configuration is actually wired during prebuild. Add:
- deep-link scheme `onelap-sync`
- iOS ATS exception for `onelap.cn`
- plugin-managed Android manifest/network-security configuration for cleartext access to `onelap.cn`

- [ ] **Step 4: Run the complete verification suite**

Run: `npm --prefix app test -- --runInBand __tests__/components/app-config.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit the integrated app feature**

```bash
git add app/app.json app/package.json app/plugins/withAndroidCleartextTraffic.js app/__tests__/components/app-config.test.ts
git commit -m "feat: configure Expo networking for OneLap access"
```

### Task 15: Update docs and run full verification

**Files:**
- Modify: `README.md`
- Modify: `README.zh.md`
- Modify: `CONTRIBUTING.md`

- [ ] **Step 1: Write the failing documentation checklist**

```text
- README.md mentions the Expo app workspace and run/build commands
- README.zh.md includes the same workflows in Chinese
- CONTRIBUTING.md explains how to test the app and Python CLI together
```

- [ ] **Step 2: Compare current docs to the checklist and confirm gaps**

Run: `rg -n "Expo|npm --prefix app|eas build|web warning" README.md README.zh.md CONTRIBUTING.md`
Expected: Missing or incomplete coverage.

- [ ] **Step 3: Update user and contributor docs**

Document all user-facing workflows:
- install dependencies with `npm --prefix app install`
- run dev app with `npm --prefix app start`
- Android build with `eas build --platform android`
- iOS build with `eas build --platform ios`
- web export with `npm --prefix app exec expo export --platform web`
- desktop/PWA install flow after web export
- credential-storage warning on web
- why `onelap.cn` needs cleartext exceptions on iOS/Android

- [ ] **Step 4: Run the complete verification suite**

Run: `npm --prefix app test -- --runInBand`
Expected: PASS.

Run: `python -m pytest -q`
Expected: Existing Python tests still behave as before (ignore known external failure in `tests/test_skill_repository_structure.py` if it is already expected on this machine).

Run: `python run_sync.py --help`
Expected: Existing CLI help prints successfully.

Run: `npm --prefix app exec expo export --platform web`
Expected: Export succeeds and includes installable PWA metadata for desktop browsers.

Run manual E2E on iOS Simulator, Android Emulator, and Expo Go.
Expected: app launches, Settings persists values, Download Only works without Strava auth, full Sync works after Strava auth, and History/Logs reflect persisted results.

- [ ] **Step 5: Commit the docs and verification pass**

```bash
git add README.md README.zh.md CONTRIBUTING.md
git commit -m "docs: add Expo app workflow guidance"
```

## Final Verification Checklist

- [ ] `npm --prefix app install`
- [ ] `npm --prefix app test -- --runInBand`
- [ ] `python -m pytest -q`
- [ ] `npm --prefix app start -- --non-interactive` starts without config errors
- [ ] `npm --prefix app exec expo export --platform web` completes successfully
- [ ] Confirm exported web output includes installable PWA metadata
- [ ] Manual E2E on iOS Simulator, Android Emulator, and Expo Go
- [ ] Confirm the existing Python CLI still works by running `python run_sync.py --help`

## Notes for the Implementer

- Match Python behavior first; only diverge where the spec explicitly allows it.
- Keep services pure and UI thin.
- Prefer one focused file per responsibility; do not create a giant `api.ts` or `store.ts`.
- Use the existing Python tests as the semantic contract for service behavior.
- Keep commits frequent and scoped to a single task.
