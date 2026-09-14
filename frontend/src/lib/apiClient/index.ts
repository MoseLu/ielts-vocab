// Public barrel for the apiClient module. Callers should import from
// '@/lib/apiClient' (which is re-exported through src/lib/index.ts) so the
// transport/authRefresh split remains a private implementation detail.
//
// Surface kept stable for backward compatibility with the legacy
// src/lib/apiClient.ts barrel:
//   apiFetch, apiRequest, buildApiUrl, refreshAuthSession,
//   setAuthSessionActive, setAuthAccessExpiry,
//   __setApiBaseOverrideForTests, ApiRequestOptions.

export { apiFetch, apiRequest, buildApiUrl, __setApiBaseOverrideForTests, setAuthSessionActive } from './transport'
export { refreshAuthSession, setAuthAccessExpiry } from './authRefresh'
export type { ApiRequestOptions } from './types'
