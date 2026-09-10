r"""HỒ SƠ TỐC ĐỌC THEO TỪNG GIỌNG — và ràng buộc TIỀN đi kèm nó.

## Vì sao có tệp này (U-01 của `VIRAL_VOICE_AUDIT_2026-09-07.md`)

`gia.py` ước thời lượng bằng **một** cặp hằng số cho **cả kho giọng**, và chú
thích của chính nó nói ra giới hạn: *"Số đo là của MỘT bộ giọng trên MỘT card."*

Một hệ khác giữ bảng tương đương cho 61 giọng (`D:\Viral::TOC_DOC`) và chênh
lệch giữa hai giọng **cùng ngôn ngữ** lên tới **43 %**.

## ⛔ RÀNG BUỘC KHÔNG ĐƯỢC PHÉP VỠ

Con số này giữ chỗ credit. `gia.py` ghi rõ: *"giữ thiếu thì khách tiêu quá số
dư — một lỗi sổ sách, không phải một lỗi hiển thị."*

⇒ Bất biến trung tâm của tệp này: **`uoc_tran(...)` LUÔN >= `tinh(giay_thật)`**,
  với mọi giọng, có hồ sơ hay không.
"""
from __future__ import annotations

import json
import pathlib
import re

import pytest

from apps.ltt_voice import gia, ho_so_giong

GOC = pathlib.Path(__file__).resolve().parents[1]


# ── 1. Ảnh chụp: hình dạng, và "rỗng" là hợp lệ ────────────────────────────

def test_anh_chup_ton_tai_va_la_JSON_hop_le():
    d = json.loads(ho_so_giong.ANH_CHUP.read_text(encoding="utf-8"))
    assert isinstance(d.get("giong"), dict), "thieu map `giong`"


def test_anh_chup_RONG_van_dung_duoc():
    """⛔ Một kho chưa từng chạy phép đo vẫn phải bán được hàng.

    Đây không phải một khoảng trống chờ lấp — nó là trạng thái khởi đầu hợp lệ,
    và mọi giọng lùi về hai hằng số chung.
    """
    assert ho_so_giong.tra("KhongTonTai") is None
    assert ho_so_giong.ky_tu_moi_giay_an_toan("KhongTonTai") is None
    assert gia.giay_uoc(1000, "KhongTonTai") == gia.giay_uoc(1000)


def test_thieu_tep_KHONG_nem(monkeypatch, tmp_path):
    monkeypatch.setattr(ho_so_giong, "ANH_CHUP", tmp_path / "khong-co.json")
    assert ho_so_giong.phien_ban() == ""


# ── 2. 🔴 Bất biến TIỀN: ước luôn >= giá thật ──────────────────────────────

def _ho_so_gia(monkeypatch, ten, toc_do, sd=0.0, khoi_dong=1.0, so_luot=3):
    monkeypatch.setattr(ho_so_giong, "DANH_SACH", {ten: {
        "ky_tu_moi_giay": toc_do, "do_lech_chuan": sd,
        "giay_khoi_dong": khoi_dong, "so_luot": so_luot}})


@pytest.mark.parametrize("n", [1, 47, 143, 500, 1500, 3000, 100_000])
def test_uoc_tran_luon_LON_HON_gia_that_khi_KHONG_co_ho_so(n):
    """Đường lùi — hành vi y hệt trước 08/09."""
    giay_that = gia.GIAY_KHOI_DONG_UOC + n / 21.16      # mo hinh do 01/09
    assert gia.uoc_tran(so_ky_tu=n) >= gia.tinh(giay_that)


@pytest.mark.parametrize("n", [1, 47, 500, 1500, 100_000])
def test_uoc_tran_luon_LON_HON_gia_that_khi_CO_ho_so(monkeypatch, n):
    """🔴 Bất biến trung tâm. Một giọng đo được 21,0 ký tự/giây với σ = 0,5 thì
    cận dưới là 20,0 — ước **thừa**, và phần thừa hoàn ngay khi job xong."""
    _ho_so_gia(monkeypatch, "G", toc_do=21.0, sd=0.5, khoi_dong=1.2)
    giay_that = 1.2 + n / 21.0
    assert gia.uoc_tran(so_ky_tu=n, giong="G") >= gia.tinh(giay_that)


