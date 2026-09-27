import JsonView from '@uiw/react-json-view'
import type { ReactNode } from 'react'
import type { BuocRun } from './buocCuaRun'
import { LoiBuoc } from './LoiBuoc'
import { gio, nhanThoiLuong } from './thoiGian'

/** Mười hai trường của `09_TARGET_DESIGN.md §8` cho MỘT bước, CÓ NHÓM.
 *
 *  ⛔ Không còn một khối JSON duy nhất. Bản cũ (`RunInspector`) đổ cả
 *     `{nodes}` và `{su_kien}` vào hai cây `@uiw/react-json-view`: mọi trường
 *     đều "có trên màn hình" và ⛔ không trường nào đọc được. Thư viện ấy vẫn
 *     dùng ở đây — nhưng cho đúng phần nó giỏi (dữ liệu LỒNG của người dùng),
 *     trong một trường CÓ TÊN, không cho cả gói.
 *
 *  ⭐ `data-truong` trên mỗi trường là hợp đồng với phép kiểm: nó đếm được 12
 *     trường có mặt. ⛔ Đừng đổi slug mà không đổi phép kiểm — và ⛔ đừng bỏ
 *     một trường chỉ vì hôm nay nó chưa có cửa dữ liệu: "chưa có cửa" là một
 *     câu trả lời, "không có dòng nào" thì không.
 */

/** Một trường: tên · giá trị · (tuỳ chọn) vì sao trống.
 *
 *  🔴 `trong` KHÔNG BAO GIỜ là chuỗi rỗng. Một ô trắng làm người đọc tưởng đã
 *     đo được và ra 0/rỗng. Nó phải NÓI rằng chưa có cửa đo.
 */
function Truong({ slug, ten, children, trong }: {
  slug: string; ten: string; children?: ReactNode; trong?: string }) {
  return (
    <div className="run-truong" data-truong={slug}>
      <dt>{ten}</dt>
      <dd>{children ?? <em className="run-truong-trong">{trong ?? 'Chưa có cửa dữ liệu cho trường này.'}</em>}</dd>
    </div>
  )
}

function Nhom({ ten, children }: { ten: string; children: ReactNode }) {
  return (
    <section className="run-nhom" aria-label={ten}>
      <h4>{ten}</h4>
      <dl>{children}</dl>
    </section>
  )
}

/** Cây JSON cho dữ liệu LỒNG, gập sẵn một cấp. Rỗng ⇒ trả `null` để `Truong`
 *  hiện câu "trống" thay vì một dấu `{}` không nói gì. */
function CayJson({ gia_tri }: { gia_tri: Record<string, unknown> | null }) {
  if (!gia_tri || !Object.keys(gia_tri).length) return null
  return <JsonView value={gia_tri} collapsed={1} />
}

