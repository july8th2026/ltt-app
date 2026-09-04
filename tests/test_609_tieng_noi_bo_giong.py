"""
test_609 — `speech.ltt`: GIỌNG DỰNG SẴN vs GIỌNG SỞ HỮU, và giọng của người khác.
(H43 Phase 05)

Sở hữu giọng kiểm ở MỘT chỗ: `features.giai_giong` (lúc thi hành). Cửa nội bộ
`runtime_noi_bo.job.bao_gia` chỉ kiểm hình dạng tham số theo `ToolSpec` — nó
**không** kiểm sở hữu và **không** giữ tiền. Đây là đúng vai (nền tảng không được
biết giá trị nào "của ai"), nên tệp này chứng minh hành vi lúc THI HÀNH và ghi lại
cách một client nội bộ nên hỏi sớm mà không import app (`tuy_chon_dong`).

Neo ở đây:
  1. Preset ⇒ `(None, preset, …)`; giọng của mình ⇒ `(ref_b64, None, …)`.
  2. Giọng NGƯỜI KHÁC và giọng KHÔNG TỒN TẠI ⇒ CÙNG MỘT THÔNG ĐIỆP (không dò được id).
  3. `bao_gia` cho giọng người khác: không ném, không giữ tiền, không tạo job.
     `tuy_chon_dong` chỉ liệt kê giọng `active` của CHÍNH người dùng.
  4. Worker thật: job với giọng người khác ⇒ `error` sau ĐÚNG MỘT lượt (không
     phải 5), hoàn đủ, cổng giọng không bị gọi.
  5. `so_lan_thu` chảy từ manifest: `so_lan_thu_for("ltt_voice.synthesize") == 5`
     và `nop_job` ghi đúng `max_attempts = 5`.
"""
from __future__ import annotations

import uuid

import pytest

TOOL = "speech.ltt"
LANE = "ltt_voice.synthesize"
VAN_BAN = "Xin chào các bạn, hôm nay chúng ta nói về một chủ đề mới."


@pytest.fixture()
def moi_truong(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       "sqlite:///" + (tmp_path / "tieng609.db").as_posix())
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LTT_VOICE_SIDECAR_TOKEN", "thu-nghiem-609")
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    import apps.ltt_voice.tables  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from platform_core import storage
    storage.set_storage(storage.LocalStorage(str(tmp_path / "kho")))
    yield
    storage.set_storage(None)
    dbmod.reset_engine()


def _session():
    from platform_core.db import get_session
    gen = get_session()
    return gen, next(gen)


def _close(gen):
    try:
        next(gen)
    except StopIteration:
        pass


def _user(credits=100) -> str:
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung
    gen, db = _session()
    try:
        u = tao_nguoi_dung(db, email="v609-" + uuid.uuid4().hex[:8] + "@example.com",
                           password="a-good-password-12")
        db.flush()
        credit.cap_tay(db, u.id, credits, by="test")
        db.commit()
        return u.id
    finally:
        _close(gen)


def _tao_giong(owner_id: str, *, public_id: str, ten: str,
               trang_thai: str = "active", co_bieu_dien: bool = True) -> str:
    from apps.ltt_voice.tables import VoiceProfile, VoiceRepr
    gen, db = _session()
    try:
        p = VoiceProfile(public_id=public_id, owner_id=owner_id, ten_hien_thi=ten,
                         ngon_ngu="vi", trang_thai=trang_thai)
        db.add(p)
        db.flush()
        if co_bieu_dien:
            db.add(VoiceRepr(profile_id=p.id, ref_id=0, engine="vieneu",
                             storage_key=f"voice/ref/{owner_id}/{public_id}.npz",
                             fingerprint="vt", trang_thai="dang_dung"))
        db.commit()
        return public_id
    finally:
        _close(gen)


# ── 1. Preset vs giọng sở hữu ────────────────────────────────────────────────

def test_preset_khong_cham_csdl_va_khong_co_ref(moi_truong):
    from apps.ltt_voice import features, giong_mau
    yc = features.chuan_hoa({"text": VAN_BAN, "preset": giong_mau.MAC_DINH})
    ref, preset, _ = features.giai_giong(None, yc)     # db=None: không được chạm
    assert ref is None and preset == giong_mau.MAC_DINH


