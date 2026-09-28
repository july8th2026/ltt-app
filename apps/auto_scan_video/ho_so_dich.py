"""HỒ SƠ DỊCH — một lời gọi cho CẢ video, quyết quan hệ nhân vật MỘT lần.

🔴 **Vì sao tệp này tồn tại.** `dich_mot_lo` là **vô trạng thái**: mỗi lô chỉ thấy
   `{ma: chu}` của chính nó. Một phim 74 đoạn đi 4 lô ⇒ **4 lần** quyết lại quan hệ
   nhân vật, độc lập nhau. Tiếng Việt mã hoá **quan hệ** vào đại từ, nên người xem
   nghe thấy quan hệ **đổi giữa video** (`ông` → `cậu` → `bạn`).

⭐ Một lời gọi thêm cho **cả video** (~16 giây) thay cho hàng chục lần đoán lại.
"""
from __future__ import annotations

import json
import logging

from platform_core.i18n import _ as _t

log = logging.getLogger(__name__)

KHOA = ("the_loai", "so_nguoi_noi", "bang_dai_tu", "bang_ten_rieng", "giong_van",
        "bang_sua_dong_am")

#: N3 (B14/V3, `docs/auto_scan_video_final/B14_SO_SANH_VIRAL/V3_DICH.md` hang 1)
#: — muon glossary sua loi DONG AM cua ASR truoc khi dich, tu
#: `D:\Viral\resources\app-src\ai_dich.py:1290-1336 _tom_tat_glossary` (chi doc).
#: Viral do that 01/09 tren chinh duong dich dang song (gemini-3.1-flash-lite,
#: 300 cue dau): model TU BAT **8/8** loi dong am da liet ke khi duoc dan cau
#: nay (vd `武林根→五灵根`, `根国清政→根骨清正`) — khong co cau dan thi mot ten
#: rieng dung `五灵根` dich SAI **0/3**.
#:
#: ⭐ **KHONG them luot goi model moi** — ghep THANG vao lien nguoi goi da tra
#:    tien san (`ho_so_dich.dung`, MOT lan/video, Task 11). Day la mot CUA PHAT
#:    HIEN: model tu ghi lai nghi van dong am no thay trong ban chep loi vao
#:    `bang_sua_dong_am`, KHONG tu sua ban dich cua ham nay hay bat ky doan nao
#:    khac — long_tieng.py (L1 so huu) chua doc truong nay, nen o pha nay no chi
#:    la mot khoa DUOC GHI RA (hien trong `tom_tat["ho_so_dich"]`), chua duoc
#:    NOI vao loi nhac dich thuc te. Noi tiep (doc + dan vao `long_tieng.loi_nhac`)
#:    la viec cua L1 — bao dieu phoi, khong tu cham vao `long_tieng.py`.
#:
#: ⛔ **KHONG kem vi du dich san trong loi nhac** — "mot vi du trong loi nhac la
#:    mot menh lenh ngam" (24/09, bon vi du khong dau tung lam tut mot ten von
#:    dung). Loi nhac duoi day chi mo ta HINH DANG JSON can, khong dua cap
#:    "chu sai -> nghia dung" tieng Viet cu the nao ca.

#: 🔑 **Khoa so cai cua lan goi nay — MOT dong cho CA video, va do la CO Y.**
#:
#:    `ai.goi_tinh_tien` dung `ma_dispatch = f"{thao_tac.ma}:{stage}:{item_key}"`
#:    duoi rang buoc `UNIQUE(run_id, ma_dispatch)`. Mot khoa HANG SO nghia la:
#:    mot luot chay = **dung mot** dong so cai cho ho so dich, du `dung()` co bi
#:    goi lai bao nhieu lan (job noi tiep sau lat cat goi lai `giai_doan_noi_dung
#:    .chay` tu dau, va dong 244 cua tep ay goi ham nay VO DIEU KIEN).
#:
#: ⭐ Va ⛔ khong co truc nao khac de chia khoa theo: ho so la cau hoi TOAN CUC
#:    cua ca video (xem docstring dau tep). Mot khoa mang so lo hay so lan thu se
#:    bien mot luot chay noi tiep thanh HAI dong tinh tien cho **cung mot** cau
#:    hoi — dung cai bay ma `giai_doan_noi_dung` da ghi lai o khoa `lo_%03d`.
#:
#: ⚠️ Cai gia cua lua chon nay, noi ra: o luot noi tiep, lan goi thu hai THAT SU
#:    ton token nhung `su_dung.ghi` nem `DaGhiRoi` va `goi_tinh_tien` nuot no, nen
#:    token ay ⛔ khong vao so. Do la danh doi CO CHU DINH — chan tinh tien hai
#:    lan quan trong hon do chinh xac tuyet doi chi phi cua ta.
ITEM_KEY = "ho_so_dich"