def test_giong_CHAM_duoc_uoc_NHIEU_giay_hon_giong_nhanh(monkeypatch):
    """Đây là toàn bộ lý do U-01 tồn tại: một hằng số phẳng không phân biệt được."""
    monkeypatch.setattr(ho_so_giong, "DANH_SACH", {
        "Nhanh": {"ky_tu_moi_giay": 25.0, "do_lech_chuan": 0.2,
                  "giay_khoi_dong": 1.0, "so_luot": 3},
        "Cham":  {"ky_tu_moi_giay": 14.0, "do_lech_chuan": 0.2,
                  "giay_khoi_dong": 1.0, "so_luot": 3},
    })
    assert gia.giay_uoc(3000, "Cham") > gia.giay_uoc(3000, "Nhanh") * 1.5


# ── 3. Cận dưới, và ba cách nó có thể sai ──────────────────────────────────

def test_tra_can_DUOI_khong_tra_trung_binh(monkeypatch):
    _ho_so_gia(monkeypatch, "G", toc_do=20.0, sd=1.0)
    assert ho_so_giong.ky_tu_moi_giay_an_toan("G") == pytest.approx(18.0)


def test_sigma_lon_bat_thuong_KHONG_cho_ra_con_so_phi_ly(monkeypatch):
    """⛔ Một σ phồng (đo trên máy tải nặng) đẩy cận dưới xuống 0 hoặc âm, và
    phép chia ở `giay_uoc` sẽ nổ hoặc cho một con số khổng lồ.

    ⭐ Trả `None` là đúng: *"không tin được"* khác *"chậm vô hạn"*.
    """
    _ho_so_gia(monkeypatch, "G", toc_do=20.0, sd=15.0)
    assert ho_so_giong.ky_tu_moi_giay_an_toan("G") is None
    assert gia.giay_uoc(1000, "G") == gia.giay_uoc(1000)


def test_it_hon_ba_luot_thi_KHONG_TIN(monkeypatch):
    """Một lượt cho một con số, không cho một dải — và không có dải thì
    `do_lech_chuan` là một số bịa."""
    _ho_so_gia(monkeypatch, "G", toc_do=20.0, sd=0.5, so_luot=1)
    assert ho_so_giong.tra("G") is None


# ── 4. Nối vào đường báo giá — và KHÔNG được chạm CSDL ─────────────────────

def test_manifest_TRUYEN_preset_xuong_uoc_tran():
    """⛔ Không truyền thì cả cơ chế này chết im lặng: `gia.py` nhận tham số,
    `ho_so_giong` có dữ liệu, và không ai nối hai đầu.

    Đúng lớp lỗi `KetQua.canh_bao` đã mắc — một đường ống đủ khớp nối, không
    bao giờ có nước (xem `DECISIONS.md` DV-010).
    """
    import ast
    cay = ast.parse((GOC / "apps/ltt_voice/manifest.py").read_text(encoding="utf-8"))
    ham = next(n for n in ast.walk(cay)
               if isinstance(n, ast.FunctionDef) and n.name == "_gia")
    goi = [n for n in ast.walk(ham)
           if isinstance(n, ast.Call) and "uoc_tran" in ast.unparse(n.func)]
    assert goi, "_gia khong goi uoc_tran"
    assert any(k.arg == "giong" for g in goi for k in g.keywords), (
        "_gia goi uoc_tran ma KHONG truyen `giong` - ho so toc do se khong bao "
        "gio duoc dung")


