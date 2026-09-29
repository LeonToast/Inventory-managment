const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8001'
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

export async function apiRequest(path: string, options: ApiOptions = {}): Promise<Response> {
  const { authenticated, json, errorMessage, ...requestOptions } = options
  const headers = new Headers(requestOptions.headers)

  if (json !== undefined) headers.set('Content-Type', 'application/json')
  if (authenticated) {
    const token = storedAccount()?.access_token
    if (token) headers.set('Authorization', `Bearer ${token}`)
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...requestOptions,
    headers,
    ...(json !== undefined ? { body: JSON.stringify(json) } : {}),
  })

  if (!response.ok) {
    const result = await response.json().catch(() => null)
    throw new Error(result?.detail || errorMessage || `Request failed (${response.status}).`)
  }

  return response
}

export async function apiJson<T>(path: string, options?: ApiOptions): Promise<T> {
  return (await apiRequest(path, options)).json() as Promise<T>
}
