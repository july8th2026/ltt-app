/**
 * kieu.ts — hinh dang du lieu ChatLTT, ánh xạ 1-1 với `su_that()` của máy chủ.
 *
 * ⛔ Không có kiểu nào ở đây mang id model nội bộ hay đường máy — máy chủ đã
 *    chiếu chúng ra trước khi trả về, và `test_623` chốt điều đó.
 */

export type LoaiKhoi =
  | 'text' | 'reasoning' | 'image' | 'audio' | 'file' | 'status' | 'error'
  // H44 P05 — khoi V3 sinh ra. Phai co o day cho khop `tables.LOAI_KHOI`;
  // hai danh sach lech nhau thi may chu ghi duoc mot thu giao dien khong khai.
  | 'tool_call'

export type Khoi = {
  type: LoaiKhoi
  text?: string
  code?: string
  key?: string
  [k: string]: unknown
}

/**
 * Trang thai cua mot khoi `tool_call`. Khop `tables.TRANG_THAI_KHOI_TOOL`.
 *
 * 🔴 MOT chieu, khong phai ba co roi. Ban truoc mang `ok` + `cho_duyet` va bo
 *    han `cho_job`, nen mot buoc DANG CHO JOB tuan tu hoa y het mot buoc DA
 *    XONG — do bang thi nghiem 06/09, `test_834` chot lai.
 */
export type TrangThaiTool = 'cho_duyet' | 'dang_chay' | 'xong' | 'loi'

export type KhoiToolCall = Khoi & {
  type: 'tool_call'
  ten?: string
  doi_so?: Record<string, unknown>
  trang_thai?: TrangThaiTool
  /** ⚠️ Chi de doc khoi CU. Nguon chan ly la `trang_thai`. */
  ok?: boolean
  cho_duyet?: boolean
  tom_tat?: string
}

/**
 * Type guard — `filter(laKhoiTool)` hep kieu duoc, `filter(k => k.type === ...)`
 * thi khong: `Khoi.type` khai la `LoaiKhoi` nen TypeScript khong tu hep.
 */
export function laKhoiTool(k: Khoi): k is KhoiToolCall {
  return k.type === 'tool_call'
}

/**
 * Trang thai cua mot khoi, ke ca khoi CU chua co truong `trang_thai`.
 *
 * ⚠️ 220 hoi thoai that co the dang mang khoi cu. Doc nguoc tu `ok`/`cho_duyet`
 *    la duong duy nhat de chung khong hien sai — nhung no **khong the** phan
 *    biet "dang chay" voi "xong", vi thong tin ay chua bao gio duoc ghi.
 *    ⇒ Khoi cu ngo ra `xong`, va do la cau tra loi trung thuc nhat con lai.
 */
export function trangThaiTool(k: KhoiToolCall): TrangThaiTool {
  if (k.trang_thai) return k.trang_thai
  if (k.cho_duyet) return 'cho_duyet'
  return k.ok === false ? 'loi' : 'xong'
}

/** Mot du an. Anh xa 1-1 voi `_p_du_an._bay()`. `payload` KHONG ra ngoai. */
export type DuAn = {
  id: string
  ten: string
  /** Khoa lac quan cua loi. Gui lai nguyen ven khi doi ten. */
  revision: number
  created_at: string
  updated_at: string
}

/** Mot mau ghi nho. Anh xa 1-1 voi `_p_ghi_nho._bay()`. */
export type GhiNho = {
  id: string
  /** ⛔ PHAM VI AP DUNG, khong phai phan loai noi dung. */
  pham_vi: 'nguoi_dung' | 'du_an' | 'hoi_thoai'
  muc_tieu_id: string
  /** Ai viet — quyet dinh QUYEN SUA, doc lap voi `pham_vi`. */
  nguon: 'nguoi' | 'model'
  noi_dung: string
  meta: Record<string, unknown>
  created_at: string
  updated_at: string
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
  /** Text: token. Job: `progress` 0-100. Mot cho, hai hinh — theo `mode`. */
  usage: {
    token_vao?: number; token_ra?: number; token_cache?: number; do_duoc?: boolean
    progress?: number
  }
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
  /** `''` = khong thuoc du an nao. H44 B5. */
  project_id?: string
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
  /** Alias chon san. May chu doc tu `default` cua hop dong, KHONG phai
   *  thu tu khai trong `models` — xem `runtime_noi_bo/danh_muc.py`. */
  model_mac_dinh?: string
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

// ── Nghien cuu (H44 B6) ─────────────────────────────────────────────────

/** Mot trich dan phan giai duoc ve MOT doan tai lieu co that cua chinh chu. */
export type TrichDan = {
  tep_id: string
  doan_id: string
  /** ⛔ `0` nghia la KHONG BIET (tep khong co khai niem trang), khong phai
   *  "trang dau". Giao dien phai hien duoc khac biet do — mot trich dan `.txt`
   *  tro vao "trang 0" trong nhu mot loi. */
  trang: number
}

/** Mot cau trong bao cao, DA phan giai nguon. Khong co nguon thi khong ton tai:
 *  `nghien_cuu.kiem_trich_dan` loai no truoc khi toi day. */
export type KhangDinh = { chu: string; nguon: TrichDan[] }

export type LyDoDung = 'xong' | 'tran_vong' | 'tran_nguon' | 'khong_co_nguon'

export type BaoCaoNghienCuu = {
  cau_hoi: string
  ly_do_dung: LyDoDung
  so_vong: number
  /** So cau model viet ra ma **khong** phan giai duoc ve nguon nao. Hien ra,
   *  khong giau: no la thuoc do do tin cua chinh luot nay. */
  so_bi_loai: number
  khang_dinh: KhangDinh[]
  nguon: { loai: string; trich_dan: TrichDan }[]
  phien_ban_gia: string
}

export type BaoGiaNghienCuu = {
  uoc_credit: number
  tran_vong: number
  tran_vong_toi_da: number
  so_du: number
  du_credit: boolean
  pham_vi: string
  phien_ban_gia: string
}

// ── Phieu duyet (H44 P04 + P09) ─────────────────────────────────────────

/** Lop chinh sach cua mot nang luc — quyet dinh HE QUA noi voi nguoi dung. */
export type LopChinhSach =
  | 'READ_ONLY' | 'FREE' | 'PAID' | 'EXTERNAL_WRITE' | 'DESTRUCTIVE'

/**
 * Mot phieu con CHO nguoi dung quyet. Hinh dang do `duyet.su_kien_can_duyet`
 * dat — "chi thu giao dien can de ve nut".
 *
 * ⛔ `credit` la so NGUOI DUNG DA NHIN THAY. May chu tinh lai luc chay va tu
 *    choi neu lech (`tao_media.tao`), nen no khong phai mot uoc luong de trang
 *    tri — no la mot phan cua thoa thuan.
 */
export type PhieuDuyet = {
  approval_id: string
  tool_name: string
  doi_so: Record<string, unknown>
  credit: number
  policy_class: LopChinhSach | string
  /** ISO. Phieu het han thi KHONG duyet duoc — may chu tra 409. */
  het_han_luc: string
}
