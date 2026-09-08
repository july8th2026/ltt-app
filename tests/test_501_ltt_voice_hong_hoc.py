"""LTT VOICE HỎNG THÌ HỎNG NHƯ THẾ NÀO — và ai phải trả tiền cho nó.

## Vì sao tệp này tồn tại

Gói V4 (prompt 10) đòi một mục *Failure tests*: cổng chết, cổng khởi động lại,
hết giờ, giọng không hợp lệ, kho hỏng, chạy đồng thời, chốt GPU, xác thực API.

Nhưng cái đáng đo ở đây **không phải "có ném lỗi không"** — mà là **lỗi thuộc
loại nào**, vì loại lỗi quyết định ba thứ mà khách nhìn thấy:

    LoiGiongNoi   -> LoiNguoiGoi  -> nền tảng KHÔNG thử lại, credit hoàn
    LoiHaTang     -> RuntimeError -> nền tảng THỬ LẠI ba lần
    DangBanTam    -> xếp lại hàng đợi, KHÔNG tính là hỏng

🔴 Xếp nhầm một lỗi vào ô khác là một hồi quy ĐÃ XẢY RA HAI LẦN ở app này, và
   cả hai lần đều tốn tiền thật của khách:

   · 31/08 — `LoiGiongNoi` được cho kế thừa `LoiNguoiGoi` để thôi thử lại ba
     lần cho một lỗi vĩnh viễn. Đúng cho *"giọng này không phải của bạn"*,
     **sai** cho *"cổng giọng đang khởi động lại"* — bản sửa ấy biến một sự cố
     mười giây thành một lượt hỏng vĩnh viễn. Sinh ra `LoiHaTang`.
   · Cùng lỗi ấy **bỏ sót nhánh ghi danh** trong `jobs.py`, sửa sau.

⇒ Nên tệp này đo **hình dạng của lỗi**, không đo thông điệp. Thông điệp đổi
  được; hình dạng đổi là đổi hành vi tính tiền.
"""
from __future__ import annotations

import io
import re

import pytest

from apps.ltt_voice import features, jobs, sidecar_client
from platform_core.jobs import LoiNguoiGoi


# ── 1. Cổng chết / khởi động lại ─────────────────────────────────────────────

def test_cong_chet_la_LOI_HA_TANG_chu_khong_phai_loi_khach(monkeypatch):
    """🔴 HỒI QUY ĐÃ XẢY RA. Cổng giọng khởi động lại sau mỗi lần deploy.

    Nếu nhánh này ném `LoiGiongNoi` thì nền tảng **không thử lại**, và mọi lượt
    đang bay lúc deploy hỏng vĩnh viễn — trong khi thông điệp hứa với khách là
    *"vui lòng thử lại"*. Mười giây gián đoạn thành một lô lượt chết.
    """
    def _chet(*a, **k):
        raise sidecar_client.LoiSidecar("Khong ket noi duoc toi cong giong")

    monkeypatch.setattr(sidecar_client, "noi", _chet)
    with pytest.raises(features.LoiHaTang):
        features.goi_cong("xin chao", preset="Adam")

    assert not issubclass(features.LoiHaTang, LoiNguoiGoi), (
        "LoiHaTang ma la LoiNguoiGoi thi nen tang THOI thu lai — dung cai no "
        "sinh ra de sua")


def test_cong_BAN_thi_xep_lai_chu_khong_tinh_la_hong(monkeypatch):
    """⛔ BẬN KHÔNG PHẢI HỎNG. Đây là bài học đắt nhất của H37 (D-005).

    Coi 429 là *hỏng* dẫn tới cooldown rồi vô hiệu hoá cả đường gọi — một buổi
    tối nhiều việc là đủ để sản phẩm tự tắt.
    """
    def _ban(*a, **k):
        raise sidecar_client.SidecarBan(retry_after_s=7.5)

    monkeypatch.setattr(sidecar_client, "noi", _ban)
    with pytest.raises(features.DangBanTam) as e:
        features.goi_cong("xin chao", preset="Adam")
    assert e.value.retry_after_s == 7.5, "mat retry_after_s thi hang doi doan mu"

    assert not issubclass(features.DangBanTam, LoiNguoiGoi)
    assert not issubclass(features.DangBanTam, features.LoiHaTang), (
        "gop BAN vao HA TANG thi mot may ban se dem vao ti le loi ha tang")


