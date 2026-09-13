"""test_987 — tiền KHÔNG được kẹt khi khách ngắt TRƯỚC byte đầu tiên.

Dải **980–989** của chương trình MASTER UPGRADE (`docs/LLM_UPGRADE_MASTER_PLAN.md`).

═══════════════════════════════════════════════════════════════════════════
 CÙNG MỘT KHUYẾT TẬT, HỌC MỘT LẦN, ÁP THIẾU MỘT TẦNG
═══════════════════════════════════════════════════════════════════════════

Máy B, sự cố **31/08**: `boc_luong` trả **suất** trong `finally`. Generator không
khởi động ⇒ khối `try` chưa từng được vào ⇒ `finally` không chạy ⇒ suất bị giữ
vĩnh viễn ⇒ cổng trả 429 suốt sáu giờ trong khi GPU rảnh. Bản vá ở đó là
`BackgroundTask` — *"chạy khi PHẢN HỒI kết thúc, kể cả khi thân chưa từng được
đọc"*.

Máy A học đúng bài đó cho **suất** (`admission.release_by_id` đi qua
`BackgroundTask` ở `server/api/streaming.py`) — nhưng **không** cho **tiền**.
Quyết toán vẫn nằm trong `finally` của generator `_phat`.

🔴 ĐO THẬT 09/09, KHÔNG PHẢI SUY LUẬN:

```
g = _phat(mo, luot); g.close()      -> quyet_toan KHONG duoc goi
next(g); g.close()                  -> quyet_toan DUOC goi
```

⇒ Khách ngắt trước byte đầu ⇒ khoản `hold` nằm lại **tới 24 giờ** (xem §đính
  chính bên dưới).

⚠️ NÓI ĐÚNG MỨC ĐỘ — BẢN ĐẦU CỦA TỆP NÀY NÓI QUÁ, VÀ ĐÃ ĐÍNH CHÍNH.

   Tôi viết *"nằm lại vĩnh viễn, không bộ quét nào thấy"*. Sai. Đọc kỹ
   `credit.tu_hoan_treo` (H41.3): cửa stream truyền `request_id` làm
   `job_id`, và không hàng `Job` nào **đang sống** mang khoá đó, nên sau
   `TU_HOAN_SAU = 24 giờ` khoản ấy **được hoàn** (trần 20 mỗi lượt bảo trì).

   ⇒ Hại thật: **tiền khách bị giữ tới một ngày cho một lượt không chạy**,
     không phải mất tiền. Vẫn đáng sửa — lưới mới biến 24 giờ thành **tức
     thì**, và quyết toán theo **số đo được** thay vì chờ một bộ quét.

   ⭐ Đáng ghi vì cách tôi biết mình sai: chính `test_363` — phép kiểm mà bản
     vá của tôi làm đỏ — mang câu *"tiền treo được `credit.tu_hoan_treo`
     quét (H41.3)"* trong docstring. Bánh cóc tôi phá cũng là thứ sửa tôi.

⭐ NHƯNG `test_292` CÒN VIẾT THÊM MỘT CÂU, VÀ CÂU ĐÓ SAI:

       "ĐỐI CHIẾU: cửa streaming không dính, vì nó quyết toán trong `finally`."

   Nó đúng cho ca generator **đã chạy** và sai cho ca generator **chưa chạy** —
   mà ca chưa chạy chính là ca `boc_luong` đã trả giá để học ở tầng dưới. Một
   lời trấn an trong tài liệu, đúng một nửa, sống tiếp vì không ai đo nửa kia.

═══════════════════════════════════════════════════════════════════════════
 BẢN VÁ: HAI ĐƯỜNG ĐỘC LẬP CHO CÙNG MỘT VIỆC
═══════════════════════════════════════════════════════════════════════════

  đường 1  `finally` của `_phat`            — khi luồng có chảy
  đường 2  `dam_bao_quyet_toan(luot)` gọi từ `BackgroundTask` của phản hồi

`luot.da_quyet_toan` bảo đảm **chỉ một** đường thật sự thu. Đây đúng khuôn máy B
đã dùng (`Suat.tra()` + `dong()` idempotent, hai đường cộng thêm chứ không thay
thế nhau).
"""
from __future__ import annotations

import ast
import pathlib
import types

import pytest

import platform_core.runtime_noi_bo.luong as L

GOC = pathlib.Path(__file__).resolve().parents[1]
STREAMING = GOC / "server" / "api" / "streaming.py"


class _Mo:
    content_type = "text/event-stream"

    def __init__(self):
        self.luong = iter([b"data: x\n\n"])

    def xong(self, **k):
        pass

    def hong(self, e):
        pass


