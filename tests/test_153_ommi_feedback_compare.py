"""
test_153 - H19.5: chạy lại kèm góp ý, và so hai bản cạnh nhau.

Vấn đề thật của người dùng: sau vài lần bấm "Chạy lại", họ có 5 ảnh na ná nhau
và **không nhớ bản nào ứng với yêu cầu nào**. Hai thứ sửa việc đó:

1. Góp ý được lưu vào chính bản sinh RA từ nó → lịch sử trả lời được "vì sao
   bản này khác bản trước".
2. Hai bản đặt cạnh nhau kèm phần prompt đã đổi → so, thay vì đoán.

Cách hỏng đắt nhất và cũng tinh vi nhất: **góp ý đặt sai chỗ trong prompt**.
Nếu nó nằm trước phần `continuity`, phần đó kéo ảnh về như cũ và người dùng
tưởng hệ thống bỏ qua góp ý của mình.
"""
from __future__ import annotations

import pytest

from apps.prompt_ai_ommi.services import storyboard as svc

A = "user-a"
B = "user-b"
PROJECT = "project-1"


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'fb.db').as_posix()}")
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    session = next(dbmod.get_session())
    yield session
    session.close()
    dbmod.reset_engine()


def _canh(db, owner=A, **kw):
    board = svc.create_board(db, owner_id=owner, project_id=PROJECT, name="Bảng")
    db.commit()
    kw.setdefault("prompt", "Một người đứng trên đồi lúc hoàng hôn")
    scene = svc.add_scene(db, board_id=board.id, owner_id=owner, **kw)
    db.commit()
    return board, scene


# ── Góp ý phải THẮNG mọi thứ phía trên ──────────────────────────────────────

def test_gop_y_nam_CUOI_prompt_sau_ca_continuity(db):
    """Đây là cách hỏng tinh vi nhất của tính năng này.

    `continuity` tồn tại để giữ cảnh giống bản trước. Nếu góp ý đứng TRƯỚC nó,
    continuity sẽ kéo ảnh về như cũ — hệ thống trông như đang bỏ qua yêu cầu
    người dùng, mà log thì sạch bong.
    """
    _, scene = _canh(db, camera="góc rộng")
    svc.update_scene(db, scene_id=scene.id, owner_id=A,
                     continuity="giữ nguyên bố cục và ánh sáng như bản trước")
    db.commit()
    prompt = svc.compose_prompt(db, scene_id=scene.id, owner_id=A,
                                feedback="đổi sang trời mưa")

    vi_tri_gop_y = prompt.find("đổi sang trời mưa")
    vi_tri_continuity = prompt.find("giữ nguyên bố cục")
    assert vi_tri_gop_y > vi_tri_continuity > -1, (
        "góp ý đứng trước continuity — continuity sẽ kéo ảnh về như cũ và người "
        "dùng tưởng góp ý bị bỏ qua")


def test_gop_y_co_nhan_ro_rang_chu_khong_dinh_thang_vao(db):
    """Dán trần câu góp ý vào cuối prompt thì model đọc nó như một phần mô tả
    cảnh, không phải như một chỉ thị sửa."""
    _, scene = _canh(db)
    prompt = svc.compose_prompt(db, scene_id=scene.id, owner_id=A,
                                feedback="bỏ cái cây bên trái")
    assert "Điều chỉnh so với bản trước:" in prompt


def test_khong_gop_y_thi_prompt_khong_doi(db):
    """Tính năng mới không được đổi hành vi của đường chạy cũ."""
    _, scene = _canh(db)
    a = svc.compose_prompt(db, scene_id=scene.id, owner_id=A)
    b = svc.compose_prompt(db, scene_id=scene.id, owner_id=A, feedback="")
    c = svc.compose_prompt(db, scene_id=scene.id, owner_id=A, feedback="   ")
    assert a == b == c
    assert "Điều chỉnh so với bản trước" not in a


