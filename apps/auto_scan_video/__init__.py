"""Auto Scan Video — san pham long tieng Viet cho video.

Ba app, mot san pham (ADR-001 D5): app nay la thu khach nhin thay, con
`asv_media` va `asv_gpu` la executor an duoi no. Chung phai ton tai rieng vi
quyen nhat job duoc loc theo **APP** chu khong theo `job_type`
(`platform_core/jobs.py:158-164`), nen mot app khai du ca ba nang luc se chi
chay duoc tren mot lan co du ca ba — va tren doi hinh chia lan, job cua no nam
`queued` mai mai, khong loi nao bao.
"""
from __future__ import annotations

#: Be mat ma app KHAC duoc phep import tu app nay. Moi thu ngoai danh sach nay
#: la noi bo, va `tools/lint_app_contract.py` chan lai.
#:
#: ⭐ Danh sach nay ngan CO CHU Y. No la ly do `thi_hanh.py` ton tai: ban dau
#:    `asv_gpu` import thang `_chay_giai_doan` tu `asv_media` — mot ten mo dau
#:    bang gach duoi, tuc mot loi hua rieng tu — va linter chan lai. Cach sua
#:    dung khong phai khai them mot ngoai le, ma la **dua than dung chung ve app
#:    so huu mo hinh run/stage** roi khai dung hai cai ten.
#:
#: ⛔ Them mot dong vao day la mot QUYET DINH KIEN TRUC. Phai sua CA HAI phia:
#:    o day va o `APP_DUOC_DUNG_APP` trong `tools/lint_app_contract.py`. Linter
#:    doi hai ban khai khop nhau chinh xac, nen khong the noi long mot ben.
BE_MAT_CONG_KHAI = {
    # Chuoi giai doan co dinh + bang tra `job_type` -> giai doan. Executor can
    # no de biet job_type nao thuoc giai doan nao.
    ("apps.auto_scan_video", "pipeline"),
    # Than thi hanh dung chung cua mot giai doan.
    ("apps.auto_scan_video.thi_hanh", "chay_theo_job_type"),
}