def _cb():
    # ⚠️ HAI TRƯỜNG DƯỚI THÊM 12/09 (dual-model): `ChuanBi` thật nay mang
    #    `la_whale` + `waiter_id` (sổ từng lượt của phòng chờ, multijob D-03) và
    #    `model_alias` (quyết toán theo GIÁ CỦA MODEL đã phục vụ, D07). Bản giả
    #    thiếu chúng thì `_phat` nổ `AttributeError` giữa luồng — tức phép kiểm
    #    đo một đường mà production không còn đi.
    #
    # ⛔ Đừng để `model_alias` là chuỗi bịa: từ D07 `quyet_toan` tra bảng giá
    #    theo tên này, và một tên không có giá làm tiền được tính bằng bảng của
    #    model khác.
    from platform_core.llm.gia_token import MODEL_GIA_MAC_DINH

    return types.SimpleNamespace(user_id="u", request_id="rid-12345678",
                                 da_giu=10, lease_id="", duong="/v1/messages",
                                 la_whale=False, model_alias=MODEL_GIA_MAC_DINH,
                                 waiter_id="")


@pytest.fixture
def bat_quyet_toan(monkeypatch):
    goi: list = []
    monkeypatch.setattr(L, "quyet_toan",
                        lambda *a, **k: goi.append(a[1]) or "ket_qua")
    return goi


# ── Khuyết tật ─────────────────────────────────────────────────────────────

def test_generator_CHUA_TUNG_chay_thi_finally_KHONG_chay(bat_quyet_toan):
    """Đây là mệnh đề cả bản vá đứng lên. Đo, đừng tin trí nhớ.

    ⛔ Nếu ngày nào đó Python đổi ngữ nghĩa này (hoặc `_phat` thôi là generator)
       thì phép kiểm này đỏ, và người sửa sẽ biết lưới an toàn có thể đã thừa —
       chứ không im lặng giữ một lớp không còn lý do.
    """
    luot = L.LuotLuong(chuan_bi=_cb(), content_type="t")
    g = L._phat(_Mo(), luot)
    g.close()
    assert bat_quyet_toan == [], (
        "finally CO chay du generator chua khoi dong — menh de goc da doi")
    assert luot.da_quyet_toan is False


def test_luoi_an_toan_thu_duoc_ca_do(bat_quyet_toan):
    """Và lưới an toàn bịt đúng ca đó."""
    luot = L.LuotLuong(chuan_bi=_cb(), content_type="t")
    L._phat(_Mo(), luot).close()
    L.dam_bao_quyet_toan(luot)
    assert bat_quyet_toan == ["rid-12345678"]
    assert luot.da_quyet_toan is True
    assert luot.ket_thuc == "khach_ngat_truoc_byte_dau", (
        "phai noi ro ca nay khac 'khach_ngat' thuong — nguoi truc can phan biet")


# ── Không được thu hai lần ─────────────────────────────────────────────────

def test_luong_DA_chay_thi_luoi_KHONG_thu_lan_hai(bat_quyet_toan):
    """💰 Vế nguy hiểm nhất của bất kỳ 'lưới an toàn' nào: nó thu thêm một lần.

    Ở đây đường 1 đã thu; đường 2 phải im lặng.
    """
    luot = L.LuotLuong(chuan_bi=_cb(), content_type="t")
    g = L._phat(_Mo(), luot)
    next(g)
    g.close()
    assert len(bat_quyet_toan) == 1
    L.dam_bao_quyet_toan(luot)
    assert len(bat_quyet_toan) == 1, "THU HAI LAN — khach bi tinh tien gap doi"


def test_goi_luoi_nhieu_lan_van_chi_thu_mot(bat_quyet_toan):
    luot = L.LuotLuong(chuan_bi=_cb(), content_type="t")
    for _ in range(4):
        L.dam_bao_quyet_toan(luot)
    assert len(bat_quyet_toan) == 1


def test_luong_chay_HET_binh_thuong_van_chi_thu_mot(bat_quyet_toan):
    luot = L.LuotLuong(chuan_bi=_cb(), content_type="t")
    list(L._phat(_Mo(), luot))
    L.dam_bao_quyet_toan(luot)
    assert len(bat_quyet_toan) == 1


# ── Đường thứ hai phải thật sự được nối vào phản hồi ───────────────────────

