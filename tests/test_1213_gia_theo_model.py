"""
test_1213_gia_theo_model — hai model, hai bảng giá, MỘT module. (D07, dual-model 2.5)

⚠️ **VÌ SAO 1213 CHỨ KHÔNG PHẢI 1212.** Plan Task 2.5 ghi tên tệp là
   `test_1212_gia_theo_model.py`. Số ấy **đã có chủ**: Task 2.4 dùng `1212` cho
   `test_1212_llm_noi_bo_theo_app.py` (chính nó cũng đã phải nhảy khỏi `1211`).
   1209/1210/1211/1212 đều đã dùng ⇒ tệp này là **1213**, trong dải 1200–1249
   đăng ký ở Task 1.2.

## Đường tiền này đang chạy thật — nên phép kiểm phải đo theo HAI chiều

28 ngày trước lượt cắt này: **10.663** lượt `ltt_llm.chat`, tiền thật, sổ thật.
Nên một bộ kiểm chỉ hỏi *"3.5 có tính đúng 20 credit/1M ra không"* là chưa đủ:
nó xanh y hệt trên một bản mà **cả hai** model cùng đọc một bảng giá miễn là
bảng ấy tình cờ đúng. Hai đối chứng, hai chiều:

  ① **giá khác nhau ⇒ hoá đơn khác nhau.** Cùng một `SuDung`, hai model, hai số
     tiền — và khác **đúng theo tỉ lệ hai bảng**, không phải khác bất kỳ.
  ② **gỡ giá của một model ⇒ NỔ TO.** Không rơi về bảng model bên cạnh. Đây mới
     là chiều nguy hiểm: rơi về bảng 3.8 cho một lượt 3.5 là thu **20 lần** giá
     đúng, im lặng, và nghiêng về phía có lợi cho ta — thứ không ai đi khiếu nại
     nhưng cũng không ai phát hiện.

Và một bánh cóc ngược lại: **giá LTT-3.8 không được đổi một đồng** trong lượt
cắt này. `test_gia_38_KHONG_doi_mot_dong_nao` là chỗ duy nhất nói điều đó.
"""
from __future__ import annotations

import ast
import inspect
import pathlib

import pytest

from platform_core.llm import canonical
from platform_core.llm import gia_token as G
from platform_core.llm.cong_vlm import SuDung
from tests.conftest import bao_dam_user

M38 = "ltt-3.8"
M35 = "ltt-3.5"

#: Gốc kho, đo từ vị trí tệp test chứ không từ `cwd` (gate chạy từ nơi khác).
GOC = pathlib.Path(__file__).resolve().parents[1]

#: Những tệp **thật sự chuyển tiền** của đường LLM. Không phải "mọi tệp có chữ
#: giá": một bộ dò quét cả kho sẽ đo lẫn cả trang bán hàng, nơi lặp qua bảng giá
#: là việc ĐÚNG.
TEP_DUONG_TIEN = (
    "platform_core/llm/thanh_toan.py",
    "platform_core/runtime_noi_bo/luong.py",
    "server/api/chat.py",
    "server/api/streaming.py",
    "apps/ltt_llm/features.py",
    "apps/ltt_llm/manifest.py",
)

#: Hàm nào là một phép tính tiền theo model.
HAM_TIEN_KW = ("giu_cho_luot", "du_so_du", "quyet_toan_luot",
               "quyet_toan_hoac_hoan", "uoc_tran")
HAM_TIEN_POS = ("tinh",)


def _su_dung(vao=0, ra=0, cache=0, dang_tin=True):
    return SuDung(token_vao=vao, token_ra=ra, token_vao_cache=cache,
                  dang_tin=dang_tin)


@pytest.fixture()
def db(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'gia.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session()
    s = next(gen)
    try:
        yield s
    finally:
        s.close()
        dbmod.reset_engine()


def _nap(db, user_id="u1", so=100_000):
    from platform_core import credit
    bao_dam_user(db, user_id)
    credit.cap_tay(db, user_id, so, by="test")
    return user_id


@pytest.fixture()
def web(tmp_path, monkeypatch):
    """Cửa công khai — cùng khuôn `test_274_gia_cong_khai`."""
    monkeypatch.setenv("LTT_DATABASE_URL",
                       "sqlite:///" + (tmp_path / "w.db").as_posix())
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from fastapi.testclient import TestClient

    from platform_core.db import Base, get_engine
    Base.metadata.create_all(get_engine())
    from server.app import create_app

    app = create_app(env={
        "LTT_ENV": "local-server-test",
        "LTT_SESSION_SECRET": "gia-theo-model-secret-1",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp_path / "c.json"),
    })
    with TestClient(app, base_url="https://testserver") as client:
        yield client
    dbmod.reset_engine()


