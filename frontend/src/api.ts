// The backend may run on either port. Setting VITE_API_BASE_URL pins a single address instead.
const API_BASE_URLS: string[] = import.meta.env.VITE_API_BASE_URL
  ? [import.meta.env.VITE_API_BASE_URL]
  : ['http://127.0.0.1:8001', 'http://127.0.0.1:8002']
let activeBaseUrl = API_BASE_URLS[0]
export const ACCOUNT_STORAGE_KEY = 'smart-lagring-account'

export type Account = {
  name: string
  email: string
  role: string
  access_token: string
}

type ApiOptions = RequestInit & {
  authenticated?: boolean
  json?: unknown
  errorMessage?: string
}

export function storedAccount(): Account | null {
  try {
    const account = JSON.parse(localStorage.getItem(ACCOUNT_STORAGE_KEY) || 'null')
    return account &&
      typeof account.name === 'string' &&
      typeof account.email === 'string' &&
      typeof account.role === 'string' &&
      typeof account.access_token === 'string' &&
      account.access_token
      ? (account as Account)
      : null
  } catch {
    return null
  }
}

// Tries the address that worked last, then the others, and only when nothing answers at all.
async function fetchFromBackend(path: string, init: RequestInit): Promise<Response> {
  const candidates = [activeBaseUrl, ...API_BASE_URLS.filter((url) => url !== activeBaseUrl)]
  let unreachable: unknown
  for (const baseUrl of candidates) {
    try {
      const response = await fetch(`${baseUrl}${path}`, init)
      activeBaseUrl = baseUrl
      return response
    } catch (error) {
      unreachable = error
    }
  }
  throw unreachable
}

export async function apiRequest(path: string, options: ApiOptions = {}): Promise<Response> {
  const { authenticated, json, errorMessage, ...requestOptions } = options
  const headers = new Headers(requestOptions.headers)

  if (json !== undefined) headers.set('Content-Type', 'application/json')
  if (authenticated) {
    const token = storedAccount()?.access_token
    if (token) headers.set('Authorization', `Bearer ${token}`)
  }

  const response = await fetchFromBackend(path, {
    ...requestOptions,
    headers,
    ...(json !== undefined ? { body: JSON.stringify(json) } : {}),
  })

  if (!response.ok) {
    const result = await response.json().catch(() => null)
    // FastAPI sends a string for our own errors and a list of objects for validation errors.
    const detail =
      typeof result?.detail === 'string'
        ? result.detail
        : Array.isArray(result?.detail)
          ? 'Kontrollera att alla fält är korrekt ifyllda.'
          : ''
    throw new Error(detail || errorMessage || `Request failed (${response.status}).`)
  }

  return response
}

export async function apiJson<T>(path: string, options?: ApiOptions): Promise<T> {
  return (await apiRequest(path, options)).json() as Promise<T>
}

export function errorText(reason: unknown, fallback: string) {
  return reason instanceof Error ? reason.message : fallback
}

// Callers that arrive while a load is running share it instead of starting another request.
export function shareInFlight(load: () => Promise<void>) {
  let pending: Promise<void> | null = null
  return () => (pending ??= load().finally(() => (pending = null)))
}
