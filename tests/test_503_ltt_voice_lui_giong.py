r"""ĐƯỜNG LÙI GIỌNG — và luật bất di bất dịch: KHÔNG ÂM THẦM ĐỔI NGƯỜI NÓI.

## Vì sao tệp này tồn tại

Trước 07/09/2026, một giọng nhân bản mất biểu diễn (ca **nâng engine**: bản ghi
gắn với phiên bản engine cũ bị cho nghỉ) làm cả lượt đọc **hỏng**, kèm một câu
sai: *"Giọng này chưa ghi danh xong. Hãy thử lại sau ít phút."* Chờ thì không
bao giờ giúp được — không có job ghi danh nào đang chạy.

Bản sửa mở một đường lùi. Nhưng một đường lùi **im lặng** còn tệ hơn không có:
hệ `D:\Viral` chạy đúng đường ấy và khách của họ báo ngày 26/08/2026 rằng
*"giọng nam bị biến thành giọng nữ"*. Nên tệp này chốt cả hai vế:

    duong lui CO chay      -> bai van doc duoc
    duong lui KHONG im     -> khach duoc noi cho biet, va ban ghi giu lai

## ⛔ Hai ràng buộc là HÌNH DẠNG, không phải thông điệp

Thông điệp đổi được. Hai thứ dưới đây đổi là **đổi hành vi**:

  ① không bao giờ nới GIỚI, không bao giờ nới LÀN;
  ② giới không rõ (`""`) ⇒ **không lùi**, không đoán.
"""
from __future__ import annotations

import ast
import pathlib
import uuid

import pytest

from apps.ltt_voice import lui_giong

GOC = pathlib.Path(__file__).resolve().parents[1]
VAN_BAN = "Xin chào các bạn, hôm nay chúng ta nói về một chủ đề mới."

#: 🔴 VĂN BẢN TIẾNG ANH CHO HỒ SƠ LÀN `en` — thêm 2026-09-10 (Q121).
#:
#:    Trước đó mọi ca ở tệp này dùng `VAN_BAN` tiếng Việt, kể cả khi hồ sƠ
#:    mang làn `en`. Tức chúng dựng một cặp **văn bản VI + giọng EN** — cặp mà
#:    `lan_ngon_ngu.quyet_dinh` nay TỪ CHỐI ngay tại cửa nộp, nên đường lùi **không
#:    bao giờ tới được** trong sản phẩm thật.
#:
#: ⛔ Và đó không chỉ làm hai ca đỏ — nó còn làm hai ca `pytest.raises` **XANH VÌ
#:    LÝ DO SAI**: chúng chờ một `LoiGiongNoi` từ *"không có ứng viên"* / *"license
#:    chưa soát"*, nhưng nhận được một `LoiGiongNoi` từ *"lệch làn"*. Một phép
#:    kiểm xanh vì lý do sai trông y hệt một phép kiểm xanh.
#:
#: ⭐ Nên hồ sơ làn nào đọc văn bản làn ấy, và hai ca `raises` nay chốt thêm
#:    **MÃ LỖI** để không bị một cửa chặn khác mua chuộc lần nữa.
VAN_BAN_EN = "Hello everyone, today we will talk about a brand new topic."

U = lui_giong.UngVien


# ── 1. Bậc thang, không có CSDL ─────────────────────────────────────────────

KHO = (
    U(ma="A-nam-bac-tin", gioi="nam", ngon_ngu="vi", vung="bac", phong_cach="tin_tuc"),
    U(ma="B-nam-bac-truyen", gioi="nam", ngon_ngu="vi", vung="bac", phong_cach="doc_truyen"),
    U(ma="C-nam-nam-tin", gioi="nam", ngon_ngu="vi", vung="nam", phong_cach="tin_tuc"),
    U(ma="D-nu-bac-tin", gioi="nu", ngon_ngu="vi", vung="bac", phong_cach="tin_tuc"),
    U(ma="E-nam-bac-tin", gioi="nam", ngon_ngu="vi", vung="bac", phong_cach="tin_tuc"),
)


def test_bac_1_khop_ca_bon_mat():
    u = lui_giong.chon(gioi="nam", ngon_ngu="vi", vung="bac",
                       phong_cach="tin_tuc", cac=KHO)
    assert u is not None and u.vung == "bac" and u.phong_cach == "tin_tuc"