def test_duong_bao_gia_KHONG_cham_CSDL_hay_MANG():
    """🔴 `manifest._gia()` chạy ở **mọi lượt báo giá**, và chú thích của chính
    nó cấm chạm CSDL/mạng. Đó là lý do hồ sơ là một **ảnh chụp JSON**, không
    phải một bảng.

    ⛔ Ngày ai đó "nâng cấp" nó thành một truy vấn, phép kiểm này đỏ.
    """
    src = (GOC / "apps/ltt_voice/ho_so_giong.py").read_text(encoding="utf-8")
    for cam in ("get_session", "sqlalchemy", "requests", "urllib", "httpx"):
        assert cam not in src, f"ho_so_giong cham `{cam}` - duong bao gia cam dieu do"


def test_doc_anh_chup_MOT_LAN_luc_import():
    """Đọc tệp ở **mỗi** lượt báo giá là một lượt I/O đĩa cho mỗi cú gõ phím
    của khách ở ô đếm ký tự."""
    assert isinstance(ho_so_giong.DANH_SACH, dict), (
        "DANH_SACH phai la du lieu da nap, khong phai mot ham")


# ── 5. Công cụ đo phải TỪ CHỐI chạy trên máy bận ───────────────────────────

def test_cong_cu_do_TU_CHOI_khi_may_ban():
    """⛔ σ đo trên máy tải nặng phồng lên, và con số ấy đi **thẳng vào phép
    giữ chỗ credit**. Không ai mất tiền (phần dư được hoàn), nhưng khách thấy
    số dư tụt sâu hơn thực tế — một trải nghiệm tệ sinh ra từ một phép đo cẩu thả.
    """
    src = (GOC / "tools/do_ho_so_giong.py").read_text(encoding="utf-8")
    assert "_may_ban" in src, "cong cu do khong kiem may ban"
    assert "Win32_Process" in src, (
        "phai hoi Win32_Process - `ps` cua Git Bash KHONG thay tien trinh Windows")
    assert "--bo-qua-kiem-may" in src, "phai co duong thoat co y thuc"


def test_cong_cu_do_DOI_it_nhat_hai_bac_do_dai():
    """Một bậc chỉ cho một điểm, và một điểm không dựng được đường thẳng —
    nên không tách được phí khởi động khỏi tốc độ đọc.

    🔴 CHỐT TÍNH CHẤT, KHÔNG CHỐT BIỂU DIỄN — và bản đầu chốt sai chỗ.

       Nó viết `len(BAC) >= 2`. Nhưng `BAC` chỉ giữ bậc **ngắn**; bậc **dài**
       dựng bằng `_van_ban_dai()` vì nó là một chuỗi lặp tới ~1.200 ký tự chứ
       không phải một hằng số gõ tay. Bản đầu của `BAC` có một dòng
       `("dai", None)` **chỉ để ghi chú** điều đó — và cái `None` ấy làm kiểu
       của cả bảng thành `str | None`, khiến mypy bắt `len(t)` ở vòng đo.

       Gỡ dòng ghi chú ⇒ `len(BAC)` còn 1 ⇒ phép kiểm đỏ, trong khi **công cụ
       vẫn đo đúng hai bậc**. Tức nó đỏ vì một thứ nó không định đo.

    ⇒ Mệnh đề thật: vòng đo phải chạy trên **hai độ dài khác nhau**. Đọc AST
      của chính vòng ấy thay vì đếm phần tử một hằng số.
    """
    import ast as _ast
    import pathlib as _pl

    nguon = (_pl.Path(__file__).resolve().parents[1]
             / "tools/do_ho_so_giong.py").read_text(encoding="utf-8")
    cay = _ast.parse(nguon)
    ham = next(n for n in _ast.walk(cay)
               if isinstance(n, _ast.FunctionDef) and n.name == "do_mot_giong")
    # Vong `for ten, t in ((...), (...))` — dem so cap trong tuple lap.
    bac = []
    for n in _ast.walk(ham):
        if isinstance(n, _ast.For) and isinstance(n.iter, _ast.Tuple):
            bac = [x for x in n.iter.elts if isinstance(x, _ast.Tuple)]
            break
    assert len(bac) >= 2, (
        f"vong do chi chay tren {len(bac)} bac do dai — mot bac cho MOT diem, "
        f"va mot diem khong dung duoc mot duong thang")
    # Và hai bậc ấy phải là hai NGUỒN khác nhau, không phải cùng một biểu thức.
    assert len({_ast.unparse(x) for x in bac}) == len(bac)

