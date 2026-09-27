import type { KhuMobile } from './kieu'

/** Ba tab của màn hẹp. `display:none` trên màn rộng (`canvas.css`) — nhưng nó
 *  vẫn ở trong DOM, và đó là CỐ Ý: phép kiểm trợ năng đọc được ba vùng ấy mà
 *  không cần thu nhỏ cửa sổ. */
export function MobileTabs({ khu, datKhu }:
    { khu: KhuMobile; datKhu: (k: KhuMobile) => void }) {
  return <nav className="canvas-mobile-tabs" aria-label="Khu vực Canvas">{(['canvas','palette','inspector'] as const).map(item=><button key={item} className={khu===item?'active':''} aria-pressed={khu===item} onClick={()=>datKhu(item)}>{item==='canvas'?'Canvas':item==='palette'?'Công cụ':'Chi tiết'}</button>)}</nav>
}
