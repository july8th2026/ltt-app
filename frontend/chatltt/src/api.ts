/**
 * api.ts — goi may chu ChatLTT. Mot cho duy nhat biet duong dan va CSRF.
 *
 * ⛔ Moi loi tra ve deu la `LoiApi` co MA doc duoc (`ban`, `het_credit`,
 *    `khong_tim_thay`, `csrf`…), khong phai mot chuoi. Giao dien re nhanh theo
 *    ma; chuoi chi de hien.
 */
import type { AnhChup, HoiThoai, NangLuc, SuThat } from './kieu'

export class LoiApi extends Error {
  code: string
  status: number
  constructor(code: string, message: string, status: number) {
    super(message || code)
    this.code = code
    this.status = status
  }
}

export type BatDauLuot = {
  conversation_id: string
  user_message_id: string
  assistant_message_id: string
  execution_id: string
}

export class Api {
  /** Hoi thoai dang mo — `taoMedia` gan job vao dung hoi thoai nay. */
  convHienTai = ''

  constructor(private goc: string, private csrf: string) {}

  private async goi<T>(duong: string, init?: RequestInit): Promise<T> {
    const r = await fetch(this.goc + duong, {
      ...init,
      headers: {
        'Content-Type': 'application/json',
        'X-CSRF-Token': this.csrf,
        ...(init?.headers ?? {}),
      },
    })
    if (!r.ok) {
      let code = `http_${r.status}`
      let msg = ''
      try {
        const than = await r.json()
        code = than?.error?.code ?? code
        msg = than?.error?.message ?? ''
      } catch {
        // Than khong phai JSON (503 cua ha tang, trang loi cua Cloudflare).
        // Ma HTTP van la thong tin — giu no, dung nuot.
      }
      throw new LoiApi(code, msg, r.status)
    }
    return (await r.json()) as T
  }

  soDu(): Promise<{ credit: number }> {
    return this.goi('/so-du')
  }

  danhMuc(): Promise<{ nang_luc: NangLuc[] }> {
    return this.goi('/danh-muc')
  }

  lietKe(tim = ''): Promise<{ hoi_thoai: HoiThoai[] }> {
    const q = tim ? `?tim=${encodeURIComponent(tim)}` : ''
    return this.goi(`/hoi-thoai${q}`)
  }

  taoHoiThoai(modelAlias: string): Promise<HoiThoai> {
    return this.goi('/hoi-thoai', {
      method: 'POST', body: JSON.stringify({ model_alias: modelAlias }),
    })
  }

  suThat(convId: string): Promise<SuThat> {
    return this.goi(`/hoi-thoai/${encodeURIComponent(convId)}`)
  }

  xoa(convId: string): Promise<unknown> {
    return this.goi(`/hoi-thoai/${encodeURIComponent(convId)}/xoa`, {
      method: 'POST', body: '{}',
    })
  }

  chonLa(convId: string, messageId: string): Promise<HoiThoai> {
    return this.goi(`/hoi-thoai/${encodeURIComponent(convId)}/chon-la`, {
      method: 'POST', body: JSON.stringify({ message_id: messageId }),
    })
  }

  /**
   * Gui mot luot. `parentId === undefined` = noi vao la dang xem;
   * `parentId === null` = gan o GOC. Hai nghia khac nhau — xem
   * `apps/chatltt/services/luot.py::MAC_DINH`.
   */
  guiLuot(convId: string, than: {
    text?: string
    modelAlias?: string
    parentId?: string | null
    taoLaiCua?: string
    anh?: string[]
  }): Promise<BatDauLuot> {
    const body: Record<string, unknown> = {}
    if (than.text !== undefined) body.text = than.text
    if (than.modelAlias) body.model_alias = than.modelAlias
    if (than.taoLaiCua) body.tao_lai_cua = than.taoLaiCua
    if (than.anh && than.anh.length) body.anh = than.anh
    if ('parentId' in than) body.parent_id = than.parentId
    return this.goi(`/hoi-thoai/${encodeURIComponent(convId)}/luot`, {
      method: 'POST', body: JSON.stringify(body),
    })
  }