#
# 🔴 `POST /xem-truoc` có một chú thích tự nhận: *"con số hiện ra ở đây là con
#    số sẽ bị tạm giữ, không phải một ước lượng thứ hai."*
#
#    Câu ấy đúng cho tới 08/09/2026, rồi `uoc_tran` nhận thêm `giong` — và nó
#    thành sai **mà không ai đụng vào route**. Một mệnh đề chép tay trong chú
#    thích không tự biết nó vừa hết đúng; chỉ một phép kiểm mới biết.
#
# ⭐ Nên bất biến ở đây **không** là "route có truyền preset không" (đó là hình
#    dạng), mà là **hai con số phải BẰNG NHAU** (đó là mệnh đề). Bất biến ấy
#    sống sót qua mọi lần đổi chữ ký của `uoc_tran`.


# ── 5. Ô "ước credit" của khách phải là ĐÚNG con số sẽ bị tạm giữ ────────────

@pytest.fixture()
def khach_voice(tmp_path, monkeypatch):
    """Một khách đã đăng nhập + token CSRF của phiên đó."""
    import re

    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'uoc.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-uoc-credit")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import apps.ltt_voice.tables  # noqa: F401
    import platform_core.models  # noqa: F401

    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from platform_core.storage import LocalStorage, set_storage
    from platform_core.users import tao_nguoi_dung
    set_storage(LocalStorage(str(tmp_path / "store")))

    gen = dbmod.get_session()
    db = next(gen)
    try:
        tao_nguoi_dung(db, email="uoc@test.com", password="matkhau-tot-12",
                       is_verified=True)
        db.commit()
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
    r = client.post("/login", data={"username": "uoc@test.com",
                                    "password": "matkhau-tot-12",
                                    "csrf_token": m.group(1)})
    assert r.status_code in (200, 302, 303)
    trang = client.get("/ltt-voice/")
    m2 = re.search(r'name="csrf_token" value="([^"]+)"', trang.text)
    assert m2, "khong lay duoc csrf tu trang Studio"
    try:
        yield client, m2.group(1)
    finally:
        client.close()
        set_storage(None)
        dbmod.reset_engine()
def _uoc_tu_route(client, csrf, text, preset=""):
    fd = {"csrf_token": csrf, "text": text}
    if preset:
        fd["preset"] = preset
    r = client.post("/ltt-voice/xem-truoc", data=fd)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d.get("ok"), d
    return d["uoc_credit"], d["da_chuan_hoa"]


