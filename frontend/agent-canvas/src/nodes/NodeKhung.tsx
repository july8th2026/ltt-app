// Khung CHUNG cho moi node (spec §13.2): tieu de, cong co kieu, huy hieu
// trang thai. ⛔ KHONG co component rieng cho tung app/connector — do la thu
// `test_967` dang dem hang chet.
import { Handle, Position } from '@xyflow/react'
import type { ReactNode } from 'react'
import type { Cong, NodeDefinition } from '../nodeDefinition'

function ChanCong({ cong, phia }: { cong: Cong; phia: 'vao' | 'ra' }) {
  return <div className={`node-cong node-cong-${phia}`}
    title={`${cong.ten} · ${cong.kieu}`}>
    <Handle type={phia === 'vao' ? 'target' : 'source'} id={cong.ten}
      position={phia === 'vao' ? Position.Left : Position.Right}
      data-kieu={cong.kieu} />
    <span className="node-cong-ten">{cong.ten}</span>
    <span className="node-cong-kieu">{cong.kieu}</span>
  </div>
}

export function NodeKhung({ dinhNghia, trangThai, children }: {
  dinhNghia: NodeDefinition; trangThai?: string; children?: ReactNode }) {
  // ⚠️ Dau tai nguyen doc TU `resource.class`, KHONG tu con so VRAM:
  // `palette_v3.RESOURCE_CONG_KHAI = ("class",)` da bo `vram_min_mb`/`slots`/
  // `est_duration_s` — suc chua ha tang khong phoi cho moi nguoi dang nhap.
  const lopTaiNguyen = dinhNghia.resource?.class
  return <div className={`node-khung node-kind-${dinhNghia.kind}`}>
    <header className="node-khung-dau">
      {dinhNghia.icon && <span className="node-icon" aria-hidden>{dinhNghia.icon}</span>}
      <span className="node-tieu-de">{dinhNghia.title}</span>
      <span className="node-kind" data-testid="node-kind">{dinhNghia.kind}</span>
      {trangThai && <span className="node-trang-thai"
        data-testid="node-trang-thai">{trangThai}</span>}
    </header>
    <div className="node-khung-than">
      <small className="node-type">{dinhNghia.type}@{dinhNghia.type_version}</small>
      {lopTaiNguyen === 'gpu'
        ? <small className="node-tai-nguyen" data-testid="node-tai-nguyen"
            title="Tài nguyên: GPU">GPU</small>
        : null}
      {dinhNghia.credential.length > 0 && <small className="node-credential">Cần kết nối</small>}
      {!dinhNghia.publish_duoc && <small className="node-sap-co">Sắp có</small>}
      {children}
    </div>
    <div className="node-cong-cot">
      {dinhNghia.cong_vao.map(c => <ChanCong key={c.ten} cong={c} phia="vao" />)}
      {dinhNghia.cong_ra.map(c => <ChanCong key={c.ten} cong={c} phia="ra" />)}
    </div>
  </div>
}