#: 🔑 **⛔ KHÔNG truyền `uoc_credit` — chủ dự án chốt PHƯƠNG ÁN B (26/09): CHỈ ĐO.**
#:
#:    `ai.goi_tinh_tien` làm **hai** việc, và ta chỉ muốn **một**:
#:      (1) **cửa chặn** margin — chỉ chạy khi `uoc_credit` khác 0 (`ai.py:835`);
#:      (2) **sổ cái** — luôn chạy.
#:    ⇒ Ta đi qua `goi_tinh_tien` để có **(2)**, và ⛔ **không** trang bị **(1)**.
#:
#: ⭐ Lý do của chủ dự án: *"Giá chỉ để tượng trưng. Sau này khi hoàn thiện hệ thống
#:    và vận hành, tôi sẽ tự đề xuất con số sau."* ⇒ Một cửa chặn ⛔ **không có ngưỡng
#:    đo được** là một cửa sẽ bị **tắt sau lần báo động giả đầu tiên** — nên đo trước,
#:    đặt ngưỡng sau.
#:
#: ⚠️ **Và phải ĐỒNG NHẤT:** cả **sáu** lời gọi LLM của app đều ⛔ không truyền
#:    `uoc_credit`. Bật cho **một** chỗ là tạo một cửa mà ⛔ không ai đoán được nó ở
#:    đâu — tệ hơn cả việc ⛔ không có cửa nào.
#:
#: ⇒ Dụng cụ thay cửa: `dong_ho["giay_llm_nan"]` · `dong_ho["giay_tts"]` ·
#:    `so_doan_nan_oan`, đọc bằng `tools/asv_doi_soat.py`. Chúng **thấy** lượt nào
#:    lỗ mà ⛔ không làm khách gặp lỗi.


class HoSoDichLoi(ValueError):
    """Model không trả về hồ sơ đọc được."""


def _doc(noi_dung: str) -> dict:
    van = str(noi_dung or "").strip()
    dau, cuoi = van.find("{"), van.rfind("}")
    if dau < 0 or cuoi < dau:
        raise HoSoDichLoi(_t('Model không trả về JSON đọc được.'))
    try:
        goc = json.loads(van[dau:cuoi + 1])
    except json.JSONDecodeError as exc:
        raise HoSoDichLoi(_t('Model trả về JSON hỏng.')) from exc
    if not isinstance(goc, dict):
        raise HoSoDichLoi(_t('Model trả về JSON sai hình dạng.'))
    return {
        "the_loai": str(goc.get("the_loai") or ""),
        "so_nguoi_noi": int(goc.get("so_nguoi_noi") or 0),
        "bang_dai_tu": dict(goc.get("bang_dai_tu") or {}),
        "bang_ten_rieng": dict(goc.get("bang_ten_rieng") or {}),
        "giong_van": str(goc.get("giong_van") or ""),
        # N3 — xem chu thich o KHOA dau tep. Rong = model khong nghi ngo dong am
        # nao, MOT cau tra loi hop le (⛔ khong phai loi doc).
        "bang_sua_dong_am": dict(goc.get("bang_sua_dong_am") or {}),
    }


