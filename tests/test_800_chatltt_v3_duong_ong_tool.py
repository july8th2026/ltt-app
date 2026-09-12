"""
test_800 — CỔNG ĐƯỜNG ỐNG TOOL của ChatLTT V3. (H44 P01, cổng cuối)

`01_CONG0_KET_QUA.md` và `01_LO_CHINH_KET_QUA.md` đã chứng minh **máy B** làm
đúng: 532 lượt, 9/9 chỉ số PASS, injection 0/30. Nhưng cả hai lô đó gọi thẳng
`llama-swap`, **không đi qua ngăn xếp LTT**. Nên chúng không nói gì về câu hỏi
còn lại, và câu đó mới là câu chặn P03:

    `tools` co di duoc tu ChatLTT xuong may B khong,
    va `tool_calls` co di nguoc len duoc khong?

⛔ Không dùng máy B, không dùng credit thật, không cần đăng nhập: `luong_vlm.mo`
   bị thay bằng một luồng SSE giả, đúng khuôn `test_600`.

## Sáu tính chất neo ở đây

  1. `tools` trong `params` **tới nguyên vẹn** thân gửi lên máy B.
  2. `parallel_tool_calls` cũng vậy — [U] llama.cpp tắt nó mặc định.
  3. `delta.tool_calls` → sự kiện `tool_call.delta`.
  4. Đối số bị cắt mảnh qua nhiều chunk → **nhiều** sự kiện, mỗi mảnh một cái.
  5. Khối `tools` **được tính** vào ước token ⇒ giữ chỗ nhiều hơn.
  6. 🔴 `su_kien.ap_dung` hiện **VỨT** nội dung `tool_call.delta` — đây là
     khoảng trống P03 phải lấp, và test này ghim nó lại để việc lấp là **cố ý**.
"""
from __future__ import annotations

import json
import uuid

import pytest

#: 🔴 BÍ DANH CỦA TOOL THỬ PHẢI LÀ MỘT MODEL **CÓ GIÁ** (D07, dual-model 2.5).
#:    Trước 2.5 chỗ này là chuỗi bịa `_ALIAS_THU` và nó chạy được **chỉ vì**
#:    `gia_token` bỏ qua model. Từ D07 giá đi theo model, nên mọi tool đi qua
#:    `runtime_noi_bo/luong.py` — tức qua `thanh_toan` — phải khai một model mà
#:    bảng giá biết. Đây là ràng buộc thật của tầng đó, không phải phiền toái
#:    của phép kiểm: một model không có giá mà vẫn giữ được tiền nghĩa là tiền
#:    đang được tính bằng bảng giá của một model **khác**.
#:
#: ⛔ Lấy từ `gia_token`, đừng gõ thẳng `"ltt-3.8"`: ngày đổi model mặc định thì
#:    một hằng số gõ tay sẽ làm sáu tệp này hỏng lại cùng lúc.
from platform_core.llm.gia_token import MODEL_GIA_MAC_DINH as _ALIAS_THU

NL = bytes([10])
TOOL_THU = "text.thu800"
JOB_THU = "appthu800.luong"
SLUG_THU = "appthu800"

TOOLS_MAU = [{
    "type": "function",
    "function": {"name": "calculator",
                 "description": "Tinh mot bieu thuc so hoc.",
                 "parameters": {"type": "object",
                                "properties": {"expression": {"type": "string"}},
                                "required": ["expression"]}},
}]


class _ThamSoSai(ValueError):
    pass


class _ExecutorGia:
    parameter_error = _ThamSoSai

    @staticmethod
    def mac_dinh_cho(cua):
        return {"sync": 1024, "stream": 4096, "job": 4096}[cua]

    def aliases(self):
        return {_ALIAS_THU: "noi-bo-model-1"}

    def model_id(self, alias):
        return self.aliases()[alias]

    def validate(self, params):
        return dict(params)

    def estimate_input(self, messages, tools=None):
        # Cùng tinh thần `apps/ltt_llm`: khối `tools` KHÔNG miễn phí. `uoc_tin_nhan`
        # đã nhét nó vào danh sách dưới dạng một phần tử `{"content": <json>}`,
        # nên nó tới đây qua `messages` và được đếm như mọi phần tử khác.
        return sum(len(str(m.get("content", ""))) for m in messages) // 2 + 10

    def sync_output_cap(self, token_input, budget_seconds):
        return 1024

    def context_output_cap(self, token_input):
        return 40000


