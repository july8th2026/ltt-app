"""LTT WORKFLOW V2 · Đợt 3C — middleware trên CẠNH (3 hook).

Nguồn thiết kế: `23_24 §6` (bài học Node-RED, 6 hook). Mỗi lượt truyền qua một
cạnh đi qua `before_route → before_dispatch → after_dispatch`; hook trả `False`
thì **chặn**.

🔴 Đây là chỗ cắm cho `WF-903` — và `WF-903` là một lỗ **có thật**, không phải
   phòng xa:

     "validate_plan loc theo app_access (tot), nhung mot version DA PUBLISH
      co the chay sau khi quyen bi thu hoi."

⇒ Quyền phải kiểm **lúc thi hành**, không chỉ lúc validate. Một `WorkflowVersion`
  là **bất biến** — nó giữ nguyên nội dung đã duyệt kể cả khi quyền của chủ nó
  đã đổi. Đó là tính chất ta MUỐN cho việc tái dựng, và chính nó tạo ra lỗ này.

⭐ Vì sao là middleware chứ không phải một `if` trong scheduler: `WF-905` đòi đo
   được scheduler tự tiêu bao nhiêu. Mỗi luật quyền/đo/giới hạn nhét thẳng vào
   lõi là một nhánh nữa trong thứ ta đang cố giữ nhỏ.
"""
from __future__ import annotations

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'wf7.db').as_posix()}")
    import platform_core.db as dbmod

    dbmod.reset_engine()
    import platform_core.models  # noqa: F401

    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session()
    session = next(gen)
    try:
        yield session
    finally:
        session.close()
        dbmod.reset_engine()


@pytest.fixture()
def sach():
    """Sổ hook là trạng thái TOÀN CỤC — dọn trước và sau mỗi bài.

    ⚠️ Không dọn thì một bài đăng ký hook sẽ đổi kết quả của bài chạy sau nó, và
       lỗi ấy chỉ hiện ra khi thứ tự chạy đổi (`-p randomly`). Kho này đã có một
       mục memory cho đúng lớp đó: *trạng thái ngoài rò vào test*.
    """
    from platform_core.workflow import canh

    canh.xoa_het_hook()
    yield
    canh.xoa_het_hook()


def _canh(nguon="a", dich="b"):
    return {"id": "e1", "source_node": nguon, "source_port": "out",
            "target_node": dich, "target_port": "in", "kind": "DATA"}


# ── Ba hook chạy đúng thứ tự ─────────────────────────────────────────────────

def test_ba_hook_chay_dung_THU_TU(db, sach):
    from platform_core.workflow import canh

    da_chay = []
    canh.dang_ky("after_dispatch", lambda ctx: da_chay.append("after") or True)
    canh.dang_ky("before_route", lambda ctx: da_chay.append("route") or True)
    canh.dang_ky("before_dispatch", lambda ctx: da_chay.append("dispatch") or True)

    assert canh.truyen(db, _canh(), ngu_canh={}) is True
    assert da_chay == ["route", "dispatch", "after"]


def test_khong_co_hook_nao_thi_van_truyen_duoc(db, sach):
    from platform_core.workflow import canh

    assert canh.truyen(db, _canh(), ngu_canh={}) is True


# ── Chặn ──────────────────────────────────────────────────────────────────────

def test_hook_tra_False_thi_CHAN(db, sach):
    from platform_core.workflow import canh

    canh.dang_ky("before_route", lambda ctx: False)
    assert canh.truyen(db, _canh(), ngu_canh={}) is False


def test_bi_chan_thi_hook_SAU_khong_chay(db, sach):
    """Chặn phải là chặn thật — không được chạy tiếp rồi mới bỏ kết quả."""
    from platform_core.workflow import canh

    da_chay = []
    canh.dang_ky("before_route", lambda ctx: False)
    canh.dang_ky("before_dispatch", lambda ctx: da_chay.append("x") or True)
    canh.dang_ky("after_dispatch", lambda ctx: da_chay.append("y") or True)

    assert canh.truyen(db, _canh(), ngu_canh={}) is False
    assert da_chay == []


def test_ly_do_CHAN_den_duoc_ben_goi(db, sach):
    """Chặn mà không nói vì sao thì người vận hành phải đoán."""
    from platform_core.workflow import canh

    def _tu_choi(ctx):
        ctx["ly_do_chan"] = "tool `ltt_llm.chat` khong con trong app_access"
        return False

    canh.dang_ky("before_route", _tu_choi)
    ngu_canh: dict = {}
    assert canh.truyen(db, _canh(), ngu_canh=ngu_canh) is False
    assert "app_access" in ngu_canh["ly_do_chan"]


