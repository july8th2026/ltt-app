/**
 * main.tsx — diem vao. Doc cau hinh tu `data-*` cua the goc, khong tu bien toan cuc.
 *
 * ⛔ `data-csrf` den tu Jinja (`issue_csrf_token`), khong phai tu localStorage:
 *    token CSRF gan voi PHIEN, va mot ban sao trong localStorage la mot ban sao
 *    song sot qua ca luc dang xuat.
 */
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { Api } from './api'
import { App } from './App'
import './chatltt.css'

/**
 * Tien to ngon ngu cua trang hien tai (`/en`, hay rong khi tieng Viet).
 *
 * 🔴 VI SAO PHAI SUY. `I18nMiddleware` chuyen huong **302** moi GET khong mang
 *    tien to sang ban co tien to. Do 03/09 tren trinh duyet that: moi lenh GET
 *    toi API tra ve HAI request (302 roi 200). Voi mot lenh JSON thi do la lang
 *    phi; voi **SSE** thi no la mot lan mo lai ket noi dai — dung cho khong nen
 *    tra them gia.
 *
 * ⚠️ Cac bundle khac (`autosub-studio`, `prompt-ai-ommi`) viet cung duong
 *    khong tien to va chiu dung phi nay. Khong sua ho o day: viec do thuoc
 *    nguoi so huu chung. Ghi lai o `docs/CHATLTT/reports/08b_*.md`.
 */
export function tienToNgonNgu(duong: string, apiGoc: string): string {
  const dau = apiGoc.split('/')[1] ?? ''
  const i = duong.indexOf(`/${dau}`)
  return i > 0 ? duong.slice(0, i) : ''
}

const goc = document.getElementById('chatltt-root')
if (goc) {
  const apiGoc = goc.dataset.api ?? '/chatltt/api'
  const api = new Api(
    tienToNgonNgu(window.location.pathname, apiGoc) + apiGoc,
    goc.dataset.csrf ?? '',
  )
  createRoot(goc).render(
    <StrictMode>
      <App api={api} />
    </StrictMode>,
  )
}