def test_giong_cua_minh_tra_ref_khong_preset(moi_truong, monkeypatch):
    from apps.ltt_voice import features, tham_chieu
    u = _user()
    vid = _tao_giong(u, public_id="vc_cua_toi_609", ten="Giọng tôi")
    monkeypatch.setattr(tham_chieu, "nap_ref_b64", lambda bd: "REF64:" + bd.storage_key)
    yc = features.chuan_hoa({"text": VAN_BAN, "voice_id": vid, "owner_id": u})
    gen, db = _session()
    try:
        ref, preset, _ = features.giai_giong(db, yc)
    finally:
        _close(gen)
    assert preset is None and ref.startswith("REF64:voice/ref/")


def test_vua_voice_id_vua_preset_bi_tu_choi_truoc_khi_hoi_csdl(moi_truong):
    from platform_core import jobs as jobq
    from apps.ltt_voice import features, giong_mau
    with pytest.raises(features.LoiGiongNoi) as e:
        features.chuan_hoa({"text": VAN_BAN, "voice_id": "vc_x",
                            "preset": giong_mau.MAC_DINH})
    assert isinstance(e.value, jobq.LoiNguoiGoi)


# ── 2. Giọng người khác ≡ giọng không tồn tại ───────────────────────────────

def test_giong_nguoi_khac_va_khong_ton_tai_CUNG_mot_thong_diep(moi_truong):
    from platform_core import jobs as jobq
    from apps.ltt_voice import features

    toi, khac = _user(), _user()
    vid_khac = _tao_giong(khac, public_id="vc_cua_khac_609", ten="Giọng khác")

    def _thu(voice_id):
        yc = features.chuan_hoa({"text": VAN_BAN, "voice_id": voice_id, "owner_id": toi})
        gen, db = _session()
        try:
            with pytest.raises(features.LoiGiongNoi) as e:
                features.giai_giong(db, yc)
            return e.value
        finally:
            _close(gen)

    e1 = _thu(vid_khac)
    e2 = _thu("vc_khong_ton_tai_609")
    assert str(e1) == str(e2), "hai cau khac nhau la cho phep do xem voice_id nao co that"
    assert isinstance(e1, jobq.LoiNguoiGoi) and isinstance(e2, jobq.LoiNguoiGoi)
    assert "không tìm thấy" in str(e1).lower()


def test_giong_dung_chung_cua_nen_tang_thi_ai_cung_doc_duoc(moi_truong, monkeypatch):
    """Kho chung mở cửa ĐỌC — đó là ngoại lệ có chủ ý, không phải lỗ."""
    from apps.ltt_voice import features, tham_chieu
    from apps.ltt_voice.tables import VoiceProfile

    toi, nen_tang = _user(), _user()
    vid = _tao_giong(nen_tang, public_id="vc_chung_609", ten="Kho chung")
    gen, db = _session()
    try:
        db.execute(VoiceProfile.__table__.update()
                   .where(VoiceProfile.public_id == vid).values(dung_chung=True))
        db.commit()
    finally:
        _close(gen)
    monkeypatch.setattr(tham_chieu, "nap_ref_b64", lambda bd: "REF")
    yc = features.chuan_hoa({"text": VAN_BAN, "voice_id": vid, "owner_id": toi})
    gen, db = _session()
    try:
        assert features.giai_giong(db, yc)[0] == "REF"
    finally:
        _close(gen)


# ── 3. Cửa nội bộ: bao_gia không kiểm sở hữu, không giữ tiền ────────────────

def test_bao_gia_giong_nguoi_khac_khong_nem_khong_giu_tien_khong_tao_job(moi_truong):
    from platform_core import credit
    from platform_core.models import Job
    from platform_core.runtime_noi_bo import job as rj

    toi, khac = _user(100), _user(100)
    vid_khac = _tao_giong(khac, public_id="vc_khac_bg_609", ten="Khác")
    gen, db = _session()
    try:
        bg = rj.bao_gia(TOOL, {"text": VAN_BAN, "voice_id": vid_khac}, db=db, user_id=toi)
        assert bg.lane == LANE and bg.credit > 0
        assert bg.tham_so_sach["voice_id"] == vid_khac
        # Không một bút toán, không một job — báo giá là báo giá.
        assert credit.so_du(db, toi) == 100
        assert db.query(Job).count() == 0
    finally:
        _close(gen)


