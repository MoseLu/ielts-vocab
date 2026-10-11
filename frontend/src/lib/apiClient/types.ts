// Public type surface for the apiClient module.
//
// Keeping types in their own file avoids a circular import between
// transport.ts (which needs ApiRequestOptions) and authRefresh.ts (which
// imports buildApiUrl from transport.ts).
export interface ApiRequestOptions extends RequestInit {
  skipAuthRefresh?: boolean
  timeoutMs?: number
  traceId?: string
  idempotencyKey?: string
}
