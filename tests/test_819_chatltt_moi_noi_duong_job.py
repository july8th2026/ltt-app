"""
test_819 — job xong ⇒ lượt tự chạy tiếp. MỐI NỐI của ĐƯỜNG JOB. (H44 P05)

`test_817` đi mối nối của đường **duyệt** và tìm ra rằng các mảnh đều xanh trong
khi chỗ khâu chúng lại thì không ai kiểm. Đường **job** còn một mối nối nữa, dài
hơn, và cho tới hôm nay **chưa phép kiểm nào chạm tới** (đo 05/09: `_dat_khoi`
0 tệp, `con_cho_job` 0 tệp, `tao_media.dong_bo` chỉ có ở dải 600 — tức đường V1
nút bấm, không phải đường V3):

    model goi image.ltt -> phieu duyet -> nop JOB THAT -> WAITING_BACKGROUND
      -> job xong  -> dong_bo() doc trang thai
      -> _dat_khoi() noi anh vao tin nhan
      -> _danh_thuc_run() -> tiep_sau_duyet() -> model vong sau -> COMPLETED

`test_816` kiểm khúc nộp job nhưng **thay `tao_media.tao` bằng một hàm giả**, nên
cả `chatltt_execution` của job lẫn hàng job thật đều chưa từng tồn tại trong một
phép kiểm nào. Tệp này nộp job thật (`J.nop_job` — có giữ tiền thật) rồi giả lập
**duy nhất** trạng thái worker trả về.

⛔ Tệp này KHÔNG chạy luồng nền thật. `chay_tiep_nen` mở một `Session` riêng, và
   một phép kiểm phụ thuộc thời điểm hai luồng chạm cùng một tệp SQLite là một
   phép kiểm sẽ đỏ ngẫu nhiên ở cổng. Mối nối được chạy **đồng bộ**, còn việc
   `_danh_thuc_run` gọi đúng ai với đối số nào thì kiểm riêng.
"""
from __future__ import annotations

import json
import re
import threading
import uuid

import pytest

NL = bytes([10])
ANH = "image.ltt"


def _sse(g):
    return b"data: " + json.dumps(g).encode() + NL + NL


def _chu(t):
    return [_sse({"choices": [{"delta": {"content": t}, "finish_reason": "stop"}]}),
            _sse({"choices": [], "usage": {"prompt_tokens": 30, "completion_tokens": 5}}),
            b"data: [DONE]" + NL + NL]


def _goi_tool(ten, doi_so):
    return [_sse({"choices": [{"delta": {"tool_calls": [
                {"index": 0, "id": "call_1", "type": "function",
                 "function": {"name": ten, "arguments": doi_so}}]}}]}),
            _sse({"choices": [{"delta": {}, "finish_reason": "tool_calls"}]}),
            _sse({"choices": [], "usage": {"prompt_tokens": 60, "completion_tokens": 9}}),
            b"data: [DONE]" + NL + NL]


@pytest.fixture()
def web(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", "sqlite:///" + (tmp_path / "s.db").as_posix())
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine
    from platform_core.registry import load_app_tables
    load_app_tables()
    Base.metadata.create_all(get_engine())
    from fastapi.testclient import TestClient
    from server.app import create_app
    app = create_app(env={
        "LTT_ENV": "local-server-test", "LTT_SESSION_SECRET": "chatltt-secret-819",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp_path / "c.json"),
    })
    from apps.chatltt.services import luot as LUOT

    def inline(execution_id, *, user_id):
        LUOT.chay(execution_id, user_id=user_id)
        return threading.current_thread()

    monkeypatch.setattr(LUOT, "khoi_chay_nen", inline)
    with TestClient(app, base_url="https://testserver") as c:
        yield c
    dbmod.reset_engine()


