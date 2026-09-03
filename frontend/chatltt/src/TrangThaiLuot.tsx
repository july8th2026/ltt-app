/**
 * TrangThaiLuot.tsx — dòng "đang làm gì" trong lúc model chưa trả chữ nào.
 *
 * ## Vì sao có tệp này
 *
 * 🔴 Đo trên production 03/09, một lượt hỏi bình thường:
 *
 *      t+0,5s  một chấm nhịp nhỏ, không chữ
 *      t+3,7s  khối "Suy luận" ĐỘT NGỘT hiện ra, đẩy mọi thứ xuống
 *      t+6,0s  chữ trả lời bắt đầu
 *
 *      CLS = 0,1642   (ngưỡng "kém" của Google là 0,1)
 *
 *    Ba giây rưỡi im lặng còn tệ hơn cú nhảy: một chấm nhịp trả lời được câu
 *    "còn sống không", nhưng không trả lời được câu "đang làm gì".
 *
 * ## Năm nguyên tắc, rút từ LibreChat @ 9e74cc0
 *
 * Họ có hẳn một họ thành phần cho đúng khoảng thời gian này (`ProgressText`,
 * `PendingSkillCall`, `Summary`). Chú thích đầu `PendingSkillCall.tsx` nói
 * thẳng ý đồ: một chỗ giữ chỗ cho *"the interim window between submit and the
 * backend's real content part landing"*, với *"same icon, same shimmer, same
 * label strings so the visual language matches the real card it'll be replaced
 * by"*.
 *
 *   1. Khoảng chờ LUÔN có người ở — không bao giờ để hộp trống.
 *   2. Chỗ giữ chỗ trông GIỐNG thứ sẽ thay nó.
 *   3. Chiều cao CỐ ĐỊNH, nội dung `absolute`.
 *   4. Đổi trạng thái theo SỰ KIỆN THẬT, không theo hẹn giờ.
 *   5. Không bày nút bấm chưa dùng được.
 *
 * ⭐ Nguyên tắc 3 là thứ thật sự giết cú nhảy 0,0749 — nó là về **hình học**,
 *    còn bốn cái kia về **thông tin**. Xem `.ltc-trangthai` trong `chatltt.css`.
 *
 * ⛔ VÀ KHÔNG BỊA RA PHA NÀO TA KHÔNG CÓ SỰ KIỆN CHO NÓ. "Đang tìm tài liệu"
 *    nghe hay nhưng ChatLTT không có bước tìm tài liệu; hiển thị nó là mô tả
 *    một tiến trình không tồn tại. Và ngày nào ta thêm RAG thật, sẽ không ai
 *    còn tin dòng trạng thái này nữa.
 */
import { useEffect, useState } from 'react'
import type { ThiHanh } from './kieu'

export type TrangThaiLuotProps = {
  ex: ThiHanh | null | undefined
  /** Đã có chữ trả lời chưa — khi có thì dòng này nhường chỗ. */
  daCoChu: boolean
  dangChay: boolean
}

/**
 * Pha suy ra từ **thứ đã có trong `ThiHanh`**, không từ một trường mới.
 *
 * ⭐ Không phải thêm cột CSDL, không phải thêm sự kiện SSE: `seq`,
 *    `reasoning_text` và `partial_text` đã đủ kể lại câu chuyện.
 *
 *   seq === 0                    → chưa có sự kiện nào ⇒ đang xếp hàng
 *   seq > 0, chưa gì khác        → `response.started` đã tới ⇒ đang chuẩn bị
 *   reasoning_text có chữ        → `reasoning.delta` đang chảy ⇒ đang suy nghĩ
 *   partial_text có chữ          → hết việc của dòng này
 */
export function phaCua(ex: ThiHanh | null | undefined, daCoChu: boolean): string {
  if (daCoChu) return ''
  if (!ex) return 'xep_hang'
  if ((ex.reasoning_text ?? '').length > 0) return 'suy_nghi'
  if ((ex.seq ?? 0) > 0) return 'chuan_bi'
  return 'xep_hang'
}

const NHAN: Record<string, string> = {
  xep_hang: 'Đang xếp hàng…',
  chuan_bi: 'Đang chuẩn bị…',
  suy_nghi: 'Đang suy nghĩ',
}

export function TrangThaiLuot({ ex, daCoChu, dangChay }: TrangThaiLuotProps) {
  const pha = dangChay ? phaCua(ex, daCoChu) : ''
  const [giay, datGiay] = useState(0)

  // Đồng hồ CHỈ chạy ở pha suy nghĩ, và nó là thứ **mô tả** một sự kiện có
  // thật (reasoning đang chảy), không phải thứ **quyết định** pha.
  useEffect(() => {
    if (pha !== 'suy_nghi') { datGiay(0); return }
    const bd = Date.now()
    const h = window.setInterval(() => datGiay(Math.floor((Date.now() - bd) / 1000)), 1000)
    return () => window.clearInterval(h)
  }, [pha])

  // ⛔ LUÔN vẽ khung, kể cả khi không có pha nào. Đó chính là nguyên tắc 3:
  //    chỗ này chiếm sẵn chiều cao của nó từ đầu, nên lúc chữ trả lời tới thì
  //    không có gì bị đẩy. Ẩn bằng `visibility` chứ không bằng `display`.
  return (
    <div
      className="ltc-trangthai"
      data-trangthai={pha || 'khong'}
      style={{ visibility: pha ? 'visible' : 'hidden' }}
      role="status"
      aria-live="polite"
    >
      <span className="ltc-trangthai__chu">
        {pha ? NHAN[pha] : ''}
        {pha === 'suy_nghi' && giay > 0 ? ` ${giay} giây…` : ''}
      </span>
    </div>
  )
}
