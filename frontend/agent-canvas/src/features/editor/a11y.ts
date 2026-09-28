// Nhãn trợ năng của React Flow mặc định là tiếng Anh (`Zoom In`, `Fit View`, `Mini Map`…);
// @xyflow/react ≥12.5 nhận `ariaLabelConfig` để thay (khoá: @xyflow/system constants).
export const NHAN_TRO_NANG_VI = {
  'node.a11yDescription.default': 'Nhấn Enter hoặc Space để chọn khối. Nhấn Delete để xoá, Escape để huỷ.',
  'node.a11yDescription.keyboardDisabled': 'Nhấn Enter hoặc Space để chọn khối, rồi dùng phím mũi tên để di chuyển. Nhấn Delete để xoá, Escape để huỷ.',
  'node.a11yDescription.ariaLiveMessage': ({ x, y }: { direction: string; x: number; y: number }) => `Đã di chuyển khối. Vị trí mới x: ${x}, y: ${y}`,
  'edge.a11yDescription.default': 'Nhấn Enter hoặc Space để chọn dây nối. Nhấn Delete để xoá, Escape để huỷ.',
  'controls.ariaLabel': 'Điều khiển khung vẽ',
  'controls.zoomIn.ariaLabel': 'Phóng to',
  'controls.zoomOut.ariaLabel': 'Thu nhỏ',
  'controls.fitView.ariaLabel': 'Vừa khung nhìn',
  'controls.interactive.ariaLabel': 'Bật/tắt tương tác',
  'minimap.ariaLabel': 'Bản đồ thu nhỏ',
  'handle.ariaLabel': 'Điểm nối',
}