@pytest.fixture()
def may(monkeypatch):
    """Model giả cho `text.chat`. `image.ltt` là tool THẬT của `anhnoibo`."""
    from platform_core import registry as reg
    from platform_core.llm import luong_vlm
    from tests.test_600_runtime_noi_bo_luong import EXECUTOR_GIA  # noqa: F401

    tool = reg.ToolSpec(name="text.chat", job_type="t819.j", description="d",
                        params_schema={"messages": {"type": "json[]"},
                                       "tools": {"type": "json[]"},
                                       "model": {"type": "enum", "values": ["thu_alias"],
                                                 "default": "thu_alias"}},
                        returns={"content": "text"},
                        admission_resource="thu_gpu819", admission_slots=1,
                        sync_executor="tests.test_600_runtime_noi_bo_luong:EXECUTOR_GIA")
    man = reg.AppManifest(slug="t819", display_name="t819", route_prefix="/t819",
                          job_types=("t819.j",), credit_cost=lambda p: 1,
                          surface="runtime", lifecycle="internal", tools=(tool,))
    goc = reg.discover
    loaded = reg.LoadedApp(manifest=man, router=None)
    monkeypatch.setattr(reg, "discover",
                        lambda apps_dir=None: [x for x in goc()
                                               if x.manifest.slug != "ltt_llm"] + [loaded])

    class Kho:
        def __init__(self):
            self.than, self.luot = [], []

        def dat(self, *luot):
            self.luot = list(luot)
            return self

    kho = Kho()

    class Gia:
        ma, content_type = 200, "text/event-stream"

        def __init__(self, ks):
            self.luong = iter(ks)

        def xong(self, tokens=0):
            pass

        def hong(self, exc):
            pass

    monkeypatch.setattr(luong_vlm, "mo",
                        lambda db, *, duong, than, timeout_s=900.0:
                        (kho.than.append(than),
                         Gia(kho.luot.pop(0) if kho.luot else _chu("mac dinh")))[1])
    return kho


@pytest.fixture(autouse=True)
def _chi_anh(monkeypatch):
    """Chỉ mời `image.ltt` cho model — để một phép kiểm đỏ nói được đỏ vì cái gì.

    ⚠️ Và ép sức khoẻ `san_sang`: `chieu()` **không mời** một năng lực chưa sẵn
       sàng, còn `anhnoibo.suc_khoe` hỏi cổng render máy B — thứ không chạy
       trong phép kiểm. Không ép thì `chieu()` trả rỗng và cả tệp này đo một
       lượt KHÔNG có tool, tức đo nhầm thứ.
    """
    from apps.chatltt.services import chieu_tool as C
    from platform_core.runtime_noi_bo import danh_muc as DM
    monkeypatch.setattr(C, "CHO_MODEL_GOI", (ANH,))
    monkeypatch.setattr(DM, "suc_khoe_cua", lambda m, now=None: "san_sang")


@pytest.fixture()
def bat_co(monkeypatch):
    from apps.chatltt.services import co_v3
    monkeypatch.setenv(co_v3.CO_TOOLS, "1")


class JobGia:
    """Thứ worker sẽ để lại. Đây là **điểm giả lập duy nhất** của tệp này."""

    def __init__(self, jid, *, status="queued", result=None, error="", progress=0):
        self.id = jid
        self.status = status
        self.result = result or {}
        self.error = error
        self.progress = progress


@pytest.fixture()
def kho_job(monkeypatch):
    kho: dict = {}
    monkeypatch.setattr("platform_core.job_history.get_owned",
                        lambda db, u, j: kho.get(str(j)))
    return kho


def _user(credits=5000):
    from platform_core import credit
    from platform_core.db import get_session
    from platform_core.users import tao_nguoi_dung
    gen = get_session()
    db = next(gen)
    try:
        email = "s819-" + uuid.uuid4().hex[:6] + "@example.com"
        u = tao_nguoi_dung(db, email=email, password="a-good-password-12",
                           is_verified=True)
        db.flush()
        credit.cap_tay(db, u.id, credits, by="test")
        db.commit()
        return u.id, email
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def _phien(app, email):
    from fastapi.testclient import TestClient
    c = TestClient(app, base_url="https://testserver")
    r = c.get("/login")
    m = re.search(r'name="csrf_token" value="([^"]+)"', r.text)
    c.post("/login", data={"username": email, "password": "a-good-password-12",
                           "csrf_token": m.group(1), "next": "/chatltt"},
           follow_redirects=True)
    csrf = re.search(r'data-csrf="([^"]+)"', c.get("/chatltt").text).group(1)
    return c, {"X-CSRF-Token": csrf}


def _phien_db():
    from platform_core.db import get_session
    gen = get_session()
    return gen, next(gen)


def _dong(gen):
    try:
        next(gen)
    except StopIteration:
        pass


class SoGia:
    """`dang_chay.LuotDangChay` giả — chỉ cần `phat` và `dung`."""

    def __init__(self):
        self.sk = []
        self.dung = threading.Event()
        self.execution_id = "ex-gia"

    def phat(self, sk):
        self.sk.append(sk)