EXECUTOR_GIA = _ExecutorGia()


@pytest.fixture()
def moi_truong(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       "sqlite:///" + (tmp_path / "l800.db").as_posix())
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine
    Base.metadata.create_all(get_engine())
    yield
    dbmod.reset_engine()


@pytest.fixture()
def app_luong(monkeypatch, moi_truong):
    from platform_core import registry as reg

    manifest = reg.AppManifest(
        slug=SLUG_THU, display_name="App thu duong ong tool",
        route_prefix=f"/{SLUG_THU}",
        job_types=(JOB_THU,), credit_cost=lambda p: 1,
        enabled=True, public=False, surface="runtime", lifecycle="internal",
        tools=(reg.ToolSpec(
            name=TOOL_THU, job_type=JOB_THU, description="tool thu 800",
            params_schema={"messages": {"type": "json[]", "required": True},
                           "model": {"type": "enum", "values": [_ALIAS_THU],
                                     "default": _ALIAS_THU},
                           "tools": {"type": "json[]"}},
            returns={"content": "text", "tool_calls": "json[]"},
            admission_resource="thu_gpu800", admission_slots=1,
            sync_executor="tests.test_800_chatltt_v3_duong_ong_tool:EXECUTOR_GIA",
        ),),
    )
    loaded = reg.LoadedApp(manifest=manifest, router=None)
    goc = reg.discover

    def discover_kem(apps_dir=None):
        return list(goc() if apps_dir is None else goc(apps_dir)) + [loaded]

    monkeypatch.setattr(reg, "discover", discover_kem)
    return manifest


def _session():
    from platform_core.db import get_session
    gen = get_session()
    return gen, next(gen)


def _close(gen):
    try:
        next(gen)
    except StopIteration:
        pass


def _user(credits=10_000):
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung
    gen, db = _session()
    try:
        u = tao_nguoi_dung(db, email="t800-" + uuid.uuid4().hex[:8] + "@example.com",
                           password="a-good-password-12")
        db.flush()
        if credits:
            credit.cap_tay(db, u.id, credits, by="test")
        db.commit()
        return u.id
    finally:
        _close(gen)


def _sse(goi):
    return b"data: " + json.dumps(goi).encode() + NL + NL


def _khoi_tool(manh: bool = False):
    """Luồng SSE giả có `tool_calls`. `manh=True` ⇒ đối số cắt làm ba chunk."""
    ds = []
    if manh:
        # ⭐ Đúng hình dạng llama-server phát thật: chunk đầu mang `id`+`name`,
        #    các chunk sau chỉ nối thêm `arguments`. Không gộp lại thì đối số là
        #    ba mảnh JSON vô nghĩa.
        ds.append(_sse({"choices": [{"delta": {"tool_calls": [
            {"index": 0, "id": "call_1", "type": "function",
             "function": {"name": "calculator", "arguments": ""}}]}}]}))
        for phan in ('{"expres', 'sion": "8123', ' * 4471"}'):
            ds.append(_sse({"choices": [{"delta": {"tool_calls": [
                {"index": 0, "function": {"arguments": phan}}]}}]}))
    else:
        ds.append(_sse({"choices": [{"delta": {"tool_calls": [
            {"index": 0, "id": "call_1", "type": "function",
             "function": {"name": "calculator",
                          "arguments": '{"expression": "8123 * 4471"}'}}]}}]}))
    ds.append(_sse({"choices": [{"delta": {}, "finish_reason": "tool_calls"}]}))
    ds.append(_sse({"choices": [], "usage": {"prompt_tokens": 100,
                                             "completion_tokens": 20}}))
    ds.append(b"data: [DONE]" + NL + NL)
    return ds