def test_gop_y_qua_dai_bi_cat_chu_khong_day_prompt_that_ra_ngoai(db):
    """Ô nhập bị dán nguyên bài không được đẩy prompt thật ra khỏi trần."""
    _, scene = _canh(db)
    prompt = svc.compose_prompt(db, scene_id=scene.id, owner_id=A,
                                feedback="x" * 5000)
    assert len(prompt) <= svc.MAX_PROMPT
    assert "Một người đứng trên đồi" in prompt, "prompt gốc bị góp ý đẩy ra ngoài"
    assert prompt.count("x") <= svc.MAX_FEEDBACK


# ── Lịch sử phải nhớ VÌ SAO ─────────────────────────────────────────────────

def test_gop_y_duoc_luu_vao_ban_sinh_ra_tu_no(db):
    _, scene = _canh(db)
    svc.record_version(db, scene_id=scene.id, owner_id=A, image_key="k1")
    svc.record_version(db, scene_id=scene.id, owner_id=A, image_key="k2",
                       feedback="sáng hơn")
    db.commit()

    ban = {v.version: v for v in svc.versions(db, scene.id, A)}
    assert ban[1].feedback == "", "bản đầu không có góp ý"
    assert ban[2].feedback == "sáng hơn", (
        "lịch sử không nhớ vì sao bản 2 khác bản 1")


# ── So hai bản ──────────────────────────────────────────────────────────────

def test_so_hai_ban_tra_ve_ca_prompt_gop_y_va_phan_khac_nhau(db):
    _, scene = _canh(db)
    svc.update_scene(db, scene_id=scene.id, owner_id=A, prompt="Trời nắng")
    svc.record_version(db, scene_id=scene.id, owner_id=A, image_key="k1")
    svc.update_scene(db, scene_id=scene.id, owner_id=A, prompt="Trời mưa")
    svc.record_version(db, scene_id=scene.id, owner_id=A, image_key="k2",
                       feedback="đổi thời tiết")
    db.commit()

    ra = svc.compare_versions(db, scene_id=scene.id, owner_id=A, left=1, right=2)
    assert ra["left"]["version"] == 1 and ra["right"]["version"] == 2
    assert ra["left"]["image_key"] == "k1" and ra["right"]["image_key"] == "k2"
    assert ra["right"]["feedback"] == "đổi thời tiết"
    assert ra["cung_anh"] is False
    noi_dung = " ".join(ra["prompt_khac_nhau"])
    assert "Trời nắng" in noi_dung and "Trời mưa" in noi_dung, (
        "không chỉ ra phần prompt đã đổi — người dùng phải tự dò hai đoạn văn")


def test_so_hai_ban_bao_khi_HAI_BAN_GIONG_HET_anh(db):
    """Chạy lại mà ra đúng ảnh cũ là chuyện có thật (cache provider). Người dùng
    phải biết ngay, không phải soi hai ảnh bằng mắt."""
    _, scene = _canh(db)
    svc.record_version(db, scene_id=scene.id, owner_id=A, image_key="giong-nhau")
    svc.record_version(db, scene_id=scene.id, owner_id=A, image_key="giong-nhau")
    db.commit()
    ra = svc.compare_versions(db, scene_id=scene.id, owner_id=A, left=1, right=2)
    assert ra["cung_anh"] is True


def test_so_ban_khong_ton_tai_thi_bao_khong_tim_thay(db):
    _, scene = _canh(db)
    svc.record_version(db, scene_id=scene.id, owner_id=A, image_key="k1")
    db.commit()
    with pytest.raises(svc.StoryboardNotFound):
        svc.compare_versions(db, scene_id=scene.id, owner_id=A, left=1, right=99)


def test_khong_so_duoc_canh_cua_nguoi_khac(db):
    """Cảnh của người khác phải là 'không tìm thấy', không phải 'không có quyền'
    — trả 403 là xác nhận cảnh đó tồn tại."""
    _, scene = _canh(db, owner=A)
    svc.record_version(db, scene_id=scene.id, owner_id=A, image_key="k1")
    svc.record_version(db, scene_id=scene.id, owner_id=A, image_key="k2")
    db.commit()
    with pytest.raises((svc.StoryboardNotFound, LookupError)):
        svc.compare_versions(db, scene_id=scene.id, owner_id=B, left=1, right=2)
