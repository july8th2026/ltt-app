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

/**
 * Huỷ và thử lại nằm ở NỀN TẢNG (`/jobs/...`), không phải trong app: hàng đợi
 * job là của nền tảng, và mỗi app tự dựng lại hai đường này là ba bản sao của
 * cùng một quy tắc hoàn credit.
 */
async function platformJobAction(jobId: string, action: 'cancel' | 'retry') {
  const response = await fetch(`/jobs/${jobId}/${action}`, {
    method: 'POST',
    headers: { 'X-CSRF-Token': csrf, 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  })
  if (!response.ok) {
    let detail = `Lỗi ${response.status}`
    try {
      const body = await response.json()
      if (typeof body?.detail === 'string') detail = body.detail
    } catch {
      /* phản hồi không phải JSON — giữ thông báo theo mã lỗi */
    }
    throw new ApiError(response.status, detail)
  }
  return (await response.json()) as { job_id?: string; status?: string }
}

/** Dừng một job đang chạy. Nền tảng hoàn lại phần credit đã giữ chỗ. */
export function cancelJob(jobId: string) {
  return platformJobAction(jobId, 'cancel')
}

/** Chạy lại một job đã lỗi/đã huỷ. Nền tảng tạo job MỚI và giữ chỗ credit mới. */
export function retryJob(jobId: string) {
  return platformJobAction(jobId, 'retry')
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


// ── Storyboard ──────────────────────────────────────────────────────────────

export type Scene = {
  id: string
  storyboard_id: string
  position: number
  title: string
  prompt: string
  camera: string
  continuity: string
  resource_ids: string[]
  image_key: string
  version: number
}

export type Storyboard = {
  id: string
  project_id: string
  name: string
  meta_prompt_id: string
  style_id: string
  aspect_ratio: string
  archived: boolean
  updated_at: string
  scenes?: Scene[]
}

export type Project = { id: string; name: string; revision: number }

/**
 * Danh sách dự án. Endpoint trả `{items: [...]}` chứ KHÔNG phải mảng trần —
 * khai sai kiểu ở đây làm `projects.length` thành `undefined`, và màn Storyboard
 * báo "chưa có dự án" dù vừa tạo xong. Trình duyệt bắt được; test không, vì mock
 * của test lúc đó mã hoá đúng cái giả định sai này.
 */
export async function listProjects(): Promise<Project[]> {
  return (await request<{ items: Project[] }>('/projects')).items
}

export function listStoryboards(projectId = ''): Promise<{ items: Storyboard[] }> {
  const query = projectId ? `?project_id=${encodeURIComponent(projectId)}` : ''
  return request(`/storyboards${query}`)
}

export function createStoryboard(body: {
  project_id: string
  name: string
}): Promise<Storyboard> {
  return request<Storyboard>('/storyboards', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function getStoryboard(id: string): Promise<Storyboard> {
  return request<Storyboard>(`/storyboards/${id}`)
}

export function addScene(
  boardId: string,
  body: { title?: string; prompt?: string; camera?: string; resource_ids?: string[] },
): Promise<Scene> {
  return request<Scene>(`/storyboards/${boardId}/scenes`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function updateScene(
  sceneId: string,
  body: Partial<Pick<Scene, 'title' | 'prompt' | 'camera' | 'continuity'>> & {
    resource_ids?: string[]
  },
): Promise<Scene> {
  return request<Scene>(`/scenes/${sceneId}`, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export function deleteScene(sceneId: string): Promise<{ ok: boolean }> {
  return request(`/scenes/${sceneId}`, { method: 'DELETE' })
}

export type SceneQuote = {
  credit: number
  scene_id: string
  reference_count: number
  prompt_preview: string
  confirmed: false
}
export type SceneJob = { id: string; status: string; credit: number; scene_id: string }

/** Báo giá khi `confirmed` false, chạy khi true — cùng một endpoint, một công thức. */
export function renderScene(
  sceneId: string,
  body: { confirmed?: boolean; feedback?: string } = {},
): Promise<SceneQuote | SceneJob> {
  return request(`/scenes/${sceneId}/render`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function attachSceneRender(
  sceneId: string,
  jobId: string,
  feedback = '',
): Promise<Scene> {
  return request<Scene>(`/scenes/${sceneId}/attach/${jobId}`, {
    method: 'POST',
    // Góp ý đi kèm bản được tạo RA từ nó, nên lịch sử trả lời được "vì sao bản
    // này khác bản trước" thay vì bày ra 5 ảnh na ná nhau.
    body: JSON.stringify({ feedback }),
  })
}

export function sceneVersions(
  sceneId: string,
): Promise<{
  items: Array<{
    version: number
    image_key: string
    created_at: string
    feedback?: string
  }>
}> {
  return request(`/scenes/${sceneId}/versions`)
}

export type SceneVersionSide = {
  version: number
  prompt: string
  image_key: string
  feedback: string
  job_id: string
  created_at: string
}
export type SceneCompare = {
  scene_id: string
  left: SceneVersionSide
  right: SceneVersionSide
  prompt_khac_nhau: string[]
  cung_anh: boolean
}

/** Hai bản cạnh nhau. Nhìn từng bản rồi bấm khôi phục là đoán; đây là so. */
export function compareSceneVersions(
  sceneId: string,
  left: number,
  right: number,
): Promise<SceneCompare> {
  return request(`/scenes/${sceneId}/compare?left=${left}&right=${right}`)
}

export function restoreSceneVersion(sceneId: string, version: number): Promise<Scene> {
  return request<Scene>(`/scenes/${sceneId}/restore/${version}`, {
    method: 'POST',
    body: JSON.stringify({}),
  })
}


// ── Tổng quan, Dự án, Chi phí, Cài đặt ──────────────────────────────────────

export type Overview = {
  counts: {
    projects: number
    resources: number
    storyboards: number
    scenes: number
    meta_prompts: number
    styles: number
    snippets: number
  }
  resource_kinds: Record<string, number>
  credit_balance: number
  recent_projects: Array<{ id: string; name: string; revision: number; updated_at: string }>
  recent_jobs: Array<{
    id: string
    status: string
    operation: string
    created_at: string
    error: string
  }>
}

export function getOverview(): Promise<Overview> {
  return request<Overview>('/overview')
}

export type CreditSummary = {
  balance: number
  days: number
  spent: number
  added: number
  entries: Array<{ delta: number; kind: string; note: string; created_at: string }>
}

export function getCredit(days = 30): Promise<CreditSummary> {
  return request<CreditSummary>(`/credit?days=${days}`)
}

export type ProjectDetail = {
  id: string
  name: string
  revision: number
  status: string
  payload: Record<string, unknown>
  updated_at: string
}

export function getProject(id: string): Promise<ProjectDetail> {
  return request<ProjectDetail>(`/projects/${id}`)
}

export function createProject(name: string): Promise<ProjectDetail> {
  return request<ProjectDetail>('/projects', {
    method: 'POST',
    body: JSON.stringify({ name }),
  })
}

export function saveProject(
  id: string,
  body: { revision: number; payload: Record<string, unknown>; name?: string },
): Promise<ProjectDetail> {
  return request<ProjectDetail>(`/projects/${id}`, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export function archiveProject(id: string): Promise<unknown> {
  return request(`/projects/${id}/archive`, {
    method: 'POST',
    body: JSON.stringify({}),
  })
}

export function cloneProject(id: string): Promise<ProjectDetail> {
  return request<ProjectDetail>(`/projects/${id}/clone`, {
    method: 'POST',
    body: JSON.stringify({}),
  })
}

export type DirectorQuote = {
  operation: string
  credit: number
  scene_count: number
  model: string
}

export function quoteProject(
  id: string,
  body: { payload?: Record<string, unknown>; operation?: string; model?: string },
): Promise<DirectorQuote> {
  return request<DirectorQuote>(`/projects/${id}/quote`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function generateProject(
  id: string,
  body: { payload?: Record<string, unknown>; operation?: string; model?: string },
): Promise<{ id: string; status: string }> {
  return request(`/projects/${id}/generate`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function applyJob(projectId: string, jobId: string): Promise<ProjectDetail> {
  return request<ProjectDetail>(`/projects/${projectId}/apply/${jobId}`, {
    method: 'POST',
    body: JSON.stringify({}),
  })
}

/** Đường tải file xuất — trình duyệt mở thẳng, không đi qua fetch. */
export function exportUrl(projectId: string, format: 'json' | 'md' | 'zip'): string {
  return `${BASE}/projects/${projectId}/export/${format}`
}

export type Preferences = { theme: string; revision: number }

export function getPreferences(): Promise<Preferences> {
  return request<Preferences>('/preferences')
}

export function savePreferences(body: {
  theme: string
  revision: number
}): Promise<Preferences> {
  return request<Preferences>('/preferences', {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}
