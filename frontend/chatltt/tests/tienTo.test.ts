/**
 * Tien to ngon ngu: mot phep tinh nho, nhung no la thu chan mot lan chuyen
 * huong 302 cho MOI lenh goi — ke ca luong SSE dai.
 */
import { describe, expect, it } from 'vitest'
import { tienToNgonNgu } from '../src/main'

describe('tienToNgonNgu', () => {
  it('tra tien to khi trang co, rong khi khong', () => {
    expect(tienToNgonNgu('/en/chatltt', '/chatltt/api')).toBe('/en')
    expect(tienToNgonNgu('/chatltt', '/chatltt/api')).toBe('')
    expect(tienToNgonNgu('/en/chatltt/', '/chatltt/api')).toBe('/en')
  })

  it('khong nham khi ten app xuat hien trong tien to', () => {
    expect(tienToNgonNgu('/vi/chatltt', '/chatltt/api')).toBe('/vi')
  })

  it('duong la thi tra rong — khong doan', () => {
    expect(tienToNgonNgu('/', '/chatltt/api')).toBe('')
    expect(tienToNgonNgu('/khac', '/chatltt/api')).toBe('')
  })
})