  /**
   * Tai mot anh len cho model vision. Tra `{key, mime, rong, cao, bytes}`.
   *
   * ⛔ `FormData`, va TUYET DOI khong dat `Content-Type` bang tay: trinh duyet
   *    phai tu sinh no de kem `boundary`. Dat tay la mot request multipart
   *    khong co boundary, va may chu tra 400 voi mot thong diep khong lien quan
   *    gi toi nguyen nhan.
   */
  async taiAnh(tep: File): Promise<{ key: string; mime: string;
    rong: number; cao: number; bytes: number }> {
    const fd = new FormData()
    fd.append('anh', tep)
    const r = await fetch(`${this.goc}/anh-vao`, {
      method: 'POST', body: fd, headers: { 'X-CSRF-Token': this.csrf },
      credentials: 'same-origin',
    })
    if (!r.ok) {
      let ma = `http_${r.status}`
      let tin = ''
      try {
        const j = await r.json()
        ma = String(j.code || ma); tin = String(j.message || j.detail || '')
      } catch { /* than khong phai JSON: giu ma HTTP */ }
      throw new LoiApi(ma, tin, r.status)
    }
    return r.json()
  }

  baoGia(nangLuc: string, thamSo: Record<string, unknown>):
  Promise<{ nang_luc: string; credit: number; phien_ban_gia: string;
            tham_so: Record<string, unknown>
            giong?: { preset: string; nguon: string; ton_credit: number } }> {
    // `hoi_thoai` de may chu biet luot tieng truoc do da chon giong nao — moi
    // lan hoi model chon lai ton 1 credit. Thieu no thi bao gia van chay, chi
    // la lan nao cung phai hoi lai.
    return this.goi('/bao-gia', {
      method: 'POST',
      body: JSON.stringify({ nang_luc: nangLuc, tham_so: thamSo,
                             hoi_thoai: this.convHienTai || '' }),
    })
  }

  /** `credit` la so nguoi dung DA NHIN THAY — may chu tu choi neu gia da doi. */
  taoMedia(nangLuc: string, thamSo: Record<string, unknown>, credit: number):
  Promise<{ message_id: string; execution_id: string; job_id: string; credit: number }> {
    return this.goi(`/hoi-thoai/${encodeURIComponent(this.convHienTai)}/tao`, {
      method: 'POST',
      body: JSON.stringify({ nang_luc: nangLuc, tham_so: thamSo, credit }),
    })
  }

  /** Nhip hoi cho mot job (Q87). An toan goi nhieu lan. */
  trangThai(executionId: string): Promise<{ status: string; seq: number }> {
    return this.goi(`/luot/${encodeURIComponent(executionId)}/trang-thai`)
  }

  /** Duong tai mot tai san — di qua cua co kiem so huu, khong phai /static. */
  duongTaiSan(khoa: string): string {
    return `${this.goc.replace(/\/api$/, '')}/tai-san/${khoa}`
  }

  dung(executionId: string): Promise<{ status: string }> {
    return this.goi(`/luot/${encodeURIComponent(executionId)}/dung`, {
      method: 'POST', body: '{}',
    })
  }

  duongStream(executionId: string): string {
    return `${this.goc}/luot/${encodeURIComponent(executionId)}/stream`
  }
}

export type SuKien =
  | { type: 'snapshot'; data: AnhChup }
  | { type: 'end'; data: { seq: number } }
  | { type: string; data: Record<string, unknown> }

/**
 * Doc mot luong SSE bang `fetch` + `ReadableStream`.
 *
 * ⭐ Khong dung `EventSource`: no khong gui duoc header (CSRF/`Authorization`)
 *    va khong huy duoc goi gon. `AbortController` cho ca hai.
 *
 * ⛔ Dem toi TRON DONG truoc khi phan tich. `ReadableStream` cat theo nhip
 *    mang chu khong theo nhip dong — mot `data: {...}` hoan toan co the toi lam
 *    ba khoi. Day dung la loi ma `platform_core/llm/dem_token_luong.py` da ghi
 *    lai o phia may chu: phan tich tung khoi roi rac la hong NGAU NHIEN theo
 *    tai, tuc chi hien ra o production.
 */
export async function docSSE(
  url: string,
  onSuKien: (sk: SuKien) => void,
  signal: AbortSignal,
): Promise<void> {
  const r = await fetch(url, { signal, headers: { Accept: 'text/event-stream' } })
  if (!r.ok || !r.body) throw new LoiApi(`http_${r.status}`, '', r.status)
  const reader = r.body.getReader()
  const decoder = new TextDecoder()
  let du = ''
  let ten = ''
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    du += decoder.decode(value, { stream: true })
    const dong = du.split('\n')
    du = dong.pop() ?? ''
    for (const d of dong) {
      const line = d.replace(/\r$/, '')
      if (line.startsWith(':')) continue              // `: ping`
      if (line.startsWith('event:')) { ten = line.slice(6).trim(); continue }
      if (!line.startsWith('data:')) continue
      const than = line.slice(5).trim()
      if (!than) continue
      try {
        onSuKien({ type: ten || 'message', data: JSON.parse(than) })
      } catch {
        // Mot dong khong phai JSON khong lam hong ca luong.
      }
      ten = ''
    }
  }
}
