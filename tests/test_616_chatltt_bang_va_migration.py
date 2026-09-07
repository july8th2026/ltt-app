"""
test_616 — Phase 07: bảng `chatltt_*` + migration Alembic lên/xuống sạch, một head.

⚠️ CẬP NHẬT 2026-09-05 (H44 P03), CÓ CHỦ ĐÍCH — không phải nới lỏng.

Phép kiểm này ghim "đúng BA bảng `chatltt_*`" và "head là `7d2c1e9f4a03`". H44
thêm ba bảng điều phối tool (`run`/`step`/`approval`) và một revision mới, nên
hai mệnh đề đó **hết đúng**. Chúng đã làm đúng việc của mình: bắt tôi phải quay
lại đây và nói ra thay đổi, thay vì để nó trôi qua.

⛔ Cách sai là đổi `==` thành `<=` cho xong. Làm vậy là gỡ chính thứ vừa bắt
   được thay đổi — lần sau ai thêm một bảng `chatltt_*` bừa sẽ không ai biết.
   Nên danh sách vẫn **chốt cứng**, chỉ là chốt sáu tên thay vì ba, và migration
   xuống một bước vẫn phải xoá **đúng** phần H44 chứ không phải mọi thứ.
"""
from __future__ import annotations

import pytest


#: Ba bảng V1 (H43) + ba bảng điều phối tool (H44) + bảng tệp (H44 P06).
#: CHỐT CỨNG — thêm bảng `chatltt_*` mà không sửa dòng này thì phép kiểm đỏ,
#: và đó là chủ ý.
BANG_V1 = {"chatltt_conversation", "chatltt_message", "chatltt_execution"}
BANG_V3 = {"chatltt_run", "chatltt_step", "chatltt_approval"}
#: ⚠️ CẬP NHẬT 06/09 (H44 P06 bước 2+3). `chatltt_tep` nối tệp đã tải lên với
#:    hội thoại; `chatltt_doan` giữ văn bản đã trích. Bánh cóc đã làm đúng việc
#:    **hai lần**: mỗi lần bắt tôi quay lại đây khai tên mới.
#:
#: 🔴 Hai bảng này ngược nhau ở đúng chỗ quan trọng: `chatltt_tep` **không được**
#:    chứa byte (test_822 chốt ở tầng schema), còn `chatltt_doan` **phải** chứa
#:    chữ — chỉ số tìm kiếm chạy trên chính nó. Byte gốc ở ngoài, chữ dẫn xuất
#:    ở trong.
BANG_P06 = {"chatltt_tep", "chatltt_doan"}

#: ⚠️ CẬP NHẬT 06/09 (H44 B4). Bánh cóc làm đúng việc lần **thứ ba**: tôi thêm
#:    `chatltt_ghi_nho` và nó bắt tôi quay lại đây khai tên.
#:
#: 🔴 Và lần này nó bắt được nhiều hơn một cái tên. Đây là bảng `chatltt_*` đầu
#:    tiên **không gắn với một hội thoại**: mẩu phạm vi `nguoi_dung` sống lâu
#:    hơn mọi hội thoại đã sinh ra nó. Chép nguyên `purged_by` của bảng bên
#:    cạnh (*"theo hội thoại chứa nó"*) sẽ để lại một kho ghi nhớ **mồ côi**
#:    sau khi người dùng xoá hết hội thoại — và không phép kiểm nào ở đây bắt
#:    được, vì tên bảng thì vẫn đúng.
BANG_B4 = {"chatltt_ghi_nho"}

TAT_CA = BANG_V1 | BANG_V3 | BANG_P06 | BANG_B4


def test_ba_bang_mang_dung_tien_to_va_registry_nap_duoc():
    from platform_core.db import Base
    from platform_core.registry import load_app_tables

    da_nap = load_app_tables()
    assert "chatltt" in da_nap
    ten = {t for t in Base.metadata.tables if t.startswith("chatltt_")}
    assert ten == TAT_CA


def test_moi_bang_chatltt_deu_co_hang_trong_governance():
    """⭐ Mệnh đề này **khó xanh hơn** danh sách tên ở trên, không dễ hơn.

    Danh sách tên chỉ hỏi *"có đúng bảng này không"*. Nó **không** bắt được ca
    thật sự nguy hiểm: một bảng `chatltt_*` mới được khai đúng tên nhưng **quên**
    khai lời hứa giữ dữ liệu — và mặc định của "quên" là không ai biết bảng ấy
    chứa gì của khách, nên không ai dọn nó khi khách xoá tài khoản.

    🔴 Thêm ở 06/09 vì `chatltt_tep` vừa mở đúng cái khe đó: nó "chỉ chứa siêu
       dữ liệu", và đó chính là câu nghe hợp lý dẫn tới xếp sai hạng.
    """
    from platform_core.public_api import governance as G

    da_khai = {s.table for s in G.STORES if s.table.startswith("chatltt_")}
    assert TAT_CA - da_khai == set(), f"thieu hang governance: {TAT_CA - da_khai}"
    assert da_khai - TAT_CA == set(), f"khai bang khong ton tai: {da_khai - TAT_CA}"


