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
    # ── Phan vai nguoi noi (pha 07 cua Auto Scan V4) ────────────────────────
    #
    # ⭐ THEM, khong sua: ca hai ham da ton tai va da chay: `autosubvideo` tu
    #    dung chung o `jobs.py`. Viec duy nhat o day la KHAI chung ra — truoc
    #    day chung la duong RIENG, nen mot app khac dung chung la voi qua rao.
    #
    # 🔑 Vi sao Auto Scan can: `hop_dong_v4.CHE_DO_GIONG_TU_KHOP` (AUTO_MATCH)
    #    phai doc dac diem giong THAT tu video de chon giong khop. Khong co
    #    bang chung nguoi noi thi "tu khop" chi con la "lay giong mac dinh" —
    #    dung dieu `ADR-V4-001` D-V4-04 cam.
    #
    # ⛔ Va no la NANG LUC CO DIEU KIEN: `USER_SELECTED` khong can no, nen
    #    khong duoc chay mac dinh. Xem `giai_doan_chep_loi.can_phan_vai`.
    ("apps.autosubvideo.ai_workflows", "diarize_file"),
    ("apps.autosubvideo.ai_workflows", "assign_speakers"),
}