def _cho_job(web, may, doi_so='{"prompt": "mot con meo", "count": 1}'):
    """Đưa một lượt tới `WAITING_BACKGROUND` với một job THẬT đã nộp.

    Trả `(uid, run_id, job_id, ex_job_id, message_id)`.
    """
    from apps.chatltt.services import duyet as D
    from apps.chatltt.services import luot_v3
    from apps.chatltt.tables import ChatlttRun, ChatlttStep

    may.dat(_goi_tool(ANH, doi_so))
    uid, email = _user()
    c, h = _phien(web.app, email)
    cv = c.post("/chatltt/api/hoi-thoai", json={"model_alias": "thu_alias"},
                headers=h).json()["id"]
    r = c.post(f"/chatltt/api/hoi-thoai/{cv}/luot", json={"text": "ve con meo"},
               headers=h)
    assert r.status_code == 202, r.text

    ds = c.get("/chatltt/api/duyet/dang-cho", headers=h).json()["items"]
    assert len(ds) == 1, ds
    gen, db = _phien_db()
    try:
        run_row = db.query(ChatlttRun).filter_by(user_id=uid).one()
        D.duyet(db, user_id=uid, approval_id=ds[0]["approval_id"])
        db.commit()
        run = luot_v3.tiep_sau_duyet(db, run_id=run_row.id, user_id=uid, so=SoGia())
        assert run.trang_thai == "WAITING_BACKGROUND", run.trang_thai
        b = db.query(ChatlttStep).filter_by(run_id=run_row.id,
                                            trang_thai="cho_job").one()
        from apps.chatltt.tables import ChatlttExecution
        ex_job = db.query(ChatlttExecution).filter_by(job_id=b.job_id).one()
        return uid, run_row.id, b.job_id, ex_job.id, run_row.message_id
    finally:
        _dong(gen)


def _khoi(mid):
    from apps.chatltt.tables import ChatlttMessage
    gen, db = _phien_db()
    try:
        return list(db.get(ChatlttMessage, mid).blocks or [])
    finally:
        _dong(gen)


# ── 1. Dừng ở WAITING_BACKGROUND với một job THẬT ──────────────────────────

def test_duyet_anh_thi_nop_job_that_va_run_cho_may(web, may, bat_co):
    uid, rid, jid, ex_job, _mid = _cho_job(web, may)
    from apps.chatltt.tables import ChatlttExecution, ChatlttRun
    gen, db = _phien_db()
    try:
        assert db.get(ChatlttRun, rid).trang_thai == "WAITING_BACKGROUND"
        ex = db.get(ChatlttExecution, ex_job)
        # Bút toán của job nối được về bước sinh ra nó — cả hai chiều.
        assert (ex.mode, ex.tool_name, ex.job_id) == ("job", ANH, jid)
        assert ex.run_id == rid and ex.step_id
    finally:
        _dong(gen)


def test_job_gan_vao_DUNG_tin_nhan_cua_run(web, may, bat_co):
    """Không có `tin_nhan` thì job đẻ ra một tin nhắn thứ hai, và câu trả lời
    của model rơi vào một chỗ khác với chỗ nó đang nói."""
    uid, rid, _jid, ex_job, mid = _cho_job(web, may)
    from apps.chatltt.tables import ChatlttExecution, ChatlttMessage
    gen, db = _phien_db()
    try:
        assert db.get(ChatlttExecution, ex_job).message_id == mid
        n = db.query(ChatlttMessage).filter_by(user_id=uid, role="assistant").count()
        assert n == 1, "job KHONG duoc de ra tin nhan assistant thu hai"
    finally:
        _dong(gen)


def test_tien_giu_theo_gia_THAT_cua_registry(web, may, bat_co):
    """Giá đi từ `anhnoibo.gia`, không từ một con số bịa trong phép kiểm."""
    from platform_core import credit
    from platform_core.runtime_noi_bo import job as J

    uid, _rid, _jid, ex_job, _mid = _cho_job(web, may)
    gen, db = _phien_db()
    try:
        from apps.chatltt.tables import ChatlttExecution
        bg = J.bao_gia(ANH, {"prompt": "mot con meo", "count": 1},
                       db=db, user_id=uid)
        assert db.get(ChatlttExecution, ex_job).credit_giu == bg.credit
        assert int(credit.so_du(db, uid)) <= 5000 - bg.credit
    finally:
        _dong(gen)