def _dat_luong(monkeypatch, khoi):
    from platform_core.llm import luong_vlm
    da_goi = []

    class Gia:
        def __init__(self, ks):
            self.ma = 200
            self.content_type = "text/event-stream"
            self.luong = iter(ks)

        def xong(self, tokens=0):
            pass

        def hong(self, exc):
            pass

    def mo(db, *, duong, than, timeout_s=900.0):
        da_goi.append({"duong": duong, "than": than})
        return Gia(khoi)

    monkeypatch.setattr(luong_vlm, "mo", mo)
    return da_goi


def _chay(user_id, params, **kw):
    from platform_core.runtime_noi_bo import luong
    gen, db = _session()
    try:
        return list(luong.mo_luong(db, user_id=user_id, tool_name=TOOL_THU,
                                   params=params, **kw))
    finally:
        _close(gen)


def _params(**g):
    d = {"model": _ALIAS_THU,
         "messages": [{"role": "user", "content": "tinh 8123 * 4471 giup toi"}]}
    d.update(g)
    return d


# ── 1+2. `tools` và `parallel_tool_calls` tới được máy B ────────────────────

def test_tools_di_nguyen_ven_toi_than_gui_len(app_luong, monkeypatch):
    """⛔ Nếu phép kiểm này đỏ thì V3 hỏng ở mắt xích ĐẦU TIÊN: model không bao
    giờ biết nó có tool nào, và mọi con số của lô đo máy B thành vô nghĩa."""
    da_goi = _dat_luong(monkeypatch, _khoi_tool())
    u = _user()
    _chay(u, _params(tools=TOOLS_MAU))

    assert len(da_goi) == 1
    than = da_goi[0]["than"]
    assert than["tools"] == TOOLS_MAU, "khoi `tools` phai toi nguyen xi"
    # Alias phải đã đổi thành id nội bộ TRƯỚC khi rời nền tảng (test_212).
    assert than["model"] == "noi-bo-model-1"


def test_parallel_tool_calls_di_toi_noi(app_luong, monkeypatch):
    """[U] `docs/function-calling.md:24` — llama.cpp TẮT gọi song song mặc định.

    Không gửi cờ thì năng lực ấy tắt ở tầng runtime, và đo bao nhiêu lượt cũng
    chỉ đo một thứ đã tắt sẵn.
    """
    da_goi = _dat_luong(monkeypatch, _khoi_tool())
    u = _user()
    _chay(u, _params(tools=TOOLS_MAU, parallel_tool_calls=True))
    assert da_goi[0]["than"]["parallel_tool_calls"] is True


# ── 3+4. `tool_calls` đi ngược lên thành sự kiện ────────────────────────────

def test_tool_calls_thanh_su_kien_tool_call_delta(app_luong, monkeypatch):
    _dat_luong(monkeypatch, _khoi_tool())
    u = _user()
    sk = _chay(u, _params(tools=TOOLS_MAU))

    goi = [s for s in sk if s["type"] == "tool_call.delta"]
    assert len(goi) == 1
    tc = goi[0]["tool_calls"][0]
    assert tc["function"]["name"] == "calculator"
    assert json.loads(tc["function"]["arguments"])["expression"] == "8123 * 4471"
    # `finish_reason` phải nói đúng là lượt dừng vì tool, không phải vì hết chữ.
    xong = [s for s in sk if s["type"] == "response.completed"]
    assert xong and xong[0]["finish_reason"] == "tool_calls"


def test_doi_so_cat_manh_ra_NHIEU_su_kien_runtime_KHONG_gop(app_luong, monkeypatch):
    """🔴 Runtime **không** gộp mảnh, và đó là đúng phân vai — nhưng phải ghim.

    `luong.py:475-477` phát mỗi mảnh thành một sự kiện. Gộp lại là việc của
    ChatLTT (P03). Ghim ở đây để P03 không giả định nhầm rằng runtime đã gộp
    hộ — một giả định như vậy chỉ lộ ra khi đối số dài, tức ở đúng ca khó.
    """
    _dat_luong(monkeypatch, _khoi_tool(manh=True))
    u = _user()
    sk = _chay(u, _params(tools=TOOLS_MAU))

    goi = [s for s in sk if s["type"] == "tool_call.delta"]
    assert len(goi) == 4, "mot chunk mot su kien, runtime khong gop"

    noi = "".join((s["tool_calls"][0].get("function") or {}).get("arguments") or ""
                  for s in goi)
    assert json.loads(noi)["expression"] == "8123 * 4471", \
        "gop lai phai ra JSON hop le — neu khong thi mat mot mieng doi so"