@pytest.mark.parametrize("co_ho_so", [False, True])
def test_o_uoc_credit_BANG_DUNG_so_se_bi_tam_giu(khach_voice, monkeypatch,
                                                 co_ho_so):
    """⛔ ĐỐI CHỨNG NẰM NGAY TRONG THAM SỐ.

    Chạy hai lần: một lần giọng **không** có hồ sơ, một lần **có**. Không có
    vế `co_ho_so=True` thì phép kiểm vẫn xanh với một route bỏ quên `preset`,
    vì khi chưa giọng nào có hồ sơ thì cả hai đầu cùng rơi về hằng số chung —
    tức nó sẽ xanh **đúng cho tới ngày cơ chế này bắt đầu có tác dụng**.
    """
    from apps.ltt_voice import giong_mau
    from apps.ltt_voice.manifest import MANIFEST

    client, csrf = khach_voice
    preset = giong_mau.DANH_SACH[0].ma
    if co_ho_so:
        _ho_so_gia(monkeypatch, preset, toc_do=9.0, sd=0.2)
        assert ho_so_giong.tra(preset) is not None, "moi gia lap khong an"

    text = "Xin chào, đây là một đoạn văn bản đủ dài để đếm cho tử tế. " * 6
    uoc, da_chuan = _uoc_tu_route(client, csrf, text, preset)
    giu = MANIFEST.credit_cost({"text": text, "preset": preset})
    assert uoc == giu, (
        f"o 'uoc credit' hien {uoc} nhung phan tam giu la {giu} "
        f"(co_ho_so={co_ho_so}) - hai cho tinh tien dang lech nhau")
    # và con số ấy phải là con số của CHÍNH văn bản đã chuẩn hoá, không phải
    # của văn bản thô — nếu không thì phép bằng ở trên có thể đúng vì cả hai
    # cùng sai một kiểu.
    assert uoc == gia.uoc_tran(so_ky_tu=len(da_chuan), giong=preset)


def test_ho_so_LAM_DOI_con_so_route_tra_ve(khach_voice, monkeypatch):
    """⭐ ĐỐI CHỨNG ĐỘ NHẠY. Phép kiểm trên chốt *"hai bên bằng nhau"*; nó vẫn
    xanh nếu `preset` bị vứt ở **cả hai** bên.

    Ở đây ta chốt điều mạnh hơn: hồ sơ **thật sự chảy tới tận HTTP**. Một giọng
    được đo là đọc nhanh phải cho ước RẺ HƠN hằng số bi quan chung — nếu không,
    con đường có khớp nối mà không có nước.
    """
    from apps.ltt_voice import giong_mau

    client, csrf = khach_voice
    preset = giong_mau.DANH_SACH[0].ma
    text = "Câu này lặp lại nhiều lần cho đủ dài mà đếm. " * 20

    khong_ho_so, _ = _uoc_tu_route(client, csrf, text, preset)
    _ho_so_gia(monkeypatch, preset, toc_do=float(gia.KY_TU_MOI_GIAY_UOC) * 3,
               sd=0.1)
    co_ho_so, _ = _uoc_tu_route(client, csrf, text, preset)

    assert co_ho_so < khong_ho_so, (
        f"do duoc mot giong doc nhanh gap ba ma uoc van {co_ho_so} "
        f"(truoc: {khong_ho_so}) - ho so KHONG toi duoc route")


def test_route_xem_truoc_KHONG_nhan_voice_id(khach_voice):
    """⚠️ `manifest._gia` chỉ đọc `preset`. Nếu route bắt đầu nhận `voice_id`
    mà `_gia` thì không, hai bên lại lệch — lần này theo hướng ngược lại.

    Phép kiểm này không cấm tương lai; nó bắt người mở đường ấy phải mở **cả
    hai** đầu cùng lúc.
    """
    import inspect

    from apps.ltt_voice.routes import _p_tao

    tham = set(inspect.signature(_p_tao.xem_truoc).parameters)
    assert "preset" in tham
    assert "voice_id" not in tham, (
        "route nhan voice_id nhung manifest._gia khong doc no - mo ca hai dau "
        "hoac khong mo dau nao")


# ── 6. Bài dài là N lượt phát, không phải một ────────────────────────────────
#
# 🔴 `gia.giay_uoc` là mô hình HAI tham số: `khoi_dong + n/toc_do`. `khoi_dong`
#    là khoảng lặng model thêm vào **mỗi lượt phát** — và `uoc_tran_lo` nói
#    thẳng điều đó: *"Phần khởi động cộng cho TỪNG đoạn, và đó là đúng: mỗi
#    đoạn là một lượt phát riêng."*
#
#    Nhưng `_gia` gọi `uoc_tran(so_ky_tu=len(ca_bai))` — tính như thể cả bài là
#    MỘT lượt. Hai hàm trong cùng một tệp giá mâu thuẫn nhau, và `uoc_tran_lo`
#    tồn tại **không người gọi** suốt thời gian ấy.
#
# ⛔ Lệch về đúng phía chốt 3.3 cấm: giữ THIẾU. Và hậu quả không phải "thu
#    thiếu 20 credit" — quyết toán vượt phần giữ thì lượt chạy bị đánh hỏng
#    **sau khi** đã tiêu hết GPU.


