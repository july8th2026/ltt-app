r"""asv_so_ke_toan_cau.py — So ke toan SO DOAN (cau thoai) xuyen qua cac giai
doan cua Auto Scan Video, doc THANG tu `asv_stage.outputs` da co san.

    python tools\asv_so_ke_toan_cau.py <run_id>

## Vi sao tep nay ton tai (N1, B14 `99_TONG_HOP_VA_NAN_PLAN.md` §3)

Khi chu du an bao *"42-66 giay khong co tieng"*, cau tra loi "ROI O CHANG NAO"
truoc gio phai lam **bang tay**: viet script dung mot lan, truy CSDL, tai
artifact JSON tu `Storage`, doan ten khoa (`bat`/`ket` chu khong phai
`bat_dau`/`ket_thuc`), roi ghep lai — mat mot buoi. Du lieu ay **da nam san**
trong `asv_stage.outputs` cua moi luot chay; thieu dung MOT ham doc ngang. Xem
`D:\Viral\resources\app-src\localize.py:114-172` de lay HINH DANG (so ke toan
cau xuyen chang, in `RƠI N CAU O DAY`) — kho do CHI DOC, khong chep ma.

## Hop dong khoa `outputs` — khoa CAP MOT, khong nam duoi `outputs["tom_tat"]`

`apps/auto_scan_video/thi_hanh.py:631-632` PHANG `tom_tat` cua giai doan thang
vao `asv_stage.outputs`:

    ket_qua = {"stage": ten, "khoa_asset": khoa_ra, **(ra.get("tom_tat") or {})}

nen `outputs["so_doan"]` doc duoc truc tiep. `tools/asv_doi_soat.py` da tra gia
cho dung cai bay nay (ban truoc cua no doc `gd["tom_tat"]` — mot khoa KHONG TON
TAI — va moi phep do tra `None` mai mai ma van xanh). Tep nay theo dung khuon
CSDL/tinh cua `asv_doi_soat.py`: **lop TINH thuan** (`so_ke_toan`, kiem duoc,
khong can CSDL) + **lop CSDL** (`outputs_bon_giai_doan`) doc `asv_stage.outputs`
qua `features.giai_doan_theo_ten`.

## Ban do `giai_doan -> khoa -> dai luong THAT` (doc tu ma nguon, khong doan)

    transcribe        so_doan          = so DOAN chep loi SAU `cat_lai` (cau)
                                          neo: ban_ghi.py:397 tom_tat();
                                               giai_doan_chep_loi.py:194 (tra ve)
    content_process   so_doan_goc      = so DOAN dau vao (= ban ghi cua
                                          transcribe; GD1 KHONG loc ban bien
                                          tap nen `giu = goc` toan bo)
                                          neo: giai_doan_noi_dung.py:216-220,431
                       so_doan          = so MUC noi dung sinh ra — 1-DOI-1 voi
                                          dau vao (`long_tieng.dung` nem
                                          `ThieuDoan` neu thieu 1 muc, nen giai
                                          doan CHI ve `succeeded` khi du)
                                          neo: long_tieng.py:552-569,662;
                                               giai_doan_noi_dung.py:427
    voice_synthesis    so_ma_noi_dung  = so MA noi dung dua vao TTS
                                          (= content_process.so_doan)
                                          neo: giai_doan_giong.py:132,812
                       so_doan          = so KHE DOC = so TEP TIENG sinh ra
                                          (nhieu `ma` co the CHIA CHUNG mot khe
                                          qua `gop_khe`)
                                          neo: nan_cho_vua.py:484 tom_tat();
                                               giai_doan_giong.py:150-152,838
                       so_khe_da_gop    = so NHOM co > 1 thanh vien — DEM NHOM,
                                          KHONG dem so ma bi hap thu (canh bao 1)
                                          neo: giai_doan_giong.py:813
                       so_doan_im_lang  = so MA bi bo qua vi RONG sau chuan hoa
                                          — MAT NOI DUNG that nhung KHONG lam
                                          giam `so_doan` (mot khe im lang van
                                          chiem dung MOT cho trong `nhom`)
                                          neo: giai_doan_giong.py:229,235-252,846
    timing_align       so_doan          = so DONG trong KE HOACH thoi gian —
                                          no lai VE 1-DOI-1 voi content_process:
                                          `nan_thoi_luong.no_ban_ke` tra lai
                                          MOT dong `ban_ke` cho MOI `ma` goc cua
                                          nhom (ke ca khe da gop)
                                          neo: giai_doan_giong.py:744-757;
                                               thoi_gian.py:319-328,435
                       so_doan_bi_cat   = TONG so lan CAT xuyen ke hoach — GOM
                                          HAI LOAI khac nhau (canh bao 2)
                                          neo: thoi_gian.py:271-345,436

## Canh bao 1 — `voice_synthesis.so_doan` (KHE) doi TEN voi `content_process.so_doan` (MA)

`nan_thoi_luong.nhom_chi_so` la MOT PHAN HOACH DAY DU cua moi chi so `ma`
(docstring cua no, `nan_thoi_luong.py:407`: *"Nhom mot phan tu van la mot
nhom (luon co mat)"*) — khong chi so nao bi RONG khoi mot nhom. Vi
`giai_doan_giong.py:150-152` dung `muc = [_gop_mot_nhom(...) for g in nhom]`
nen `voice_synthesis.so_doan == len(nhom)` DUNG BANG DINH NGHIA. Ket qua:
hieu `so_ma_noi_dung - so_doan(khe)` LUON duoc giai thich TRON VEN boi GOP —
no KHONG THE la mot cau ROI THAT o chang nay.

⚠️ Nhung `so_khe_da_gop` (dem SO NHOM co > 1 thanh vien) chi bang dung hieu so
   khi MOI nhom gop co CHINH XAC 2 thanh vien. Mot nhom 3 thanh vien dong gop 2
   vao hieu so nhung chi dem 1 vao `so_khe_da_gop` — cong cu nay IN CA HAI con
   so va KHONG suy hieu so tu `so_khe_da_gop`.

## Canh bao 2 — `timing_align.so_doan_bi_cat` TRON hai loai CAT khac nhau

Doc `thoi_gian.py:220-345`: (a) cat VE 0 ms nhung dong VAN O LAI trong ke
hoach (`cat = dai_sau; dai_sau = 0` roi van `ke.append(...)` —
`thoi_gian.py:271-279,298-306,319-328`) — KHONG lam giam `so_doan`; (b) BI
LOAI HAN khoi ke hoach o vong `while` cuoi ham, khi tong do dai vuot video
nguon (`ke.pop()` — `thoi_gian.py:341-345`) — DAY MOI la ROI THAT, lam giam
`so_doan`. Hai loai CUNG cong vao `so_doan_bi_cat`. ⇒ cong cu nay tach:

    roi_that = content_process.so_doan - timing_align.so_doan   (loai b)
    con_dong_mat_tieng = so_doan_bi_cat - roi_that                (loai a)

## Gioi han co y

CHI doc `outputs` da co san trong CSDL. KHONG tai artifact tu `Storage`, KHONG
nap model, KHONG chay lai giai doan nao — nen cong cu nay chay trong VAI GIAY
tren mot `run_id` bat ky. Giai doan CHUA chay hay `outputs` THIEU khoa can thi
in `⛔ chua co`, KHONG in `0` (`0` la "do duoc va bang khong"; vang la "chua do
duoc" — hai dieu NGUOC nhau).
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ⭐ Ten phim tieng Trung lam console cp1252 NEM (da xay ra 28/09). `reconfigure`
#    sua TAI CHO luong DANG CO — khong boc mot `TextIOWrapper` MOI (boc moi se
#    lam pytest hong capture luc import, xem canh bao dau `asv_doi_soat.py`).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ══════════════════════════════════════════════════════════════════════════════
#  Hang so — ten giai doan + khoa outputs, khai ra thanh DU LIEU
# ══════════════════════════════════════════════════════════════════════════════

#: Bon giai doan mang dai luong "so cau" — xem ban do o dau tep. Cac giai doan
#: KHAC cua `pipeline.CHUOI` (media_prepare, audio_prepare, compose, render,
#: edit_plan, image_finish, qc, qc_do_luong, qc_ai) KHONG dem "cau", nen bang in
#: ra danh dau ro "khong dem cau" cho chung — KHONG lay `0` hay `⛔ chua co` gia
#: mao mot dieu chung khong do.
TRANSCRIBE = "transcribe"
CONTENT_PROCESS = "content_process"
VOICE_SYNTHESIS = "voice_synthesis"
TIMING_ALIGN = "timing_align"

GIAI_DOAN_DEM_CAU: tuple[str, ...] = (
    TRANSCRIBE, CONTENT_PROCESS, VOICE_SYNTHESIS, TIMING_ALIGN)

#: `{ten_giai_doan: (khoa can doc,...)}` — cung tinh than voi `KHOA_CAN` cua
#: `asv_doi_soat.py`: khai ra thanh du lieu de mot phep kiem co hoc doi chieu
#: duoc, va de mot khoa moi khong roi vao quen lang.
KHOA_CAN: dict[str, tuple[str, ...]] = {
    TRANSCRIBE: ("so_doan",),
    CONTENT_PROCESS: ("so_doan_goc", "so_doan"),
    VOICE_SYNTHESIS: ("so_ma_noi_dung", "so_doan", "so_khe_da_gop",
                      "so_doan_im_lang"),
    TIMING_ALIGN: ("so_doan", "so_doan_bi_cat"),
}

#: Ba ly do KHAC LOAI mot con so co the vang mat — cung khuon voi
#: `asv_doi_soat.THIEU_GIAI_DOAN/CHUA_XONG/THIEU_KHOA`.
THIEU_GIAI_DOAN = "giai_doan_chua_chay"
CHUA_XONG = "giai_doan_chua_xong"
THIEU_KHOA = "outputs_thieu_khoa"

#: Nhan hien thi khi mot con so KHONG do duoc — KHONG bao gio la `"0"`.
CHUA_CO = "⛔ chưa có"


# ══════════════════════════════════════════════════════════════════════════════
#  Lop TINH — thuan, kiem duoc, KHONG can CSDL
# ══════════════════════════════════════════════════════════════════════════════

def _doc_so(outputs_theo_giai_doan: dict[str, dict],
           trang_thai_theo_giai_doan: dict[str, str | None],
           ten_giai_doan: str, khoa: str) -> tuple[int | None, str]:
    """`(gia_tri, ly_do_neu_thieu)`. `gia_tri=None` <=> con so CHUA do duoc.

    `ly_do_neu_thieu` rong khi `gia_tri` khong `None`.
    """
    tt = trang_thai_theo_giai_doan.get(ten_giai_doan)
    if tt is None:
        return None, THIEU_GIAI_DOAN
    if str(tt) != "succeeded":
        return None, f"{CHUA_XONG}:{tt}"
    out = outputs_theo_giai_doan.get(ten_giai_doan) or {}
    if khoa not in out or out.get(khoa) is None:
        return None, THIEU_KHOA
    try:
        return int(out[khoa]), ""
    except (TypeError, ValueError):
        return None, f"{THIEU_KHOA}:kieu_du_lieu_la_{type(out[khoa]).__name__}"


def so_ke_toan(outputs_theo_giai_doan: dict[str, dict],
              trang_thai_theo_giai_doan: dict[str, str | None]) -> dict:
    """So ke toan cau xuyen bon giai doan — TINH THUAN tren hai map da doc san.

    Tra ve mot dict co `hang` (mot dong cho moi giai doan, cho `dinh_dang_bang`
    in) va `chan_doan` (danh sach cau ve tung CHANG chuyen tiep — cho biet
    chang nao ROI THAT, chang nao chi GOP, chang nao CHUA phan biet duoc).
    """
    def lay(ten: str, khoa: str) -> tuple[int | None, str]:
        return _doc_so(outputs_theo_giai_doan, trang_thai_theo_giai_doan,
                       ten, khoa)

    so_doan_transcribe, ly_do_transcribe = lay(TRANSCRIBE, "so_doan")

    so_doan_goc_cp, ly_do_goc_cp = lay(CONTENT_PROCESS, "so_doan_goc")
    so_doan_cp, ly_do_cp = lay(CONTENT_PROCESS, "so_doan")

    so_ma_vs, ly_do_ma_vs = lay(VOICE_SYNTHESIS, "so_ma_noi_dung")
    so_doan_vs, ly_do_vs = lay(VOICE_SYNTHESIS, "so_doan")
    so_khe_gop_vs, ly_do_khe_gop_vs = lay(VOICE_SYNTHESIS, "so_khe_da_gop")
    so_im_lang_vs, ly_do_im_lang_vs = lay(VOICE_SYNTHESIS, "so_doan_im_lang")

    so_doan_ta, ly_do_ta = lay(TIMING_ALIGN, "so_doan")
    so_cat_ta, ly_do_cat_ta = lay(TIMING_ALIGN, "so_doan_bi_cat")

    hang = [
        {"giai_doan": TRANSCRIBE, "so_doan": so_doan_transcribe,
         "ly_do": ly_do_transcribe,
         "phu": {}},
        {"giai_doan": CONTENT_PROCESS, "so_doan": so_doan_cp,
         "ly_do": ly_do_cp,
         "phu": {"so_doan_goc": (so_doan_goc_cp, ly_do_goc_cp)}},
        {"giai_doan": VOICE_SYNTHESIS, "so_doan": so_doan_vs,
         "ly_do": ly_do_vs,
         "phu": {"so_ma_noi_dung": (so_ma_vs, ly_do_ma_vs),
                 "so_khe_da_gop": (so_khe_gop_vs, ly_do_khe_gop_vs),
                 "so_doan_im_lang": (so_im_lang_vs, ly_do_im_lang_vs)}},
        {"giai_doan": TIMING_ALIGN, "so_doan": so_doan_ta,
         "ly_do": ly_do_ta,
         "phu": {"so_doan_bi_cat": (so_cat_ta, ly_do_cat_ta)}},
    ]

    chan_doan: list[dict] = []

    # ── Chang 1: transcribe -> content_process (dau vao) ────────────────────
    if so_doan_transcribe is None or so_doan_goc_cp is None:
        chan_doan.append({
            "chang": "transcribe -> content_process (dau vao)",
            "loai": "chua_du_so",
            "cau": f"⛔ chưa đủ số để đối chiếu ({CHUA_CO})."})
    elif so_doan_transcribe != so_doan_goc_cp:
        chan_doan.append({
            "chang": "transcribe -> content_process (dau vao)",
            "loai": "chua_phan_biet_duoc",
            "cau": (f"⛔ CHƯA PHÂN BIỆT ĐƯỢC — lệch {so_doan_transcribe} → "
                    f"{so_doan_goc_cp} mà GD1 lẽ ra giữ nguyên toàn bộ (không "
                    "lọc bản biên tập ở content_process). Không đoán — cần đọc "
                    "thêm (có thể là hai lượt chạy khác nhau, hoặc cache).")})
    else:
        chan_doan.append({
            "chang": "transcribe -> content_process (dau vao)",
            "loai": "khop", "cau": f"khớp ({so_doan_transcribe}), không rơi."})

    # ── Chang 2: content_process (dau vao vs muc sinh ra, TRONG giai doan) ──
    if so_doan_goc_cp is None or so_doan_cp is None:
        chan_doan.append({
            "chang": "content_process (đầu vào → mục sinh ra)",
            "loai": "chua_du_so",
            "cau": f"⛔ chưa đủ số để đối chiếu ({CHUA_CO})."})
    elif so_doan_goc_cp != so_doan_cp:
        chan_doan.append({
            "chang": "content_process (đầu vào → mục sinh ra)",
            "loai": "chua_phan_biet_duoc",
            "cau": (f"⛔ CHƯA PHÂN BIỆT ĐƯỢC — lệch {so_doan_goc_cp} → "
                    f"{so_doan_cp}. Theo mã (`long_tieng.dung`, "
                    "long_tieng.py:552-569) đây là 1-đối-1 và thiếu 1 mục sẽ "
                    "ném ThieuDoan (giai đoạn không thể succeeded với số lệch) "
                    "— một lệch thấy được ở đây là MÂU THUẪN với đọc mã, "
                    "không đoán nguyên nhân.")})
    else:
        chan_doan.append({
            "chang": "content_process (đầu vào → mục sinh ra)",
            "loai": "khop", "cau": f"khớp ({so_doan_cp}), không rơi."})

    # ── Chang 3: content_process -> voice_synthesis (GOP khe, khong ROI) ────
    if so_doan_cp is None or so_ma_vs is None or so_doan_vs is None:
        chan_doan.append({
            "chang": "content_process -> voice_synthesis",
            "loai": "chua_du_so",
            "cau": f"⛔ chưa đủ số để đối chiếu ({CHUA_CO})."})
    elif so_doan_cp != so_ma_vs:
        chan_doan.append({
            "chang": "content_process -> voice_synthesis (đầu vào)",
            "loai": "chua_phan_biet_duoc",
            "cau": (f"⛔ CHƯA PHÂN BIỆT ĐƯỢC — content_process.so_doan="
                    f"{so_doan_cp} khác voice_synthesis.so_ma_noi_dung="
                    f"{so_ma_vs}, hai khoá lẽ ra cùng một đại lượng (số mã nội "
                    "dung đưa vào TTS). Không đoán — cần điều tra.")})
    else:
        hieu = so_ma_vs - so_doan_vs
        if hieu < 0:
            chan_doan.append({
                "chang": "content_process -> voice_synthesis",
                "loai": "chua_phan_biet_duoc",
                "cau": (f"⛔ CHƯA PHÂN BIỆT ĐƯỢC — số liệu mâu thuẫn: "
                        f"so_doan(khe)={so_doan_vs} > so_ma_noi_dung="
                        f"{so_ma_vs}. Không thể xảy ra theo "
                        "`nan_thoi_luong.nhom_chi_so` (phân hoạch đầy đủ) — "
                        "cần điều tra, không đoán.")})
        elif hieu == 0:
            chan_doan.append({
                "chang": "content_process -> voice_synthesis",
                "loai": "khop",
                "cau": f"khớp ({so_ma_vs} mã = {so_doan_vs} khe), không gộp."})
        else:
            khe_gop_txt = (str(so_khe_gop_vs) if so_khe_gop_vs is not None
                          else CHUA_CO)
            giai_thich_du = (so_khe_gop_vs is not None and hieu == so_khe_gop_vs)
            chan_doan.append({
                "chang": "content_process -> voice_synthesis",
                "loai": "gop_khong_roi",
                "cau": (
                    f"GỘP (không rơi thật): {so_ma_vs} → {so_doan_vs} khe, "
                    f"giảm {hieu} mã do gộp vào khe khác — LUÔN đúng theo "
                    "`nan_thoi_luong.nhom_chi_so` (phân hoạch đầy đủ, "
                    "nan_thoi_luong.py:407: mỗi mã luôn thuộc đúng một nhóm). "
                    f"so_khe_da_gop={khe_gop_txt} (đếm SỐ NHÓM > 1 thành viên"
                    + ("; khớp đúng hiệu số vì mọi nhóm gộp đều 2 thành viên)"
                       if giai_thich_du else
                       "; KHÔNG nhất thiết bằng hiệu số ở trên — nếu có nhóm "
                       ">2 thành viên thì so_khe_da_gop < hiệu số, số liệu vẫn "
                       "ĐÚNG, chỉ là so_khe_da_gop không phải phép trừ trực "
                       "tiếp)."))})
        if so_im_lang_vs:
            ma_im_lang_txt = (f"{so_im_lang_vs} mã"
                              if so_im_lang_vs is not None else CHUA_CO)
            chan_doan.append({
                "chang": "voice_synthesis (nội dung mất, KHÔNG đổi so_doan)",
                "loai": "mat_noi_dung",
                "cau": (f"⚠️ {ma_im_lang_txt} bị BỎ QUA vì rỗng sau chuẩn hoá "
                        "(khoảng lặng) — MẤT lời thoại thật, nhưng KHÔNG làm "
                        "giảm so_doan (khe im lặng vẫn chiếm một chỗ trong "
                        "nhóm). Đây là một loại rơi THỨ BA, khác cả gộp lẫn "
                        "cắt.")})
        elif so_im_lang_vs == 0:
            chan_doan.append({
                "chang": "voice_synthesis (nội dung mất)",
                "loai": "khop",
                "cau": "đo được và bằng 0 — không mã nào bị bỏ vì rỗng."})

    # ── Chang 4: content_process -> timing_align (ROI THAT vs CON DONG) ─────
    if so_doan_cp is None or so_doan_ta is None:
        chan_doan.append({
            "chang": "content_process -> timing_align",
            "loai": "chua_du_so",
            "cau": f"⛔ chưa đủ số để đối chiếu ({CHUA_CO})."})
    else:
        roi_that = so_doan_cp - so_doan_ta
        if roi_that < 0:
            chan_doan.append({
                "chang": "content_process -> timing_align",
                "loai": "chua_phan_biet_duoc",
                "cau": (f"⛔ CHƯA PHÂN BIỆT ĐƯỢC — timing_align.so_doan="
                        f"{so_doan_ta} > content_process.so_doan={so_doan_cp}. "
                        "Không thể xảy ra theo `nan_thoi_luong.no_ban_ke` (nổ "
                        "lại 1-đối-1) — cần điều tra, không đoán.")})
        elif roi_that == 0:
            chan_doan.append({
                "chang": "content_process -> timing_align",
                "loai": "khop",
                "cau": f"khớp ({so_doan_ta}), không đoạn nào bị loại hẳn."})
        else:
            chan_doan.append({
                "chang": "content_process -> timing_align",
                "loai": "roi_that",
                "cau": (f"◄── RƠI {roi_that} CÂU Ở ĐÂY: {so_doan_cp} → "
                        f"{so_doan_ta} — {roi_that} dòng bị LOẠI HẲN khỏi kế "
                        "hoạch (thoi_gian.py:341-345, vòng cắt đuôi khi bản "
                        "lồng tiếng vẫn dài hơn video nguồn sau các nấc nắn).")})

    # ── so_doan_bi_cat doi chieu — tach rieng vi can CA hai gia tri o tren ──
    if so_doan_cp is not None and so_doan_ta is not None and so_cat_ta is not None:
        roi_that = so_doan_cp - so_doan_ta
        con_dong_mat_tieng = so_cat_ta - roi_that
        if con_dong_mat_tieng < 0:
            chan_doan.append({
                "chang": "timing_align (so_doan_bi_cat đối chiếu)",
                "loai": "chua_phan_biet_duoc",
                "cau": (f"⛔ CHƯA PHÂN BIỆT ĐƯỢC — so_doan_bi_cat={so_cat_ta} "
                        f"nhỏ hơn số dòng bị loại hẳn ({roi_that}). Mâu thuẫn "
                        "với `thoi_gian.py` (so_cat cộng dồn CẢ hai loại cắt) "
                        "— cần điều tra, không đoán.")})
        elif con_dong_mat_tieng > 0:
            chan_doan.append({
                "chang": "timing_align (so_doan_bi_cat đối chiếu)",
                "loai": "con_dong_mat_tieng",
                "cau": (f"⚠️ {con_dong_mat_tieng} dòng bị cắt VỀ 0 ms nhưng "
                        "VẪN CÒN một dòng trong kế hoạch (mất tiếng, còn vị "
                        f"trí) — thoi_gian.py:271-279,298-306. Cộng với "
                        f"{roi_that} dòng bị loại hẳn = so_doan_bi_cat="
                        f"{so_cat_ta}.")})
        else:
            chan_doan.append({
                "chang": "timing_align (so_doan_bi_cat đối chiếu)",
                "loai": "khop",
                "cau": (f"so_doan_bi_cat={so_cat_ta} khớp trọn vẹn với số "
                        f"dòng bị loại hẳn ({roi_that}) — không có dòng nào "
                        "bị cắt-về-0-mà-còn-dòng.")})
    elif so_cat_ta is None:
        chan_doan.append({
            "chang": "timing_align (so_doan_bi_cat đối chiếu)",
            "loai": "chua_du_so",
            "cau": f"⛔ chưa đủ số để đối chiếu ({CHUA_CO})."})

    return {"hang": hang, "chan_doan": chan_doan}


def _hien_thi_so(gia_tri: int | None, ly_do: str) -> str:
    if gia_tri is not None:
        return str(gia_tri)
    if ly_do == THIEU_GIAI_DOAN:
        return f"{CHUA_CO} (giai đoạn chưa chạy)"
    if ly_do.startswith(CHUA_XONG):
        return f"{CHUA_CO} (trạng thái={ly_do.partition(':')[2]})"
    if ly_do.startswith(THIEU_KHOA):
        chi_tiet = ly_do.partition(":")[2]
        return f"{CHUA_CO} (thiếu khoá trong outputs{': ' + chi_tiet if chi_tiet else ''})"
    return CHUA_CO


def dinh_dang_bang(ket_qua: dict) -> str:
    """`{hang, chan_doan}` cua `so_ke_toan` -> van ban de doc. TINH THUAN."""
    dong: list[str] = []
    dong.append("== SO KE TOAN CAU — XUYEN CAC GIAI DOAN (chi doc outputs) ==")
    dong.append("")
    for h in ket_qua["hang"]:
        gt = _hien_thi_so(h["so_doan"], h["ly_do"])
        dong.append(f"{h['giai_doan']:<18} so_doan = {gt}")
        for ten_phu, (gia_tri_phu, ly_do_phu) in h["phu"].items():
            dong.append(f"{'':<18}   {ten_phu} = "
                        f"{_hien_thi_so(gia_tri_phu, ly_do_phu)}")
    dong.append("")
    for ten in _GIAI_DOAN_KHONG_DEM_CAU:
        dong.append(f"{ten:<18} — (không đếm câu, ngoài phạm vi N1)")
    dong.append("")
    dong.append("-- ĐỐI CHIẾU TỪNG CHẶNG --")
    for cd in ket_qua["chan_doan"]:
        dong.append(f"[{cd['chang']}]")
        dong.append(f"  {cd['cau']}")
    dong.append("")
    roi = [cd for cd in ket_qua["chan_doan"] if cd["loai"] == "roi_that"]
    mo_ho = [cd for cd in ket_qua["chan_doan"]
            if cd["loai"] == "chua_phan_biet_duoc"]
    if roi:
        dong.append(f"🔴 TÓM TẮT: {len(roi)} chặng RƠI THẬT.")
    elif not mo_ho:
        dong.append("✅ TÓM TẮT: không chặng nào rơi thật trong dữ liệu đọc "
                    "được (chênh lệch quan sát được đều là gộp/cắt-còn-dòng, "
                    "không phải mất dòng khỏi kế hoạch).")
    if mo_ho:
        dong.append(f"⛔ {len(mo_ho)} chặng CHƯA PHÂN BIỆT ĐƯỢC — xem chi tiết "
                    "ở trên, đừng suy diễn thêm.")
    return "\n".join(dong)


#: Ten cac giai doan con lai cua `pipeline.CHUOI` — nap o `main()` (can import
#: `apps.auto_scan_video.pipeline`), giu bien module-level rong o day de
#: `dinh_dang_bang` dung duoc trong test THUAN (khong import CHUOI).
_GIAI_DOAN_KHONG_DEM_CAU: tuple[str, ...] = ()


# ══════════════════════════════════════════════════════════════════════════════
#  Lop CSDL — doc `asv_stage.outputs`, KHONG tai artifact, KHONG nap model
# ══════════════════════════════════════════════════════════════════════════════

def outputs_bon_giai_doan(db, run_id: str) -> dict[str, dict]:
    """`{ten_giai_doan: dict(outputs)}` cho bon giai doan cua `GIAI_DOAN_DEM_CAU`.

    Cung khuon voi `asv_doi_soat.outputs_tung_giai_doan`: doc `asv_stage.outputs`
    qua `features.giai_doan_theo_ten`, KHONG doc `dong_thoi_gian`.
    """
    from apps.auto_scan_video import features

    ra: dict[str, dict] = {}
    for ten in GIAI_DOAN_DEM_CAU:
        s = features.giai_doan_theo_ten(db, run_id, ten)
        ra[ten] = dict((s.outputs if s is not None else None) or {})
    return ra


def trang_thai_bon_giai_doan(db, run_id: str) -> dict[str, str | None]:
    """`{ten_giai_doan: trang_thai}` — `None` khi KHONG co dong `AsvStage` nao."""
    from apps.auto_scan_video import features

    ra: dict[str, str | None] = {}
    for ten in GIAI_DOAN_DEM_CAU:
        s = features.giai_doan_theo_ten(db, run_id, ten)
        ra[ten] = None if s is None else str(s.status)
    return ra


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    run_id = argv[1]

    from tools.asv_chay_worker_that import nap_env
    nap_env()

    from platform_core.db import get_session

    from apps.auto_scan_video import pipeline
    from apps.auto_scan_video.tables import AsvRun

    global _GIAI_DOAN_KHONG_DEM_CAU
    _GIAI_DOAN_KHONG_DEM_CAU = tuple(
        ten for ten in pipeline.TEN_GIAI_DOAN if ten not in GIAI_DOAN_DEM_CAU)

    gen = get_session()
    db = next(gen)
    try:
        run = db.get(AsvRun, run_id)
        if run is None:
            print(f"KHÔNG THẤY run {run_id!r} trong CSDL này.")
            return 1

        outs = outputs_bon_giai_doan(db, run.id)
        tt = trang_thai_bon_giai_doan(db, run.id)
        ket_qua = so_ke_toan(outs, tt)
        print(dinh_dang_bang(ket_qua))
        return 0
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
