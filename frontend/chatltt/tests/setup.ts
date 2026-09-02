import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

// 🔴 DON DOM SAU MOI TEST — bat buoc, va day la ly do:
//
//    `@testing-library/react` chi tu don khi vitest chay o che do `globals`.
//    Cau hinh cua kho nay KHONG bat `globals` (xem `vite.config.ts`), nen moi
//    `render()` chong them mot cay vao `document.body`. Hau qua khong phai mot
//    loi ro rang ma la `getByLabelText` bao "found multiple elements" — mot
//    thong diep tro vao dong TEST chu khong tro vao nguyen nhan.
afterEach(() => { cleanup() })

// jsdom khong cai `scrollIntoView`, va `App` goi no moi lan su that doi.
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = function scrollIntoView() {}
}