# ── A. Hai bảng giá ──────────────────────────────────────────────────────────

def test_mot_trieu_token_ra_moi_model_dung_so_da_chot():
    """Con số trung tâm của D07, cả hai chiều một lượt."""
    assert G.tinh(_su_dung(ra=1_000_000), M35).ra_mcredit == 20_000
    assert G.tinh(_su_dung(ra=1_000_000), M38).ra_mcredit == 400_000


def test_gia_38_KHONG_doi_mot_dong_nao():
    """🔴 BÁNH CÓC TIỀN ĐANG CHẠY. 10.663 lượt trong 28 ngày đã tính theo bảng
    này; Task 2.5 chỉ **thêm** một model, không đụng hoá đơn của ai.

    Nhãn cũng nằm trong bánh cóc: đổi nhãn mà giữ số là làm hỏng việc đối soát
    (`public_api/pricing.py`), đổi số mà giữ nhãn còn tệ hơn.
    """
    g = G.BANG_GIA[M38]
    assert (g.vao_moi_1m, g.vao_cache_1m, g.ra_1m) == (50, 10, 400)
    assert g.phien_ban == "ltt-vlm-2026-08-22"


def test_gia_35_dung_so_D07_chot():
    g = G.BANG_GIA[M35]
    assert (g.vao_moi_1m, g.vao_cache_1m, g.ra_1m) == (13, 3, 20)
    assert g.phien_ban == "ltt-3.5-2026-09-11"


def test_HAI_MODEL_HAI_HOA_DON_cho_cung_mot_luot():
    """⭐ ĐỐI CHỨNG CHIỀU ①: giá khác nhau **phải** ra tiền khác nhau.

    Một bản cài sai — cả hai model cùng đọc một bảng — làm mọi phép kiểm "3.8
    tính đúng" xanh. Chỉ sự **tương phản** mới đỏ ở đó.

    Và không chỉ "khác": khác **đúng tỉ lệ hai bảng**, tính lại từ `BANG_GIA`
    chứ không gõ một con số thứ hai vào đây.
    """
    su = _su_dung(vao=100_000, ra=10_000, cache=40_000)
    a, b = G.tinh(su, M38), G.tinh(su, M35)
    assert a.tong_mcredit != b.tong_mcredit
    g38, g35 = G.BANG_GIA[M38], G.BANG_GIA[M35]
    assert b.ra_mcredit * g38.ra_1m == a.ra_mcredit * g35.ra_1m
    assert b.vao_moi_mcredit * g38.vao_moi_1m == a.vao_moi_mcredit * g35.vao_moi_1m


def test_nhan_gia_di_theo_model_khong_theo_he_thong():
    """Đối soát ba tháng sau đọc **hai** sự thật ghi cùng lúc: tiền và bảng nào."""
    assert G.tinh(_su_dung(ra=10), M35).phien_ban_gia == G.BANG_GIA[M35].phien_ban
    assert G.tinh(_su_dung(ra=10), M38).phien_ban_gia == G.BANG_GIA[M38].phien_ban
    assert (G.uoc_tran(token_vao_uoc=10, max_tokens=10, model=M35).phien_ban_gia
            == G.BANG_GIA[M35].phien_ban)


def test_bang_gia_phu_dung_danh_muc_cong_khai():
    """🔑 HAI CHỖ KHAI CÙNG MỘT ĐIỀU — đây là chỗ bắt khớp.

    `canonical.ALIAS_SANG_ID` nói *model nào bán*; `gia_token.BANG_GIA` nói *giá
    bao nhiêu*. `gia_token` **không import** `canonical` (vòng import qua
    `registry`), nên thứ ghép hai đầu lại phải là một phép kiểm. Thêm model mà
    quên giá ⇒ đỏ ở đây, chứ không phải một `KeyError` ở lượt gọi thật đầu tiên.
    """
    assert set(G.BANG_GIA) == set(canonical.ALIAS_SANG_ID)
    assert set(G.BANG_GIA) == set(canonical.MODEL_HOP_LE)
    assert G.MODEL_GIA_MAC_DINH == canonical.MODEL_MAC_DINH


