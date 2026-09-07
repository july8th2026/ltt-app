import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, vi } from 'vitest'

afterEach(cleanup)

/* 🔴 Dọn cả URL, không chỉ DOM.
 *
 *    Từ 07/09 `OmmiShell` giữ màn hình trong `location.hash` chứ không chỉ
 *    trong `useState` — để nút Back và việc tải lại trang hoạt động đúng.
 *    Cái giá của nó: **URL là trạng thái toàn cục**, và jsdom dùng CHUNG một
 *    `window.location` cho mọi phép kiểm trong cùng một tệp.
 *
 * ⛔ Thiếu dòng này thì một phép kiểm bấm sang `Kho tài nguyên` sẽ để lại
 *    `#/resources`, và phép kiểm SAU đó — dù `render()` hoàn toàn mới — vẫn mở
 *    ra màn ấy. Đo 07/09: đúng hai phép kiểm `Tổng quan` trong
 *    `ResourceLibrary.test.tsx` đỏ vì lý do này, và triệu chứng
 *    (*"Unable to find text: Bắt đầu từ ba bước"*) không hề nhắc tới URL.
 *
 * ⭐ `cleanup` đã dọn DOM từ lâu vì cùng một lý do. URL chỉ là một mảnh trạng
 *    thái chung nữa, và nó cần đúng cách đối xử ấy.
 */
afterEach(() => {
  window.location.hash = ''
})

HTMLCanvasElement.prototype.getContext = vi.fn(() => null)