# ── 2. `_dat_khoi` — NỐI, không THAY ───────────────────────────────────────

def test_anh_NOI_them_khong_xoa_tool_call_va_chu(web, may, bat_co, kho_job):
    """🔴 Phát hiện #5 của P05. `dong_bo` của đường V1 **thay toàn bộ**
    `tin.blocks` — đúng ở đó vì mỗi lần bấm là một tin nhắn riêng. Với V3 thì
    tin nhắn ấy đang mang khối `tool_call` của cả lượt, và thay toàn bộ là
    người dùng thấy một bức ảnh xuất hiện **thay chỗ** câu trả lời vừa đọc."""
    from apps.chatltt.services import tao_media as TM

    uid, _rid, jid, ex_job, mid = _cho_job(web, may)
    truoc = _khoi(mid)
    assert any(k["type"] == "tool_call" for k in truoc), truoc

    kho_job[jid] = JobGia(jid, status="done",
                          result={"image_keys": ["anh-1"], "credit_cost": 3})
    may.dat(_chu("Anh xong roi nhe."))
    gen, db = _phien_db()
    try:
        TM.dong_bo(db, user_id=uid, execution_id=ex_job)
    finally:
        _dong(gen)

    sau = _khoi(mid)
    assert {"type": "image", "key": "anh-1"} in sau
    assert [k for k in sau if k["type"] == "tool_call"], "khoi tool_call bi XOA"


def test_anh_dung_TRUOC_phan_chu(web, may, bat_co, kho_job):
    """Model sẽ nói **về** bức ảnh ở vòng sau, nên câu ấy phải nằm dưới nó."""
    from apps.chatltt.services import tao_media as TM

    uid, _rid, jid, ex_job, mid = _cho_job(web, may)
    kho_job[jid] = JobGia(jid, status="done", result={"image_keys": ["anh-1"]})
    gen, db = _phien_db()
    try:
        TM.dong_bo(db, user_id=uid, execution_id=ex_job)
    finally:
        _dong(gen)

    sau = _khoi(mid)
    loai = [k["type"] for k in sau]
    if "text" in loai:
        assert loai.index("image") < loai.index("text")


def test_dong_bo_goi_HAI_lan_khong_nhan_doi_khoi(web, may, bat_co, kho_job):
    """Client hỏi theo nhịp 2 giây; `dong_bo` phải an toàn khi gọi nhiều lần."""
    from apps.chatltt.services import tao_media as TM

    uid, _rid, jid, ex_job, mid = _cho_job(web, may)
    kho_job[jid] = JobGia(jid, status="done", result={"image_keys": ["anh-1"]})
    gen, db = _phien_db()
    try:
        TM.dong_bo(db, user_id=uid, execution_id=ex_job)
        TM.dong_bo(db, user_id=uid, execution_id=ex_job)
    finally:
        _dong(gen)

    sau = _khoi(mid)
    assert len([k for k in sau if k["type"] == "image"]) == 1


def test_duong_NUT_BAM_van_THAY_toan_bo(web, may, bat_co):
    """⛔ Đường V1 **không** được đổi theo. `noi_them` bật theo `run_id`, nên một
    job không thuộc run nào vẫn thay sạch — đó là hành vi đúng của nó."""
    from apps.chatltt.services.tao_media import _dat_khoi

    class Tin:
        blocks = [{"type": "text", "text": "cu"}]

    t = Tin()
    _dat_khoi(t, [{"type": "image", "key": "k"}], noi_them=False)
    assert t.blocks == [{"type": "image", "key": "k"}]


# ── 3. Đánh thức: job xong ⇒ lượt chạy tiếp ────────────────────────────────

def test_job_xong_thi_run_CHAY_TIEP_va_ket_thuc(web, may, bat_co, kho_job,
                                                monkeypatch):
    from apps.chatltt.services import luot_v3, tao_media as TM
    from apps.chatltt.tables import ChatlttRun

    uid, rid, jid, ex_job, _mid = _cho_job(web, may)
    kho_job[jid] = JobGia(jid, status="done", result={"image_keys": ["anh-1"]})
    may.dat(_chu("Day la buc anh ban muon."))

    goi = []
    gen, db = _phien_db()
    try:
        monkeypatch.setattr(
            luot_v3, "chay_tiep_nen",
            lambda run_id, *, user_id: (
                goi.append(run_id),
                luot_v3.tiep_sau_duyet(db, run_id=run_id, user_id=user_id,
                                       so=SoGia()))[0])
        TM.dong_bo(db, user_id=uid, execution_id=ex_job)
        assert goi == [rid], "run KHONG duoc danh thuc"
        db.expire_all()
        assert db.get(ChatlttRun, rid).trang_thai == "COMPLETED"
    finally:
        _dong(gen)