def test_hang_so_cu_la_BI_DANH_cua_bang_38_khong_phai_ban_chep():
    """Mã chưa truyền model đọc hằng số; hằng số **dẫn xuất**, không gõ lại."""
    g = G.BANG_GIA[G.MODEL_GIA_MAC_DINH]
    assert G.GIA_VAO_MOI_CREDIT_1M == g.vao_moi_1m
    assert G.GIA_VAO_CACHE_CREDIT_1M == g.vao_cache_1m
    assert G.GIA_RA_CREDIT_1M == g.ra_1m
    assert G.PHIEN_BAN_GIA == g.phien_ban


# ── B. Model bắt buộc, thiếu giá thì NỔ ──────────────────────────────────────

@pytest.mark.parametrize("ten", ["ltt_llm", "ltt_llm_vision", "qwen38-vision",
                                 "qwen38-api", "qwen35-api", ""])
def test_ten_khong_phai_model_cong_khai_thi_KeyError(ten):
    """Tên đã cắt (D02) **và** id nội bộ đều không phải khoá bảng giá.

    Id nội bộ nằm trong danh sách vì đó là nhầm lẫn dễ xảy ra nhất: nó là chuỗi
    mà lớp gateway cầm trên tay.
    """
    with pytest.raises(KeyError):
        G.tinh(_su_dung(ra=10), ten)
    with pytest.raises(KeyError):
        G.uoc_tran(token_vao_uoc=1, max_tokens=1, model=ten)


def test_GO_gia_cua_mot_model_thi_NEM_chu_khong_roi_ve_model_kia(monkeypatch):
    """⭐ ĐỐI CHỨNG CHIỀU ②, và là chiều nguy hiểm hơn.

    Tiêm một bảng giá **thiếu `ltt-3.5`** — đúng trạng thái của một kho vừa
    thêm model mà quên giá. Yêu cầu: nổ. Nếu mã có bất kỳ đường rơi nào về bảng
    3.8, phép kiểm này đỏ; mà đường rơi ấy là thu **20 lần** giá đúng ở token ra.
    """
    monkeypatch.setattr(G, "BANG_GIA", {M38: G.BANG_GIA[M38]}, raising=True)
    with pytest.raises(KeyError):
        G.tinh(_su_dung(ra=1_000_000), M35)
    with pytest.raises(KeyError):
        G.uoc_tran(token_vao_uoc=1_000, max_tokens=1_000, model=M35)
    # Và model còn lại vẫn tính được — nếu không thì phép kiểm trên xanh nhờ
    # "mọi thứ đều nổ", chứ không nhờ điều nó định đo.
    assert G.tinh(_su_dung(ra=1_000_000), M38).ra_mcredit == 400_000


def test_go_gia_thi_ca_DUONG_TIEN_cung_nem(db, monkeypatch):
    """Chiều ② đo ở tầng `thanh_toan`, không chỉ ở tầng bảng.

    Một `KeyError` bị nuốt ở giữa đường là y hệt một đường rơi về giá model kia.
    """
    from platform_core.llm import thanh_toan as T
    u = _nap(db)
    monkeypatch.setattr(G, "BANG_GIA", {M38: G.BANG_GIA[M38]}, raising=True)
    with pytest.raises(KeyError):
        T.giu_cho_luot(db, user_id=u, request_id="r-go", token_vao_uoc=1_000,
                       max_tokens=1_000, model=M35)
    with pytest.raises(KeyError):
        T.du_so_du(db, user_id=u, token_vao_uoc=1_000, max_tokens=1_000, model=M35)


@pytest.mark.parametrize("ham,ten_tham_so", [
    (G.tinh, "model"),
    (G.uoc_tran, "model"),
])
def test_model_KHONG_co_mac_dinh_ngam_o_tang_gia(ham, ten_tham_so):
    """⛔ Một mặc định ngầm ở đây nghĩa là ngày ai đó quên truyền, lượt 3.5 bị
    thu theo bảng 3.8 và **không gì đỏ**."""
    p = inspect.signature(ham).parameters[ten_tham_so]
    assert p.default is inspect.Parameter.empty