export function NodeExecutionInspector({ buoc }: { buoc: BuocRun }) {
  const thoiLuong = nhanThoiLuong(buoc.thoiLuongMs)
  return (
    <section className="run-node-inspector" aria-label={`Chi tiết bước ${buoc.ten}`}>
      <header><strong>{buoc.ten}</strong>
        <span data-node-status-chi-tiet={buoc.status}>{buoc.nhanTrangThai}</span></header>

      <Nhom ten="Tình trạng">
        <Truong slug="trang_thai" ten="Trạng thái">
          {buoc.nhanTrangThai}
          {buoc.hetHan && <> · kết thúc vì HẾT HẠN chờ, không vì ai trả lời</>}
        </Truong>
        <Truong slug="ly_do_cho" ten="Lý do chờ"
          trong={buoc.status === 'WAITING'
            ? 'Bước đang chờ nhưng máy chủ chưa nói vì sao.'
            : 'Bước này không ở trạng thái chờ.'}>
          {buoc.lyDoCho || undefined}
        </Truong>
        <Truong slug="lan_thu" ten="Lần thử">
          {buoc.lanThu === 0 ? 'Chưa thử lần nào' : `Lần ${buoc.lanThu}`}
        </Truong>
        {/* ⛔ KHONG hien `0s` khi khong do duoc — xem `buocCuaRun.ts`. */}
        <Truong slug="thoi_luong" ten="Thời lượng"
          trong="Lượt chạy không ghi mốc bắt đầu/kết thúc riêng cho bước này, nên không đo được.">
          {thoiLuong ?? undefined}
        </Truong>
      </Nhom>

      <Nhom ten="Tiền và tài nguyên">
        <Truong slug="chi_phi" ten="Chi phí">{buoc.chiPhi} credit</Truong>
        <Truong slug="tai_nguyen" ten="Tài nguyên"
          trong="Bước này không nộp job nào, nên không giữ GPU hay máy chạy.">
          {buoc.jobId
            ? <>Job <code>{buoc.jobId}</code>
                <small> — tên GPU/lease không nằm trong dữ liệu lượt chạy</small></>
            : undefined}
        </Truong>
      </Nhom>

      <Nhom ten="Dữ liệu">
        <Truong slug="dau_vao" ten="Đầu vào"
          trong="Bước này không khai tham số nào trong workflow.">
          <CayJson gia_tri={buoc.dauVao}/>
        </Truong>
        {/* `output_ref` chi ve theo cua SO SANH (`runs_v3.py::_nodes_so_sanh`);
            luong SSE co tinh bo no de goi moi giay khong phinh ra. */}
        <Truong slug="dau_ra" ten="Đầu ra"
          trong="Lượt chạy đang xem không mang đầu ra của bước. Bấm “So sánh với lượt gốc” để máy chủ trả con trỏ đầu ra.">
          <CayJson gia_tri={buoc.dauRa}/>
        </Truong>
        <Truong slug="artifact" ten="Artifact"
          trong="Bước này không sinh ra tệp nào, hoặc đầu ra chưa được nạp.">
          {buoc.artifact
            ? <code>{typeof buoc.artifact === 'string'
                ? buoc.artifact : JSON.stringify(buoc.artifact)}</code>
            : undefined}
        </Truong>
      </Nhom>

      <Nhom ten="Chuyện đã xảy ra">
        <Truong slug="nhat_ky" ten="Nhật ký"
          trong="Lượt chạy chưa ghi sự kiện nào cho bước này.">
          {buoc.nhatKy.length
            ? <ol className="run-nhat-ky">{buoc.nhatKy.map(e =>
                <li key={e.seq}><time>{gio(e.created_at)}</time> {e.loai}</li>)}</ol>
            : undefined}
        </Truong>
        {/* "Lich su thu lai" suy tu `attempt` + su kien cua buoc: ⛔ khong co
            bang lich su rieng trong `RunV3`. Noi ro thay vi ve mot bang rong. */}
        <Truong slug="lich_su_thu_lai" ten="Lịch sử thử lại"
          trong="Bước này chưa chạy quá một lượt.">
          {buoc.lanThu > 1
            ? <>Đã chạy {buoc.lanThu} lượt.
                <small> Mốc từng lượt không có trong dữ liệu lượt chạy — chỉ có tổng số lượt.</small></>
            : undefined}
        </Truong>
        <Truong slug="loi" ten="Lỗi" trong="Bước này không báo lỗi.">
          {buoc.loi ? <LoiBuoc loi={buoc.loi}/> : undefined}
        </Truong>
      </Nhom>

      {/* ⭐ `node_id` song O DAY, khong o cot dau dong thoi gian: nguoi di go
          loi can no, nguoi dung binh thuong thi khong. */}
      <details className="run-ky-thuat">
        <summary>Chi tiết kỹ thuật</summary>
        <dl>
          <div className="run-truong"><dt>node_id</dt><dd><code>{buoc.nodeId}</code></dd></div>
          <div className="run-truong"><dt>status</dt><dd><code>{buoc.status}</code></dd></div>
          <div className="run-truong"><dt>job_id</dt>
            <dd><code>{buoc.jobId || '(không có)'}</code></dd></div>
          {buoc.loi && <div className="run-truong"><dt>error</dt>
            <dd><code>{buoc.loi.tho}</code></dd></div>}
        </dl>
      </details>
    </section>
  )
}
