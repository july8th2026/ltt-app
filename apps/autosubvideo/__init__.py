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
    # ⛔ `diarize_file`/`assign_speakers` DA RUT khoi be mat (22/09, asv-final):
    #    Auto Scan la MOT giong thuyet minh, khong ai doc nhan nguoi noi. Hai
    #    ham van song o `jobs.py` cua chinh app nay.
    # ── Tang TAC GIA phu de (pha 14 cua Auto Scan V6) ───────────────────────
    #
    # 🔑 **App nay so huu HAI viec, va chi mot trong hai duoc khai o day.**
    #
    #      · tac gia — kieu chu, phan doan, dung `.ass`/`.srt`   -> CONG KHAI
    #      · ma hoa  — `burn.burn()` chay ffmpeg dot vao hinh    -> RIENG
    #
    # ⛔ `burn` **co y** khong co mat. Goi no la cach doc tu nhien nhat cua
    #    *"dung tai viet lai renderer"* va la cach SAI: no chay mot luot ffmpeg
    #    DAY DU cua rieng no, tuc video bi ma hoa lai HAI lan. Auto Scan da co
    #    mot `-filter_complex` va chi can dat them mot mat xich `ass=` vao do.
    #
    # ⭐ Nen su vang mat cua `burn` o day khong phai mot thieu sot — no la lop
    #    cuong che duy nhat cho quyet dinh ay. Mot phien sau muon "tai dung cho
    #    nhanh" se bi linter chan, thay vi de mot khoan no GPU chay im lang cho
    #    toi pha 26 (*Renderer fusion*).
    ("apps.autosubvideo.style_registry", "list_ids"),
    # ⭐ `list_ids` DUYET (chay moi request, chi can chuoi); `list_presets`
    #    HIEN (chay khi mo trang, can `label` + `description`). Hai cau hoi
    #    khac nhau, va goi ham nang cho cau nhe la chi phi tra deu dan cho
    #    khong. Ca hai deu doc `_PRESETS`, nen chung khong the lech nhau.
    ("apps.autosubvideo.style_registry", "list_presets"),
    ("apps.autosubvideo.style_registry", "get_config"),
    ("apps.autosubvideo.segmenter", "SegmentMode"),
    ("apps.autosubvideo.segmenter", "SubtitleEvent"),
    ("apps.autosubvideo.ass_builder", "build_ass"),
    ("apps.autosubvideo.ass_builder", "build_srt"),
    # ── Tinh chinh kieu chu (pha 16 cua Auto Scan V6) ───────────────────
    #
    # ⭐ Xin MO HINH chu khong xin mot ham duyet. `SubtitleStyleConfig` mang
    #    ca hinh dang lan mien gia tri (`extra="forbid"`, `font_size` 12..120,
    #    `bg_opacity` 0..1, `alignment` 1..9), nen Auto Scan duyet tinh chinh
    #    cua khach bang **chinh no**. Viet lai nhung rang buoc ay o phia Auto
    #    Scan la tao mot ban sao se lech, va lech im lang: hai ban deu "hop
    #    le" theo luat cua chinh minh.
    ("apps.autosubvideo.schemas", "SubtitleStyleConfig"),
    # ── Phu de nguon tieng Trung (asv-final, lan phu-de, 22/09) ─────────────
    #
    # ⭐ MO RONG nang luc cua app nay thay vi chep sang Auto Scan: ngat dong
    #    chu Han (`_wrap_text` chi ngat theo dau cach, nen mot cau tieng Trung
    #    ra MOT dong dai vo han) va hoi mot font co VE duoc cac ky tu khong
    #    (`is_font_available` chi tra loi "co font ten do khong").
    ("apps.autosubvideo.segmenter", "wrap_lines"),
    ("apps.autosubvideo.font_checker", "missing_glyphs"),
}