def test_streaming_py_noi_luoi_vao_BackgroundTask():
    """⛔ Một lưới an toàn không được gọi thì không phải một lưới an toàn.

    Bộ nhớ dự án có nguyên một mục cho lớp lỗi này: *"năng lực có, không ai đi
    trên đường"*. Nên chốt cả việc **nối dây**, không chỉ việc **tồn tại**.
    """
    van = STREAMING.read_text(encoding="utf-8")
    assert "dam_bao_quyet_toan" in van, (
        "server/api/streaming.py khong goi dam_bao_quyet_toan -> luoi khong duoc noi")
    assert "BackgroundTask(_ket_thuc_che_chan)" in van, (
        "luoi quyet toan khong con duoc noi vao BackgroundTask")

    # 🔴 Va CHE CHAN phai la that. `starlette/background.py` (1.3.1) KHONG boc
    #    `CancelScope(shield=True)`, nen khi cancel scope bao quanh da bi huy —
    #    dung canh `Kludex/starlette#1438` mo ta, va ta co BON tang
    #    `BaseHTTPMiddleware` — thi `await run_in_threadpool(...)` vo o checkpoint
    #    dau, `_ket_thuc` khong chay MOT DONG: tien chua quyet toan, suat chua nha.
    #
    # ⛔ Khong chot dong nay thi mot ban "don dep" go `shield` di se XANH, va ta
    #    mat luoi ma khong ai bao.
    cay = ast.parse(van)
    che = next((n for n in ast.walk(cay)
                if isinstance(n, ast.AsyncFunctionDef)
                and n.name == "_ket_thuc_che_chan"), None)
    assert che is not None, "`_ket_thuc_che_chan` bien mat"

    # ⛔ ĐỌC CẤU TRÚC, KHÔNG ĐỌC VĂN BẢN. Ban dau ve nay viet
    #     assert "shield" in ast.dump(che)
    #    va no XANH ngay ca khi da go `shield` khoi ma — vi `ast.dump` keo theo
    #    ca DOCSTRING, ma docstring co chu "shield". Phep kiem khop voi LOI GIAI
    #    THICH thay vi khop voi HANH VI. Doi chung bat duoc no, khong phai toi.
    co_shield = any(
        isinstance(muc.context_expr, ast.Call)
        and getattr(muc.context_expr.func, "attr", "") == "CancelScope"
        and any(kw.arg == "shield"
                and isinstance(kw.value, ast.Constant) and kw.value.value is True
                for kw in muc.context_expr.keywords)
        for nut in ast.walk(che) if isinstance(nut, (ast.With, ast.AsyncWith))
        for muc in nut.items)
    assert co_shield, (
        "`_ket_thuc_che_chan` khong con `anyio.CancelScope(shield=True)` — "
        "BackgroundTask lai co the bi huy TRUOC khi chay, va suat khong duoc nha.")

    # ⚠️ `_ket_thuc` duoc TRUYEN vao `run_in_threadpool`, khong duoc GOI thang —
    #    nen tim no trong cac `Call.func` la tim sai cho (ban dau toi tim sai, va
    #    ve nay do ngay ca khi ma dung). Tim mot tham chieu ten la du va dung.
    ten = {n.id for n in ast.walk(che) if isinstance(n, ast.Name)}
    assert "_ket_thuc" in ten, (
        "ham che chan khong con nhac toi `_ket_thuc` — che chan mot thu khac thi "
        "tien van chua quyet toan va suat van chua nha.")


def test_luoi_chay_TRUOC_viec_nha_suat_va_nha_suat_luon_chay():
    """Thứ tự và bảo đảm, đọc bằng AST.

    Nhả suất nằm trong `finally` để một ngoại lệ ở đường tiền **không** làm kẹt
    suất — nếu không, một lỗi tiền sẽ đẻ thêm đúng sự cố 31/08.
    """
    cay = ast.parse(STREAMING.read_text(encoding="utf-8"))
    ham = next((n for n in ast.walk(cay)
                if isinstance(n, ast.FunctionDef) and n.name == "_ket_thuc"), None)
    assert ham is not None, "khong tim thay `_ket_thuc`"
    thu = ham.body[0]
    assert isinstance(thu, ast.Try), "`_ket_thuc` phai la try/finally"
    assert "dam_bao_quyet_toan" in ast.dump(ast.Module(body=thu.body, type_ignores=[]))
    assert "release_by_id" in ast.dump(
        ast.Module(body=thu.finalbody, type_ignores=[])), (
        "nha suat phai nam trong `finally` — mot loi o duong tien khong duoc "
        "lam ket suat (do dung la su co 31/08)")


def test_duong_thu_nhat_van_con():
    """Lưới an toàn **cộng thêm**, không thay thế `finally`.

    Bỏ `finally` đi và chỉ dựa vào `BackgroundTask` là đổi hai đường độc lập lấy
    một đường — đúng thứ máy B đã cố ý không làm.
    """
    van = (GOC / "platform_core" / "runtime_noi_bo" / "luong.py").read_text(
        encoding="utf-8")
    cay = ast.parse(van)
    ham = next(n for n in ast.walk(cay)
               if isinstance(n, ast.FunctionDef) and n.name == "_phat")
    co_finally = [n for n in ast.walk(ham)
                  if isinstance(n, ast.Try) and n.finalbody
                  and "quyet_toan" in ast.dump(
                      ast.Module(body=n.finalbody, type_ignores=[]))]
    assert co_finally, "`_phat` khong con quyet toan trong `finally`"
