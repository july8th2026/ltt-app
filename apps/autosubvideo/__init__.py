"""App autosubvideo — di tru tu auto_sub_video (BOT GEMINI)."""

#: Be mat ma app KHAC duoc phep import tu app nay. Moi thu ngoai danh sach nay
#: la noi bo, va `tools/lint_app_contract.py` chan lai.
#:
#: ⭐ `transcribe_file` la duong chep loi DUY NHAT dang chay trong nen tang. Auto
#:    Scan Video **boc** no thay vi uy quyen mot job sang app nay, va ly do rat
#:    cu the: `manifest.py:47,51` o day khai `requires=("ffmpeg",)` trong khi
#:    khai `gpu_vram_mb` cho `transcribe`/`diarize`. Uy quyen la ke thua ban khai
#:    do — tren mot doi hinh chia lan, viec GPU se bi xep vao lan ffmpeg.
#:    Xem `docs/auto_scan_video/adr/ADR-001-execution-billing-resource.md` D5.
#:
#: ⛔ Khai o day KHONG lam app nay doi hanh vi. Duong cu cua `autosubvideo` chay
#:    nguyen nhu truoc; day chi la mot ban khai rang mot cai ten da la cong khai.
#:    Them mot dong vao day la mot QUYET DINH KIEN TRUC: phai sua CA HAI phia,
#:    o day va o `APP_DUOC_DUNG_APP` trong `tools/lint_app_contract.py`.
BE_MAT_CONG_KHAI = {
    ("apps.autosubvideo.transcription", "transcribe_file"),
}
