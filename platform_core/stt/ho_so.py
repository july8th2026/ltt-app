"""Hồ sơ tham số STT — **có tên, không có mặc định**.

## Vì sao tệp này tồn tại

**Sáu** chỗ trong hệ sinh thái LTT gọi `faster_whisper` với **sáu bộ tham số
khác nhau**, và khác biệt ấy **quyết định đầu ra**, không phải quyết định tốc độ.

Bốn trong sáu đến từ bốn bot đang migrate, và chúng nằm ở `HO_SO` dưới đây:

```
bot_transcript  engine/stt.py:303       word_ts=True   vad_filter=KHONG  beam=1
bot_pause       engine/stt.py:337       word_ts=True   vad_filter=True   beam=5(vi)/1(en)
bot_dungvideo   engine/stt.py:48        word_ts=False  vad_filter=True   beam=5
bot_dungvideo   evaluation/.../whisper  word_ts=False  vad_filter=False  —
```

⛔ **Hai chỗ còn lại đang chạy trong nền tảng, và tệp này KHÔNG kê tên chúng** —
xem chú thích sau `HO_SO`. Bảng đối chiếu đầy đủ ở
`docs/migration/workflow_apps/07_CROSS_BOT_SYNTHESIS.md` §2.

## Tên hồ sơ là tên NĂNG LỰC, không phải tên app

Bản đầu đặt tên theo bot dùng nó (`transcript`, `pause`, `video`). Chốt
`test_60::test_no_app_slug_is_hardcoded_in_the_platform` bắt ngay: một tên app
trong mã nền tảng là dấu hiệu registry bị đi vòng, và `transcript` vừa là tên
hồ sơ vừa là slug của một App.

⭐ Chốt ấy ép ra một cái tên **tốt hơn**. Hồ sơ mô tả *thứ nó tạo ra* — có mốc
từ hay không, VAD nằm trong whisper hay ở tầng trên — nên hai App khác nhau
cần cùng một hành vi thì dùng chung được, thay vì mỗi App một hồ sơ trùng nội
dung. Docstring của chính chốt ấy nói đúng câu này: *nền tảng đặt tên cho
NĂNG LỰC, không bao giờ cho APP*.

🔴 **Ba lý do khiến chúng KHÔNG hoà được thành một mặc định**, mỗi lý do đủ để
một mình chặn:

1. `transcript` **cấm** `vad_filter`: nó chạy VAD riêng (`vad.py`) ở tầng trên.
   Bật thêm là VAD hai lần, và ranh giới đoạn đổi.
2. `pause` **dùng chính ranh giới** mà `vad_filter` tạo ra (kèm
   `speech_pad_ms=200`) để quyết định cắt ở đâu. Đổi ranh giới ⇒ đổi vị trí chèn
   khoảng lặng ⇒ đổi tệp âm thanh giao cho khách.
3. `transcript` **bắt buộc** `word_timestamps=True` (có phép kiểm ném lỗi nếu
   thiếu); `dungvideo` cố ý **tắt** vì không cần và nó đắt.

⛔ **Không có "tham số mặc định hợp lý" ở đây.** Bên gọi phải nêu tên hồ sơ, và
`lay()` **từ chối** một tên không có. Một mặc định ngầm ở tệp này là một quyết
định về **đầu ra của sản phẩm** mà không ai ký tên.

⭐ Đây chính là ca mà `AGENTS.md`/MASTER-GUARDRAILS mô tả: cùng một *tên* năng
lực ("gọi whisper"), khác *ngữ nghĩa*. Gộp trước khi audit ngữ nghĩa là đẻ ra
một `common_utils.py` làm hỏng ba đường cùng lúc — và hỏng **im lặng**, vì cả ba
vẫn chạy và vẫn ra tệp.

## `pause` là một HÀM của ngôn ngữ, không phải một bộ số

`configs/bot_config_pause.json` đang chạy khai `beam_size_vi=5 / beam_size_en=1`
và `best_of_vi=3 / best_of_en=1`. Nên `pause` có **hai** biến thể, chọn theo
`language`. Đó là lý do `lay()` nhận `ngon_ngu` chứ không chỉ nhận tên.

## Nguồn của những con số này

Mã legacy cho *hình dạng*; `configs/` đang chạy cho *giá trị*. Hai nguồn ấy
**lệch nhau** — xem `docs/migration/workflow_apps/08_CAU_HINH_THAT_TREN_PRODUCTION.md`
§1. Bảng dưới lấy theo **bản đang chạy**.
"""
from __future__ import annotations

from typing import Any, Optional


class KhongCoHoSo(KeyError):
    """Tên hồ sơ không có. Cố ý là lỗi, không phải rơi về một mặc định."""


