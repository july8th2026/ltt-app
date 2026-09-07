/**
 * KhoiTool.tsx — ve mot khoi `tool_call`. (H44 P09 buoc 4)
 *
 * ## Truoc P09, vong lap tool chay ma KHONG AI NHIN THAY
 *
 * `ThongDiepView` chi doc `image`/`audio`/`error`/`status` + phan chu. Khoi
 * `tool_call` roi vao nhanh "khoi la" cua A5 — dung hop dong, nhung nghia la
 * mot san pham agentic khong co bang chung nao ve viec no da lam gi.
 *
 * ## ⛔ `tom_tat` KHONG duoc do ra man hinh
 *
 * `KetQua.tom_tat()` viet cho **model** doc. Voi mot luot thanh cong no la
 * JSON: `{"key": "a.png"}`. Ve no ra la dung thu `KhoiLa.test.tsx` goi la
 * *"te hon vo: no trong nhu san pham von the"* — chi khac la lan nay JSON nam
 * trong mot cai khung dep.
 *
 * ⇒ `xong` khong hien ket qua: cau tra loi cua tro ly nam ngay duoi, bang
 *   tieng Viet. `loi` thi hien **phan cau chu** cua thong diep, bo ma `LOI[..]`.
 *
 * ## Doi so hien theo NHAN, khoa la thi AN
 *
 * Mot khoa chua ai dat nhan (`prompt`, `giong`, ...) hien nguyen ten la mot
 * manh JSON tren man hinh. `test_835` chot rang moi khoa cua tool NOI BO deu
 * co nhan — nen "an" chi ap cho tool ngoai chua ai lam nhan, khong phai mot
 * duong tron cho tool cua chinh minh.
 *
 * ## Bo cuc muon tu `assistant-ui` (MIT, doc dac ta 06/09, KHONG cham ma)
 *
 * Root / Trigger (luon hien) / Content (gap lai mac dinh), va **tu mo khi chua
 * phai mot thanh cong im lang** — xem `TU_MO` ben duoi, cho ban mau cua ho chi
 * mo khi `running` con o day `loi` cung phai mo.
 * Xem `docs/CHATLTT_V3/11_KE_HOACH_P09_UX.md` §0.2.
 */
import { useState } from 'react'
import { trangThaiTool, type KhoiToolCall, type TrangThaiTool } from './kieu'

/** Ten tool → cau nguoi doc hieu. Khoa la ngo ra chinh no da bo tien to. */
const NHAN_TOOL: Record<string, string> = {
  'noi_bo.thoi_gian': 'Xem ngày giờ',
  'noi_bo.tinh': 'Tính toán',
  'noi_bo.tim_tai_lieu': 'Tìm trong tài liệu của bạn',
  'noi_bo.ghi_nho': 'Ghi nhớ một điều về bạn',
  'image.ltt': 'Vẽ ảnh',
  'speech.ltt': 'Đọc thành tiếng',
}

/**
 * Khoa doi so → nhan. Khoa VANG o day thi **khong hien**, xem docstring.
 *
 * 🔴 Sau nhom `noi_bo.*` la doi so cua HAI tool TRA TIEN ma model duoc phep de
 *    nghi (`chieu_tool.CHO_MODEL_GOI`). Do 07/09 tren trinh duyet that, truoc
 *    khi co may dong nay: mot khoi `cho_duyet` cua `image.ltt` ve ra
 *    **rong hoan toan** — chi "Ve anh — Dang cho ban duyet", khong mot dong
 *    nao noi se ve cai gi.
 *
 * ⛔ `test_835` co y KHONG doi nhan cho tool ngoai, ly le la *"hop dong nam o
 *    app khac"*. Ly le do dung ve QUYEN SO HUU nhung sai ve KET QUA: dung hai
 *    tool duy nhat tieu tien cua khach lai la hai tool ve ra man hinh trang.
 *    Va `tables.py` da tu hua dieu nguoc lai — `ChatlttApproval.doi_so` chu
 *    thich la *"doi so nguoi dung NHIN THAY khi bam"*.
 */
