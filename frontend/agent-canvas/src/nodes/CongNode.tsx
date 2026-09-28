// Cong cua node: HANG co nhan, va KHAY chi co cham.
//
// 🔴 HAI BAT BIEN CUA UI-0 SONG TRONG TEP NAY. Do lai tren trinh duyet that,
//    ⛔ khong doc ma roi tuyen bo:
//
//    1. MOI cong co MOT vi tri rieng. `.react-flow__handle` la
//       `position:absolute`, va `.react-flow__handle-left` la `{top:50%;left:0}`
//       — khong co to tien DINH VI o tung cong thi ca 15 cong quy chieu ve
//       chinh THE NODE va roi dung mot diem 6x6px (do 27/09: 15 cong / 1 vi tri).
//       => moi cong, o hang hay o khay, deu nam trong mot boc `position:relative`.
//
//    2. `elementFromPoint` tai TAM mot cong tra ve CHINH cong do. Bay cu:
//       nhan kieu (`.node-cong-kieu`, `opacity:.6` => mot stacking context) la
//       sibling dung SAU trong DOM nen no ve DE LEN cong. Cong da co dung vi
//       tri ma van khong keo duoc, va moi phep do toa do deu xanh.
//       => `z-index` cua handle, va nhan chu KHONG duoc phu len tam cong.
import { Handle, Position } from '@xyflow/react'
import type { Cong } from '../nodeDefinition'

const nhanCong = (cong: Cong) => `${cong.ten} · ${cong.kieu}`

/** Kieu cong -> `data-kieu`, de CSS to mau cham theo kieu (`09 §5` P0). */
const HandleCong = ({ cong, phia }: { cong: Cong; phia: 'vao' | 'ra' }) =>
  <Handle type={phia === 'vao' ? 'target' : 'source'} id={cong.ten}
    position={phia === 'vao' ? Position.Left : Position.Right}
    data-kieu={cong.kieu} data-bat-buoc={cong.bat_buoc ? '1' : undefined} />

/** Mot HANG cong: cham + ten + kieu. Cao >= `--handle-hit` (24px, WCAG 2.2 AA
 *  2.5.8). Danh cho cong DANG CO DAY, BAT BUOC, hay kieu khong vo huong. */
export function HangCong({ cong, phia, daNoi }: {
  cong: Cong; phia: 'vao' | 'ra'; daNoi?: boolean }) {
  return <div className={`node-cong node-cong-${phia}`}
    data-da-noi={daNoi ? '1' : undefined}
    data-bat-buoc={cong.bat_buoc ? '1' : undefined}
    title={nhanCong(cong)}>
    <HandleCong cong={cong} phia={phia} />
    <span className="node-cong-ten">{cong.ten}</span>
    <span className="node-cong-kieu">{cong.kieu}</span>
  </div>
}

/** KHAY cong: mot luoi CHAM, khong nhan chu. Tooltip mang `ten · kieu`.
 *
 *  ⭐ Day la phep cat tra loi 525px, va no la phep cat DUY NHAT khong pha bat
 *     bien 1 o tren. Ba duong da xet va bo:
 *
 *     - BO VE handle cua cong phu  => moi canh dang tro vao no bi React Flow
 *                                     vut IM LANG (khong tim thay handle).
 *     - Xep cham doc, buoc 14px    => 24px vung bam cua hai cham canh nhau
 *                                     chong len => WCAG 2.5.8 do, va tam cong
 *                                     chi con cach mep hop ben 2px.
 *     - Giu 15 hang 24px           => 360px chi rieng cong, tran 320px vo nghia.
 *
 *     Khay xep NGANG theo buoc 24px (`gap:12px` + cham 12px) nen chin tham so
 *     vo huong gon vao MOT dong 24px, va hai vung bam 24px chi CHAM NHAU chu
 *     khong chong nhau => bat bien 2 con nguyen.
 */
export function KhayCong({ congs, phia }: { congs: Cong[]; phia: 'vao' | 'ra' }) {
  if (!congs.length) return null
  return <div className={`node-khay node-khay-${phia}`}
    aria-label={`${congs.length} cổng ${phia === 'vao' ? 'vào' : 'ra'} tuỳ chọn`}>
    {congs.map(cong => <span key={cong.ten} className="node-khay-o"
      title={nhanCong(cong)}>
      <HandleCong cong={cong} phia={phia} />
    </span>)}
  </div>
}