#: Tham số truyền thẳng cho `WhisperModel.transcribe`.
#:
#: ⚠️ Khoá vắng mặt **khác** khoá đặt `None`: `transcript` không có
#:    `vad_filter` là một quyết định, và truyền `vad_filter=None` cho
#:    faster-whisper không tương đương với việc không truyền gì.
HO_SO: dict[str, dict[str, Any]] = {
    # bot_transcript — VAD chạy RIÊNG ở tầng trên, nên không có `vad_filter`.
    "moc_tu_vad_ngoai": {
        "word_timestamps": True,          # "HARD RULE" trong mã legacy
        "beam_size": 1,
        "best_of": 1,
        "temperature": 0.0,
        "condition_on_previous_text": False,
    },
    # bot_pause, tiếng Việt.
    "moc_tu_vad_trong_vi": {
        "word_timestamps": True,
        "vad_filter": True,
        "vad_parameters": {"min_silence_duration_ms": 500, "speech_pad_ms": 200},
        "beam_size": 5,
        "best_of": 3,
        "temperature": 0.0,
        "condition_on_previous_text": False,
    },
    # bot_pause, tiếng Anh — CÙNG một bot, KHÁC hai tham số.
    "moc_tu_vad_trong_en": {
        "word_timestamps": True,
        "vad_filter": True,
        "vad_parameters": {"min_silence_duration_ms": 500, "speech_pad_ms": 200},
        "beam_size": 1,
        "best_of": 1,
        "temperature": 0.0,
        "condition_on_previous_text": False,
    },
    # bot_dungvideo, đường chính.
    "khong_moc_tu_vad_trong": {
        "word_timestamps": False,
        "vad_filter": True,
        "vad_parameters": {"min_silence_duration_ms": 500, "threshold": 0.5},
        "beam_size": 5,
        "condition_on_previous_text": False,
    },
    # bot_dungvideo, bước tự chấm điểm — chỉ cần dò ngôn ngữ.
    "chi_do_ngon_ngu": {
        "word_timestamps": False,
        "vad_filter": False,
    },
}

# ⛔ HAI CHO GOI KHAC trong nen tang co ho so RIENG, va chung KHONG duoc ke
#    ten o day.
#
#    Ban dau tep nay co mot `HO_SO_DA_CO` liet ke chung kem slug cua app. Chot
#    `test_60::test_no_app_slug_is_hardcoded_in_the_platform` bat ngay: mot ten
#    app xuat hien trong ma nen tang la dau hieu registry bi di vong. Chot do
#    dung, va danh sach mien tru cua no tu ghi rang "them mot ten vao day khong
#    mien phi — no lam bo do mu voi chuoi ay".
#
# ⇒ Ban sua la GO TEN KHOI CORE, khong phai xin mien tru. Bang doi chieu day du
#   (cho goi nao, ho so nao, vi sao khong migrate o V1) nam o
#   `docs/migration/workflow_apps/07_CROSS_BOT_SYNTHESIS.md` §2 — dung cho cua
#   no, vi do la mot su that ve TAI LIEU MIGRATE chu khong ve NEN TANG.

#: Hồ sơ nào chọn theo ngôn ngữ. Khoá = tên gốc, giá trị = {ngôn ngữ: tên thật}.
THEO_NGON_NGU: dict[str, dict[str, str]] = {
    "moc_tu_vad_trong": {"vi": "moc_tu_vad_trong_vi",
                         "en": "moc_tu_vad_trong_en"},
}


def ten_thuc(ten: str, ngon_ngu: Optional[str] = None) -> str:
    """Tên hồ sơ thật, sau khi giải phần phụ thuộc ngôn ngữ.

    ⚠️ `pause` mà không nêu ngôn ngữ thì **không** đoán: một lượt tiếng Anh chạy
       bằng `beam_size=5` của tiếng Việt vẫn ra kết quả hợp lệ, chỉ là chậm hơn
       và khác đi — đúng loại sai lặng lẽ mà tệp này sinh ra để chặn.
    """
    if ten not in THEO_NGON_NGU:
        return ten
    bang = THEO_NGON_NGU[ten]
    khoa = (ngon_ngu or "").strip().lower()
    if khoa not in bang:
        raise KhongCoHoSo(
            f"ho so `{ten}` chon theo ngon ngu; can mot trong "
            f"{sorted(bang)}, nhan {ngon_ngu!r}")
    return bang[khoa]


def lay(ten: str, ngon_ngu: Optional[str] = None) -> dict[str, Any]:
    """Bản sao tham số của một hồ sơ. Ném `KhongCoHoSo` nếu tên không có.

    ⛔ Trả **bản sao**: bên gọi thêm `language=` vào là chuyện bình thường, và
       một lần sửa tại chỗ sẽ làm hỏng mọi lượt sau trong cùng tiến trình.
    """
    thuc = ten_thuc(ten, ngon_ngu)
    if thuc not in HO_SO:
        raise KhongCoHoSo(
            f"khong co ho so STT ten `{thuc}`; co: {sorted(HO_SO)}")
    tham_so = dict(HO_SO[thuc])
    if "vad_parameters" in tham_so:
        tham_so["vad_parameters"] = dict(tham_so["vad_parameters"])
    return tham_so
