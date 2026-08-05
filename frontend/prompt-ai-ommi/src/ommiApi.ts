/**
 * ommiApi.ts — lớp gọi API duy nhất của PROMPT AI OMMI.
 *
 * Không component nào tự gọi `fetch`. Một chỗ gọi nghĩa là một chỗ gắn CSRF,
 * một chỗ dịch lỗi sang tiếng người dùng, và một chỗ để sửa khi hợp đồng đổi.
 */

const BASE = '/prompt-ai-ommi/api'

export const RESOURCE_KINDS = ['character', 'background', 'prop', 'vehicle', 'misc'] as const
export type ResourceKind = (typeof RESOURCE_KINDS)[number]

/** Nhãn tiếng Việt cho từng nhóm — khớp ô "Phân loại tài nguyên". */
export const KIND_LABEL: Record<string, string> = {
  character: 'Nhân vật',
  background: 'Bối cảnh',
  prop: 'Đạo cụ',
  vehicle: 'Phương tiện',
  misc: 'Khác',
}

export type Variant = {
  id: string
  label: string
  storage_key: string
  thumb_key: string
  width: number
  height: number
  bytes_size: number
  position: number
}

export type Resource = {
  id: string
  kind: ResourceKind
  name: string
  description: string
  prompt_text: string
  attributes: Record<string, unknown>
  cover_variant_id: string
  is_catalog: boolean
  archived: boolean
  updated_at: string
  variants?: Variant[]
  tags?: string[]
}

export type ResourcePage = {
  items: Resource[]
  total: number
  limit: number
  offset: number
  counts: Record<string, number>
  kinds: string[]
}

