/** Định dạng thời gian cho mặt THỰC THI. Thuần, không React, không I/O.
 *
 *  ⭐ CẮT CHUỖI ISO, ⛔ KHÔNG `toLocaleTimeString`. Múi giờ/locale của máy chạy
 *     test và của máy người dùng khác nhau sẽ làm con số TRÔI — một phép so giờ
 *     trong vitest xanh trên máy này, đỏ trên máy khác. Cắt chuỗi thì không.
 *     (Luật này có từ `RunV3Panel` bản đầu; giữ nguyên khi dời sang đây.)
 */

/** `"2026-09-24T00:00:10+00:00"` -> `"00:00:10"`. */
export const gio = (iso: string) => iso.slice(11, 19)

/** Số MILI-GIÂY giữa hai mốc ISO, hoặc `null` khi không đo được.
 *
 *  ⭐ `null`, ⛔ KHÔNG `0`. "Không đo được" và "mất 0 giây" là HAI chuyện, và
 *     gộp chúng vào một giá trị làm mất khả năng phân biệt: một bước chưa có
 *     mốc nào sẽ hiện `0s` y như một bước chạy tức thì. Bên gọi phải tự quyết
 *     hiện gì cho `null` — và phải hiện KHÁC.
 */
export function khoangMs(tuIso: string, denIso: string): number | null {
  const ms = new Date(denIso).getTime() - new Date(tuIso).getTime()
  return Number.isFinite(ms) && ms >= 0 ? ms : null
}

/** `1234` -> `"1s"`, `64000` -> `"1m 4s"`. `null` -> `null` (bên gọi quyết). */
export function nhanThoiLuong(ms: number | null): string | null {
  if (ms === null) return null
  const s = Math.round(ms / 1000)
  return s < 60 ? `${s}s` : `${Math.floor(s / 60)}m ${s % 60}s`
}

/** Tiện dụng: hai mốc ISO -> nhãn, hoặc `null`. */
export const thoiLuong = (tuIso: string, denIso: string) =>
  nhanThoiLuong(khoangMs(tuIso, denIso))