# ── `WF-903`: quyền kiểm LÚC THI HÀNH ────────────────────────────────────────

def test_WF903_quyen_bi_THU_HOI_sau_khi_publish_thi_bi_chan(db, sach):
    """🔴 Lỗ có thật: một version đã publish chạy sau khi quyền bị thu hồi.

    `WorkflowVersion` **bất biến** — nó giữ nguyên nội dung đã duyệt kể cả khi
    quyền của chủ nó đã đổi. Bất biến là tính chất ta MUỐN (tái dựng được), và
    chính nó tạo ra lỗ này. Nên bản vá không thể nằm ở `validate`, nó phải nằm ở
    **thời điểm truyền**.
    """
    from platform_core.workflow import canh

    duoc_phep = {"ltt_llm"}

    def _kiem_quyen(ctx):
        if ctx.get("app_slug") not in duoc_phep:
            ctx["ly_do_chan"] = f"khong co quyen: {ctx.get('app_slug')}"
            return False
        return True

    canh.dang_ky("before_dispatch", _kiem_quyen)

    assert canh.truyen(db, _canh(), ngu_canh={"app_slug": "ltt_llm"}) is True

    duoc_phep.clear()          # quyen bi thu hoi SAU khi version da publish
    ngu_canh: dict = {"app_slug": "ltt_llm"}
    assert canh.truyen(db, _canh(), ngu_canh=ngu_canh) is False
    assert "khong co quyen" in ngu_canh["ly_do_chan"]


# ── Hook hỏng không được giết scheduler ──────────────────────────────────────

def test_hook_NEM_LOI_thi_CHAN_chu_khong_lan_ra_scheduler(db, sach):
    """⛔ Một hook lỗi phải fail-CLOSED, và không được làm sập vòng lặp.

    Fail-closed vì hook là chỗ cắm của **kiểm quyền**: một hook quyền ném lỗi mà
    ta cho đi tiếp là **mở cổng khi bộ gác ngã**.
    """
    from platform_core.workflow import canh

    def _hong(ctx):
        raise RuntimeError("hook hong")

    canh.dang_ky("before_route", _hong)
    ngu_canh: dict = {}
    assert canh.truyen(db, _canh(), ngu_canh=ngu_canh) is False
    assert "hook hong" in ngu_canh["ly_do_chan"]


def test_hook_sau_KHONG_chay_khi_hook_truoc_nem_loi(db, sach):
    from platform_core.workflow import canh

    da_chay = []
    canh.dang_ky("before_route", lambda ctx: (_ for _ in ()).throw(
        RuntimeError("no")))
    canh.dang_ky("before_dispatch", lambda ctx: da_chay.append("x") or True)

    assert canh.truyen(db, _canh(), ngu_canh={}) is False
    assert da_chay == []


# ── Hợp đồng đăng ký ─────────────────────────────────────────────────────────

def test_dang_ky_diem_KHONG_TON_TAI_bi_tu_choi_NGAY(db, sach):
    """Gõ sai tên điểm cắm là một hook **không bao giờ chạy** — im lặng.

    Từ chối lúc đăng ký biến một lỗi im lặng thành một lỗi ồn ào, ở đúng chỗ
    người viết đang nhìn.
    """
    from platform_core.workflow import canh

    with pytest.raises(ValueError):
        canh.dang_ky("before_disptach", lambda ctx: True)   # go sai


def test_nhieu_hook_cung_mot_diem_chay_theo_thu_tu_dang_ky(db, sach):
    from platform_core.workflow import canh

    da_chay = []
    for i in range(3):
        canh.dang_ky("before_route",
                     lambda ctx, i=i: da_chay.append(i) or True)
    assert canh.truyen(db, _canh(), ngu_canh={}) is True
    assert da_chay == [0, 1, 2]


def test_hook_thay_doi_NGU_CANH_thi_hook_sau_nhin_thay(db, sach):
    """Ngữ cảnh là đường truyền giữa các hook — nếu không thì mỗi hook phải tự đo lại."""
    from platform_core.workflow import canh

    canh.dang_ky("before_route", lambda ctx: ctx.update(dau="A") or True)
    thay = []
    canh.dang_ky("before_dispatch", lambda ctx: thay.append(ctx.get("dau")) or True)

    assert canh.truyen(db, _canh(), ngu_canh={}) is True
    assert thay == ["A"]