def _doan_that(text: str) -> list:
    from apps.ltt_voice import text_pipeline
    from apps.ltt_voice.tham_so_cong_khai import TRAN_MOI_LUOT_SINH
    da = text_pipeline.chuan_hoa(text)
    return text_pipeline.chia_doan(da, tran_moi_doan=TRAN_MOI_LUOT_SINH,
                                   can_bang=True)


@pytest.mark.parametrize("so_lan", [1, 40, 400])
def test_giu_cho_KHONG_THAP_HON_gia_theo_TUNG_doan(so_lan):
    """🔴 Bất biến tiền, viết theo **mô hình giá của chính hệ**, không theo một
    hằng số chép tay: giá thật của bản ghép là tổng giá của từng đoạn."""
    from apps.ltt_voice.manifest import MANIFEST

    text = ("Đây là một câu tiếng Việt bình thường để kiểm phép chia đoạn. "
            * so_lan)
    doan = _doan_that(text)
    theo_doan = gia.tinh_lo([gia.giay_uoc(len(d)) for d in doan])
    assert MANIFEST.credit_cost({"text": text}) >= theo_doan, (
        f"{so_lan} lan -> {len(doan)} doan: giu "
        f"{MANIFEST.credit_cost({'text': text})} < gia theo tung doan "
        f"{theo_doan} — CHOT 3.3 VO")


def test_bai_NHIEU_DOAN_giu_NHIEU_HON_bai_mot_doan_cung_do_dai():
    """⭐ ĐỐI CHỨNG ĐỘ NHẠY. Phép kiểm trên vẫn xanh với bản cũ ở văn bản ngắn
    (một đoạn thì hai công thức trùng nhau) — nên nó phải đi kèm một phép kiểm
    chứng minh số đoạn **thật sự làm đổi** con số.

    Không có nó, cả mục 6 này xanh-rỗng đúng cho tới bài đầu tiên vượt trần.
    """
    from apps.ltt_voice.manifest import MANIFEST

    text = "Đây là một câu tiếng Việt bình thường để kiểm phép chia đoạn. " * 400
    doan = _doan_that(text)
    assert len(doan) > 1, "van ban mau khong con bi chia — sua lai phep kiem"
    da_dai = len("".join(doan))
    assert MANIFEST.credit_cost({"text": text}) > gia.uoc_tran(so_ky_tu=da_dai), (
        "giu cho khong doi khi bai bi chia thanh nhieu doan — `_gia` van dang "
        "tinh ca bai nhu MOT luot phat")


def test_o_bao_gia_va_phan_giu_van_BANG_NHAU_khi_bai_bi_chia(khach_voice):
    """⛔ Hai đầu phải đổi CÙNG LÚC. Sửa `_gia` mà quên `xem_truoc` là dựng lại
    đúng cái lỗ mà mục 5 vừa bịt, chỉ ở một độ dài khác.

    ⭐ Chốt bằng HAI CON SỐ, không bằng một phép khớp chuỗi `"uoc_tran_lo" in
       nguon`. Khớp chuỗi chỉ chốt được **hình dạng** hôm nay; hai con số bằng
       nhau là **mệnh đề**, và nó sống sót qua mọi lần đổi tên hàm.
    """
    from apps.ltt_voice.manifest import MANIFEST

    client, csrf = khach_voice
    text = "Đây là một câu tiếng Việt bình thường để kiểm phép chia đoạn. " * 400
    assert len(_doan_that(text)) > 1, "van ban mau khong con bi chia"

    uoc, _ = _uoc_tu_route(client, csrf, text)
    assert uoc == MANIFEST.credit_cost({"text": text}), (
        f"o bao gia hien {uoc}, phan tam giu la "
        f"{MANIFEST.credit_cost({'text': text})} — hai cho tinh tien lech nhau "
        f"o bai nhieu doan")


