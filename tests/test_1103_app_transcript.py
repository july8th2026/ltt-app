"""App `transcript` — hợp đồng, ranh giới, và ba phép kiểm chuyển từ bot legacy.

## Cái tệp này CÓ chốt

- hợp đồng App/ToolSpec khớp `24_NODE_CONTRACTS.md` ở những chỗ **chạm tiền và
  chạm khôi phục sau sự cố** (`side_effect`, `idempotency`, `admission_*`);
- ranh giới: GUI và Node đi vào **cùng một** service;
- ba phép kiểm nội dung mà `bot/worker.py` từng làm — chúng là **quà** của bot
  legacy, chuyển thẳng thay vì phải suy ra;
- `chuan_hoa` từ chối **trước khi chạy**, không dừng giữa chừng.

## Cái tệp này KHÔNG chốt, và vì sao

⛔ Không chốt giá trị ngưỡng (`min_s`, `max_s`, `silence_text`…). Chúng đến từ
   `configs/` đang chạy (`08_CAU_HINH_THAT_TREN_PRODUCTION.md`) và sẽ đổi khi
   production đổi. Chốt chúng ở đây là dựng một bản sao thứ hai của cấu hình —
   và bản sao ấy sẽ trôi, đúng cơ chế đã hỏng năm lần trong kho này.

⛔ Không gọi model thật. Một phép kiểm nạp whisper biến một worker pytest thành
   ~10 luồng torch, và ngân sách `-n` **không đếm tiến trình cháu**.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from apps.transcript import jobs as app_jobs
from apps.transcript.manifest import MANIFEST
from apps.transcript.services import phien_am

GOC = Path(__file__).resolve().parent.parent


def _tool():
    return MANIFEST.tools[0]


# ── 1. Hợp đồng ─────────────────────────────────────────────────────────────

def test_manifest_khai_dung_nhung_gi_nen_tang_doc() -> None:
    assert MANIFEST.slug == "transcript"
    assert MANIFEST.group == "Workflow"
    assert MANIFEST.job_types == ("transcript.run",)
    assert MANIFEST.requires == ("gpu",)


def test_bon_cong_deu_DONG_o_V1() -> None:
    """`public`/`lifecycle`/`api_exposed` đóng là CHỦ Ý, không phải quên.

    Mở một cổng khi parity chưa đóng là mời khách vào một App chưa chứng minh
    được nó làm đúng việc của bản cũ.
    """
    assert MANIFEST.public is False
    assert MANIFEST.lifecycle == "development"
    assert _tool().api_exposed is False
    assert _tool().api_contract == {}


def test_toolspec_va_manifest_KHONG_the_lech_job_type() -> None:
    """Node và GUI phải tạo cùng một `job_type` — bất biến N2."""
    assert _tool().job_type in MANIFEST.job_types


def test_idempotency_khong_gom_language() -> None:
    """`language` để trống nghĩa là **tự dò**, và hai lần tự dò trên cùng tệp
    cho cùng kết quả. Gom nó vào khoá sẽ tách hai lượt giống hệt nhau thành
    hai job — tức trả tiền hai lần cho một việc.
    """
    khoa = _tool().idempotency["key_fields"]
    assert "audio" in khoa
    assert "language" not in khoa
    for ten in khoa:
        assert ten in _tool().params_schema, f"`{ten}` khong co trong schema"


def test_admission_khai_ca_HAI_ve() -> None:
    """Khai tài nguyên mà `slots=0` thì admission **không cấp lease** — tức
    khai một nửa là không khai. Bốn model thật trên một máy 10 lõi đã sập một
    lần vì đúng loại thiếu sót này."""
    t = _tool()
    assert t.admission_resource
    assert t.admission_slots >= 1


# ── 2. Ranh giới: GUI và Node đi vào CÙNG service ───────────────────────────

def test_routes_va_jobs_deu_goi_MOT_service() -> None:
    """Bất biến #2. Nếu hai đường gọi hai hàm khác nhau thì chúng sẽ trôi khỏi
    nhau, và trôi **im lặng** — cả hai vẫn chạy, vẫn ra kết quả."""
    thu_muc = GOC / "apps" / "transcript"
    for ten in ("routes.py", "jobs.py"):
        van = (thu_muc / ten).read_text(encoding="utf-8")
        assert "from .services import phien_am" in van, ten


def test_app_khong_import_app_khac() -> None:
    for tep in (GOC / "apps" / "transcript").rglob("*.py"):
        van = tep.read_text(encoding="utf-8")
        for dong in van.splitlines():
            d = dong.strip()
            if d.startswith(("from apps.", "import apps.")):
                assert d.startswith(("from apps.transcript",
                                     "import apps.transcript")), \
                    f"{tep.name}: {d}"


def test_router_khong_tu_viet_prefix() -> None:
    """Nền tảng gắn prefix từ `MANIFEST.route_prefix`. Viết tay ở router là hai
    nguồn cho một đường dẫn, và chúng sẽ lệch."""
    from apps.transcript.routes import router
    assert all(not r.path.startswith("/transcript") for r in router.routes)


# ── 3. `chuan_hoa` từ chối TRƯỚC khi chạy ───────────────────────────────────

def test_thieu_audio_bi_tu_choi() -> None:
    with pytest.raises(phien_am.LoiPhienAm):
        phien_am.chuan_hoa({})


def test_min_lon_hon_max_bi_tu_choi_TRUOC_khi_chay() -> None:
    """Dừng giữa chừng nghĩa là đã tiêu một suất GPU cho một lượt chắc chắn
    thất bại — tệ hơn cả không chạy."""
    with pytest.raises(phien_am.LoiPhienAm):
        phien_am.chuan_hoa({"audio": "k", "min_s": 6.0, "max_s": 3.0})
    with pytest.raises(phien_am.LoiPhienAm):
        phien_am.chuan_hoa({"audio": "k", "min_s": 5.0, "max_s": 5.0})
    with pytest.raises(phien_am.LoiPhienAm):
        phien_am.chuan_hoa({"audio": "k", "min_s": 0, "max_s": 6.0})
    with pytest.raises(phien_am.LoiPhienAm):
        phien_am.chuan_hoa({"audio": "k", "min_s": "ba", "max_s": 6.0})


def test_chuan_hoa_giu_nguyen_tham_so_hop_le() -> None:
    yc = phien_am.chuan_hoa({"audio": "k.wav", "language": " vi ",
                             "min_s": 1.5, "max_s": 6.0,
                             "include_silence": False})
    assert (yc.ngon_ngu, yc.min_s, yc.max_s,
            yc.kem_khoang_lang) == ("vi", 1.5, 6.0, False)


# ── 4. Ba phép kiểm nội dung, chuyển từ `bot/worker.py` ─────────────────────

def test_thieu_words_bi_bat_o_cho_con_noi_duoc_nguyen_nhan() -> None:
    """Hồ sơ `transcript` bắt buộc `word_timestamps=True`.

    Thiếu `words`, bước dựng dòng thời gian vẫn chạy — nó chỉ **không có gì để
    dựng** và trả về rỗng. Bắt ở đây, nơi còn nói được vì sao.
    """
    with pytest.raises(phien_am.LoiPhienAm):
        phien_am._kiem_co_mocs_tu([])
    with pytest.raises(phien_am.LoiPhienAm):
        phien_am._kiem_co_mocs_tu([{"start": 0, "end": 1, "text": "a"}])
    phien_am._kiem_co_mocs_tu(
        [{"start": 0, "end": 1, "text": "a",
          "words": [{"start": 0, "end": 1, "text": "a"}]}])


def test_dong_thoi_gian_DOC_DUOC_tu_theo_khoa_cua_service_stt() -> None:
    """`platform_core.stt.service` trả mỗi từ `{start, end, text}`; engine
    legacy đọc `word`. Lệch khoá thì mọi từ bị bỏ, `make_timeline_v2` trả rỗng
    và MỌI job chết ở "dung dong thoi gian ra ket qua rong" (đo 22/09 trên
    `en_1500.wav`: STT ra 84 từ, dòng thời gian 0 đoạn)."""
    from apps.transcript.services.engine.segment.core import make_timeline_v2

    doan_stt = [{"start": 0.0, "end": 2.5, "text": "Xin chào các bạn.",
                 "words": [{"start": 0.0, "end": 0.6, "text": "Xin"},
                           {"start": 0.6, "end": 1.2, "text": "chào"},
                           {"start": 1.2, "end": 1.8, "text": "các"},
                           {"start": 1.8, "end": 2.5, "text": "bạn."}]}]
    dong = make_timeline_v2(doan_stt, audio_duration=2.5, target_min=1.5,
                            target_max=6.0)
    noi = [d for d in dong if d["type"] == "speech"]
    assert noi, "dong thoi gian rong — tu theo khoa `text` bi bo"
    assert " ".join(d["text"] for d in noi) == "Xin chào các bạn."


def test_hai_doan_speech_lien_tiep_trung_noi_dung_bi_TU_CHOI() -> None:
    """Lỗi NỘI DUNG, không phải lỗi hình thức: tệp vẫn hợp lệ, khách vẫn đọc
    được, và câu bị lặp nằm giữa một bản dài."""
    lap = [{"type": "speech", "start": 0, "end": 1, "text": "Xin  chao."},
           {"type": "speech", "start": 1, "end": 2, "text": "Xin chao"}]
    with pytest.raises(phien_am.LoiPhienAm):
        phien_am._kiem_khong_trung_lien_tiep(lap)
    # Legacy `_normalize_for_dedupe` (bot/worker.py:166-170) KHÔNG hạ chữ:
    # khác hoa/thường là hai câu khác nhau.
    phien_am._kiem_khong_trung_lien_tiep(
        [{"type": "speech", "start": 0, "end": 1, "text": "Xin chao"},
         {"type": "speech", "start": 1, "end": 2, "text": "xin chao"}])
    # Speech chữ rỗng là lỗi (legacy `speech_missing_text`).
    with pytest.raises(phien_am.LoiPhienAm):
        phien_am._kiem_khong_trung_lien_tiep(
            [{"type": "speech", "start": 0, "end": 1, "text": " . "}])


def test_mot_doan_lang_XEN_GIUA_thi_khong_con_la_trung_lien_tiep() -> None:
    """Đối chứng: thiếu nó, một phép kiểm "luôn ném" cũng xanh."""
    phien_am._kiem_khong_trung_lien_tiep([
        {"type": "speech", "start": 0, "end": 1, "text": "xin chao"},
        {"type": "silence", "start": 1, "end": 3, "text": "[B-ROLL / PAUSE]"},
        {"type": "speech", "start": 3, "end": 4, "text": "xin chao"}])


@pytest.mark.parametrize("doan, vi_sao", [
    ([], "dong thoi gian rong"),
    ([{"type": "speech", "start": 0, "text": "a"}], "thieu `end`"),
    ([{"type": "la", "start": 0, "end": 1, "text": "a"}], "`type` khong hop le"),
    ([{"type": "speech", "start": 2, "end": 1, "text": "a"}], "end <= start"),
    ([{"type": "silence", "start": 0, "end": 1, "text": "x"}], "khong co speech"),
])
def test_schema_nghiem_ngat_bat_dung_nam_ca(doan, vi_sao) -> None:
    with pytest.raises(phien_am.LoiPhienAm):
        phien_am._kiem_schema_nghiem_ngat(doan)


def test_schema_hop_le_thi_KHONG_nem() -> None:
    phien_am._kiem_schema_nghiem_ngat(
        [{"type": "speech", "start": 0.0, "end": 3.5, "text": "xin chao",
          "scene_id": "S0001", "index": 1}])


@pytest.mark.parametrize("hong", [
    {"words": []},                 # khoá thừa
    {"end": -1.0},                 # end < start
    {"text": "   "},               # speech chữ rỗng
    {"scene_id": ""},              # scene_id rỗng
    {"index": 0},                  # index <= 0
])
def test_schema_nghiem_ngat_DU_LUAT_legacy(hong: dict) -> None:
    """`bot/worker.py::_validate_output_segments_strict` — bản port đầu bỏ sót
    năm luật này (đối chiếu 22/09)."""
    doan = {"type": "speech", "start": 0.0, "end": 3.5, "text": "xin chao",
            "scene_id": "S0001", "index": 1, **hong}
    with pytest.raises(phien_am.LoiPhienAm):
        phien_am._kiem_schema_nghiem_ngat([doan])


def test_chieu_schema_ra_DUNG_SAU_khoa_va_KHONG_co_words() -> None:
    """🔴 Đo trên **1.932 lượt job thật** ở `D:/FULL AUTO VIDEO/.../output/`:
    6.934/6.934 đoạn có đúng tập khoá `{start,end,text,type,scene_id,index}`,
    và **0 đoạn** có `words`.

    Bản đầu của `_chieu_schema` giữ `words` khi có và không sinh `index` — hai
    lệch parity mà **không phép kiểm tự dựng nào bắt được**, vì cả hai vẫn cho
    một dòng thời gian hợp lệ. Chỉ dữ liệu thật mới nói ra.

    ⚠️ Sáu khoá luôn CÓ MẶT, kể cả khi rỗng: `scene_id=""`, `index=0`. Một khoá
       vắng mặt và một khoá rỗng là hai thứ khác nhau với bên tiêu thụ.
    """
    ra = phien_am._chieu_schema([{
        "type": "speech", "start": 0, "end": 1, "text": "a",
        "scene_id": "S0001", "index": 1,
        "words": [{"start": 0, "end": 1, "text": "a"}],
        "rac_noi_bo": 123, "debug": "khong duoc ra ngoai"}])
    assert set(ra[0]) == set(phien_am.KHOA_DAY_DU)
    assert "words" not in ra[0]

    # Thiếu `scene_id`/`index` thì thành rỗng, KHÔNG biến mất.
    thieu = phien_am._chieu_schema([
        {"type": "silence", "start": 1, "end": 3, "text": "[B-ROLL / PAUSE]"}])
    assert thieu[0]["scene_id"] == "" and thieu[0]["index"] == 0
    assert set(thieu[0]) == set(phien_am.KHOA_DAY_DU)


# ── 5. Handler ──────────────────────────────────────────────────────────────

def test_handler_ton_tai_va_nhan_ctx() -> None:
    import inspect
    tham = list(inspect.signature(app_jobs.handle).parameters)
    assert tham[:2] == ["params", "ctx"]
