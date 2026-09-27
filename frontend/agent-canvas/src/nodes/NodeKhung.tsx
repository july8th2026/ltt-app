// Khung CHUNG cho moi node (spec §13.2): danh tinh, trang thai, tom tat cau
// hinh, cong, tom tat luot chay. ⛔ KHONG co component rieng cho tung app/
// connector — do la thu `test_967` dang dem hang chet.
//
// ⭐ NAM THU, va dung nam (`09 §3.2`). Truoc ban va nay node ve: icon · title ·
//    kind · trangThai · type@version · GPU · "Can ket noi" · "Sap co" · than ·
//    TOAN BO cong => `app.video.generate` cao 525px, va thu nguoi dung can doc
//    o khoang cach 1m (ten buoc) nam o hang thu TU, nho hon chuoi
//    `app.video.generate@1` o hang ba (`01 §4.1`).
import type { CSSProperties, ReactNode } from 'react'
import type { NodeDefinition } from '../nodeDefinition'
import { HangCong, KhayCong } from './CongNode'
import { RONG_MUC, laMedia, nodeCoMatMedia, phanLoaiCong, type MucDo } from './matDo'
import { nhanTomTatChay, type HuyHieu, type SucKhoe, type TomTatChay } from './tomTat'
import '../styles/node.css'

export type ThamSoKhung = {
  dinhNghia: NodeDefinition
  /** Nhan tieng Viet cua trang thai run (`RunV3Panel.NHAN_TRANG_THAI_NODE`). */
  trangThai?: string
  /** Truc 1 — VIEN (`09 §3.3`). */
  sucKhoe?: SucKhoe
  /** Truc 2 — HUY HIEU GOC (`09 §3.3`). */
  huyHieu?: HuyHieu[]
  /** Ten cac cong DANG CO DAY (ca vao va ra). */
  congDaNoi?: ReadonlySet<string>
  tomTatChay?: TomTatChay
  mucDo: MucDo
  /** Dong tom tat cau hinh — do `NodeRenderer` tinh theo `kind`. */
  children?: ReactNode
}

