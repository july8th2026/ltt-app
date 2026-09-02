/**
 * kieu.ts — hinh dang du lieu ChatLTT, ánh xạ 1-1 với `su_that()` của máy chủ.
 *
 * ⛔ Không có kiểu nào ở đây mang id model nội bộ hay đường máy — máy chủ đã
 *    chiếu chúng ra trước khi trả về, và `test_623` chốt điều đó.
 */

export type LoaiKhoi =
  | 'text' | 'reasoning' | 'image' | 'audio' | 'file' | 'status' | 'error'

export type Khoi = {
  type: LoaiKhoi
  text?: string
  code?: string
  key?: string
  [k: string]: unknown
}

export type TrangThai =
  | 'draft' | 'streaming' | 'queued' | 'done' | 'failed' | 'cancelled'

export type ThiHanh = {
  id: string
  status: TrangThai
  mode: 'stream' | 'job'
  tool_name: string
  partial_text: string
  reasoning_text: string
  finish_reason: string
  usage: { token_vao?: number; token_ra?: number; token_cache?: number; do_duoc?: boolean }
  credit: { giu: number; thu: number; hoan: number }
  error_code: string
  error_text: string
  job_id: string | null
  seq: number
}

export type ThongDiep = {
  id: string
  parent_id: string | null
  role: 'user' | 'assistant' | 'system'
  blocks: Khoi[]
  status: TrangThai
  model_alias: string
  execution_id: string | null
  created_at: string
  execution?: ThiHanh
}

export type HoiThoai = {
  id: string
  title: string
  model_alias: string
  current_leaf_id: string | null
  archived: boolean
  created_at: string
  updated_at: string
}

export type SuThat = { conversation: HoiThoai; messages: ThongDiep[] }

export type ModelAlias = {
  description?: string
  stability?: string
  constraints?: Record<string, unknown>
}

export type NangLuc = {
  ten: string
  phuong_thuc: 'text' | 'image' | 'audio'
  che_do: 'stream' | 'job'
  nhan: string
  models: Record<string, ModelAlias>
  tuy_chon: Record<string, { value: string; label: string }[]>
  gia: Record<string, unknown>
  duong_dan_app: string
  san_sang: 'san_sang' | 'ban' | 'chua_san_sang'
  hop_dong: Record<string, unknown>
}

/** Ảnh chụp một lượt đang chảy — máy chủ gửi ở sự kiện `snapshot` của SSE. */
export type AnhChup = {
  execution_id: string
  status: TrangThai
  seq: number
  partial_text: string
  reasoning_text: string
  finish_reason: string
  usage: ThiHanh['usage']
  credit: ThiHanh['credit']
  error_code: string
  job_id: string | null
}