# ── 5. Khối `tools` không miễn phí ──────────────────────────────────────────

def test_khoi_tools_duoc_tinh_vao_uoc_token(app_luong, monkeypatch):
    """`luong.py:123-125`: định nghĩa tool đi kèm MỖI lượt và không hề nhỏ.

    Không đếm nó là ước thiếu — và với V3, `tools` có mặt ở **mọi** lượt gọi.
    """
    from platform_core.runtime_noi_bo import luong

    khong = luong.uoc_tin_nhan(_params())
    co = luong.uoc_tin_nhan(_params(tools=TOOLS_MAU))
    assert len(co) == len(khong) + 1, "khoi `tools` phai thanh mot phan tu de dem"
    them = [m for m in co if m not in khong][0]
    assert "calculator" in them["content"]


def test_co_tools_thi_giu_cho_NHIEU_HON(app_luong, monkeypatch):
    """Hệ quả tiền của phép kiểm trên, đo bằng `credit_giu` thật."""
    _dat_luong(monkeypatch, _khoi_tool())
    u1, u2 = _user(), _user()
    a = _chay(u1, _params())[0]
    b = _chay(u2, _params(tools=TOOLS_MAU))[0]
    assert a["type"] == b["type"] == "response.started"
    assert b["credit_giu"] >= a["credit_giu"]


# ── 6. 🔴 KHOẢNG TRỐNG mà P03 phải lấp ──────────────────────────────────────

def test_hien_tai_su_kien_tool_call_delta_KHONG_duoc_luu(moi_truong):
    """🔴 GHIM MỘT KHOẢNG TRỐNG, KHÔNG PHẢI GHIM MỘT HÀNH VI ĐÚNG.

    `apps/chatltt/services/su_kien.py:72-73` nhận `tool_call.delta` rồi `pass`:
    tăng `seq`, **không giữ nội dung**. Ống thông ở tầng runtime (năm phép kiểm
    trên) nhưng **bịt ở tầng ChatLTT**.

    ⛔ Phép kiểm này sẽ ĐỎ khi P03 làm đúng việc của nó. Đó là chủ ý: nó buộc
       việc lấp khoảng trống thành một hành động **cố ý và được ghi lại**, thay
       vì một thay đổi lặng lẽ mà không ai đối chiếu lại với đặc tả.

    Khi P03 lấp: đổi phép kiểm này thành phép kiểm nội dung ĐÃ được giữ, và ghi
    trong commit rằng nó thay thế đúng dòng này.
    """
    from apps.chatltt.services import su_kien as S
    from apps.chatltt.tables import ChatlttExecution

    ex = ChatlttExecution(message_id="msg_x", conversation_id="cv_x",
                          user_id="u_x", tool_name="text.chat", mode="stream")
    ex.seq = 0
    ex.partial_text = ""
    ex.reasoning_text = ""
    ex.usage = {}

    ket = S.ap_dung(ex, {"type": "tool_call.delta", "tool_calls": [
        {"index": 0, "id": "call_1", "type": "function",
         "function": {"name": "calculator", "arguments": '{"expression": "1+1"}'}}]})

    assert ket is False, "tool_call.delta khong phai su kien ket thuc"
    assert ex.seq == 1, "seq VAN tang — client noi lai dem duoc"
    assert ex.partial_text == "", "khong lan sang van ban tra loi"
    assert not hasattr(ex, "tool_calls"), \
        ("HIEN TAI khong co cho luu tool_calls. Neu dong nay do, P03 da lap "
         "khoang trong — hay cap nhat phep kiem nay CO Y, dung xoa no.")