def test_bac_2_noi_VUNG_truoc():
    """Không có vùng ấy thì nới VÙNG, **giữ** phong cách.

    ⭐ Vùng nới trước phong cách có lý do: giọng miền Bắc đọc thay giọng miền
       Nam thì nghe ra ngay nhưng vẫn hiểu; một giọng tin tức đọc thay giọng kể
       chuyện thì đổi hẳn NHỊP của cả bài.
    """
    u = lui_giong.chon(gioi="nam", ngon_ngu="vi", vung="trung",
                       phong_cach="tin_tuc", cac=KHO)
    assert u is not None and u.phong_cach == "tin_tuc", u


def test_bac_3_noi_PHONG_CACH_khi_khong_con_gi():
    u = lui_giong.chon(gioi="nam", ngon_ngu="vi", vung="trung",
                       phong_cach="khong_co_phong_cach_nay", cac=KHO)
    assert u is not None and u.gioi == "nam" and u.ngon_ngu == "vi"


def test_TAT_DINH_cung_dau_vao_cho_cung_giong():
    """Hai lượt đọc lại của cùng một bài phải ra cùng một người nói thay.

    ⛔ Không có ràng buộc này thì lỗi "sao hai bản nghe khác nhau" không ai tái
       hiện được — nó phụ thuộc thứ tự hàng trả về từ CSDL.
    """
    ra = {lui_giong.chon(gioi="nam", ngon_ngu="vi", vung="bac",
                         phong_cach="tin_tuc", cac=KHO).ma for _ in range(20)}
    assert len(ra) == 1, ra


# ── 2. 🔴 HAI THỨ KHÔNG BAO GIỜ ĐƯỢC NỚI ────────────────────────────────────

def test_KHONG_BAO_GIO_noi_GIOI():
    """Chỉ có giọng nữ trong kho ⇒ một yêu cầu giọng nam phải trả `None`.

    🔴 Đây là ca `D:\\Viral` đã hỏng. Chú thích trong `giong_piper.py` của họ:
       *"moi duong LUI GIONG o backend khong co cach nao biet khach dang chon
       nam hay nu ⇒ lui ve ... giong NU, ke ca khi khach chon giong NAM."*
    """
    chi_nu = tuple(u for u in KHO if u.gioi == "nu")
    assert lui_giong.chon(gioi="nam", ngon_ngu="vi", cac=chi_nu) is None


def test_KHONG_BAO_GIO_noi_LAN():
    chi_vi = tuple(u for u in KHO if u.ngon_ngu == "vi")
    assert lui_giong.chon(gioi="nam", ngon_ngu="en", cac=chi_vi) is None


@pytest.mark.parametrize("gioi", ["", "  ", "khac", None])
def test_gioi_KHONG_RO_thi_khong_lui(gioi):
    """⛔ Không có nghĩa nào cho "cùng giới với một giới không biết"."""
    assert lui_giong.chon(gioi=gioi, ngon_ngu="vi", cac=KHO) is None


def test_kho_rong_thi_None_chu_khong_nem():
    assert lui_giong.chon(gioi="nam", ngon_ngu="vi", cac=()) is None


def test_ung_vien_tu_giong_mau_deu_lan_vi_va_co_gioi():
    """20 giọng mẫu đều thuộc làn `vi` và đều khai giới — nếu không thì đường
    lùi mặc định rỗng và không ai biết."""
    cac = lui_giong.tu_giong_mau()
    assert len(cac) >= 20
    assert all(u.ngon_ngu == "vi" for u in cac)
    assert all(u.gioi in ("nam", "nu") for u in cac), \
        [u.ma for u in cac if u.gioi not in ("nam", "nu")]
    # Cả hai giới phải có mặt, nếu không thì một nửa số khách không lùi được.
    assert {u.gioi for u in cac} == {"nam", "nu"}


# ── 3. Cảnh báo phải điền được, không còn chỗ trống ─────────────────────────

def test_canh_bao_khong_con_dau_ngoac_nhon():
    u = lui_giong.chon(gioi="nam", ngon_ngu="vi", cac=KHO)
    cau = lui_giong.dien_canh_bao(lui_giong.CANH_BAO, u)
    assert "{giong_thay}" not in cau and "{mo_ta}" not in cau, cau
    assert u.ma in cau


def test_lan_ngon_ngu_doi_chieu_tra_cau_DA_DIEN():
    """🔴 HỒI QUY. `doi_chieu` từng trả KHUÔN còn chỗ trống, và `dien_canh_bao`
    có **0 nơi gọi** — tức khách sẽ đọc đúng chuỗi `{lan_giong}` trên màn hình
    nếu cảnh báo có bao giờ tới được đó."""
    from apps.ltt_voice import lan_ngon_ngu
    (cau,) = lan_ngon_ngu.doi_chieu("vi", "The quick brown fox jumps over the lazy dog.")
    assert "{lan_giong}" not in cau and "{lan_text}" not in cau, cau