const NHAN_DOI_SO: Record<string, string> = {
  mui_gio: 'Múi giờ',
  bieu_thuc: 'Phép tính',
  cau_hoi: 'Tìm',
  so_doan: 'Số đoạn',
  noi_dung: 'Nội dung',
  lau_dai: 'Nhớ lâu dài',
  // `image.ltt` — `prompt` la doi so BAT BUOC, xem `apps/anhnoibo/manifest.py`.
  prompt: 'Mô tả',
  negative_prompt: 'Tránh vẽ',
  count: 'Số ảnh',
  // `speech.ltt` — `text` la doi so BAT BUOC, xem `apps/ltt_voice/manifest.py`.
  text: 'Văn bản',
  voice_id: 'Giọng',
  preset: 'Kiểu giọng',
}

const NHAN_TRANG_THAI: Record<TrangThaiTool, string> = {
  cho_duyet: 'Đang chờ bạn duyệt',
  dang_chay: 'Đang chạy',
  xong: 'Xong',
  loi: 'Không chạy được',
}

/**
 * Trang thai TU MO. Chi `xong` gap lai.
 *
 * ⚠️ Ban dau day la `['cho_duyet', 'dang_chay']` — "con viec thi con phai
 *    nhin". `KhoiTool.test.tsx` bat ngay: **loi cung phai tu mo**. Mot cau bao
 *    loi nam sau mot cu bam la mot cau bao loi khong ai doc, va nguoi dung chi
 *    thay "Khong chay duoc" ma khong bao gio biet VI SAO.
 *
 * ⭐ Vi tu dung khong phai *"con viec"* ma *"khong phai mot thanh cong im
 *    lang"*. Chi mot ket qua **xong** moi duoc quyen im.
 */
const TU_MO: readonly TrangThaiTool[] = ['cho_duyet', 'dang_chay', 'loi']

/**
 * Doi so -> `[nhan, gia tri]`, BO khoa chua ai lam nhan.
 *
 * ⭐ Xuat ra de `TheDuyet` dung CHUNG mot bang nhan. Hai bang nhan la hai
 *    bang se troi khoi nhau — va o day chung se troi ve phia nguy hiem: the
 *    duyet la cho nguoi dung quyet dinh TIEU TIEN, nen mot doi so bi an o do
 *    dat hon mot doi so bi an trong khoi tool.
 */
export function doiSoCoNhan(doiSo: Record<string, unknown> | undefined | null):
  Array<readonly [string, string]> {
  return Object.entries(doiSo ?? {})
    .filter(([k]) => NHAN_DOI_SO[k])
    .map(([k, v]) => [NHAN_DOI_SO[k], giaTri(v)] as const)
    .filter(([, v]) => v !== '')
}

/** Khoa nao CO nhan — `TheDuyet` can biet de quyet dinh cho sua o dau. */
export function khoaCoNhan(doiSo: Record<string, unknown> | undefined | null): string[] {
  return Object.keys(doiSo ?? {}).filter((k) => NHAN_DOI_SO[k])
}

/** Nhan cua mot khoa, hoac chinh khoa neu chua ai dat nhan. */
export function nhanCuaKhoa(khoa: string): string {
  return NHAN_DOI_SO[khoa] ?? khoa
}

export function nhanTool(ten: string): string {
  if (NHAN_TOOL[ten]) return NHAN_TOOL[ten]
  // ⛔ Ngo ra phan sau dau cham chu KHONG ngo ra ca `noi_bo.xyz`: mot tien to
  //    ky thuat tren man hinh la mot manh cua he thong ro ra ngoai.
  const sau = ten.includes('.') ? ten.slice(ten.indexOf('.') + 1) : ten
  return sau.replace(/_/g, ' ').trim() || 'Công cụ'
}

/** Bo ma may khoi thong diep loi: `LOI[het_tien]: khong du credit` → phan chu. */
export function cauLoi(tomTat: string): string {
  const m = /^LOI\[[^\]]*\]:\s*/.exec(tomTat || '')
  const chu = m ? tomTat.slice(m[0].length) : (tomTat || '')
  return chu.trim() || 'Công cụ không chạy được.'
}

