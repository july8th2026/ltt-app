"""
test_822 — bảng tệp của ChatLTT: SỞ HỮU trước, tính năng sau. (H44 P06 bước 2)

⛔ Tệp này được viết **trước** `apps/chatltt/services/kho_tep.py`, theo đúng dòng
   kế hoạch P06 §4 tự đặt ra: *"Sở hữu là **bề mặt quyền mới** ⇒ test ACL trước,
   không sau"*. Một bề mặt quyền được test **sau** là một bề mặt quyền đã sống
   một quãng không ai canh.

## Ba mệnh đề mà tệp này chốt, và vì sao từng cái

1. **Bảng không chứa byte nào.** `chatltt_tep` là một bảng **liên kết**: nó nói
   *tệp nào thuộc hội thoại nào*, còn byte nằm ở `storage` qua `upload_sessions`
   như mọi tệp khác của nền tảng. Ngày ai đó thêm một cột `noi_dung` vào đây là
   ngày ChatLTT có kho lưu trữ riêng, đi vòng qua hạn mức và qua `promote`.

2. **`user_id` là `String(36)`, không phải số.** Bài học đã trả giá ở
   `apps/ltt_voice/tables.py:66-75`: khai số ⇒ mọi khách thành chủ số 0, và
   triệu chứng là *"ai cũng thấy tệp của người khác"* chứ không phải một lỗi.

3. **CONTENT, không OPERATIONAL.** Đây là lần **thứ ba** cùng một ca: P03 đã
   ghi `chatltt_run` **không thể** là OPERATIONAL, và §7 của P06 bác `Job.params`
   làm chỗ giữ liên kết vì `jobs` là OPERATIONAL — **tự già đi**. Treo tri thức
   của khách vào một bảng tự dọn là hẹn ngày nó biến mất khỏi một hội thoại vẫn
   còn nguyên.

⭐ Đối chứng dương có mặt ở mọi phép kiểm ACL: mỗi lần chốt *"người khác KHÔNG
   thấy"*, cùng dữ liệu ấy phải chứng minh được *"chủ thì CÓ thấy"*. Không có vế
   sau thì một hàm luôn trả rỗng cũng qua sạch — đúng luật Bẫy 24.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

#: Tệp này nằm ở `tests/`, nên `parents[1]` là gốc kho — và
#: `tests/` không đổi chỗ. (Luật cấm `parents[n]` ở CLAUDE.md nhắm vào mã
#: app, nơi tệp CÓ đổi chỗ và hỏng lặng lẽ.)
GOC = Path(__file__).resolve().parents[1]

CHU = "u-chu-that"
NGUOI_KHAC = "u-nguoi-khac"


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", "sqlite:///" + (tmp_path / "t.db").as_posix())
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine, get_session
    from platform_core.registry import load_app_tables
    load_app_tables()
    Base.metadata.create_all(get_engine())
    gen = get_session()
    s = next(gen)
    yield s
    try:
        next(gen)
    except StopIteration:
        pass
    dbmod.reset_engine()


def _hoi_thoai(db, user_id: str) -> str:
    from apps.chatltt.tables import ChatlttConversation
    c = ChatlttConversation(user_id=user_id, title="t")
    db.add(c)
    db.flush()
    return c.id


def _upload(db, user_id: str, *, status: str = "promoted", ten: str = "a.pdf") -> str:
    from platform_core.models import UploadSession
    u = UploadSession(
        user_id=user_id, app_slug="chatltt",
        staging_key=f"stg/{user_id}/{ten}/{id(object())}",
        final_key=f"fin/{user_id}/{ten}", filename=ten,
        content_type="application/pdf", expected_size=10, actual_size=10,
        status=status,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1))
    db.add(u)
    db.flush()
    return u.id


def _user(db, uid: str) -> None:
    """`upload_sessions.user_id` có FK `RESTRICT` sang `users` — phải có thật."""
    from platform_core.models import User
    if db.get(User, uid) is None:
        db.add(User(id=uid, email=f"{uid}@x.test", password_hash="x"))
        db.flush()


@pytest.fixture()
def canh(db):
    """Cảnh chuẩn: chủ có 1 hội thoại + 1 upload đã promote; người khác cũng có."""
    for u in (CHU, NGUOI_KHAC):
        _user(db, u)
    return {
        "hoi_thoai_chu": _hoi_thoai(db, CHU),
        "upload_chu": _upload(db, CHU),
        "hoi_thoai_khac": _hoi_thoai(db, NGUOI_KHAC),
        "upload_khac": _upload(db, NGUOI_KHAC, ten="b.pdf"),
    }


# ── 1. Hình dạng bảng: nó KHÔNG được là một kho ────────────────────────────

def test_bang_KHONG_co_cot_nao_chua_byte():
    """🔴 Mệnh đề 1. `chatltt_tep` chỉ được **trỏ** tới byte, không **giữ** byte.

    Cửa *"phải giữ credit mới được lưu file"* ở `upload_sessions` tồn tại để
    không ai biến input của job thành kho lưu trữ miễn phí. Một cột nhị phân ở
    đây đi vòng qua đúng cái cửa ấy — nên phép kiểm chặn ở tầng **schema**, chỗ
    không quên được, chứ không ở một dòng ghi chú.
    """
    from sqlalchemy import LargeBinary, Text

    from apps.chatltt.tables import ChatlttTep

    for cot in ChatlttTep.__table__.columns:
        assert not isinstance(cot.type, LargeBinary), f"{cot.name} giu byte"
    # `Text` được phép cho *tên*/*lỗi*, nhưng không cho một cột tên gợi nội dung.
    cam = {"noi_dung", "content", "du_lieu", "data", "blob", "bytes", "van_ban"}
    assert not (cam & {c.name for c in ChatlttTep.__table__.columns})


def test_user_id_la_chuoi_KHONG_phai_so():
    """🔴 Mệnh đề 2 — `apps/ltt_voice/tables.py:66-75` đã trả giá cho bài này."""
    from sqlalchemy import Integer, String

    from apps.chatltt.tables import ChatlttTep

    kieu = ChatlttTep.__table__.c.user_id.type
    assert isinstance(kieu, String), f"user_id kieu {kieu!r}"
    assert not isinstance(kieu, Integer)
    assert kieu.length == 36


def test_governance_xep_CONTENT_khong_phai_OPERATIONAL():
    """🔴 Mệnh đề 3 — lần thứ ba của cùng một ca (P03 `chatltt_run`, P06 §7
    `jobs`). OPERATIONAL tự già đi ⇒ tệp biến mất khỏi hội thoại vẫn còn."""
    from platform_core.public_api import governance as G

    hang = [s for s in G.STORES if s.table == "chatltt_tep"]
    assert hang, "chatltt_tep chua khai trong governance"
    assert hang[0].klass == G.CONTENT, hang[0].klass


# ── 2. Sở hữu — mỗi phép kiểm âm đi kèm một đối chứng dương ────────────────

def test_gan_duoc_khi_CA_HAI_deu_cua_chu(db, canh):
    """⭐ Đối chứng dương của cả mục này. Không có nó, một hàm luôn ném cũng
    qua sạch mọi phép kiểm bên dưới."""
    from apps.chatltt.services import kho_tep

    t = kho_tep.gan(db, user_id=CHU, conversation_id=canh["hoi_thoai_chu"],
                    upload_id=canh["upload_chu"])
    assert t.user_id == CHU
    assert t.trang_thai_trich == kho_tep.MOI


def test_KHONG_gan_duoc_upload_cua_NGUOI_KHAC(db, canh):
    from apps.chatltt.services import kho_tep

    with pytest.raises(kho_tep.KhongDuocPhep):
        kho_tep.gan(db, user_id=CHU, conversation_id=canh["hoi_thoai_chu"],
                    upload_id=canh["upload_khac"])


def test_KHONG_gan_duoc_vao_hoi_thoai_cua_NGUOI_KHAC(db, canh):
    """⛔ Chiều ngược lại của phép kiểm trên, và nó **khác**: ở đây kẻ gọi sở
    hữu tệp nhưng không sở hữu hội thoại. Kiểm một chiều là để hở chiều kia."""
    from apps.chatltt.services import kho_tep

    with pytest.raises(kho_tep.KhongDuocPhep):
        kho_tep.gan(db, user_id=CHU, conversation_id=canh["hoi_thoai_khac"],
                    upload_id=canh["upload_chu"])


def test_nguoi_KHAC_khong_liet_ke_duoc_tep_cua_hoi_thoai_chu(db, canh):
    from apps.chatltt.services import kho_tep

    kho_tep.gan(db, user_id=CHU, conversation_id=canh["hoi_thoai_chu"],
                upload_id=canh["upload_chu"])
    db.flush()

    assert kho_tep.cua_hoi_thoai(
        db, user_id=CHU, conversation_id=canh["hoi_thoai_chu"]), "chu phai THAY"
    assert kho_tep.cua_hoi_thoai(
        db, user_id=NGUOI_KHAC, conversation_id=canh["hoi_thoai_chu"]) == []


def test_nguoi_KHAC_khong_doc_duoc_MOT_tep_theo_id(db, canh):
    """⛔ Liệt kê và đọc-một là **hai** cửa. Đã có ca bịt cửa liệt kê mà quên
    cửa đọc-theo-id, và id thì đoán được từ một lần chia sẻ màn hình."""
    from apps.chatltt.services import kho_tep

    t = kho_tep.gan(db, user_id=CHU, conversation_id=canh["hoi_thoai_chu"],
                    upload_id=canh["upload_chu"])
    db.flush()

    assert kho_tep.mot(db, user_id=CHU, tep_id=t.id) is not None
    assert kho_tep.mot(db, user_id=NGUOI_KHAC, tep_id=t.id) is None


def test_nguoi_KHAC_khong_doi_duoc_trang_thai_trich(db, canh):
    """🔴 Cửa GHI, không phải cửa đọc. Một kẻ không đọc được vẫn có thể **phá**
    nếu hàm ghi không tự kiểm chủ."""
    from apps.chatltt.services import kho_tep

    t = kho_tep.gan(db, user_id=CHU, conversation_id=canh["hoi_thoai_chu"],
                    upload_id=canh["upload_chu"])
    db.flush()

    assert not kho_tep.danh_dau(db, user_id=NGUOI_KHAC, tep_id=t.id,
                                trang_thai=kho_tep.XONG)
    db.refresh(t)
    assert t.trang_thai_trich == kho_tep.MOI

    assert kho_tep.danh_dau(db, user_id=CHU, tep_id=t.id,
                            trang_thai=kho_tep.XONG, so_doan=7)
    db.refresh(t)
    assert (t.trang_thai_trich, t.so_doan) == (kho_tep.XONG, 7)


# ── 3. Vòng đời ────────────────────────────────────────────────────────────

def test_upload_CHUA_promote_thi_KHONG_gan_duoc(db, canh):
    """🔴 P06 §7: trích văn bản là một **job trả tiền**, và cửa credit nằm ở
    `promote`. Cho gắn một upload mới `pending` là mở đúng đường vòng mà cửa ấy
    sinh ra để chặn — biến input của job thành kho lưu trữ miễn phí."""
    from apps.chatltt.services import kho_tep

    chua = _upload(db, CHU, status="pending", ten="chua.pdf")
    with pytest.raises(kho_tep.ChuaSanSang):
        kho_tep.gan(db, user_id=CHU, conversation_id=canh["hoi_thoai_chu"],
                    upload_id=chua)


def test_gan_HAI_LAN_cung_mot_upload_chi_ra_MOT_hang(db, canh):
    """⭐ Bấm hai lần / F5 giữa chừng là ca thường, không phải góc hiếm. Ràng
    buộc `unique` ở CSDL là thứ không quên; một `if` trong route thì quên được
    — cùng luật `ux_chatltt_approval_step`."""
    from apps.chatltt.services import kho_tep

    a = kho_tep.gan(db, user_id=CHU, conversation_id=canh["hoi_thoai_chu"],
                    upload_id=canh["upload_chu"])
    db.flush()
    b = kho_tep.gan(db, user_id=CHU, conversation_id=canh["hoi_thoai_chu"],
                    upload_id=canh["upload_chu"])
    db.flush()

    assert a.id == b.id
    assert len(kho_tep.cua_hoi_thoai(
        db, user_id=CHU, conversation_id=canh["hoi_thoai_chu"])) == 1


def test_rang_buoc_unique_o_tang_CSDL_chu_khong_chi_o_ham(db, canh):
    """⛔ Phép kiểm trên chứng minh **hàm** không tạo bản trùng. Phép kiểm này
    chứng minh **CSDL** cũng không cho — kể cả khi có người ghi thẳng, hoặc hai
    tiến trình chạy song song lọt qua cùng một `if`."""
    from sqlalchemy.exc import IntegrityError

    from apps.chatltt.services import kho_tep
    from apps.chatltt.tables import ChatlttTep

    kho_tep.gan(db, user_id=CHU, conversation_id=canh["hoi_thoai_chu"],
                upload_id=canh["upload_chu"])
    db.flush()

    db.add(ChatlttTep(user_id=CHU, conversation_id=canh["hoi_thoai_chu"],
                      upload_id=canh["upload_chu"], ten_tep="a.pdf"))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_cung_mot_upload_gan_duoc_vao_HAI_hoi_thoai_khac_nhau(db, canh):
    """⭐ Ràng buộc `unique` phải là `(conversation_id, upload_id)`, **không**
    phải riêng `upload_id`. Hỏi cùng một tài liệu ở hai hội thoại là việc bình
    thường; một ràng buộc quá chặt biến việc bình thường thành lỗi 500."""
    from apps.chatltt.services import kho_tep

    hai = _hoi_thoai(db, CHU)
    kho_tep.gan(db, user_id=CHU, conversation_id=canh["hoi_thoai_chu"],
                upload_id=canh["upload_chu"])
    kho_tep.gan(db, user_id=CHU, conversation_id=hai,
                upload_id=canh["upload_chu"])
    db.flush()

    assert len(kho_tep.cua_hoi_thoai(db, user_id=CHU,
                                     conversation_id=hai)) == 1


def test_danh_dau_LOI_giu_lai_ly_do(db, canh):
    """Trích hỏng là ca **thường** (PDF ảnh scan, tệp mã hoá). Người dùng phải
    đọc được vì sao, nếu không thì tệp nằm im mãi mà không ai biết tại sao."""
    from apps.chatltt.services import kho_tep

    t = kho_tep.gan(db, user_id=CHU, conversation_id=canh["hoi_thoai_chu"],
                    upload_id=canh["upload_chu"])
    db.flush()
    kho_tep.danh_dau(db, user_id=CHU, tep_id=t.id, trang_thai=kho_tep.LOI,
                     ly_do="pdf chi co anh, khong co lop chu")
    db.refresh(t)
    assert t.trang_thai_trich == kho_tep.LOI
    assert "khong co lop chu" in t.ly_do_loi


def test_migration_UPGRADE_chi_THEM_bang_moi():
    """⭐ Bước 2 không được sửa một bảng đang có dữ liệu thật.

    ⛔ Chỉ đọc thân `upgrade()`, không đọc cả tệp. `downgrade()` **phải** có
       `drop_table` — đó là việc của nó, và chính là thứ chứng minh migration
       này hạ lại được mà không mất hàng nào của ai. Bản đầu của phép kiểm
       này quét cả module nên nó sẽ đỏ vì một dòng đúng — một phép kiểm
       **mạnh hơn thứ nó đo**, đúng cái bẫy đã ghi trong memory.
    """
    import ast

    p = GOC / "alembic" / "versions" / "20260906_1100_chatltt_tep.py"
    assert p.exists(), p
    cay = ast.parse(p.read_text(encoding="utf-8"))
    than = [n for n in cay.body
            if isinstance(n, ast.FunctionDef) and n.name == "upgrade"]
    assert than, "migration khong co ham upgrade()"
    goi = {n.func.attr for n in ast.walk(than[0])
           if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
    assert "create_table" in goi
    assert not ({"alter_column", "drop_column", "drop_table"} & goi), goi

    ha = [n for n in cay.body
          if isinstance(n, ast.FunctionDef) and n.name == "downgrade"]
    goi_ha = {n.func.attr for n in ast.walk(ha[0])
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
    assert "drop_table" in goi_ha, "ha lai duoc la mot phan cua 'chi them'"