def dung(db, run, ban_ghi: dict, *, ctx=None) -> dict:
    """MỘT lời gọi, đi qua CỬA TRẢ TIỀN. Hỏng thì trả hồ sơ RỖNG.

    🔴 **`ai.goi_tinh_tien`, ⛔ không `ai.goi`.** `ai.py:806` khai `goi_tinh_tien`
       là **đường trả tiền DUY NHẤT**: nó chặn TRƯỚC khi ngân sách của lượt chạy
       đã hết, và ghi SỔ CÁI sau khi gọi — dù thành hay bại. Bản đầu của tệp này
       gọi `ai.goi` trực tiếp, và vì `giai_doan_noi_dung` gọi nó **vô điều kiện
       trên mọi lượt `content_process` thật**, hậu quả là: khách hết ngân sách vẫn
       phát sinh một lời gọi thật ~16 giây, và chi phí model ⛔ không bao giờ vào
       `su_dung` — nên báo cáo margin và `quyet_toan` lệch đúng một lời gọi mỗi
       video. `test_408` chốt điều này bằng AST.

    ⚠️ **HAI ca hỏng KHÁC loại, và chúng ⛔ không được gộp thành một:**

           model trả rác        ->  hồ sơ RỖNG, đi tiếp
           cửa chặn ngân sách   ->  NÉM LẠI

       Hồ sơ là thứ làm bản dịch **tốt hơn**, ⛔ không phải thứ bản dịch cần để
       CHẠY — nên một model trả rác ⛔ không được làm chết lượt chạy. Nhưng *"hết
       ngân sách"* là một trạng thái **khách phải biết**: `features.kiem_tran_chi`
       ném `AsvError` (một `ValueError`) **trước khi** gọi model, và nuốt nó thành
       "hồ sơ rỗng" biến một thất bại chính sách sạch sẽ thành một lượt chạy im
       lặng nghèo hơn mà ⛔ không ai giải thích được vì sao.
    """
    from . import ai, features, pipeline

    dong = [f'{d["ma"]}: {d["chu"]}' for d in (ban_ghi.get("doan") or [])]
    tin = [
        {"role": "system", "content": (
            "Doc toan bo loi thoai cua mot video roi tra ve DUY NHAT mot doi "
            "tuong JSON voi dung cac khoa: the_loai, so_nguoi_noi, bang_dai_tu, "
            "bang_ten_rieng, giong_van, bang_sua_dong_am.\n"
            "bang_dai_tu: voi MOI cap vai, ghi tu tu xung (`toi`) va tu goi "
            "(`goi`) bang tieng Viet se dung suot ca video.\n"
            "bang_ten_rieng: ten goc -> dang viet tieng Viet, chot MOT lan.\n"
            "bang_sua_dong_am: ban chep loi nay co the do MAY NGHE NHAM mot cum "
            "tu DONG AM (dung ngu phap nhung SAI NGHIA so voi boi canh chung cua "
            "ca video — vi du mot ten rieng hay thuat ngu bi nghe thanh mot cum "
            "khac phat am giong het). Neu CO CAN CU ro rang tu boi canh, ghi "
            "moi cap {cum_nghe_nham: nghia_dung_theo_boi_canh}. KHONG doan mo "
            "ho, KHONG suy dien tu mot lan xuat hien duy nhat neu boi canh "
            "khong ro. De {} (rong) neu khong phat hien cum nao.\n"
            "Khong giai thich gi them.")},
        {"role": "user", "content": "\n".join(dong)},
    ]
    try:
        # ⚠️ `temperature=0.2` la khai TUONG MINH cua ben goi, va no giu nguyen
        #    hanh vi truoc ban sua nay: `ai.NHIET_DO_THEO_THAO_TAC` ⛔ khong co
        #    muc nao cho `ho_so_dich`, nen `nhiet_do_cho` tra `None` va bo mot
        #    con so o day ⛔ khong ghi de mot nhiet do GHIM nao ca (N-23).
        kq = ai.goi_tinh_tien(db, run, ai.HO_SO_DICH, tin,
                              stage=pipeline.CONTENT_PROCESS,
                              item_key=ITEM_KEY,
                              ctx=ctx, temperature=0.2)
        return _doc(kq["noi_dung"])
    except features.AsvError:
        # 🔴 **CUA CHAN vi het ngan sach — ⛔ KHONG nuot.** Xem docstring: day la
        #    mot trang thai KHACH phai biet, va no xay ra **truoc khi** model duoc
        #    goi, nen ⛔ khong co gi de "di tiep voi ho so rong" ca. Nem lai de
        #    `giai_doan_noi_dung` / `thi_hanh` bao dung mot that bai chinh sach.
        raise
    except Exception as exc:  # noqa: BLE001
        # ⭐ Hồ sơ là thứ làm bản dịch TỐT HƠN, ⛔ không phải thứ nó cần để CHẠY.
        #    Hỏng thì đi tiếp với hồ sơ rỗng và NÓI RA, ⛔ không làm chết lượt chạy.
        log.warning("khong dung duoc ho so dich (%s: %s)", type(exc).__name__, exc)
        return {k: ({} if k.startswith("bang_") else "") for k in KHOA}