export class ApiError extends Error {
  readonly status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

let csrf = ''
export function setCsrfToken(token: string): void {
  csrf = token
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method ?? 'GET').toUpperCase()
  const headers = new Headers(init.headers)
  if (method !== 'GET') headers.set('X-CSRF-Token', csrf)
  if (init.body && !(init.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }
  const response = await fetch(`${BASE}${path}`, { ...init, headers })
  if (!response.ok) {
    // Máy chủ trả `detail` bằng tiếng Việt; dùng thẳng thay vì dịch lại ở đây,
    // để thông báo người dùng thấy khớp với thứ máy chủ thật sự từ chối.
    let detail = `Lỗi ${response.status}`
    try {
      const body = await response.json()
      if (typeof body?.detail === 'string') detail = body.detail
    } catch {
      /* phản hồi không phải JSON — giữ thông báo mặc định */
    }
    throw new ApiError(response.status, detail)
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export function listResources(params: {
  kind?: string
  q?: string
  archived?: boolean
  limit?: number
  offset?: number
} = {}): Promise<ResourcePage> {
  const query = new URLSearchParams()
  if (params.kind) query.set('kind', params.kind)
  if (params.q) query.set('q', params.q)
  if (params.archived) query.set('archived', 'true')
  query.set('limit', String(params.limit ?? 40))
  query.set('offset', String(params.offset ?? 0))
  return request<ResourcePage>(`/resources?${query.toString()}`)
}

export function getResource(id: string): Promise<Resource> {
  return request<Resource>(`/resources/${id}`)
}

export function createResource(body: {
  kind: string
  name: string
  description?: string
  prompt_text?: string
}): Promise<Resource> {
  return request<Resource>('/resources', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function updateResource(
  id: string,
  body: Partial<Pick<Resource, 'name' | 'kind' | 'description' | 'prompt_text'>> & {
    tags?: string[]
  },
): Promise<Resource> {
  return request<Resource>(`/resources/${id}`, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export function archiveResource(id: string, archived: boolean): Promise<Resource> {
  return request<Resource>(`/resources/${id}/archive`, {
    method: 'POST',
    body: JSON.stringify({ archived }),
  })
}

export function uploadImage(id: string, file: File, label = ''): Promise<Variant> {
  const form = new FormData()
  form.set('csrf_token', csrf)
  form.set('label', label)
  form.set('file', file)
  return request<Variant>(`/resources/${id}/images`, { method: 'POST', body: form })
}

export function deleteImage(resourceId: string, variantId: string): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>(`/resources/${resourceId}/images/${variantId}`, {
    method: 'DELETE',
  })
}

/**
 * Đường dẫn xem ảnh. Máy chủ trả URL app tự phục vụ (hoặc redirect sang CDN khi
 * có R2) — KHÔNG phải token, vì token của storage chỉ sống trong RAM của một
 * tiến trình và web/worker là hai tiến trình khác nhau.
 */
export function imageUrl(
  resourceId: string,
  variantId: string,
): Promise<{ url?: string }> {
  return request(`/resources/${resourceId}/images/${variantId}/url`)
}

export type Quote = {
  credit: number
  count: number
  reference_count: number
  confirmed: false
}
export type StartedJob = { id: string; status: string; credit: number }

/**
 * Báo giá khi `confirmed` là false, chạy khi true. Cùng một endpoint để con số
 * người dùng thấy và con số bị trừ không thể lệch nhau.
 */
export function generateImage(
  id: string,
  body: {
    prompt?: string
    count?: number
    aspect_ratio?: string
    reference_variant_ids?: string[]
    confirmed?: boolean
  },
): Promise<Quote | StartedJob> {
  return request(`/resources/${id}/images/generate`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function attachJobImages(id: string, jobId: string): Promise<{ variants: Variant[] }> {
  return request(`/resources/${id}/images/from-job`, {
    method: 'POST',
    body: JSON.stringify({ job_id: jobId }),
  })
}

export type JobStatus = {
  id: string
  status: string
  progress: number
  progress_msg: string
  error: string
  result: { image_keys?: string[] } | null
}

export function jobStatus(jobId: string): Promise<JobStatus> {
  return request<JobStatus>(`/jobs/${jobId}`)
}

// ── Thư viện: meta prompt / đoạn prompt / phong cách ────────────────────────

export type LibraryKind = 'meta' | 'snippet' | 'style'

export type LibraryItem = {
  id: string
  kind: LibraryKind
  name: string
  body: string
  is_catalog: boolean
  cloned_from_id: string
  archived: boolean
  updated_at: string
  purpose?: string
  category?: string
  negative?: string
  version?: number
  versions?: Array<{ version: number; note: string; created_at: string }>
}

export type LibraryPage = {
  items: LibraryItem[]
  total: number
  catalog: boolean
  counts: Record<string, number>
}

export function listLibrary(
  kind: LibraryKind,
  params: { q?: string; catalog?: boolean } = {},
): Promise<LibraryPage> {
  const query = new URLSearchParams()
  if (params.q) query.set('q', params.q)
  if (params.catalog) query.set('catalog', 'true')
  return request<LibraryPage>(`/library/${kind}?${query.toString()}`)
}

export function getLibraryItem(kind: LibraryKind, id: string): Promise<LibraryItem> {
  return request<LibraryItem>(`/library/${kind}/${id}`)
}

export function createLibraryItem(
  kind: LibraryKind,
  body: { name: string; body?: string },
): Promise<LibraryItem> {
  return request<LibraryItem>(`/library/${kind}`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function updateLibraryItem(
  kind: LibraryKind,
  id: string,
  body: { name?: string; body?: string; note?: string },
): Promise<LibraryItem> {
  return request<LibraryItem>(`/library/${kind}/${id}`, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export function archiveLibraryItem(
  kind: LibraryKind,
  id: string,
  archived: boolean,
): Promise<LibraryItem> {
  return request<LibraryItem>(`/library/${kind}/${id}/archive`, {
    method: 'POST',
    body: JSON.stringify({ archived }),
  })
}

/** "Dùng mẫu này" — tạo bản sao riêng của người dùng từ một mẫu catalog. */
export function cloneLibraryItem(kind: LibraryKind, id: string): Promise<LibraryItem> {
  return request<LibraryItem>(`/library/${kind}/${id}/clone`, {
    method: 'POST',
    body: JSON.stringify({}),
  })
}