def test_ket_qua_job_TOI_DUOC_model_vong_sau(web, may, bat_co, kho_job,
                                             monkeypatch):
    """Mối nối dễ đứt nhất: ảnh vẽ xong nhưng model không hề biết."""
    from apps.chatltt.services import luot_v3, tao_media as TM

    uid, _rid, jid, ex_job, _mid = _cho_job(web, may)
    kho_job[jid] = JobGia(jid, status="done",
                          result={"image_keys": ["anh-cua-toi"]})
    may.dat(_chu("xong"))
    gen, db = _phien_db()
    try:
        monkeypatch.setattr(
            luot_v3, "chay_tiep_nen",
            lambda run_id, *, user_id: luot_v3.tiep_sau_duyet(
                db, run_id=run_id, user_id=user_id, so=SoGia()))
        TM.dong_bo(db, user_id=uid, execution_id=ex_job)
    finally:
        _dong(gen)

    vai = [m["role"] for m in may.than[-1]["messages"]]
    assert vai[-2:] == ["assistant", "tool"]
    assert "anh-cua-toi" in str(may.than[-1]["messages"][-1]["content"])


def test_vong_sau_van_la_TEXT_CHAT_khong_phai_image_ltt(web, may, bat_co,
                                                        kho_job, monkeypatch):
    """🔴 `tao_media.tao` gọi `S.mo_execution(message=tra_loi, ...)`, và hàm đó
    **ghi đè** `tra_loi.execution_id` sang execution của job. `tiep_sau_duyet`
    lại đọc đúng trường ấy để biết mở luồng bằng năng lực nào.

    Hệ quả không phải nhãn sai: `luot.dong_su_kien` truyền `ex.tool_name` thẳng
    vào `L.mo_luong()`. Vòng model sau một job sẽ được mở bằng **`image.ltt`** —
    tức hỏi cỗ máy vẽ ảnh một câu hỏi chữ."""
    from apps.chatltt.services import luot_v3, tao_media as TM
    from apps.chatltt.tables import ChatlttExecution

    uid, rid, jid, ex_job, _mid = _cho_job(web, may)
    kho_job[jid] = JobGia(jid, status="done", result={"image_keys": ["a"]})
    may.dat(_chu("xong"))
    gen, db = _phien_db()
    try:
        monkeypatch.setattr(
            luot_v3, "chay_tiep_nen",
            lambda run_id, *, user_id: luot_v3.tiep_sau_duyet(
                db, run_id=run_id, user_id=user_id, so=SoGia()))
        TM.dong_bo(db, user_id=uid, execution_id=ex_job)
        db.expire_all()
        ds = db.query(ChatlttExecution).filter_by(run_id=rid).all()
        vong = [e for e in ds if e.id != ex_job]
        assert vong, "khong co execution nao cho vong model"
        assert {e.tool_name for e in vong} == {"text.chat"}, \
            [(e.tool_name, e.mode) for e in vong]
        assert {e.mode for e in vong} == {"stream"}
    finally:
        _dong(gen)


def test_tep_tra_cho_model_doc_CONG_RA_DA_KHAI(web, may, bat_co):
    """🔴 Bản cũ đoán `files`/`outputs`/`keys`. **Không tên nào trong ba cái đó
    tồn tại**: `image.ltt` khai `image_keys`, `speech.ltt` khai `audio_key`. Nên
    model luôn đọc `{"tao_xong": true, "tep": []}` — một câu tự mâu thuẫn, và
    nó không bao giờ tham chiếu được bức ảnh vừa vẽ ở lượt sau."""
    from apps.chatltt.services.bo_chay_tool import _tep_cua

    assert _tep_cua(ANH, {"image_keys": ["a", "b"]}) == ["a", "b"]
    assert _tep_cua("speech.ltt", {"audio_key": "am-1"}) == ["am-1"]


def test_ba_ten_khoa_DOAN_khong_con_duoc_chap_nhan(web, may, bat_co):
    """Phép kiểm đột biến: trả lại lối đoán thì phải đỏ."""
    from apps.chatltt.services.bo_chay_tool import _tep_cua

    for khoa in ("files", "outputs", "keys"):
        assert _tep_cua(ANH, {khoa: ["x"]}) == [], khoa


