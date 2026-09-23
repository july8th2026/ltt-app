// Palette nhom theo `category` (spec §13.4).
//
// ⭐ `NHAN_NHOM` KHONG vi pham luat "khong hardcode ten app": tam category la
//    mot danh muc CO DINH cua spec §4.4 (`nut.CATEGORY`), khong phai ten app
//    hay ten tool. Them mot app khong bao gio phai sua tep nay.
import { locPalette, timNut } from '../nodeDefinition'
import type { Gia, NhomPalette, NodeDefinition } from '../nodeDefinition'

export const NHAN_NHOM: Record<string, string> = {
  TRIGGERS: 'Kích hoạt', FLOW: 'Luồng', DATA: 'Dữ liệu', NETWORK: 'Mạng',
  AI: 'AI', LTT_APPS: 'App LTT', CONNECTORS: 'Kết nối',
  SUBWORKFLOWS: 'Workflow con',
}

//: Nhom "gan day" khong phai mot category cua spec — dat khoa ngoai `CATEGORY`
//  de no khong bao gio dung ten voi mot nhom that.
const GAN_DAY = '__GAN_DAY__'

/** Kieu MIME keo-tha. Chi mang `type` — ben nhan tra lai `NodeDefinition` tu
 *  palette, khong chep dinh nghia qua dataTransfer. */
export const MIME_NODE = 'application/x-ltt-node'

function nhanGia(gia: Gia): string {
  if (gia.kieu === 'mien_phi') return 'Miễn phí'
  if (gia.kieu === 'co_dinh') return `${gia.so} credit`
  // `theo_registry`: gia nam o bang gia job (`registry`), khong o dinh nghia.
  return 'Theo bảng giá'
}

function The({ nd, onChon }: {
  nd: NodeDefinition; onChon: (n: NodeDefinition) => void }) {
  // ⚠️ Dau tai nguyen doc TU `resource.class`, KHONG tu con so VRAM:
  // `palette_v3.RESOURCE_CONG_KHAI = ("class",)` da bo `vram_min_mb`/`slots`/
  // `est_duration_s` — suc chua ha tang khong phoi cho moi nguoi dang nhap.
  const lopTaiNguyen = nd.resource?.class
  return <button type="button" className="palette-the" disabled={!nd.publish_duoc}
    draggable={nd.publish_duoc}
    onDragStart={e => e.dataTransfer.setData(MIME_NODE, nd.type)}
    onClick={() => onChon(nd)}>
    {nd.icon && <span className="palette-icon" aria-hidden>{nd.icon}</span>}
    <span className="palette-tieu-de">{nd.title}</span>
    <small className="palette-mo-ta">{nd.description}</small>
    <small className="palette-type">{nd.type}@{nd.type_version}</small>
    <small className="palette-gia">{nhanGia(nd.gia)}</small>
    {lopTaiNguyen === 'gpu'
      ? <small className="palette-tai-nguyen" data-testid="palette-tai-nguyen"
          title="Tài nguyên: GPU">GPU</small>
      : null}
    {nd.credential.length > 0 && <small className="palette-credential">Cần kết nối</small>}
    {!nd.publish_duoc && <small className="palette-sap-co">Sắp có</small>}
  </button>
}

export function PaletteV2({ nhom, truyVan, onTruyVan, onChon, ganDay = [] }: {
  nhom: NhomPalette[]; truyVan: string; onTruyVan: (q: string) => void
  onChon: (nd: NodeDefinition) => void; ganDay?: string[] }) {
  const loc = locPalette(nhom, truyVan)
  const gan = ganDay.map(t => timNut(nhom, t)).filter(Boolean) as NodeDefinition[]
  const hien: NhomPalette[] = (!truyVan.trim() && gan.length)
    ? [{ category: GAN_DAY, nut: gan }, ...loc] : loc
  return <aside className="palette" aria-label="Bảng node">
    <input type="search" className="palette-tim" value={truyVan}
      aria-label="Tìm node" placeholder="Tìm node…"
      onChange={e => onTruyVan(e.target.value)} />
    {hien.length === 0 && <p className="palette-trong">Không tìm thấy node nào.</p>}
    {hien.map(n => <section key={n.category} className="palette-nhom">
      <h3>{n.category === GAN_DAY ? 'Gần đây'
        : NHAN_NHOM[n.category] ?? n.category}</h3>
      {n.nut.map(x => <The key={`${n.category}:${x.type}`} nd={x} onChon={onChon} />)}
    </section>)}
  </aside>
}