function giaTri(v: unknown): string {
  if (typeof v === 'boolean') return v ? 'có' : 'không'
  if (typeof v === 'number' || typeof v === 'string') return String(v)
  // ⛔ Doi tuong/mang KHONG duoc `JSON.stringify` ra man hinh. Khong co nhan
  //    nao cho hinh dang do, nen no bi bo qua nhu mot khoa la.
  return ''
}

export function KhoiTool({ khoi }: { khoi: KhoiToolCall }) {
  const tt = trangThaiTool(khoi)
  const tuMo = TU_MO.includes(tt)

  // ⭐ Tu mo khi chua phai mot thanh cong im lang, roi de nguoi dung tu gap.
  //    Dong bo trong luc render (khong `useEffect`) — cung cach ban mau
  //    streaming cua `assistant-ui` lam, va no tranh mot nhip ve sai truoc khi
  //    effect chay.
  const [mo, datMo] = useState(tuMo)
  const [dongBo, datDongBo] = useState(tuMo)
  if (dongBo !== tuMo) {
    datDongBo(tuMo)
    if (tuMo) datMo(true)
  }

  const doiSo = doiSoCoNhan(khoi.doi_so)

  /**
   * ⭐ Mot khoi `cho_duyet` KHONG duoc phep rong. Ca ung dung nay fail-closed
   *    (`lop_chinh_sach` tra `DESTRUCTIVE` khi khong khai), va mot phieu duyet
   *    trang la fail-OPEN o giao dien: no trong vo hai, nen nguoi ta bam.
   *
   * ⛔ Duong nay le ra khong bao gio chay — banh coc `test_840` chot rang moi
   *    tool trong `CHO_MODEL_GOI` deu co nhan cho doi so BAT BUOC cua no. No o
   *    day vi banh coc chay luc gate con bo giao dien la mot BAN DA BUILD: mot
   *    lan doi ten tham so ben app khac co the len may chu truoc khi ai kip
   *    build lai.
   */
  const thieuChiTiet = tt === 'cho_duyet' && doiSo.length === 0
  const coThan = doiSo.length > 0 || tt === 'loi' || thieuChiTiet

  const ten = nhanTool(String(khoi.ten ?? ''))

  return (
    <div className="ltc-tool" data-trang-thai={tt}>
      {/*
        ⛔ `aria-label` khong phai trang tri. Hai `<span>` lien nhau khong co
           khoang trang giua, nen ten kha truy cap tinh ra la
           "Tinh toanDang cho ban duyet" — dinh lien. Do 06/09 tren trinh
           duyet that: `button.textContent` tra ve dung chuoi dinh ay.
        ⭐ Loi nay KHONG nhin thay duoc: `gap` cua flexbox tach hai chu tren man
           hinh, nen mat thay dep trong khi tai nghe thay mot tu la.
      */}
      <button
        type="button"
        className="ltc-tool__nut"
        aria-label={`${ten} — ${NHAN_TRANG_THAI[tt]}`}
        aria-expanded={coThan ? mo : undefined}
        disabled={!coThan}
        onClick={() => datMo((x) => !x)}
      >
        <span className="ltc-tool__ten">{ten}</span>
        <span className="ltc-tool__tt">{NHAN_TRANG_THAI[tt]}</span>
      </button>
      {coThan && mo && (
        <div className="ltc-tool__than">
          {doiSo.length > 0 && (
            /* `<dl>` chu khong phai `<div>`: day dung la cap thuat ngu-dinh
               nghia, va trinh doc man hinh ngat giua `<dt>` va `<dd>` — thu
               ma hai `<span>` canh nhau khong lam duoc. */
            <dl className="ltc-tool__doiso">
              {doiSo.map(([nhan, v]) => (
                <div className="ltc-tool__dong" key={nhan}>
                  <dt className="ltc-tool__khoa">{nhan}</dt>
                  <dd className="ltc-tool__gt">{v}</dd>
                </div>
              ))}
            </dl>
          )}
          {thieuChiTiet && (
            <p className="ltc-tool__loi">
              Không hiển thị được chi tiết của yêu cầu này — đừng duyệt.
            </p>
          )}
          {tt === 'loi' && (
            <p className="ltc-tool__loi">{cauLoi(String(khoi.tom_tat ?? ''))}</p>
          )}
        </div>
      )}
    </div>
  )
}
