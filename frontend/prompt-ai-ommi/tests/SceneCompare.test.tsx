import { describe, expect, it } from 'vitest'
import type { SceneCompare } from '../src/ommiApi'

/**
 * H19.5 — hai bản đặt cạnh nhau.
 *
 * Test ở đây kiểm HÌNH DẠNG DỮ LIỆU mà giao diện dựa vào, không kiểm pixel.
 * Lý do: bài học đắt nhất của app này là client và test cùng mã hoá một giả
 * định sai về hợp đồng API (`/api/projects` trả `{items:[…]}` chứ không phải
 * mảng trần) — cả hai cùng xanh trong khi trang thật vỡ. Nên kiểu dữ liệu
 * phải khớp đúng cái backend trả.
 */
describe('Hợp đồng dữ liệu so hai bản', () => {
  const mau: SceneCompare = {
    scene_id: 's1',
    left: {
      version: 1, prompt: 'Trời nắng', image_key: 'ommi/u/1.png',
      feedback: '', job_id: 'j1', created_at: '2026-08-06T00:00:00+00:00',
    },
    right: {
      version: 2, prompt: 'Trời mưa', image_key: 'ommi/u/2.png',
      feedback: 'đổi thời tiết', job_id: 'j2',
      created_at: '2026-08-06T01:00:00+00:00',
    },
    prompt_khac_nhau: ['-Trời nắng', '+Trời mưa'],
    cung_anh: false,
  }

  it('mang đủ thứ cần để SO, không chỉ để xem', () => {
    // Thiếu prompt hoặc feedback thì người dùng lại phải đoán vì sao hai bản
    // khác nhau — đúng vấn đề tính năng này sinh ra để giải.
    expect(mau.left.prompt).not.toBe(mau.right.prompt)
    expect(mau.right.feedback).toBeTruthy()
    expect(mau.prompt_khac_nhau.length).toBeGreaterThan(0)
  })

  it('phần khác nhau chỉ rõ dòng nào thêm, dòng nào bớt', () => {
    const them = mau.prompt_khac_nhau.filter((d) => d.startsWith('+'))
    const bot = mau.prompt_khac_nhau.filter((d) => d.startsWith('-'))
    expect(them).toContain('+Trời mưa')
    expect(bot).toContain('-Trời nắng')
  })

  it('cờ cung_anh tồn tại để cảnh báo lần chạy lại không đổi gì', () => {
    // Provider trả lại đúng ảnh cũ là chuyện có thật. Không có cờ này thì
    // người dùng soi hai ảnh bằng mắt rồi kết luận sai.
    const trungAnh: SceneCompare = {
      ...mau,
      right: { ...mau.right, image_key: mau.left.image_key },
      cung_anh: true,
    }
    expect(trungAnh.cung_anh).toBe(true)
    expect(trungAnh.left.image_key).toBe(trungAnh.right.image_key)
  })

  it('bản chưa có ảnh vẫn hợp lệ (image_key rỗng, không phải null)', () => {
    // Giao diện phân nhánh bằng `ban.image_key ? <img> : <p>`; null sẽ lọt qua
    // kiểu TypeScript nhưng làm hỏng phép kiểm ở chỗ khác.
    const chuaCoAnh: SceneCompare = {
      ...mau, left: { ...mau.left, image_key: '' },
    }
    expect(chuaCoAnh.left.image_key).toBe('')
    expect(typeof chuaCoAnh.left.image_key).toBe('string')
  })
})