@pytest.mark.parametrize("ten_ham", ["giu_cho_luot", "du_so_du",
                                     "quyet_toan_luot", "quyet_toan_hoac_hoan"])
def test_model_KHONG_co_mac_dinh_ngam_o_tang_thanh_toan(ten_ham):
    from platform_core.llm import thanh_toan as T
    p = inspect.signature(getattr(T, ten_ham)).parameters["model"]
    assert p.default is inspect.Parameter.empty


@pytest.mark.parametrize("ten", [M38, M35])
def test_khong_do_duoc_van_nem_KhongDoDuocError(ten):
    """Luật cũ không được mất khi thêm model: 0 token ≠ miễn phí."""
    with pytest.raises(G.KhongDoDuocError):
        G.tinh(SuDung(dang_tin=False), ten)


def test_khong_do_duoc_XET_TRUOC_model_la():
    """Thứ tự hai chốt là một quyết định, không phải tình cờ.

    Bên gọi bắt `KhongDoDuocError` để **hoàn trọn**. Để `KeyError` chen lên
    trước là biến một lượt đáng hoàn thành một lỗi 500 giữa đường tiền.
    """
    with pytest.raises(G.KhongDoDuocError):
        G.tinh(SuDung(dang_tin=False), "khong-phai-model")


# ── C. Đường tiền thật: giữ, quyết toán, hoàn ────────────────────────────────

def test_giu_cho_theo_model_KHONG_giu_theo_bang_kia(db):
    """Giữ theo bảng 3.8 cho một lượt 3.5 là giữ thừa gấp ~20 lần ở token ra —
    tức từ chối `402` một khách có đủ tiền."""
    from platform_core.llm import thanh_toan as T
    u = _nap(db, so=1_000_000)
    a = T.giu_cho_luot(db, user_id=u, request_id="h38", token_vao_uoc=100_000,
                       max_tokens=50_000, model=M38)
    b = T.giu_cho_luot(db, user_id=u, request_id="h35", token_vao_uoc=100_000,
                       max_tokens=50_000, model=M35)
    assert b < a
    assert a == G.uoc_tran(token_vao_uoc=100_000, max_tokens=50_000,
                           model=M38).tong_credit_lam_tron_len
    assert b == G.uoc_tran(token_vao_uoc=100_000, max_tokens=50_000,
                           model=M35).tong_credit_lam_tron_len