def test_tuy_chon_dong_chi_liet_ke_giong_active_cua_chinh_minh(moi_truong):
    """Đường HỎI SỚM cho client nội bộ mà không import app: đọc `options` của schema."""
    from platform_core.agent.tools import resolve_params_schema

    toi, khac = _user(), _user()
    cua_toi = _tao_giong(toi, public_id="vc_toi_a_609", ten="A")
    _tao_giong(toi, public_id="vc_toi_tat_609", ten="Tắt", trang_thai="disabled")
    _tao_giong(khac, public_id="vc_khac_b_609", ten="B")
    gen, db = _session()
    try:
        schema = resolve_params_schema(TOOL, db=db, user_id=toi)
    finally:
        _close(gen)
    assert schema["voice_id"]["values"] == [cua_toi]
    assert schema["voice_id"]["options"][0]["label"] == "A"


# ── 4. Worker thật: giọng người khác ⇒ hỏng NGAY, không 5 lượt ─────────────

def test_worker_giong_nguoi_khac_hong_sau_mot_luot_hoan_du_khong_goi_cong(moi_truong, monkeypatch):
    import platform_core.job_runner as runner
    from platform_core import credit
    from platform_core.models import JOB_ERROR, Job, JobEvent
    from platform_core.runtime_noi_bo import job as rj
    from apps.ltt_voice import sidecar_client

    toi, khac = _user(100), _user(100)
    vid_khac = _tao_giong(khac, public_id="vc_khac_w_609", ten="Khác")

    gen, db = _session()
    try:
        bg = rj.bao_gia(TOOL, {"text": VAN_BAN, "voice_id": vid_khac}, db=db, user_id=toi)
        j = rj.nop_job(db, user_id=toi, bao_gia=bg, idempotency_key="idem-609")
        db.commit()
        job_id = j.id
        assert j.max_attempts == 5                    # từ manifest.so_lan_thu
        held = credit.so_da_giu(db, job_id)
        assert held == bg.credit > 0
    finally:
        _close(gen)

    goi = []

    def _cong_bi_goi(*a, **k):
        goi.append(1)
        raise AssertionError("cong giong bi goi cho mot yeu cau da sai tu dau")

    monkeypatch.setattr(sidecar_client, "noi", _cong_bi_goi)
    monkeypatch.setattr(sidecar_client, "noi_dai", _cong_bi_goi)
    monkeypatch.setattr(runner, "_vram_can", lambda jt: 0)    # không giành GPU thật
    assert runner._chay_mot_job("w-609") is True
    assert goi == []

    gen, db = _session()
    try:
        j = db.get(Job, job_id)
        assert j.status == JOB_ERROR and j.attempts == 1
        assert "không tìm thấy" in (j.error or "").lower()
        ma = {e.event_code for e in db.query(JobEvent).filter(JobEvent.job_id == job_id)}
        assert "failed" in ma and "retry_scheduled" not in ma
        assert credit.so_du(db, toi) == 100
    finally:
        _close(gen)


# ── 5. so_lan_thu chảy từ manifest ─────────────────────────────────────────

def test_so_lan_thu_synthesize_la_5_va_khong_import_cheo():
    from apps.ltt_voice.manifest import MANIFEST
    assert MANIFEST.so_lan_thu_for(LANE) == 5
    tool = next(t for t in MANIFEST.tools if t.name == TOOL)
    assert tool.admission_resource == "vieneu_gpu" and tool.admission_slots == 1
    assert tool.tuy_chon_dong == {
        "voice_id": "apps.ltt_voice.tham_chieu:tuy_chon_voice_id",
        # ⭐ THEM 04/09: kho DUNG CHUNG. Truoc do mot tai khoan chua nhan ban
        #    giong nao thay o chon giong RONG — tuc khong co lua chon nao, va do
        #    la trang thai cua gan nhu moi khach moi. Hai khoa nay khac vai:
        #    `voice_id` la giong CUA HO (kiem so huu), `preset` la kho chung
        #    (khong thuoc ai). Gop lam mot la xoa mat ranh gioi do.
        "preset": "apps.ltt_voice.tham_chieu:tuy_chon_preset",
    }