def test_ghi_danh_khi_cong_chet_CUNG_la_ha_tang(monkeypatch):
    """⚠️ Nhánh này từng BỊ BỎ SÓT khi `LoiHaTang` được thêm cho nhánh sinh.

    Hai cửa, một quy tắc — và cửa bị quên là cửa sẽ nuốt tiền ghi danh.
    """
    import inspect
    ma = inspect.getsource(jobs._ghi_danh)
    assert "LoiHaTang" in ma, (
        "nhanh ghi danh khong con phan biet ha tang voi loi khach")


# ── 2. Giọng không hợp lệ — chặn ở CỬA, không để xuống worker ────────────────

def test_preset_bia_bi_chan_va_KHONG_thu_lai():
    """Một `preset` gõ sai chạy lại y hệt sẽ hỏng y hệt ⇒ không được thử lại."""
    with pytest.raises(features.LoiGiongNoi):
        features.chuan_hoa({"text": "xin chao", "preset": "Giong Khong Co That",
                            "owner_id": "u1"})
    assert issubclass(features.LoiGiongNoi, LoiNguoiGoi)


def test_khong_duoc_vua_voice_id_vua_preset():
    """Hai danh tính trong một yêu cầu là một yêu cầu không có nghĩa duy nhất."""
    with pytest.raises(features.LoiGiongNoi):
        features.chuan_hoa({"text": "xin chao", "preset": "Adam",
                            "voice_id": "vc_" + "a" * 32, "owner_id": "u1"})


def test_van_ban_rong_bi_chan_truoc_khi_giu_credit():
    with pytest.raises(features.LoiGiongNoi):
        features.chuan_hoa({"text": "   ", "owner_id": "u1"})


# ── 3. Tốc độ: giá trị vô nghĩa KHÔNG được thành một lượt chạy lạ ───────────

@pytest.mark.parametrize("gt", ["abc", "-3", "0", "99", "", None, "1e9"])
def test_toc_do_vo_nghia_ep_ve_nac_hop_le(gt):
    """⛔ Ép về, KHÔNG ném.

    `features.chuan_hoa` là cửa CHUNG cho cả web lẫn Public API. Ném ở đây
    nghĩa là một tích hợp gửi `speed: 0` nhận lỗi thay vì nhận tiếng — trong
    khi ý định của họ rõ ràng và một mặc định an toàn tồn tại.
    """
    yc = features.chuan_hoa({"text": "xin chao", "toc_do": gt, "owner_id": "u1"})
    from apps.ltt_voice import toc_do
    assert yc.toc_do in toc_do.CAC_NAC, f"toc_do={gt!r} -> {yc.toc_do!r} khong hop le"


# ── 4. Kho hỏng ──────────────────────────────────────────────────────────────

def test_kho_hong_khi_hoi_nghe_thu_thi_NOI_CHUA_CO_chu_khong_no(monkeypatch):
    """Một kho hỏng và một tệp chưa dựng phải dẫn tới CÙNG hành vi giao diện."""
    import platform_core.storage as st
    from apps.ltt_voice import nghe_thu

    class _Hong:
        def exists(self, key):
            raise OSError("kho khong voi toi")

    monkeypatch.setattr(st, "get_storage", lambda: _Hong())
    nghe_thu._DEM.clear()
    assert nghe_thu.co_san("voice/mau/x/v.wav") is False


def test_kho_hong_khi_DUNG_nghe_thu_thi_khong_lam_hong_job(monkeypatch):
    """⛔ Người gọi là đuôi job GHI DANH — giọng đã ghi danh xong ở trên rồi."""
    import platform_core.storage as st
    from apps.ltt_voice import nghe_thu

    class _Hong:
        def exists(self, key):
            return False

        def put(self, *a, **k):
            raise OSError("het cho")

    monkeypatch.setattr(st, "get_storage", lambda: _Hong())
    monkeypatch.setattr(features, "goi_cong", lambda *a, **k: (b"RIFF", {}))
    nghe_thu._DEM.clear()
    assert nghe_thu.dung("voice/mau/x/v.wav", preset="Adam") is False