# ── 7. Giao diện KHÔNG được giữ một bảng giá thứ hai ─────────────────────────
#
# 🔴 `vo.py` cấp `ky_tu_moi_giay` cho template kèm một chú thích đúng nguyên
#    tắc: *"CÙNG hằng số mà phần giữ credit dùng … Hai chỗ ước thời lượng bằng
#    hai tỉ lệ khác nhau là hai chỗ nói với khách hai con số khác nhau."*
#
#    Nhưng nó cấp **một** trong **ba** số của công thức. `voice.js` gõ nốt hai
#    số còn lại và viết nguyên văn `Math.ceil((1.5 + n / 18) * 0.2)`.
#
# ⭐ Nên bảng giá thứ hai vẫn tồn tại — nó chỉ nấp sau một hằng số **đã được
#    cấp đúng**, tức chỗ khó nhìn nhất. Một chú thích nói "dùng chung hằng số"
#    làm người đọc tin cả khối đã dùng chung.
#
# ⛔ Và 08/09/2026 nó thành sai: giá cộng phí khởi động cho TỪNG đoạn.

JS = GOC / "server/static/voice.js"


def _ma_js(s: str) -> str:
    """Bỏ chú thích `/* */` và `//` — chỉ còn mã thật.

    🔴 BẮT BUỘC, và không phải vì gọn. Chú thích ngay cạnh bản vá **trích dẫn**
       công thức cũ để giải thích vì sao nó sai. Một phép kiểm khớp chuỗi thô
       sẽ báo động trên chính lời giải thích của nó — lỗi đã mắc nhiều lần
       trong kho này (xem `test_505::_ma_thuc`).

    ⚠️ Thô: một `//` bên trong chuỗi ký tự cũng bị cắt. Chấp nhận được ở đây vì
       ta chỉ hỏi *"có hằng số giá nào không"*, và cắt thừa chỉ làm phép kiểm
       **dễ xanh oan hơn** — nên nó đi kèm một self-test ngay dưới.
    """
    s = re.sub(r"/\*.*?\*/", " ", s, flags=re.S)
    return re.sub(r"//[^\n]*", " ", s)


def test_bo_loc_chu_thich_THAT_SU_cat():
    """⛔ SELF-TEST. Không có nó thì một `_ma_js` hỏng làm **mọi** phép kiểm
    dưới đây xanh vĩnh viễn — và chúng sẽ xanh một cách rất thuyết phục."""
    assert "1.5" not in _ma_js("/* go 1.5 o day */ var a = 2;")
    assert "1.5" not in _ma_js("// go 1.5 o day\nvar a = 2;")
    assert "1.5" in _ma_js("var a = 1.5;"), "bo loc cat ca MA THAT"


#: Các **hình dạng công thức** cấm, không phải các con số trần.
#:
#: 🔴 Bản đầu cấm thẳng chuỗi `"1.5"`, và nó đỏ ngay — vì `1.5` cũng là một
#:    **nấc tốc độ phát lại** (`[1, 1.25, 1.5, 0.75]`), hoàn toàn không liên
#:    quan tới giá.
#:
#: ⭐ Đó là lỗi "phép kiểm mạnh hơn thứ nó đo": mệnh đề thật là *"công thức giá
#:    không gõ tay hằng số"*, không phải *"con số 1.5 không được tồn tại"*. Một
#:    phép kiểm rộng hơn mệnh đề của nó sẽ đỏ vì những lý do không phải lỗi, và
#:    rồi có người nới nó ra cho đến khi nó không còn chốt gì.
CAM = [
    r"1\.5\s*\+",         # `1.5 + n/...`  - phi khoi dong go tay
    r"n\s*/\s*18\b",      # `n / 18`       - toc do go tay
    r"\*\s*0\.2\b",      # `* 0.2`        - credit moi giay go tay
]