# ── 4. Nối vào ứng dụng — đọc AST, không cần CSDL ───────────────────────────

def _ham(tep: str, ten: str):
    cay = ast.parse((GOC / tep).read_text(encoding="utf-8"))
    return next(n for n in ast.walk(cay)
                if isinstance(n, ast.FunctionDef) and n.name == ten)


def test_giai_giong_THUC_SU_goi_duong_lui():
    """`giai_giong` phai THAT SU noi vao duong lui, khong chi co ve nhu the.

    ⛔ VIET LAI Task 12 / D007 (2026-09-11): ban cu dem loi goi
       `lui_giong.chon` THEO TEN ngay trong than `giai_giong`. D007 tach
       phan chon duong lui ra `_chon_duong_lui` (dung chung voi ban CHI
       KIEM `giai_giong_kiem`, khong cham storage) -- cung mot cach ma
       `test_384::test_giai_giong_doi_chieu_lan_o_CA_HAI_nhanh` da tach
       `_chot_lan` khoi `giai_giong` truoc do. Dem theo ten se DO ngay ca
       khi duong lui van noi nguyen ven, chi vi mot lop goi ham trung gian
       doi ten -- dung cai bay chinh test_384 da ghi lai.

    ⭐ Nen nay chot CHUOI HAI MAT XICH: `giai_giong` goi `_chon_duong_lui`,
       va `_chon_duong_lui` goi that `lui_giong.chon`. Menh de nay bat bien
       voi ten ham trung gian, va van do neu mot mat xich bi cat.
    """
    gg = _ham("apps/ltt_voice/features.py", "giai_giong")
    goi_gg = {getattr(n.func, "id", "") for n in ast.walk(gg)
             if isinstance(n, ast.Call)}
    assert "_chon_duong_lui" in goi_gg, \
        "giai_giong khong goi _chon_duong_lui — duong lui dang khong duoc gan vao"

    # Mat xich thu hai: _chon_duong_lui phai THAT SU hoi lui_giong.chon.
    dl = _ham("apps/ltt_voice/features.py", "_chon_duong_lui")
    goi_dl = {ast.unparse(n.func) for n in ast.walk(dl) if isinstance(n, ast.Call)}
    assert any("lui_giong.chon" in g for g in goi_dl), \
        "_chon_duong_lui khong goi lui_giong.chon — duong lui dang khong duoc gan vao"

    # D007: ban CHI KIEM cung phai voi toi duong lui (khong chi ban NAP
    # that) -- neu khong thi mot yeu cau se lui giong khi chay that lai
    # KHONG bi tu choi som o /quotes, vi ban chi-kiem khong biet duong lui
    # co ton tai hay khong.
    gk = _ham("apps/ltt_voice/features.py", "giai_giong_kiem")
    goi_gk = {getattr(n.func, "id", "") for n in ast.walk(gk)
             if isinstance(n, ast.Call)}
    assert "_chon_duong_lui" in goi_gk, \
        "giai_giong_kiem khong goi _chon_duong_lui — pre-check khong chot duong lui"


def test_jobs_KHONG_VUT_canh_bao_di():
    """🔴 HỒI QUY CHỜ SẴN. Dòng cũ là `ref_b64, preset, _ = ...`.

    Dấu gạch dưới ấy làm **cả chuỗi cảnh báo chết**: `doi_chieu` chạy mỗi lượt,
    `KetQua.canh_bao` có sẵn, `as_result()` có khoá `canh_bao` — và không có gì
    đi giữa hai đầu. Nay `lui_giong` báo qua đúng kênh đó, nên vứt nó đi là
    biến đường lùi thành một lần đổi người nói **im lặng**.

    ⛔ Hỏi CÂY CÚ PHÁP, không khớp chuỗi: một bánh cóc khớp với chính lời giải
       thích của nó thì không chốt gì.
    """
    ham = _ham("apps/ltt_voice/jobs.py", "_tao_tieng")
    for n in ast.walk(ham):
        if not isinstance(n, ast.Assign):
            continue
        for dich in n.targets:
            if not isinstance(dich, ast.Tuple) or len(dich.elts) != 3:
                continue
            ten = [getattr(e, "id", "") for e in dich.elts]
            if ten[:2] == ["ref_b64", "preset"]:
                assert ten[2] != "_", (
                    "_tao_tieng dang vut canh_bao di bang mot dau gach duoi")
                return
    pytest.fail("khong tim thay cho `ref_b64, preset, ... = giai_giong(...)`")


