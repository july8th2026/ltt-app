// Inspector V2 (`09_TARGET_DESIGN.md` §6) — NAM tab thay cho mot cot 15 o.
//
// 🔴 HAI LUAT BAT BUOC cua tab "Cấu hình", ca hai la mot loi DO DUOC:
//
// 1. Truong phu thuoc phai AN, ⛔ khong hien xam. Hom nay mot buoc vua tha
//    xuong hien BA dropdown "— chưa có lựa chọn nào —" cung luc, vi ca ba
//    `depends_on` `model` ma `model` chua chon. Luat nay nam trong
//    `FormTuLuocDo` (no la cho biet `x-ltt-dong`), khong o day.
// 2. O KET NOI nam ngay trong tab nay, va tao duoc mot ket noi TAI CHO
//    (`OKetNoi`).
//
// ⭐ PHA NAY LAM DUNG TAB "Cấu hình". Bon tab kia DAT CHO — va chung noi thang
//    ra rang chung dat cho. ⛔ Mot tab trong trong nhu da hoat dong la thu te
//    nhat: no lam nguoi dung ket luan "tinh nang nay hong", va lam lan sau
//    khong ai phan biet duoc "chua lam" voi "lam roi ma loi".
//
// ⛔ Tep nay KHONG dung `editorState` nao rieng. No nhan `dispatch` + trang
//    hien tai tu cho goi, va ghi `credential_ref` bang action `graph` DA CO —
//    ⛔ khong them mot action nao vao `editorState.ts` (so S3, chu la UI-3).
import { useState } from 'react'
import type { NodeDefinition } from '../nodeDefinition'
import type { CanvasEdge, CanvasNode, GoiYBieuThuc } from '../workflowApi'
import { FormTuLuocDo } from './FormTuLuocDo'
import { OKetNoi } from './OKetNoi'
import './inspector.css'

/** ⚠️ KIEU CUC BO, co y. `credential_ref` thuoc **muc tren cung** cua mot buoc
 *  (`bien_dich._node_tu_dinh_nghia` doc `n["credential_ref"]`), nhung kieu
 *  `CanvasNode` song o `workflowApi.ts` — so S4, chu la UI-7. Lan UI-5 KHONG
 *  tu sua tep do; dong khai bao can them da bao dieu phoi. Kieu nay la cho
 *  tam, ⛔ khong phai mot hinh dang thu hai cua buoc. */
export type BuocCoKetNoi = CanvasNode & { credential_ref?: string }

/** Nam tab cua §6. Thu tu la thu tu nguoi dung di qua, khong phai thu tu
 *  chung duoc lam xong. */
const TAB = ['Cấu hình', 'Dữ liệu vào', 'Tuỳ chọn', 'Kết quả', 'Chạy thử'] as const
type Tab = typeof TAB[number]

type Props = {
  buoc: BuocCoKetNoi | null
  dinhNghia: NodeDefinition | null
  nodes: CanvasNode[]
  edges: CanvasEdge[]
  csrf: string
  readOnly?: boolean
  goiY?: GoiYBieuThuc
  /** `undefined` = may chu chua xac nhan chi phi. ⛔ Khong doi thanh `0`: hai
   *  trang thai khac loai gop vao mot gia tri thi mat kha nang phan biet. */
  gia?: number
  onLabel: (label: string) => void
  onParam: (ten: string, gia_tri: unknown) => void
  /** Ghi `credential_ref` o MUC TREN CUNG cua buoc. */
  onKetNoi: (ref: string) => void
  onXoa?: () => void
  onNhanBan?: () => void
}

function DatCho({ ten, vi_sao }: { ten: string; vi_sao: string }) {
  return <div className="inspector-dat-cho" role="status">
    <strong>{ten} — chưa hoạt động</strong>
    <p>{vi_sao}</p>
  </div>
}

