"""Executor AN lan `gpu` cua Auto Scan Video (xem `manifest.py`)."""

#: Be mat ma app KHAC duoc phep import tu app nay.
#:
#: ⭐ Chi `auto_scan_video` (app cha) goi. Hai ten, hai viec khac nhau:
#:    · `bo_do`  — so dang ky bo do cua `qc_do_luong` (giong, SQUIM,
#:      MetricX nam SAU no; app cha khong biet va khong can biet);
#:    · `venv`   — giao thuc chay mot bo do trong `qc-venv`.
#:
#: ⛔ `ocr_khung` DA XOA 26/09 (Task 21): mot duong duy nhat voice->voice ⇒
#:    khong ai doc chu dot vao hinh nua. Xem `apps/auto_scan_video/nguon_loi.py`.
BE_MAT_CONG_KHAI = {
    ("apps.asv_gpu.do_luong", "bo_do"),
    ("apps.asv_gpu.do_luong", "venv"),
}
