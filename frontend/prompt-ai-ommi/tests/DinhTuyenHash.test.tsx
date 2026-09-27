/**
 * DinhTuyenHash.test.tsx — man hinh phai nam trong URL, khong chi trong state.
 *
 * 🔴 VI SAO CHOT. Truoc 07/09 `OmmiShell` giu man trong `useState` va khong co
 *    tich hop lich su nao. Do la BA loi nguoi dung that:
 *
 *      tai lai trang  -> ve `overview`, mat cho dang xem
 *      nut Back       -> THOAT khoi app thay vi ve man truoc
 *      chia se link   -> khong tro duoc toi mot man cu the
 *
 *    Cai thu hai nang nhat tren di dong: Back la cu chi dieu huong chinh.
 *
 * ⭐ Plan xep S2 thanh viec cua BO DO ("view con la nut React khong `href`,
 *    can kich ban dieu huong rieng"). Do xong thi thay cho hong nam o SAN PHAM,
 *    va sua no thi bo do doc duoc luon — nhung do la he qua, khong phai muc dich.
 */
import { cleanup, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { MAN_MAC_DINH, nhanMan, OmmiShell } from '../src/OmmiShell'

/* ⭐ Ba phep duoi doc `MAN_MAC_DINH` thay vi go ten man. Hanh vi dang bao ve
 *    la "hash bay ba phai roi ve mot man THAT, khong render vung trong" — no
 *    KHONG doi khi mac dinh doi. Ban truoc go /Tổng quan/ va DO ngay khi Q-3
 *    doi mac dinh sang `studio`: mot phep kiem go con so/ten cua mot quyet dinh
 *    la mot phep kiem se do khi quyet dinh doi. */
const NHAN_MAC_DINH = new RegExp(nhanMan(MAN_MAC_DINH))

function dat(hash: string) {
  window.location.hash = hash
}

/* ⛔ Hoi RAIL, khong hoi ca trang. Man `Storyboard` co mot nut chua chinh chu
 *    "Storyboard" ben trong no, nen `getByRole('button', {name: /Storyboard/})`
 *    tren toan trang tim ra HAI phan tu va nem loi. Phep kiem phai hoi dung
 *    thu no muon biet: **nut nao tren thanh dieu huong dang duoc danh dau**.
 */
function nutRail(ten: RegExp) {
  const rail = document.querySelector('.ommi-rail') as HTMLElement
  return within(rail).getByRole('button', { name: ten })
}

afterEach(() => {
  cleanup()
  window.location.hash = ''
})

describe('dinh tuyen theo hash', () => {
  it('mo dung man tu hash co san', () => {
    dat('#/storyboard')
    render(<OmmiShell csrfToken="x" />)
    const nut = nutRail(/Storyboard/)
    expect(nut.getAttribute('aria-current')).toBe('page')
  })

  it('hash bay ba roi ve man mac dinh, KHONG render vung trong', () => {
    // ⛔ Hash la duong vao TU NGOAI — khong duoc tin. Mot `#/khong-co-that`
    //    ma render mot vung trong la mot trang trang khong ai giai thich duoc.
    dat('#/khong-co-that')
    render(<OmmiShell csrfToken="x" />)
    const nut = nutRail(NHAN_MAC_DINH)
    expect(nut.getAttribute('aria-current')).toBe('page')
  })

  it('khong co hash thi mo man mac dinh', () => {
    dat('')
    render(<OmmiShell csrfToken="x" />)
    const nut = nutRail(NHAN_MAC_DINH)
    expect(nut.getAttribute('aria-current')).toBe('page')
  })

  it('man CHUA XAY khong vao duoc bang hash', () => {
    // Nut cua man chua xay bi `disabled`; hash khong duoc la duong vong qua do.
    dat('#/chua-xay')
    render(<OmmiShell csrfToken="x" />)
    const nut = nutRail(NHAN_MAC_DINH)
    expect(nut.getAttribute('aria-current')).toBe('page')
  })
})