export function StepInspector({ buoc, dinhNghia, nodes, edges, csrf, readOnly,
                                goiY, gia, onLabel, onParam, onKetNoi, onXoa,
                                onNhanBan }: Props) {
  const [tab, setTab] = useState<Tab>(TAB[0])
  if (!buoc || !dinhNghia) return <p>Chọn một node để xem tham số.</p>

  // ⛔ O ket noi chi hien khi buoc THAT SU doi mot ket noi. Hien no cho moi
  //    buoc la day nguoi dung di tao mot bi mat khong ai dung — va
  //    `bien_dich._node_tu_dinh_nghia` tu choi mot `credential_ref` tren buoc
  //    khong nhan credential (`credential_khong_ho_tro`), nen o do se la mot
  //    cai bay.
  const kieuChoPhep = dinhNghia.credential ?? []

  return <>
    <small>THAM SỐ</small>
    <h2>{dinhNghia.title}</h2>
    <p className="inspector-type">{dinhNghia.type}@{dinhNghia.type_version}</p>
    {dinhNghia['x-ltt-loi'] && <p className="inspector-loi" role="status">
      Một phần lựa chọn của node này chưa tải được — các ô ấy bị khóa.</p>}
    <nav className="inspector-tabs" aria-label="Phần của bước">
      {TAB.map(ten => <button key={ten} type="button"
        className={tab === ten ? 'active' : ''} aria-pressed={tab === ten}
        onClick={() => setTab(ten)}>{ten}</button>)}
    </nav>
    <div className="inspector-than">
      {tab === TAB[0] && <>
        <input aria-label="Tên hiển thị của node" disabled={readOnly}
          value={buoc.label ?? ''} placeholder={dinhNghia.title}
          onChange={event => onLabel(event.target.value)} />
        {kieuChoPhep.length > 0 &&
          <OKetNoi kieuChoPhep={kieuChoPhep} buocType={dinhNghia.type}
            giaTri={buoc.credential_ref ?? ''} csrf={csrf} readOnly={readOnly}
            onChange={onKetNoi} />}
        <FormTuLuocDo luocDo={dinhNghia.tham_so}
          giaTri={(buoc.data.params ?? {}) as Record<string, unknown>}
          readOnly={readOnly} goiY={goiY} onChange={onParam} />
      </>}
      {tab === TAB[1] && <DatCho ten="Dữ liệu vào"
        vi_sao={`Cây dữ liệu của các bước trước (kéo một trường sang ô để sinh
          biểu thức) là việc của lằn Data picker. Hôm nay bước này có
          ${edges.filter(e => e.target === buoc.id).length} đường nối vào và
          ${nodes.length} bước trên trang.`} />}
      {tab === TAB[2] && <DatCho ten="Tuỳ chọn"
        vi_sao="Số lần thử lại, thời gian chờ, cách xử lý lỗi và mức chạy song
          song đọc từ lược đồ máy chủ. Các ô ấy chưa được nối." />}
      {tab === TAB[3] && <DatCho ten="Kết quả"
        vi_sao="Lược đồ đầu ra và kết quả thật của lượt chạy gần nhất thuộc
          bảng Lượt chạy, chưa nối vào đây." />}
      {tab === TAB[4] && <DatCho ten="Chạy thử"
        vi_sao={dinhNghia.co_mock
          ? 'Bước này có chế độ Mock ở máy chủ, nhưng cửa chạy MỘT bước chưa mở.'
          : 'Bước này không có chế độ Mock, nên chạy thử sẽ tiêu credit thật. '
            + 'Cửa chạy MỘT bước chưa mở.'} />}
    </div>
    {/* Sticky action o chan panel (§6 luat 4).
        ⚠️ Nhan la "Chạy thử bước", KHONG phai "Chạy thử" nhu §6 ghi: tab thu
           nam cung ten "Chạy thử", va hai dieu khien trung ten trong mot panel
           thi nguoi dung doc man hinh nghe hai lan cung mot cau va khong biet
           cai nao lam gi. No MO tab do — mot nut bam duoc ma khong lam gi thi
           te hon mot nut khoa co ly do. */}
    <footer className="inspector-hanh-dong">
      <button type="button" onClick={() => setTab(TAB[4])}>Chạy thử bước</button>
      <button type="button" disabled={readOnly || !onNhanBan}
        onClick={() => onNhanBan?.()}>Nhân bản</button>
      <button type="button" className="danger" disabled={readOnly || !onXoa}
        onClick={() => onXoa?.()}>Xóa bước</button>
    </footer>
    <footer className="inspector-gia">{gia === undefined
      ? 'Chi phí do server xác nhận'
      : `Tối đa ${gia} credit`}</footer>
  </>
}