def test_model_va_NGUOI_DUNG_thay_cung_mot_tap_artifact(web, may, bat_co):
    """⛔ Hai nguồn cho câu hỏi *"job này đẻ ra những gì"* là hai nguồn sẽ
    lệch — và chỗ chúng lệch là chỗ người dùng thấy một bức ảnh trong khi
    model nói nó không tạo được gì."""
    from apps.chatltt.services.bo_chay_tool import _tep_cua
    from apps.chatltt.services.tao_media import khoi_artifact

    kq = {"image_keys": ["a", "b"], "credit_cost": 3}
    assert _tep_cua(ANH, kq) == [k["key"] for k in khoi_artifact(ANH, kq)]


def test_tool_LA_khong_giet_luot(web, may, bat_co):
    """Gỡ một app là chuyện có thật. Mất danh sách tệp không được giết lượt."""
    from apps.chatltt.services.bo_chay_tool import _tep_cua

    assert _tep_cua("khong.ton.tai", {"image_keys": ["a"]}) == []


# ── 4. Giới hạn KÉO — ghim lại để không ai tưởng nó đã xong ────────────────

def test_KHONG_AI_HOI_thi_run_nam_im(web, may, bat_co, kho_job):
    """⚠️ Đây là **giới hạn đã biết**, không phải lỗi: `dong_bo` chỉ chạy khi
    client hỏi. Đường ĐẨY thật là một chỗ móc trong `job_runner` —
    `platform_core`, ngoài ranh giới app này.

    Ghim nó bằng một phép kiểm để ngày ai đó làm đường đẩy, phép kiểm này đỏ và
    buộc người ta đọc lại đoạn này."""
    from apps.chatltt.tables import ChatlttRun

    uid, rid, jid, _ex, _mid = _cho_job(web, may)
    kho_job[jid] = JobGia(jid, status="done", result={"image_keys": ["a"]})
    gen, db = _phien_db()
    try:
        assert db.get(ChatlttRun, rid).trang_thai == "WAITING_BACKGROUND"
    finally:
        _dong(gen)


# ── 5. Hỏng ────────────────────────────────────────────────────────────────

def test_job_THAT_BAI_thi_run_van_ket_tu_te(web, may, bat_co, kho_job,
                                            monkeypatch):
    from apps.chatltt.services import luot_v3, tao_media as TM
    from apps.chatltt.tables import ChatlttRun

    uid, rid, jid, ex_job, mid = _cho_job(web, may)
    kho_job[jid] = JobGia(jid, status="error", error="may B khong tra loi")
    may.dat(_chu("Xin loi, khong ve duoc anh."))
    gen, db = _phien_db()
    try:
        monkeypatch.setattr(
            luot_v3, "chay_tiep_nen",
            lambda run_id, *, user_id: luot_v3.tiep_sau_duyet(
                db, run_id=run_id, user_id=user_id, so=SoGia()))
        TM.dong_bo(db, user_id=uid, execution_id=ex_job)
        db.expire_all()
        assert db.get(ChatlttRun, rid).trang_thai == "COMPLETED"
    finally:
        _dong(gen)
    assert "khong ve duoc" in str(_khoi(mid))


def test_job_hong_thi_tien_HOAN_het(web, may, bat_co, kho_job, monkeypatch):
    from apps.chatltt.services import luot_v3, tao_media as TM
    from apps.chatltt.tables import ChatlttExecution

    uid, _rid, jid, ex_job, _mid = _cho_job(web, may)
    kho_job[jid] = JobGia(jid, status="error", error="vo")
    may.dat(_chu("khong ve duoc"))
    gen, db = _phien_db()
    try:
        monkeypatch.setattr(luot_v3, "chay_tiep_nen",
                            lambda run_id, *, user_id: None)
        TM.dong_bo(db, user_id=uid, execution_id=ex_job)
        db.expire_all()
        ex = db.get(ChatlttExecution, ex_job)
        assert ex.credit_thu == 0 and ex.credit_hoan == ex.credit_giu
    finally:
        _dong(gen)