export function NodeKhung(p: ThamSoKhung) {
  const { dinhNghia, trangThai, mucDo } = p
  const daNoi = p.congDaNoi ?? new Set<string>()
  // ⚠️ Dau tai nguyen doc TU `resource.class`, KHONG tu con so VRAM:
  // `palette_v3.RESOURCE_CONG_KHAI = ("class",)` da bo `vram_min_mb`/`slots`/
  // `est_duration_s` — suc chua ha tang khong phoi cho moi nguoi dang nhap.
  const lopTaiNguyen = dinhNghia.resource?.class
  const vao = phanLoaiCong(dinhNghia.cong_vao, daNoi, mucDo)
  const ra = phanLoaiCong(dinhNghia.cong_ra, daNoi, mucDo)
  const nhanChay = nhanTomTatChay(p.tomTatChay)
  // ⭐ `type@version` di vao TOOLTIP, ⛔ khong len mat node: `09 §3.2` cam hien
  //    `app.video.generate@1` cho nguoi dung cuoi. Phan tu van o trong DOM
  //    (`.node-type`, an bang CSS o moi muc) vi do la danh tinh MAY doc —
  //    cong cu tro nang va phep kiem doc no, nguoi dung thi khong phai doc.
  const dinhDanh = `${dinhNghia.type}@${dinhNghia.type_version}`
  // 🔴 `app_name` LEN TRUOC, khong phai `title`. `01 §4.1` do duoc phan cap
  //    thi giac bi LON NGUOC tren `app.video.generate`: thu to nhat va dam
  //    nhat la `title` = "Sinh video từ mô tả" (mot cau bi cat 60 ky tu), con
  //    "Tạo Video Seedance" — *ten thật sự dùng được* — nam o hang thu TU,
  //    nho hon ca chuoi `app.video.generate@1` o hang ba. So do `09 §3.2` ve
  //    dung "⬤ Tạo Video Seedance", tuc CHINH `app_name`.
  //
  // ⛔ `title` KHONG bi vut: node `core.*` co `app_name` RONG (`core.stop` ->
  //    "Dừng" chi nam o `title`), va khi hai ten khac nhau thi `title` van la
  //    thong tin — no tut xuong mot dong nho, ⛔ khong mat.
  const tenChinh = dinhNghia.app_name || dinhNghia.title
  const tenPhu = dinhNghia.app_name && dinhNghia.title !== dinhNghia.app_name
    ? dinhNghia.title : ''
  return <div className={`node-khung node-kind-${dinhNghia.kind}`}
    data-muc-do={mucDo} data-suc-khoe={p.sucKhoe ?? 'idle'}
    data-testid="node-khung"
    style={{ '--node-rong': `${RONG_MUC[mucDo]}px` } as CSSProperties}
    title={`${tenChinh} — ${dinhDanh}`}>
    <header className="node-khung-dau">
      {dinhNghia.icon && <span className="node-icon" aria-hidden>{dinhNghia.icon}</span>}
      <span className="node-tieu-de">{tenChinh}</span>
      <span className="node-kind" data-testid="node-kind">{dinhNghia.kind}</span>
      {trangThai && <span className="node-trang-thai"
        data-testid="node-trang-thai">{trangThai}</span>}
    </header>

    {/* `node-than-an` o muc compact: khoi nay van o trong DOM (danh tinh may
        doc + hai canh bao) nhung ⛔ khong chiem cho tren mat node. */}
    <div className={`node-khung-than${mucDo === 'compact' ? ' node-than-an' : ''}`}>
      <small className="node-type">{dinhDanh}</small>
      {/* ⭐ Dong nay ton 0 HANG: khoi `than` da ton tai san cho GPU/"Cần kết
          nối"/"Sắp có", nen `title` chen vao day chu khong mo mot hang moi. */}
      {tenPhu && <small className="node-ten-phu"
        data-testid="node-ten-phu">{tenPhu}</small>}
      {lopTaiNguyen === 'gpu'
        ? <small className="node-tai-nguyen" data-testid="node-tai-nguyen"
            title="Tài nguyên: GPU">GPU</small>
        : null}
      {dinhNghia.credential.length > 0 && <small className="node-credential">Cần kết nối</small>}
      {!dinhNghia.publish_duoc && <small className="node-sap-co">Sắp có</small>}
      {mucDo !== 'compact' && p.children}
    </div>

    {/* Khay MEDIA — chi o `expanded`, va chi khi node co mat media (`09 §3.4`).
        ⚠️ Day la mot cho GIU CHO co nhan: `RunV3Node` khong mang artifact nen
        chua co anh nao de tai. ⛔ Khong ve mot <img> tro vao dau ca — mot
        thumbnail 16:9 mau xam la mot loi hua ve du lieu khong ton tai. */}
    {mucDo === 'expanded' && nodeCoMatMedia(dinhNghia) && <div className="node-media"
      data-testid="node-media" aria-label="Kết quả media">
      <span className="node-media-khung" aria-hidden />
      <small>{dinhNghia.cong_ra.filter(c => laMedia(c.kieu))
        .map(c => c.kieu).join(' · ')}</small>
    </div>}

    <div className="node-cong-cot">
      {vao.hang.map(c => <HangCong key={c.ten} cong={c} phia="vao"
        daNoi={daNoi.has(c.ten)} />)}
      <KhayCong congs={vao.khay} phia="vao" />
      {ra.hang.map(c => <HangCong key={c.ten} cong={c} phia="ra"
        daNoi={daNoi.has(c.ten)} />)}
      <KhayCong congs={ra.khay} phia="ra" />
    </div>

    {!!nhanChay && mucDo !== 'compact' && <footer className="node-chan"
      data-testid="node-tom-tat-chay">{nhanChay}</footer>}

    {/* Huy hieu GOC — truc 2. Nam sau cung trong DOM va `position:absolute` de
        khong day bo cuc; `pointer-events:none` de ⛔ khong bao gio an mot cong. */}
    {!!p.huyHieu?.length && <div className="node-huy-hieu" data-testid="node-huy-hieu">
      {p.huyHieu.map(h => <span key={h.loai} className={`node-hh node-hh-${h.loai}`}
        data-loai={h.loai} title={h.moTa}>{h.nhan}</span>)}
    </div>}
  </div>
}
