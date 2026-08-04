import '@testing-library/jest-dom/vitest'

class TestResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = TestResizeObserver as typeof ResizeObserver

class TestDOMMatrixReadOnly {
  m11=1
  m12=0
  m21=0
  m22=1
  m41=0
  m42=0
  constructor(_transform?:string) {}
}
window.DOMMatrixReadOnly=TestDOMMatrixReadOnly as unknown as typeof DOMMatrixReadOnly