def test_danh_thuc_VO_thi_dong_bo_van_tra_tien_do(web, may, bat_co, kho_job,
                                                  monkeypatch):
    """⛔ Job ĐÃ xong và tiền ĐÃ quyết toán. Biến một lần đánh thức hỏng thành
    lỗi của `dong_bo` là làm hỏng cả việc **đọc tiến độ** — thứ duy nhất đang
    hoạt động."""
    from apps.chatltt.services import luot_v3, tao_media as TM

    uid, _rid, jid, ex_job, _mid = _cho_job(web, may)
    kho_job[jid] = JobGia(jid, status="done", result={"image_keys": ["a"]})

    def no(*_a, **_k):
        raise RuntimeError("luong nen khong len duoc")

    gen, db = _phien_db()
    try:
        monkeypatch.setattr(luot_v3, "nen_chay_tiep", no)
        r = TM.dong_bo(db, user_id=uid, execution_id=ex_job)
        assert r["status"] == "done"
    finally:
        _dong(gen)


# ── 6. `con_cho_job` — một job xong KHÔNG phải là xong ─────────────────────

def test_con_cho_job_dung_khi_job_chua_xong(web, may, bat_co, kho_job):
    from apps.chatltt.services import luot_v3

    uid, rid, jid, _ex, _mid = _cho_job(web, may)
    kho_job[jid] = JobGia(jid, status="running", progress=40)
    gen, db = _phien_db()
    try:
        assert luot_v3.con_cho_job(db, user_id=uid, run_id=rid) is True
        assert luot_v3.nen_chay_tiep(db, user_id=uid, run_id=rid) is False
    finally:
        _dong(gen)


def test_job_xong_thi_KHONG_con_cho_va_nen_chay_tiep(web, may, bat_co, kho_job):
    from apps.chatltt.services import luot_v3

    uid, rid, jid, _ex, _mid = _cho_job(web, may)
    kho_job[jid] = JobGia(jid, status="done", result={"image_keys": ["a"]})
    gen, db = _phien_db()
    try:
        assert luot_v3.con_cho_job(db, user_id=uid, run_id=rid) is False
        assert luot_v3.nen_chay_tiep(db, user_id=uid, run_id=rid) is True
    finally:
        _dong(gen)


def test_job_BIEN_MAT_khong_lam_run_ket_vinh_vien(web, may, bat_co, kho_job):
    """`get_owned` trả `None` (job bị dọn, hoặc của người khác) ⇒ không được
    coi là "đang chờ" mãi mãi — `ket_qua_job` sẽ nói `job_bien_mat` cho model."""
    from apps.chatltt.services import luot_v3

    uid, rid, _jid, _ex, _mid = _cho_job(web, may)
    gen, db = _phien_db()
    try:
        assert luot_v3.con_cho_job(db, user_id=uid, run_id=rid) is False
    finally:
        _dong(gen)


def test_nguoi_KHAC_khong_thay_buoc_cho_job(web, may, bat_co, kho_job):
    """⛔ ĐỐI CHỨNG DƯƠNG NẰM TRONG CÙNG PHÉP KIỂM, không ở hàm khác.

    Một phép kiểm chỉ khẳng định `is False` cho người lạ **vẫn xanh** khi
    `con_cho_job` hỏng và luôn trả `False` — nó không phân biệt được *"chặn
    đúng người lạ"* với *"chặn tất cả"*. Đối chứng có tồn tại ở một hàm khác,
    nhưng xoá hàm ấy thì phép kiểm này thành rỗng mà không ai biết.

    ⭐ Luật do phiên Mobile V1 nêu 06/09 sau khi một kết quả âm của họ —
    "cảm ứng không pan được" trên một canvas **rỗng** — suýt thành một phát
    hiện: trước khi ghi một kết quả âm, hỏi *điều kiện nào đáng lẽ phải cho
    kết quả DƯƠNG ở đây*, rồi chạy đúng điều kiện đó.
    """
    from apps.chatltt.services import luot_v3

    uid, rid, jid, _ex, _mid = _cho_job(web, may)
    kho_job[jid] = JobGia(jid, status="running")
    gen, db = _phien_db()
    try:
        # DƯƠNG: chủ sở hữu THẤY bước đang chờ.
        assert luot_v3.con_cho_job(db, user_id=uid, run_id=rid) is True
        # ÂM: người lạ không thấy gì.
        assert luot_v3.con_cho_job(db, user_id="u-nguoi-la", run_id=rid) is False
        assert luot_v3.nen_chay_tiep(db, user_id="u-nguoi-la", run_id=rid) is False
    finally:
        _dong(gen)