# ── 5. Chốt GPU / đồng thời ──────────────────────────────────────────────────

def test_manifest_khai_chot_MOT_SUAT_cho_ca_ba_cua():
    """🔴 MỘT GPU = MỘT VIỆC.

    Không khai `admission_resource` thì cửa đồng bộ đi vòng qua hàng đợi và hai
    lượt cùng đập vào một card (Q114). Đây là hằng số duy nhất giữ điều đó.
    """
    from apps.ltt_voice.manifest import MANIFEST
    t = MANIFEST.tools[0]
    assert t.admission_resource == "vieneu_gpu"
    assert t.admission_slots == 1


def test_manifest_khai_tran_runtime_de_bat_job_TREO():
    """Trần tồn tại để bắt job **treo**, không phải job chậm: một job treo mà
    vẫn đập nhịp sẽ giữ slot vô hạn và không ai được báo."""
    from apps.ltt_voice.manifest import MANIFEST
    assert MANIFEST.max_runtime_s["ltt_voice.synthesize"] >= 300
    assert MANIFEST.max_runtime_s["ltt_voice.enroll"] >= 120


def test_manifest_khai_lan_worker_rieng():
    """⛔ Thiếu làn `voice` trong `LTT_WORKER_POOLS` thì job nằm `queued` MÃI
    MÃI — không lỗi, không cảnh báo, `/health/ready` vẫn 200."""
    from apps.ltt_voice.manifest import MANIFEST
    assert "voice" in MANIFEST.requires


# ── 6. Hết giờ ───────────────────────────────────────────────────────────────

def test_moi_cua_sidecar_deu_co_TRAN_THOI_GIAN():
    """⛔ Không có trần thì một cổng treo giữ một worker vĩnh viễn — và trần
    runtime của job không cứu được, vì worker vẫn đang đập nhịp."""
    import inspect
    for ten in ("noi", "noi_dai", "noi_lo", "ghi_danh", "ghi_danh_kho",
                "giong_dung_san"):
        ham = getattr(sidecar_client, ten)
        nguon = inspect.getsource(ham)
        assert "timeout" in nguon, f"sidecar_client.{ten} khong dat timeout"


def test_probe_song_co_tran_NGAN():
    """`song()` nằm trên đường dựng trang — trần của nó là trần kiên nhẫn của
    người dùng, không phải trần của một lượt sinh."""
    assert sidecar_client.SONG_TIMEOUT_S <= 3.0


# ── 7. Xác thực / bề mặt công khai ───────────────────────────────────────────

def test_cong_cu_api_van_fail_closed():
    """⛔ `api_exposed=True` KHÔNG nghĩa là đang mở.

    Ba cổng độc lập (Q92). Phép kiểm này chốt cổng thứ nhất còn nguyên; hai
    cổng kia là biến môi trường của máy chủ.
    """
    from apps.ltt_voice.manifest import MANIFEST
    t = MANIFEST.tools[0]
    assert t.api_exposed is True
    assert t.name == "speech.ltt"
    assert "jobs:create" in t.api_contract["scopes"]


def test_tham_so_sinh_mau_KHONG_ra_hop_dong_cong_khai():
    """⛔ Q119: cache CUDA graph khoá theo `(B, temperature, top_k, top_p)`.

    Cho khách chỉnh ba tham số đó là mời họ làm nở cache graph trên GPU của ta
    cho tới khi hết VRAM. Và `temperature` cao làm lệch tông giữa các đoạn.
    """
    from apps.ltt_voice.manifest import MANIFEST
    khoa = set(MANIFEST.tools[0].params_schema)
    assert not (khoa & {"temperature", "top_k", "top_p", "repetition_penalty"})


def test_cong_bo_nang_luc_khong_lo_GIA_TRI_tham_so():
    """Lộ `temperature=0.8` là mời một tích hợp coi nó là hợp đồng — rồi ngày
    ta đổi nó sau một lượt đo là ngày ta phá hợp đồng mà không hề khai."""
    from voice_sidecar import tham_so
    cb = tham_so.cong_bo()
    assert "phien_ban_tham_so" in cb
    assert not (set(cb) & {"temperature", "top_k", "top_p"})