def test_route_ket_qua_TRA_canh_bao_ve_studio():
    """Cảnh báo phải đi hết đường tới trình duyệt, không dừng ở cửa JSON."""
    src = (GOC / "apps/ltt_voice/routes/_p_tao.py").read_text(encoding="utf-8")
    ham = _ham("apps/ltt_voice/routes/_p_tao.py", "ket_qua")
    khoa = {n.value for n in ast.walk(ham)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    assert "canh_bao" in khoa, "route /ket-qua khong tra `canh_bao`"
    assert "canh_bao" in src


def test_studio_co_o_HIEN_canh_bao():
    html = (GOC / "apps/ltt_voice/templates/ltt_voice_studio.html").read_text(
        encoding="utf-8")
    js = (GOC / "server/static/voice.js").read_text(encoding="utf-8")
    assert 'id="lv-kq-canh-bao"' in html, "studio thieu o hien canh bao"
    assert "lv-kq-canh-bao" in js, "voice.js khong dien vao o canh bao"
    # ⛔ `textContent`, khong `innerHTML`: cho dat chuoi vao DOM bang innerHTML
    #    la cho se bi dung sai sau ba lan sua.
    i = js.index("lv-kq-canh-bao")
    assert "innerHTML" not in js[i:i + 900], "o canh bao dang dung innerHTML"


# ── 5. Thi hành thật, có CSDL ───────────────────────────────────────────────

@pytest.fixture()
def moi_truong(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       "sqlite:///" + (tmp_path / "lui503.db").as_posix())
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LTT_VOICE_SIDECAR_TOKEN", "thu-nghiem-503")
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    import apps.ltt_voice.tables  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    yield
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


def _tao_ho_so(*, gioi: str, trang_thai: str = "active",
               co_bieu_dien: bool = False, ngon_ngu: str = "vi") -> tuple:
    from apps.ltt_voice.tables import VoiceProfile, VoiceRepr
    owner = "u-" + uuid.uuid4().hex[:8]
    pid = "vc_" + uuid.uuid4().hex[:20]
    gen, db = _session()
    try:
        p = VoiceProfile(public_id=pid, owner_id=owner, ten_hien_thi="Giong thu",
                         ngon_ngu=ngon_ngu, gioi=gioi, trang_thai=trang_thai)
        db.add(p)
        db.flush()
        if co_bieu_dien:
            db.add(VoiceRepr(profile_id=p.id, ref_id=0, engine="vieneu",
                             storage_key="k", fingerprint="vt",
                             trang_thai="dang_dung"))
        db.commit()
    finally:
        _close(gen)
    return owner, pid


def _giai(owner: str, pid: str, text: str = VAN_BAN):
    from apps.ltt_voice import features
    yc = features.chuan_hoa({"text": text, "voice_id": pid, "owner_id": owner})
    gen, db = _session()
    try:
        return features.giai_giong(db, yc)
    finally:
        _close(gen)


def test_mat_bieu_dien_MA_BIET_GIOI_thi_LUI_va_CO_CANH_BAO(moi_truong):
    """Ca thật: nâng engine ⇒ `voice_repr` cũ nghỉ ⇒ profile `active` mà rỗng."""
    from apps.ltt_voice import giong_mau
    owner, pid = _tao_ho_so(gioi="nam", co_bieu_dien=False)
    ref, preset, canh_bao = _giai(owner, pid)
    assert ref is None, "lui giong khong duoc tra mot ref"
    assert giong_mau.hop_le(preset), preset
    assert canh_bao, "⛔ lui giong IM LANG — day la loi ta dang di sua"
    assert preset in canh_bao[0], canh_bao


def test_lui_giong_GIU_DUNG_GIOI(moi_truong):
    from apps.ltt_voice import giong_mau
    for gioi in ("nam", "nu"):
        owner, pid = _tao_ho_so(gioi=gioi, co_bieu_dien=False)
        _ref, preset, _cb = _giai(owner, pid)
        g = next(x for x in giong_mau.DANH_SACH if x.ma == preset)
        assert g.gioi == gioi, f"yeu cau {gioi} nhung lui ve {preset} ({g.gioi})"


def test_gioi_KHONG_RO_thi_KHONG_lui_va_noi_THAT_vi_sao(moi_truong):
    """⛔ Câu cũ ở nhánh này là *"chưa ghi danh xong, thử lại sau ít phút"* —
    và chờ thì không bao giờ giúp được. Một lời khuyên không dẫn tới đâu tệ hơn
    một lời từ chối."""
    from apps.ltt_voice import features
    owner, pid = _tao_ho_so(gioi="", co_bieu_dien=False)
    with pytest.raises(features.LoiGiongNoi) as e:
        _giai(owner, pid)
    cau = str(e.value).lower()
    assert "ghi danh lại" in cau or "ghi danh lai" in cau, cau
    assert "ít phút" not in cau, "van con khuyen khach CHO — cho khong giup duoc"


def test_lan_en_chua_lui_duoc_va_noi_that(moi_truong):
    """Giới hạn ĐÃ BIẾT: chưa có giọng mẫu làn `en` nên chưa có ứng viên."""
    from apps.ltt_voice import features
    owner, pid = _tao_ho_so(gioi="nu", ngon_ngu="en", co_bieu_dien=False)
    with pytest.raises(features.LoiGiongNoi) as e:
        _giai(owner, pid, VAN_BAN_EN)
    assert getattr(e.value, "ma", "") == "", (
        "phai hong vi KHONG CO UNG VIEN, khong phai vi lech lan")


def test_DANG_GHI_DANH_co_cau_RIENG_khong_bao_la_dang_bi_tat(moi_truong):
    """🔴 `dang_ghi_danh` và `disabled` từng dùng CHUNG một câu.

    Với một giọng vừa nộp và đang chờ worker, câu *"đang bị tắt, hãy bật lại"*
    bảo khách đi làm một việc **không tồn tại** — không có nút bật nào cho một
    giọng chưa ghi danh xong.
    """
    from apps.ltt_voice import features
    owner, pid = _tao_ho_so(gioi="nam", trang_thai="dang_ghi_danh")
    with pytest.raises(features.LoiGiongNoi) as e:
        _giai(owner, pid)
    assert "bị tắt" not in str(e.value), str(e.value)

    owner2, pid2 = _tao_ho_so(gioi="nam", trang_thai="disabled")
    with pytest.raises(features.LoiGiongNoi) as e2:
        _giai(owner2, pid2)
    assert str(e2.value) != str(e.value), \
        "hai trang thai khac nhau van dung chung mot cau"


def test_giong_LANH_khong_bi_lui(moi_truong, monkeypatch):
    """⛔ ĐỐI CHỨNG. Không có test này thì một hàm luôn-luôn-lùi cũng xanh."""
    from apps.ltt_voice import tham_chieu
    monkeypatch.setattr(tham_chieu, "nap_ref_b64", lambda bd: "REF64")
    owner, pid = _tao_ho_so(gioi="nam", co_bieu_dien=True)
    ref, preset, canh_bao = _giai(owner, pid)
    assert ref == "REF64" and preset is None
    assert canh_bao == (), canh_bao


# ── 4. Kho chung làm ứng viên lùi (09/09/2026) ──────────────────────────────
#
# Trước bản này, `tu_giong_mau()` gán cứng `ngon_ngu="vi"` cho cả 20 preset, nên
# một giọng làn `en` mất biểu diễn **không lùi được** — khách nhận lỗi thay vì
# một bản đọc. Kho chung đã có 17 giọng `en` từ 01/09; chúng chỉ chưa bao giờ
# được đưa vào danh sách ứng viên.

def _tao_kho_chung(*, gioi: str, ngon_ngu: str, ten: str,
                   license_status: str = "ok") -> str:
    """Một giọng KHO CHUNG có biểu diễn sống. Trả `public_id`."""
    from apps.ltt_voice.tables import VoiceProfile, VoiceRepr
    pid = "vc_" + uuid.uuid4().hex[:20]
    gen, db = _session()
    try:
        p = VoiceProfile(public_id=pid, owner_id="", ten_hien_thi=ten,
                         ngon_ngu=ngon_ngu, gioi=gioi, trang_thai="active",
                         dung_chung=True, license_status=license_status)
        db.add(p)
        db.flush()
        db.add(VoiceRepr(profile_id=p.id, ref_id=0, engine="vieneu",
                         storage_key="k-chung", fingerprint="vt-chung",
                         trang_thai="dang_dung"))
        db.commit()
    finally:
        _close(gen)
    return pid


def test_lan_EN_mat_bieu_dien_NAY_LUI_DUOC_qua_kho_chung(moi_truong, monkeypatch):
    """Năng lực mới: làn `en` không còn là ngõ cụt."""
    from apps.ltt_voice import tham_chieu
    monkeypatch.setattr(tham_chieu, "nap_ref_b64", lambda bd: "REF-CHUNG")
    _tao_kho_chung(gioi="nam", ngon_ngu="en", ten="Oliver")
    owner, pid = _tao_ho_so(gioi="nam", ngon_ngu="en", co_bieu_dien=False)

    ref, preset, canh_bao = _giai(owner, pid, VAN_BAN_EN)

    assert ref == "REF-CHUNG", "lan en van khong lui duoc"
    assert preset is None, "kho chung khong phai preset cua engine"
    assert len(canh_bao) == 1, "lui im lang — dung thu tep nay di sua"


def test_lui_kho_chung_dung_TEN_chu_khong_phai_public_id(moi_truong, monkeypatch):
    """⛔ `ma` của giọng chung là `vc_<hex>`. Đưa mã máy cho khách đọc là vô dụng."""
    from apps.ltt_voice import tham_chieu
    monkeypatch.setattr(tham_chieu, "nap_ref_b64", lambda bd: "REF-CHUNG")
    chung = _tao_kho_chung(gioi="nu", ngon_ngu="en", ten="Amelia")
    owner, pid = _tao_ho_so(gioi="nu", ngon_ngu="en", co_bieu_dien=False)

    _ref, _preset, canh_bao = _giai(owner, pid, VAN_BAN_EN)

    assert "Amelia" in canh_bao[0], canh_bao
    assert chung not in canh_bao[0], "public_id lot ra cau canh bao"


def test_lan_VI_VAN_lui_ve_PRESET_du_kho_chung_da_co(moi_truong):
    """🔴 CHỐNG HỒI QUY — lý do đường lùi đi HAI BƯỚC chứ không gộp một danh sách.

    `giai_giong` gọi `chon()` **không truyền** `vung`/`phong_cach`, nên cả hai là
    `""`. Giọng kho chung không có hai trường ấy ⇒ chúng khớp nấc ① *"cùng vùng,
    cùng phong cách"*, trong khi preset của engine — vốn CÓ vùng và phong cách
    thật — trượt nấc ① lẫn ② và chỉ được nhặt ở nấc ③.

    ⇒ Gộp hai kho vào một danh sách sẽ **lặng lẽ** đổi mọi lượt lùi tiếng Việt
      sang giọng kho chung. Test này đỏ ngay nếu ai đó gộp lại.
    """
    _tao_kho_chung(gioi="nam", ngon_ngu="vi", ten="Khong duoc chon")
    owner, pid = _tao_ho_so(gioi="nam", ngon_ngu="vi", co_bieu_dien=False)

    ref, preset, canh_bao = _giai(owner, pid)

    assert preset is not None, "lan vi phai lui ve PRESET cua engine"
    assert ref is None, "lan vi khong duoc lui sang kho chung"
    assert "Khong duoc chon" not in canh_bao[0], canh_bao


def test_kho_chung_CHUA_SOAT_LICENSE_thi_khong_duoc_lam_ung_vien(moi_truong):
    """⛔ Cổng license phải chặn cả đường LÙI, không chỉ đường chọn giọng.

    Một đường lùi có lối riêng bỏ qua `_dieu_kien_kho_chung()` là một cổng bị
    vòng — và nó bị vòng ở đúng nhánh không ai nhìn.
    """
    from apps.ltt_voice import features
    _tao_kho_chung(gioi="nam", ngon_ngu="en", ten="Chua soat",
                   license_status="cho_soat")
    owner, pid = _tao_ho_so(gioi="nam", ngon_ngu="en", co_bieu_dien=False)

    with pytest.raises(features.LoiGiongNoi) as e:
        _giai(owner, pid, VAN_BAN_EN)
    assert getattr(e.value, "ma", "") == "", (
        "phai hong vi LICENSE CHUA SOAT, khong phai vi lech lan")


def test_ung_vien_kho_chung_BO_giong_khong_ro_gioi(moi_truong):
    """Giới `""` là một giá trị THẬT nghĩa là *không biết* — không đoán hộ."""
    from apps.ltt_voice import tham_chieu
    _tao_kho_chung(gioi="", ngon_ngu="en", ten="Khong ro gioi")
    gen, db = _session()
    try:
        cac = tham_chieu.ung_vien_kho_chung(db)
    finally:
        _close(gen)
    assert all(u.gioi in ("nam", "nu") for u in cac), cac