def test_khong_bang_chatltt_nao_bi_xep_OPERATIONAL():
    """🔴 Ba lần cùng một ca — P03 (`chatltt_run`), P06 §7 (bác `Job.params` vì
    `jobs` LÀ operational), P06 bước 2 (`chatltt_tep`). Ba lần thì thôi ghi chú,
    dựng một phép kiểm.

    OPERATIONAL **tự già đi** theo hạn riêng. Một bảng `chatltt_*` bị xếp vào đó
    nghĩa là một phần của hội thoại biến mất trong khi hội thoại vẫn còn — người
    dùng mở lại và thấy thứ mình từng đính vào nay không còn ở đó.
    """
    from platform_core.public_api import governance as G

    sai = [s.table for s in G.STORES
           if s.table.startswith("chatltt_") and s.klass == G.OPERATIONAL]
    assert sai == [], sai


#: Revision cua migration H44 (ba bang dieu phoi tool). Ghim theo ID chu
#: khong theo "head" — head doi moi khi ai do them migration.
REV_H44 = "4b8e21c6d907"


def test_alembic_mot_head_va_migration_chatltt_noi_dung_chuoi():
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    scripts = ScriptDirectory.from_config(Config("alembic.ini"))
    heads = scripts.get_heads()
    assert len(heads) == 1, heads
    # ⚠️ KHÔNG giả định migration H44 **là** head. Nó là head lúc viết phép kiểm
    #    này (05/09), rồi `9f3a71b4c2e8` (users.mcredit_du) chồng lên. Ghim theo
    #    **revision id** thì phép kiểm nói đúng thứ nó định nói, và không đỏ mỗi
    #    lần có ai thêm một migration khác.
    rev = scripts.get_revision(REV_H44)
    assert "chatltt" in (rev.doc or "").lower()
    # Head nay la migration H44; no phai noi TIEP migration H43, khong thay the.
    assert rev.revision == REV_H44
    assert rev.down_revision == "7d2c1e9f4a03"


@pytest.mark.timeout(240)
def test_upgrade_head_roi_downgrade_mot_buoc_sach(tmp_path, monkeypatch):
    """Lên head tạo đủ sáu bảng; xuống một bước xoá ĐÚNG phần H44, giữ nguyên V1.

    ⭐ Mệnh đề cuối là điều kiện của đường lùi (`02_ADR_ORCHESTRATION.md` §7):
       hạ migration H44 phải làm mất `run`/`step`/`approval` mà **hội thoại cũ
       không đổi một byte**. Nếu nó cũng xoá `chatltt_message` thì "lùi được"
       chỉ là một câu trong tài liệu.
    """
    from sqlalchemy import create_engine, inspect

    url = "sqlite:///" + (tmp_path / "mig.db").as_posix()
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    from alembic import command
    from alembic.config import Config

    cfg = Config("alembic.ini")
    # Len DUNG moc H44, khong len "head": phep kiem duoi do bat bien cua
    # migration NAY, nen no phai dung o day du sau nay co bao nhieu
    # migration khac chong len.
    command.upgrade(cfg, REV_H44)
    insp = inspect(create_engine(url))
    bang = set(insp.get_table_names())
    assert (BANG_V1 | BANG_V3) <= bang
    idx = {i["name"] for i in insp.get_indexes("chatltt_message")}
    assert {"ix_chatltt_msg_conv_parent", "ix_chatltt_msg_conv_created"} <= idx
    # Hai rang buoc DUY NHAT la cong chong duyet hai lan (02_HOP_DONG.md §2).
    idx_ap = {i["name"] for i in insp.get_indexes("chatltt_approval")}
    assert {"ux_chatltt_approval_step", "ux_chatltt_approval_idem"} <= idx_ap
    assert all(i["unique"] for i in insp.get_indexes("chatltt_approval")
               if i["name"] in ("ux_chatltt_approval_step", "ux_chatltt_approval_idem"))
    # Hai cot noi len run/step phai NULLABLE — moi hang V1 van hop le, khong backfill.
    cot = {c["name"]: c for c in insp.get_columns("chatltt_execution")}
    assert cot["run_id"]["nullable"] and cot["step_id"]["nullable"]

    # Xuong MOT buoc: mat dung phan H44, giu nguyen V1.
    command.downgrade(cfg, "-1")
    insp = inspect(create_engine(url))
    bang2 = set(insp.get_table_names())
    assert (bang - bang2) == BANG_V3, "xuong mot buoc phai xoa DUNG ba bang H44"
    assert BANG_V1 <= bang2, "hoi thoai cu KHONG duoc mat khi lui H44"
    cot2 = {c["name"] for c in insp.get_columns("chatltt_execution")}
    assert "run_id" not in cot2 and "step_id" not in cot2

    # Xuong tiep mot buoc nua: het sach chatltt_*  (menh de goc cua H43).
    command.downgrade(cfg, "-1")
    insp = inspect(create_engine(url))
    assert not {t for t in set(insp.get_table_names()) if t.startswith("chatltt_")}