@pytest.mark.parametrize("mau", CAM)
def test_voice_js_KHONG_go_tay_hang_so_gia(mau):
    """Ba con số của công thức giá không được gõ tay trong **mã** của JS."""
    ma = _ma_js(JS.read_text(encoding="utf-8"))
    assert not re.search(mau, ma), (
        f"`voice.js` con go tay cong thuc gia `{mau}` — do la ban chep cua mot "
        f"hang so trong `gia.py`, va no se troi khi gia doi")


def test_voice_js_LAY_ca_ba_so_tu_may_chu():
    """⭐ ĐỐI CHỨNG NGƯỢC của phép kiểm trên.

    Không có vế này thì xoá sạch phần tính credit cũng làm mọi thứ xanh — và
    "không có bảng giá thứ hai" đúng theo nghĩa tệ nhất.
    """
    ma = _ma_js(JS.read_text(encoding="utf-8"))
    for khoa in ("cfg.kyTuMoiGiay", "cfg.giayKhoiDong", "cfg.creditMoiGiay"):
        assert khoa in ma, f"`voice.js` khong doc `{khoa}` tu may chu"


def test_vo_py_cap_du_BA_so_va_lay_tu_gia_py():
    """Và ba số ấy phải đến từ `gia.py`, không phải gõ lại trong `vo.py` —
    nếu không thì bảng giá thứ hai chỉ dời sang một tệp khác."""
    nguon = (GOC / "apps/ltt_voice/vo.py").read_text(encoding="utf-8")
    for khoa, hang in (("ky_tu_moi_giay", "gia.KY_TU_MOI_GIAY_UOC"),
                       ("giay_khoi_dong", "gia.GIAY_KHOI_DONG_UOC"),
                       ("credit_moi_giay", "gia.MCREDIT_MOI_GIAY")):
        assert re.search(rf'"{khoa}":\s*{re.escape(hang)}', nguon), (
            f"`vo.py` khong cap `{khoa}` tu `{hang}`")


def test_template_TRUYEN_ca_ba_so_xuong_JS():
    """⛔ Ba khớp nối, ba chỗ đứt được. `vo.py` cấp mà template không truyền thì
    `cfg.giayKhoiDong` là `undefined`, `|| 0` nuốt nó, và ước thời lượng **im
    lặng** mất phần khởi động — không lỗi, không cảnh báo."""
    html = (GOC / "apps/ltt_voice/templates/ltt_voice_studio.html").read_text(
        encoding="utf-8")
    for js_ten, py_ten in (("kyTuMoiGiay", "ky_tu_moi_giay"),
                           ("giayKhoiDong", "giay_khoi_dong"),
                           ("creditMoiGiay", "credit_moi_giay")):
        assert re.search(rf"{js_ten}:\s*{{{{\s*{py_ten}\s*\|", html), (
            f"template khong truyen `{py_ten}` thanh `{js_ten}`")


def test_route_xem_truoc_tra_ETA(khach_voice):
    """U-11: khách phải thấy *"khoảng 2 phút 40"*, không phải một thanh chạy
    vô định. Và con số ấy phải đến từ phép chia THẬT."""
    client, csrf = khach_voice
    text = "Đây là một câu tiếng Việt bình thường để kiểm phép chia đoạn. " * 400
    r = client.post("/ltt-voice/xem-truoc", data={"csrf_token": csrf, "text": text})
    d = r.json()
    assert d["ok"], d
    assert d["giay_uoc"] > 0
    doan = _doan_that(text)
    assert d["so_doan"] == len(doan)
    assert d["giay_uoc"] == pytest.approx(
        sum(gia.giay_uoc(len(x)) for x in doan), rel=0.01), (
        "ETA khong khop phep chia that")
