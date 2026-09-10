"""App `audio_pause` — hợp đồng, ranh giới, và hai luật dễ mất nhất khi port.

## Hai luật được chốt ở đây, và cả hai đều là hành vi ĐÃ CHẠY một năm

1. **Hai mốc rơi đúng cùng một giây thì GỘP, lấy khoảng lặng LỚN HƠN** — không
   cộng dồn, không im lặng bỏ một cái. Cộng dồn nghe hợp lý hơn, và đó chính là
   cách một bản port làm mất parity: nó *cải tiến* một hành vi mà không ai xin.

2. **`language` chọn HỒ SƠ STT**, nên nó nằm trong khoá luỹ đẳng — khác hẳn
   `transcript.run`. `beam_size` là 5 với `vi` và 1 với `en`, nên hai lượt cùng
   audio + cùng kế hoạch nhưng khác ngôn ngữ là **hai việc khác nhau**.

⛔ Không gọi model thật và không gọi ffmpeg: một phép kiểm nạp whisper biến một
   worker pytest thành ~10 luồng torch, và ngân sách `-n` không đếm tiến trình
   cháu.

⛔ Không chốt giá trị ngưỡng (`0.65`, `50`, `15000`, `0.8`). Chúng đến từ
   `configs/` đang chạy và sẽ đổi; chốt ở đây là dựng một bản sao thứ hai của
   cấu hình. Thứ bất biến là *hình dạng*.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from apps.audio_pause import jobs as app_jobs
from apps.audio_pause.manifest import MANIFEST
from apps.audio_pause.services import chen_lang

GOC = Path(__file__).resolve().parent.parent


def _tool():
    return MANIFEST.tools[0]


def _ke_hoach(n: int = 1) -> list[dict]:
    return [{"id": i, "anchor_text": f"cau {i}", "pause_ms": 800}
            for i in range(1, n + 1)]


# ── 1. Hợp đồng ─────────────────────────────────────────────────────────────

def test_manifest_va_tool_khop_nhau() -> None:
    assert MANIFEST.slug == "audio_pause"
    assert MANIFEST.group == "Workflow"
    assert _tool().job_type in MANIFEST.job_types
    assert MANIFEST.public is False and MANIFEST.lifecycle == "development"
    assert _tool().api_exposed is False


def test_HAI_dau_ra_va_ca_hai_deu_duoc_khai() -> None:
    """Transcript đã dịch mốc là thứ bước sau tiêu thụ. Trả về một mình tệp âm
    thanh là làm đứt mạch — và đứt ở chỗ không ai thấy ngay."""
    assert set(_tool().returns) == {"audio", "transcript"}


def test_language_NAM_TRONG_khoa_luy_dang() -> None:
    """Khác `transcript.run`, và lý do là thật: `language` chọn hồ sơ STT
    (`beam_size` 5 với `vi`, 1 với `en`), nên nó đổi kết quả phiên âm, tức đổi
    vị trí cắt."""
    khoa = _tool().idempotency["key_fields"]
    assert set(khoa) == {"audio", "pause_plan", "language"}
    for ten in khoa:
        assert ten in _tool().params_schema


def test_language_la_ENUM_khong_phai_chuoi_tu_do() -> None:
    """Một ngôn ngữ ngoài danh sách sẽ buộc phải đoán một hồ sơ — và một lần
    đoán ở đây vẫn ra kết quả hợp lệ, chỉ là khác đi."""
    truong = _tool().params_schema["language"]
    assert truong["type"] == "enum"
    assert set(truong["values"]) == set(chen_lang.NGON_NGU_CO_HO_SO)
    assert truong["default"] in truong["values"]


def test_admission_khai_ca_hai_ve() -> None:
    assert _tool().admission_resource and _tool().admission_slots >= 1


# ── 2. Ranh giới ────────────────────────────────────────────────────────────

def test_routes_va_jobs_deu_goi_MOT_service() -> None:
    for ten in ("routes.py", "jobs.py"):
        van = (GOC / "apps" / "audio_pause" / ten).read_text(encoding="utf-8")
        assert "from .services import chen_lang" in van, ten


def test_khong_import_app_khac() -> None:
    for tep in (GOC / "apps" / "audio_pause").rglob("*.py"):
        for dong in tep.read_text(encoding="utf-8").splitlines():
            d = dong.strip()
            if d.startswith(("from apps.", "import apps.")):
                assert d.startswith(("from apps.audio_pause",
                                     "import apps.audio_pause")), f"{tep.name}: {d}"


def test_service_KHONG_tu_nap_whisper() -> None:
    """`engine/stt.py` của bot legacy **không** được chuyển sang: nó là bản sao
    thứ hai của việc nạp model, và `platform_core/stt` đã lo việc đó với hồ sơ
    có tên. Hai chỗ nạp model là hai chỗ hồ sơ có thể lệch nhau."""
    engine = GOC / "apps" / "audio_pause" / "services" / "engine"
    assert not (engine / "stt.py").exists()
    for tep in engine.glob("*.py"):
        assert "faster_whisper" not in tep.read_text(encoding="utf-8"), tep.name


def test_ho_so_stt_la_ten_NANG_LUC() -> None:
    from platform_core.stt import ho_so

    assert chen_lang.HO_SO_STT in ho_so.THEO_NGON_NGU
    for ngon_ngu in chen_lang.NGON_NGU_CO_HO_SO:
        ho_so.lay(chen_lang.HO_SO_STT, ngon_ngu)     # không ném là đủ


# ── 3. `chuan_hoa` từ chối TRƯỚC khi chạy ───────────────────────────────────

@pytest.mark.parametrize("params, vi_sao", [
    ({}, "thieu audio"),
    ({"audio": "k.wav"}, "thieu pause_plan"),
    ({"audio": "k.wav", "pause_plan": []}, "pause_plan rong"),
    ({"audio": "k.wav", "pause_plan": ["khong phai dict"]}, "moc khong phai dict"),
    ({"audio": "k.wav", "pause_plan": [{"id": 1}]}, "moc thieu khoa"),
])
def test_dau_vao_hong_bi_tu_choi(params, vi_sao) -> None:
    with pytest.raises(chen_lang.LoiChenLang):
        chen_lang.chuan_hoa(params)


def test_ngon_ngu_ngoai_danh_sach_bi_TU_CHOI_khong_bi_DOAN() -> None:
    with pytest.raises(chen_lang.LoiChenLang):
        chen_lang.chuan_hoa({"audio": "k.wav", "pause_plan": _ke_hoach(),
                             "language": "fr"})


def test_tran_lang_nguoc_bi_tu_choi() -> None:
    for xau in ({"min_pause_ms": 5000, "max_pause_ms": 100},
                {"min_pause_ms": 0, "max_pause_ms": 100},
                {"nguong_khop": 0.0}, {"nguong_khop": 1.5}):
        with pytest.raises(chen_lang.LoiChenLang):
            chen_lang.chuan_hoa({"audio": "k.wav", "pause_plan": _ke_hoach(),
                                 **xau})


def test_chuan_hoa_giu_nguyen_dau_vao_hop_le() -> None:
    yc = chen_lang.chuan_hoa({"audio": "k.wav", "pause_plan": _ke_hoach(2),
                              "language": "EN", "nguong_khop": 0.7})
    assert yc.ngon_ngu == "en" and yc.nguong_khop == 0.7
    assert len(yc.ke_hoach) == 2


# ── 4. Luật gộp khi hai mốc trùng giây ──────────────────────────────────────

def test_hai_moc_trung_giay_thi_GOP_va_lay_cai_LON_HON(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Không cộng dồn (800+1500=2300) và không bỏ một cái.

    🔴 Đây là chỗ một bản port "hợp lý hơn" sẽ đi chệch, và đi chệch **im
       lặng**: tệp ra vẫn phát được, chỉ dài hơn bản cũ.
    """
    goi: list[tuple[str, int]] = []

    def gia_lap_lang(duong, ms, sr, channels=1):
        goi.append(("lang", int(ms)))
        Path(duong).write_bytes(b"x")
        return duong

    def gia_lap_cat(vao, ra, bat_dau, ket_thuc=None, fade_ms=10):
        Path(ra).write_bytes(b"x")
        return ra

    def gia_lap_noi(cac_tep, ra):
        Path(ra).write_bytes(b"x")
        return ra

    monkeypatch.setattr(chen_lang.audio_splicer, "generate_silence", gia_lap_lang)
    monkeypatch.setattr(chen_lang.audio_splicer, "cut_audio_segment", gia_lap_cat)
    monkeypatch.setattr(chen_lang.audio_splicer, "concat_audio_files", gia_lap_noi)
    monkeypatch.setattr(chen_lang, "_thoi_luong_wav", lambda d: 10.0)

    ke_hoach = [{"at_sec": 4.0, "pause_ms": 800, "id": 1},
                {"at_sec": 4.0, "pause_ms": 1500, "id": 2}]
    (tmp_path / "vao.wav").write_bytes(b"x")
    chen_lang._ghep_voi_khoang_lang(str(tmp_path / "vao.wav"), ke_hoach,
                                    tmp_path, 24000, 1)

    lang = [ms for loai, ms in goi if loai == "lang"]
    assert lang == [1500], (
        "hai moc trung giay phai GOP va lay cai LON HON; nhan " + repr(lang))


