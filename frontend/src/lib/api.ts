import { z } from 'zod'

export const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, schema: z.ZodType<T>, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: { Accept: 'application/json', 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!res.ok) {
    let message = res.statusText
    try {
      const body: unknown = await res.json()
      if (body && typeof body === 'object' && 'detail' in body) {
        const detail = body.detail
        message = Array.isArray(detail)
          ? detail.map((d: { msg?: string }) => d.msg ?? String(d)).join('; ')
          : String(detail)
      }
    } catch {
      // keep the status text
    }
    throw new ApiError(res.status, message)
  }
  return schema.parse(await res.json())
}

/** GET JSON from the backend and validate it against a Zod schema at the boundary. */
export function apiGet<T>(path: string, schema: z.ZodType<T>): Promise<T> {
  return request(path, schema)
}

export function apiPost<T>(path: string, schema: z.ZodType<T>, body?: unknown): Promise<T> {
  return request(path, schema, {
    method: 'POST',
    body: body === undefined ? undefined : JSON.stringify(body),
  })
}

export function apiPut<T>(path: string, schema: z.ZodType<T>, body: unknown): Promise<T> {
  return request(path, schema, { method: 'PUT', body: JSON.stringify(body) })
}

/** Link to a stored source document, opened at a page when given. */
export function documentUrl(documentId: string, page?: number | null): string {
  return `${BASE_URL}/documents/${documentId}/file${page ? `#page=${page}` : ''}`
}