def test_du_so_du_tra_loi_theo_model(db):
    """SỰ TƯƠNG PHẢN ở cửa 402: cùng một số dư, hai câu trả lời khác nhau.

    Số dư đặt **giữa** hai trần: đủ cho 3.5, không đủ cho 3.8. Một bản cài đọc
    một bảng giá duy nhất trả **cùng** một câu cho cả hai, bất kể bảng nào.
    """
    from platform_core.llm import thanh_toan as T
    vao, ra = 200_000, 100_000
    tran38 = G.uoc_tran(token_vao_uoc=vao, max_tokens=ra,
                        model=M38).tong_credit_lam_tron_len
    tran35 = G.uoc_tran(token_vao_uoc=vao, max_tokens=ra,
                        model=M35).tong_credit_lam_tron_len
    assert tran35 < tran38, "phep kiem nay vo nghia neu hai tran bang nhau"
    u = _nap(db, so=(tran35 + tran38) // 2)
    assert T.du_so_du(db, user_id=u, token_vao_uoc=vao, max_tokens=ra, model=M35)
    assert not T.du_so_du(db, user_id=u, token_vao_uoc=vao, max_tokens=ra, model=M38)


def test_quyet_toan_thu_theo_MODEL_DA_PHUC_VU(db):
    """D07 hệ quả 4, đo trên sổ thật: hai lượt giống hệt, hai số tiền."""
    from platform_core.llm import thanh_toan as T
    u = _nap(db, so=1_000_000)
    su = _su_dung(vao=200_000, ra=100_000)

    T.giu_cho_luot(db, user_id=u, request_id="q38", token_vao_uoc=200_000,
                   max_tokens=100_000, model=M38)
    a = T.quyet_toan_luot(db, user_id=u, request_id="q38", su_dung=su, model=M38)
    T.giu_cho_luot(db, user_id=u, request_id="q35", token_vao_uoc=200_000,
                   max_tokens=100_000, model=M35)
    b = T.quyet_toan_luot(db, user_id=u, request_id="q35", su_dung=su, model=M35)

    assert a.thu_credit > b.thu_credit
    assert a.chi_phi_mcredit == G.tinh(su, M38).tong_mcredit
    assert b.chi_phi_mcredit == G.tinh(su, M35).tong_mcredit
    assert a.phien_ban_gia == G.BANG_GIA[M38].phien_ban
    assert b.phien_ban_gia == G.BANG_GIA[M35].phien_ban


def test_khong_do_duoc_hoan_du_va_nhan_gia_VAN_la_cua_model(db):
    """Hoàn trọn (INV-003) không được đánh mất nhãn giá của model đã chạy."""
    from platform_core import credit
    from platform_core.llm import thanh_toan as T
    u = _nap(db, so=1_000_000)
    ban_dau = credit.so_du(db, u)
    giu = T.giu_cho_luot(db, user_id=u, request_id="r-hoan", token_vao_uoc=10_000,
                         max_tokens=5_000, model=M35)
    kq = T.quyet_toan_hoac_hoan(db, user_id=u, request_id="r-hoan",
                                su_dung=_su_dung(dang_tin=False), model=M35)
    assert kq.thu_credit == 0
    assert kq.hoan_credit == giu
    assert kq.da_do_duoc is False
    assert kq.phien_ban_gia == G.BANG_GIA[M35].phien_ban
    assert credit.so_du(db, u) == ban_dau, "hoan tron phai tra lai dung so du cu"


# ── D. Tĩnh (AST): mọi đường tiền truyền model THẬT ──────────────────────────

def _cac_loi_goi(tep: pathlib.Path):
    """Yield `(ten_ham, node)` cho mỗi lời gọi tính tiền **của đường LLM**.

    ⚠️ LỌC THEO MÔ-ĐUN, KHÔNG CHỈ THEO TÊN HÀM. `tinh`/`uoc_tran` là tên chung
       của **bốn** bảng giá khác nhau trong kho (`image_gen/gia.py`,
       `anhnoibo/gia.py`, `ltt_voice/gia.py`, `chatltt/gia_nghien_cuu.py`) và
       chúng không nhận `model`. Một bộ dò chỉ nhìn tên hàm sẽ đòi chúng truyền
       một tham số vô nghĩa — tức nó đo sai thứ và sẽ bị người sau tắt đi.
    """
    cay = ast.parse(tep.read_text(encoding="utf-8"))
    for n in ast.walk(cay):
        if not isinstance(n, ast.Call) or not isinstance(n.func, ast.Attribute):
            continue
        ten = n.func.attr
        mo_dun = n.func.value.id if isinstance(n.func.value, ast.Name) else ""
        if ten in HAM_TIEN_POS or ten == "uoc_tran":
            if mo_dun not in ("gia_token", "G"):
                continue
        elif ten not in HAM_TIEN_KW:
            continue
        yield ten, n


def test_MOI_cho_goi_tinh_tien_trong_kho_deu_truyen_model():
    """Bánh cóc: không ai được thêm một lời gọi thiếu `model`.

    Quét **mã sản phẩm**, không quét `tests/` — một phép kiểm có quyền dựng
    tình huống thiếu giá, mã sản phẩm thì không.
    """
    thieu, so_thay = [], 0
    for thu_muc in ("platform_core", "apps", "server", "tools"):
        for p in (GOC / thu_muc).rglob("*.py"):
            for ten, n in _cac_loi_goi(p):
                so_thay += 1
                if "model" in {k.arg for k in n.keywords}:
                    continue
                if ten in HAM_TIEN_POS and len(n.args) >= 2:
                    continue
                thieu.append(f"{p.relative_to(GOC).as_posix()}:{n.lineno} {ten}")
    assert not thieu, ("loi goi tinh tien khong truyen `model`: " + str(thieu))
    # Đối chứng: bộ dò phải THẤY gì đó. Đo 12/09: 18 lời gọi.
    assert so_thay >= 16, f"bo do chi thay {so_thay} loi goi — no dang mu"


def test_cua_tien_truyen_model_THAT_chu_khong_phai_HANG_MAC_DINH():
    """🔴 Điều D07 hệ quả 4 thật sự đòi: **model thật đã phục vụ**.

    Truyền `canonical.MODEL_MAC_DINH` ở một cửa tiền thì mọi phép kiểm "có
    truyền model" ở trên vẫn xanh, mà lượt `ltt-3.5` vẫn bị thu giá `ltt-3.8`.
    Nên ở sáu tệp đường tiền, đối số model phải là một **biến**, không phải một
    hằng chuỗi và không phải một hằng mặc định.
    """
    cam_ten = {"MODEL_MAC_DINH", "MODEL_NOI_BO_MAC_DINH", "MODEL_GIA_MAC_DINH"}
    xau, so_thay = [], 0
    for ten_tep in TEP_DUONG_TIEN:
        p = GOC / ten_tep
        for ten, n in _cac_loi_goi(p):
            bieu_thuc = None
            for k in n.keywords:
                if k.arg == "model":
                    bieu_thuc = k.value
            if bieu_thuc is None and ten in HAM_TIEN_POS and len(n.args) >= 2:
                bieu_thuc = n.args[1]
            if bieu_thuc is None:
                continue
            so_thay += 1
            dau = f"{ten_tep}:{n.lineno} {ten}"
            if isinstance(bieu_thuc, ast.Constant):
                xau.append(dau + " (hang chuoi)")
            elif isinstance(bieu_thuc, ast.Attribute) and bieu_thuc.attr in cam_ten:
                xau.append(dau + f" ({bieu_thuc.attr})")
            elif isinstance(bieu_thuc, ast.Name) and bieu_thuc.id in cam_ten:
                xau.append(dau + f" ({bieu_thuc.id})")
    assert not xau, "cua tien dung model mac dinh thay vi model that: " + str(xau)
    # ⭐ ĐỐI CHỨNG CHO CHÍNH BỘ DÒ: một bộ dò không thấy gì thì xanh tuyệt đối.
    assert so_thay >= 14, f"bo do chi thay {so_thay} loi goi — no dang mu"


def test_bo_do_tinh_CO_DO_khi_tiem_ban_cu():
    """Đối chứng tiêm: dựng lại đúng khuôn trước 2.5 và đòi bộ dò đỏ.

    Không có ca này thì hai phép kiểm AST ở trên có thể là hai hàm luôn xanh.
    """
    cu = ("import x\n"
          "def f(su_dung):\n"
          "    return gia_token.tinh(su_dung)\n")
    cay = ast.parse(cu)
    goi = [n for n in ast.walk(cay)
           if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
           and n.func.attr in HAM_TIEN_POS]
    assert len(goi) == 1
    n = goi[0]
    assert not {k.arg for k in n.keywords} & {"model"} and len(n.args) < 2, (
        "khuon cu phai bi cham la THIEU model")

    mac_dinh = ast.parse(
        "gia_token.tinh(su_dung, canonical.MODEL_MAC_DINH)\n").body[0].value
    assert isinstance(mac_dinh.args[1], ast.Attribute)
    assert mac_dinh.args[1].attr == "MODEL_MAC_DINH", (
        "bo do thu hai phai nhan ra hang mac dinh")


# ── E. Bề mặt công khai + cửa job ────────────────────────────────────────────

def test_trang_gia_cong_khai_hien_gia_CA_HAI_model(web):
    """D07 hệ quả 3. Khách không chọn được model nếu chỉ thấy giá một model."""
    trang = web.get("/gia-api").text
    for ten in (M38, M35):
        g = G.BANG_GIA[ten]
        assert ten in trang, f"thieu ten model {ten}"
        assert g.phien_ban in trang, f"thieu nhan gia cua {ten}"
        for so in (g.vao_moi_1m, g.vao_cache_1m, g.ra_1m):
            assert str(so) in trang, f"thieu gia {so} cua {ten}"
    # Lớp đệm alias vẫn đứng: id nội bộ không lộ ra trang bán hàng.
    assert "qwen38" not in trang
    assert "qwen35" not in trang


def test_dieu_khoan_cong_bo_gia_CA_HAI_model(web):
    """Một điều khoản in giá của một model trong khi bán hai là một điều khoản
    SAI cho một nửa số khách — tệ hơn một trang im lặng."""
    from platform_core.public_api import dieu_khoan as dk

    moi = dk.bang_gia_moi_model()
    assert set(moi) == set(G.BANG_GIA)
    assert moi[M35]["token_ra"] == G.BANG_GIA[M35].ra_1m

    trang = web.get("/api-dieu-khoan").text
    for ten in (M38, M35):
        assert G.BANG_GIA[ten].phien_ban in trang, f"thieu nhan gia {ten}"
        assert str(G.BANG_GIA[ten].ra_1m) in trang


def test_ti_le_cache_trong_dieu_khoan_TINH_RA_khong_go_cung():
    """"20%" gõ cứng là một điều khoản công bố sai ở đúng model thứ hai."""
    b35 = G.bang_gia(M35)
    b38 = G.bang_gia(M38)
    assert "20%" in b38["ghi_chu"]
    assert "20%" not in b35["ghi_chu"]
    assert f"{round(100 * 3 / 13)}%" in b35["ghi_chu"]


def test_credit_cost_cua_cua_JOB_theo_model():
    """Trần của cửa job phải dùng **cùng** bảng giá mà quyết toán sẽ dùng."""
    from apps.ltt_llm.manifest import MAX_TOKENS_TRAN, MANIFEST

    # ⚠️ Lượt phải đủ LỚN để hai bảng giá tách nhau sau khi làm tròn lên credit
    #    nguyên. Một lượt 8.000 ký tự / 2.000 token ra tốn **1 credit ở cả hai**
    #    (sàn `max(1, …)`) — và một phép kiểm dựng trên lượt ấy xanh y hệt trên
    #    bản chỉ có MỘT bảng giá. Đo 12/09: 24 credit (3.8) so với 4 (3.5).
    than = {"messages": [{"role": "user", "content": "x" * 500_000}],
            "max_tokens": MAX_TOKENS_TRAN}
    a = MANIFEST.credit_cost({**than, "model": M38})
    b = MANIFEST.credit_cost({**than, "model": M35})
    assert b < a, "gia job khong doi theo model"
    # Vắng `model` ⇒ mặc định của cửa, **cùng** mặc định `kiem_tham_so` áp.
    assert MANIFEST.credit_cost(than) == MANIFEST.credit_cost(
        {**than, "model": canonical.MODEL_MAC_DINH})


@pytest.mark.parametrize("ten", [M38, M35])
def test_tran_giu_cho_job_KHONG_BAO_GIO_thap_hon_gia_that(ten):
    """Bất biến cũ của `test_256`, nay phải đúng cho **từng** model.

    Giữ thiếu thì khách tiêu quá số dư — và một bản cài lấy trần của model rẻ
    cho lượt của model đắt là đúng lỗi ấy.
    """
    from apps.ltt_llm.manifest import MANIFEST

    tran = MANIFEST.credit_cost({
        "messages": [{"role": "user", "content": "x" * 8_000}],
        "max_tokens": 2_000, "model": ten})
    for vao in (100, 1_600, 3_200):
        for ra in (0, 500, 2_000):
            that = G.tinh(_su_dung(vao=vao, ra=ra), ten)
            assert that.tong_credit_lam_tron_len <= tran


@pytest.mark.parametrize("ten", [M38, M35])
def test_KetQua_bao_gia_theo_model_no_da_chay(ten):
    """`credit_cost` trong kết quả job là **tiền thật** — nó phải theo model."""
    from apps.ltt_llm.features import KetQua

    kq = KetQua(noi_dung="x", suy_nghi="", tool_calls=(), finish_reason="stop",
                model=ten, token_vao=200_000, token_ra=100_000,
                token_vao_cache=0, do_duoc=True)
    assert kq.gia_that_credit() == G.tinh(
        _su_dung(vao=200_000, ra=100_000), ten).tong_credit_lam_tron_len
    assert kq.as_result()["credit_cost"] == kq.gia_that_credit()


def test_KetQua_hai_model_bao_HAI_gia():
    """Tương phản, vì "theo model" chỉ đo được bằng hai model."""
    from apps.ltt_llm.features import KetQua

    def _gia(ten):
        return KetQua(noi_dung="x", suy_nghi="", tool_calls=(),
                      finish_reason="stop", model=ten, token_vao=200_000,
                      token_ra=100_000, token_vao_cache=0,
                      do_duoc=True).gia_that_credit()

    assert _gia(M38) > _gia(M35) > 0