def test_diem_cat_gom_dau_cuoi_va_KHU_TRUNG(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Điểm cắt là `{0.0} ∪ {mốc} ∪ {hết tệp}`, đã khử trùng. Một mốc rơi đúng
    0.0 hoặc đúng cuối tệp không được đẻ ra một đoạn dài 0 giây."""
    doan: list[tuple[float, float]] = []

    def gia_lap_cat(vao, ra, bat_dau, ket_thuc=None, fade_ms=10):
        doan.append((bat_dau, ket_thuc))
        Path(ra).write_bytes(b"x")
        return ra

    monkeypatch.setattr(chen_lang.audio_splicer, "generate_silence",
                        lambda d, ms, sr, channels=1: (Path(d).write_bytes(b"x"), d)[1])
    monkeypatch.setattr(chen_lang.audio_splicer, "cut_audio_segment", gia_lap_cat)
    monkeypatch.setattr(chen_lang.audio_splicer, "concat_audio_files",
                        lambda ds, ra: (Path(ra).write_bytes(b"x"), ra)[1])
    monkeypatch.setattr(chen_lang, "_thoi_luong_wav", lambda d: 10.0)

    (tmp_path / "vao.wav").write_bytes(b"x")
    chen_lang._ghep_voi_khoang_lang(
        str(tmp_path / "vao.wav"),
        [{"at_sec": 0.0, "pause_ms": 500, "id": 1},
         {"at_sec": 4.0, "pause_ms": 500, "id": 2},
         {"at_sec": 10.0, "pause_ms": 500, "id": 3}],
        tmp_path, 24000, 1)

    assert doan == [(0.0, 4.0), (4.0, 10.0)]
    assert all(b < e for b, e in doan), "co doan dai 0 giay"


def test_khong_sinh_ra_doan_nao_thi_NEM(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Nối một danh sách rỗng cho ra một tệp 0 byte mà ffmpeg vẫn trả 0 — đúng
    loại thất bại im lặng phải chặn ở đây."""
    monkeypatch.setattr(chen_lang, "_thoi_luong_wav", lambda d: 0.0)
    (tmp_path / "vao.wav").write_bytes(b"x")
    with pytest.raises(chen_lang.LoiChenLang):
        chen_lang._ghep_voi_khoang_lang(str(tmp_path / "vao.wav"), [],
                                        tmp_path, 24000, 1)


# ── 5. Handler ──────────────────────────────────────────────────────────────

def test_handler_nhan_params_va_ctx() -> None:
    import inspect
    assert list(inspect.signature(app_jobs.handle).parameters)[:2] == \
        ["params", "ctx"]


# ─────────────────────────────────────────────────────────────────────────────
# `ke_hoach_ghep` — phần QUYẾT ĐỊNH của phép ghép, tách ra để kiểm không cần audio
# ─────────────────────────────────────────────────────────────────────────────
#
# 🔴 Vì sao bốn bài dưới đây là thứ duy nhất kiểm được ở App này.
#
#    `Bot_PausePipeline` **không để lại hiện vật nào** trên máy: `workdir_bot`
#    rỗng, `state_pause.json` ghi 3.099 chu kỳ, log có 1.398 lượt `job_done`
#    nhưng bản ghi chỉ mang `elapsed_s` và một liên kết Drive — không tệp kết
#    quả, không số mốc khớp/trượt.
#
# ⇒ Mệnh đề *"kết quả như bot đã giao"* ở App này **không kiểm được**, và sẽ vẫn
#   thế trừ khi lấy lại được tệp từ Drive. Thứ kiểm được là bốn quyết định của
#   thuật toán, đối chiếu từng dòng với `bot/worker.py:999-1043`.

def test_ke_hoach_ghep_giu_DUNG_bon_quyet_dinh_cua_ban_goc() -> None:
    """Bốn quyết định, đối chiếu `bot/worker.py:999-1043`."""
    k = chen_lang.ke_hoach_ghep

    # 1. Điểm cắt = {0.0} ∪ {mọi at_sec} ∪ {thời lượng}, khử trùng rồi sắp.
    ra = k(10.0, [{"at_sec": 4.0, "pause_ms": 800}])
    assert [(x[0], x[2], x[3]) for x in ra] == [
        ("doan", 0.0, 4.0), ("lang", 800.0, 0.0), ("doan", 4.0, 10.0)]

    # 4. Khoảng lặng đặt TRƯỚC đoạn bắt đầu tại mốc đó (dòng 1032-1039).
    assert ra[1][0] == "lang" and ra[2][0] == "doan"

    # 3. Đoạn ngắn hơn 0.001 giây thì bỏ (dòng 1029-1030).
    assert all(b - a >= 0.001 for loai, _i, a, b in k(
        10.0, [{"at_sec": 9.9999, "pause_ms": 500}]) if loai == "doan")


def test_HAI_MOC_cung_mot_giay_thi_lay_cai_LON_HON_chu_khong_cong_don() -> None:
    """⚠️ Chỗ dễ "sửa cho hợp lý" nhất trong cả App.

    Cộng dồn nghe đúng hơn — 800 + 1800 = 2600 — và nó **không phải** hành vi đã
    chạy một năm. `bot/worker.py:1018` dùng `max`, và chú thích ngay trên đó gọi
    đây là *"Collision — merge (use larger pause)"*.
    """
    ra = chen_lang.ke_hoach_ghep(10.0, [
        {"at_sec": 4.0, "pause_ms": 800}, {"at_sec": 4.0, "pause_ms": 1800}])
    lang = [x for x in ra if x[0] == "lang"]
    assert len(lang) == 1, "hai moc cung giay phai thanh MOT khoang lang"
    assert lang[0][2] == 1800.0, "phai lay cai LON HON"
    assert lang[0][2] != 2600.0, "cong don la mat parity"


def test_MOC_O_DAU_tep_sinh_lang_truoc_moi_thu() -> None:
    ra = chen_lang.ke_hoach_ghep(10.0, [{"at_sec": 0.0, "pause_ms": 1500}])
    assert ra[0][0] == "lang" and ra[0][2] == 1500.0


def test_HAI_BIEN_ke_thua_tu_ban_goc__khong_sua_vi_duong_that_khong_cham_toi() -> None:
    """Hai biên có thật, và tệp này ghi lại chúng thay vì lặng lẽ sửa.

    ⛔ **Mốc rơi đúng cuối tệp thì bị BỎ IM LẶNG.** Vòng lặp chạy tới
       `len(diem_cat) - 1`, nên `thoi_luong` không bao giờ là `bat_dau` của một
       đoạn — khoảng lặng khai ở đó không bao giờ được sinh.

    ⛔ **Mốc vượt thời lượng sinh một đoạn QUÁ ĐUÔI audio** (`[10.0, 12.0]`), và
       `cut_audio_segment` sẽ được yêu cầu cắt sau EOF.

    ⭐ Không sửa, vì **đường thật không chạm tới**: `at_sec` sinh ra từ việc khớp
       văn bản với mốc thời gian của **chính bản ghi lời ấy**, nên nó luôn ≤ thời
       lượng. Khác hẳn ca `sequential_timeline` bên `video_assembly` — ở đó
       khiếm khuyết **đo được là đang xảy ra** trên 115/125 cảnh của một job
       thật, nên sửa; ở đây thì không có phép đo nào nói nó từng xảy ra.

    ⚠️ Nhưng nếu sau này có người gọi `ke_hoach_ghep` với mốc thô do người dùng
       nhập thẳng, hai biên này thành **có thật**. Bài kiểm ở đây là chỗ họ đọc
       được điều đó.
    """
    cuoi = chen_lang.ke_hoach_ghep(10.0, [{"at_sec": 10.0, "pause_ms": 1500}])
    assert [x[0] for x in cuoi] == ["doan"], "moc o cuoi tep bi bo — ghi nhan"

    vuot = chen_lang.ke_hoach_ghep(10.0, [{"at_sec": 12.0, "pause_ms": 900}])
    assert vuot[-1][3] == 12.0 > 10.0, "sinh doan qua duoi audio — ghi nhan"