# ── 8. Trần ký tự — hai trần KHÁC NHAU, đừng gộp ────────────────────────────

def test_hai_tran_ky_tu_la_HAI_HANG_SO_RIENG():
    """`TRAN_MOI_LUOT_SINH` là trần của MỘT lượt `infer` (trần chất lượng).
    `TRAN_KY_TU_CONG_KHAI` là trần của MỘT YÊU CẦU.

    ⚠️ Hôm nay **cả hai đều bằng 1.500**, và phép kiểm này KHÔNG đòi chúng khác
       nhau — đòi vậy là ép mở một cổng chưa đo (V10 còn nợ CER/WER, tương đồng
       người nói, clipping, tỉ lệ hỏng cho bản GHÉP).

    ⭐ Thứ đáng chốt là chúng vẫn là **hai cái tên riêng**. Trước 31/08 chúng là
       một con số, và hệ quả là văn bản 3.000 ký tự bị *từ chối* trong khi chính
       thông điệp lỗi đã hứa một con đường long-form. Gộp lại lần nữa là làm
       mất khả năng nới một trần mà không nới trần kia.
    """
    from apps.ltt_voice import tham_so_cong_khai as t
    assert t.TRAN_MOI_LUOT_SINH == 1500
    assert t.TRAN_KY_TU_CONG_KHAI >= t.TRAN_MOI_LUOT_SINH
    import inspect
    nguon = inspect.getsource(t)
    assert nguon.count("TRAN_KY_TU_CONG_KHAI = ") == 1
    assert "TRAN_KY_TU_CONG_KHAI = TRAN_MOI_LUOT_SINH" not in nguon, (
        "hai tran bi noi lai lam mot bi danh — go duoc kha nang noi rieng tung cai")


def test_van_ban_vuot_tran_bi_chan_o_CUA_va_KHONG_tao_job(khach_hong):
    """🔴 Chặn ở CỬA, và bằng chứng là **không có job nào được tạo**.

    ⛔ Phép kiểm bản đầu hỏi `features.chuan_hoa` và đỏ — vì trần công khai
       **không** ở đó, nó ở route. Đó là một phép kiểm sai chỗ, không phải một
       lỗi sản phẩm: `chuan_hoa` là cửa chung cho cả Public API, và ép độ dài ở
       đó sẽ áp trần của WEB lên một cửa có hợp đồng riêng.

    ⭐ Và "trả 400" chưa đủ. Thứ tốn tiền của khách là một job **được tạo rồi
       mới hỏng** — nên phép kiểm đếm job, không đọc thông điệp.
    """
    from apps.ltt_voice.tham_so_cong_khai import TRAN_KY_TU_CONG_KHAI
    client, uid = khach_hong

    import platform_core.db as dbmod
    from platform_core.models import Job
    from sqlalchemy import select, func

    def _dem():
        gen = dbmod.get_session()
        db = next(gen)
        try:
            return db.execute(select(func.count(Job.id))).scalar() or 0
        finally:
            try:
                next(gen)
            except StopIteration:
                pass

    truoc = _dem()
    tok = _csrf(client)
    r = client.post("/ltt-voice/tao", data={
        "text": "a" * (TRAN_KY_TU_CONG_KHAI + 1), "csrf_token": tok})
    assert r.status_code == 400, f"van ban vuot tran ma cua nhan: {r.status_code}"
    assert _dem() == truoc, "da tao job cho mot yeu cau chac chan hong"


def _csrf(client) -> str:
    m = re.search(r'name="csrf_token" value="([^"]+)"', client.get("/ltt-voice").text)
    assert m, "khong tim thay csrf_token"
    return m.group(1)


@pytest.fixture()
def khach_hong(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'hong.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-hong-hoc")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    import apps.ltt_voice.tables  # noqa: F401

    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from platform_core.storage import LocalStorage, set_storage
    from platform_core.users import tao_nguoi_dung
    set_storage(LocalStorage(str(tmp_path / "store")))

    gen = dbmod.get_session()
    db = next(gen)
    try:
        u = tao_nguoi_dung(db, email="hong@test.com",
                           password="matkhau-tot-12", is_verified=True)
        db.commit()
        from platform_core import credit
        credit.nap(db, user_id=u.id, amount=100, note="test")
        db.commit()
        uid = str(u.id)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    from fastapi.testclient import TestClient

    from server.app import create_app
    client = TestClient(create_app(), base_url="https://testserver",
                        follow_redirects=False)
    m = re.search(r'name="csrf_token" value="([^"]+)"', client.get("/login").text)
    assert m
    client.post("/login", data={"username": "hong@test.com",
                                "password": "matkhau-tot-12",
                                "csrf_token": m.group(1)})
    try:
        yield client, uid
    finally:
        client.close()
        set_storage(None)
        dbmod.reset_engine()


# ── 9. Khuếch đại chi phí qua từ điển phát âm ───────────────────────────────

def test_tu_dien_khong_duoc_lam_no_van_ban_qua_TRAN_SAU_CHUAN_HOA():
    """🔴 Lỗ đã đo: 1.499 ký tự thô -> 120.749 ký tự sau từ điển (80,6x).

    `manifest._gia()` ước giá **không** có từ điển (nó không được chạm CSDL),
    còn worker thì CÓ áp. Hệ quả không phải "thu thiếu" mà là `credit_held` bé
    hơn thực tế ⇒ quyết toán vượt phần giữ ⇒ lượt chạy giữa chừng bị đánh hỏng.
    """
    import inspect
    ma = inspect.getsource(jobs._tao_tieng)
    assert "_tran_sau" in ma, "mat tran sau chuan hoa — lo khuech dai chi phi mo lai"
    assert "len(yc.text) * 3" in ma, "tran sau chuan hoa doi cong thuc ma khong ai khai"


# ── 10. Cửa sổ thử lại phải SỐNG SÓT QUA MỘT LẦN DEPLOY ─────────────────────

def test_MOI_cua_nop_job_deu_khai_SO_LAN_THU_JOB():
    """🔴 ĐO THẬT 02/09/2026 — giết cổng giọng rồi nộp một lượt đọc:

        max_attempts = 3  ->  attempts=3, status='error' sau ~45 giay
                              (cua so thu lai chi 10s + 20s = ~30 giay)

    Nhưng riêng phần **nạp model** khi deploy đã đo **39,9–73,1 giây**. Nên bản
    sửa 31/08 (`LoiHaTang` để job được thử lại) sửa đúng việc **phân loại** lỗi
    mà **không** sửa kết quả: ba lần thử vẫn thua một lần khởi động lại.

    ⭐ Tiền thì vẫn đúng — sổ ghi `hold -1` rồi `refund +1`, khách không bị thu.
       Cái mất là công việc và một thông điệp lỗi không đáng có.

    ⛔ Bốn cửa nộp job, và cửa bị quên là cửa sẽ chết lặng lẽ khi deploy.
    """
    import pathlib as _p
    import re as _re

    goc = _p.Path(__file__).resolve().parents[1] / "apps/ltt_voice/routes"
    thieu, so_cua = [], 0
    for tep in goc.glob("_p_*.py"):
        noi_dung = tep.read_text(encoding="utf-8")
        for khoi in _re.findall(r"submit_with_credit\((?:[^()]|\([^()]*\))*\)",
                                noi_dung):
            so_cua += 1
            if "max_attempts" not in khoi:
                thieu.append(tep.name)

    # ⛔ ĐỐI CHỨNG (Bẫy 31) — thêm 07/09/2026.
    #
    #    Docstring nói *"BỐN cửa nộp job, và cửa bị quên là cửa sẽ chết lặng lẽ
    #    khi deploy"*. Nhưng phép kiểm lái bằng một mẫu chuỗi: đổi tên
    #    `submit_with_credit`, bọc nó qua một hàm trung gian, hay đưa lời gọi
    #    xuống một tệp không khớp `_p_*.py` — `findall` khớp **0** lần, `thieu`
    #    rỗng, XANH. Bốn cửa mất người canh mà không dòng nào báo.
    #
    #    Đo 07/09/2026: 4 lời gọi trong 6 tệp `_p_*.py`.
    assert so_cua >= 4, (
        f"chi thay {so_cua} loi goi `submit_with_credit` — mong doi >= 4 (con "
        f"so trong docstring). Hoac ham da doi ten / bi boc lai, hoac mot cua "
        f"nop job da chuyen cho. Ca hai deu phai xem bang MAT.")

    assert not thieu, (
        f"cua nop job KHONG khai max_attempts: {sorted(set(thieu))} — "
        f"job o day se chet khi deploy")


def test_so_lan_thu_du_song_qua_lan_nap_model_cham_nhat():
    """Cửa sổ = tổng backoff luỹ thừa của `SO_LAN_THU_JOB - 1` lần chờ.

    Phải rộng hơn **73,1 giây** (lần nạp model chậm nhất đã đo), và có biên.
    """
    from apps.ltt_voice.tham_so_cong_khai import SO_LAN_THU_JOB
    BASE, TRAN = 10, 600          # platform_core/jobs.py
    cua_so = sum(min(TRAN, BASE * 2 ** (n - 1))
                 for n in range(1, SO_LAN_THU_JOB))
    assert cua_so >= 150, (
        f"cua so thu lai {cua_so}s — hep hon hai lan nap model cham nhat (73,1s)")


def test_so_lan_thu_KHONG_qua_lon():
    """⛔ Đừng đổi thành "thử lại mãi".

    Một cổng hỏng THẬT phải báo cho khách trong thời gian hợp lý. Job này chạy
    bình thường 12–25 giây; im lặng nhiều phút là một kiểu hỏng khác.
    """
    from apps.ltt_voice.tham_so_cong_khai import SO_LAN_THU_JOB
    assert SO_LAN_THU_JOB <= 6


# ── 11. Từ điển viết tắt — thêm bằng ĐO, và giữ phần đã LOẠI ────────────────

def test_viet_tat_da_do_duoc_giai_ra():
    """Bốn mục thêm 02/09/2026 đều có bằng chứng A/B (xem `tu_dien.py`)."""
    from apps.ltt_voice import tu_dien
    ra = tu_dien.ap_dung("Tai file WAV hoac MP3 qua HTTPS va HTTP.")
    for con in ("WAV", "MP3", "HTTPS", "HTTP"):
        assert con not in ra, f"{con} khong duoc giai ra"


def test_HTTPS_khong_bi_HTTP_an_mat_mot_nua():
    """⛔ `HTTP` là tiền tố của `HTTPS`.

    Nếu phép khớp không chặn biên phải thì `HTTPS` thành `"hát tê tê pê" + "S"`
    — một chuỗi *gần đúng*, tức kiểu hỏng khó thấy nhất.
    """
    from apps.ltt_voice import tu_dien
    ra = tu_dien.ap_dung("Dung HTTPS nhe.")
    assert "hát tê tê pê ét" in ra
    assert "ét" in ra and not ra.endswith("S nhe.")


def test_RTX_va_HTML_VAN_de_nguyen():
    """🔴 BÁNH CÓC CHO MỘT BẢN SỬA SUÝT LÀM HỎNG.

    Đo A/B 02/09/2026: engine đọc `RTX` và `HTML` **đúng sẵn**; giải chúng ra
    làm ASR nghe thành `AZTX` và `hát, kềm L`. Hai trong năm ứng viên sẽ làm
    hỏng một thứ đang chạy tốt — và cả hai "trông cần sửa" y hệt ba cái kia.

    ⛔ Phép kiểm này tồn tại để lần sau ai đó thấy `RTX` trong một bản ghi ASR
       hỏng thì phải ĐO LẠI trước khi thêm, chứ không thêm ngay.
    """
    from apps.ltt_voice import tu_dien
    ra = tu_dien.ap_dung("Card RTX 3090 xuat file HTML.")
    assert "RTX" in ra and "HTML" in ra
    for t in tu_dien.DA_THU_VA_LOAI:
        assert t not in tu_dien.VIET_TAT, (
            f"{t} da duoc do la TE HON khi giai ra — dung them lai")


def test_viet_tat_van_PHAN_BIET_HOA_THUONG():
    """"AI" là viết tắt; "ai" là đại từ tiếng Việt và tuyệt đối không được đọc
    thành "ây ai"."""
    from apps.ltt_voice import tu_dien
    assert "ây ai" not in tu_dien.ap_dung("ai la nguoi do")
    assert "ây ai" in tu_dien.ap_dung("mo hinh AI moi")

