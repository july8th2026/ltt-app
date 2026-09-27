"""Storyboard OMMI — cảnh, thứ tự, phiên bản, ghép prompt.

Hai thứ đáng bảo vệ nhất ở đây:

1. **Chạy lại một cảnh** không đụng cảnh khác và không mất bản cũ. Không có nó
   thì sửa một khung phải trả tiền dựng lại cả bộ.
2. **Ghép prompt** chỉ lấy tài nguyên và phong cách của chính người gọi — chuỗi
   này đi thẳng vào provider.
"""
from __future__ import annotations

import pytest

from apps.prompt_ai_ommi.services import resources as rsvc
from apps.prompt_ai_ommi.services import storyboard as svc
from apps.prompt_ai_ommi.tables import OmmiScene, OmmiStyle

A = "user-a"
B = "user-b"
PROJECT = "project-1"


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'sb.db').as_posix()}")
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


def _board(db, owner=A, name="Bảng của tôi"):
    row = svc.create_board(db, owner_id=owner, project_id=PROJECT, name=name)
    db.commit()
    return row


def _scene(db, board, owner=A, **kw):
    row = svc.add_scene(db, board_id=board.id, owner_id=owner, **kw)
    db.commit()
    return row


# ── sở hữu ─────────────────────────────────────────────────────────────────

def test_other_user_cannot_touch_a_board(db):
    board = _board(db)
    with pytest.raises(svc.StoryboardNotFound):
        svc.get_owned_board(db, board.id, B)
    with pytest.raises(svc.StoryboardNotFound):
        svc.update_board(db, board_id=board.id, owner_id=B, name="Cướp")
    with pytest.raises(svc.StoryboardNotFound):
        svc.add_scene(db, board_id=board.id, owner_id=B)


def test_other_user_cannot_touch_a_scene(db):
    board = _board(db)
    scene = _scene(db, board, title="Cảnh 1")
    with pytest.raises(svc.StoryboardNotFound):
        svc.update_scene(db, scene_id=scene.id, owner_id=B, title="Cướp")
    with pytest.raises(svc.StoryboardNotFound):
        svc.delete_scene(db, scene_id=scene.id, owner_id=B)
    assert db.get(OmmiScene, scene.id).title == "Cảnh 1"


def test_boards_are_listed_per_user(db):
    _board(db, A, "Của A")
    _board(db, B, "Của B")
    assert [r.name for r in svc.list_boards(db, A)] == ["Của A"]


# ── thứ tự cảnh ────────────────────────────────────────────────────────────

def test_scenes_get_sequential_positions(db):
    board = _board(db)
    for index in range(3):
        _scene(db, board, title=f"Cảnh {index}")
    assert [s.position for s in svc.scenes(db, board.id, A)] == [0, 1, 2]


def test_deleting_a_scene_closes_the_gap(db):
    """Để hở chỗ trong `position` thì lần chèn sau tính sai và cảnh nhảy lung
    tung — người dùng thấy như dữ liệu hỏng."""
    board = _board(db)
    first = _scene(db, board, title="Một")
    _scene(db, board, title="Hai")
    _scene(db, board, title="Ba")
    svc.delete_scene(db, scene_id=first.id, owner_id=A)
    db.commit()
    remaining = svc.scenes(db, board.id, A)
    assert [s.title for s in remaining] == ["Hai", "Ba"]
    assert [s.position for s in remaining] == [0, 1]


def test_reorder_requires_the_exact_set_of_scenes(db):
    board = _board(db)
    one = _scene(db, board, title="Một")
    two = _scene(db, board, title="Hai")
    with pytest.raises(svc.StoryboardError):
        svc.reorder(db, board_id=board.id, owner_id=A, scene_ids=[one.id])
    svc.reorder(db, board_id=board.id, owner_id=A, scene_ids=[two.id, one.id])
    db.commit()
    assert [s.title for s in svc.scenes(db, board.id, A)] == ["Hai", "Một"]


def test_scene_count_is_capped(db):
    board = _board(db)
    for index in range(svc.MAX_KHUNG_HINH):
        svc.add_scene(db, board_id=board.id, owner_id=A, title=str(index))
    db.commit()
    with pytest.raises(svc.StoryboardError):
        svc.add_scene(db, board_id=board.id, owner_id=A)


# ── phiên bản theo cảnh ────────────────────────────────────────────────────

def test_rerunning_one_scene_keeps_the_previous_image(db):
    board = _board(db)
    scene = _scene(db, board, prompt="canh mot")
    svc.record_version(db, scene_id=scene.id, owner_id=A, image_key="k/1.png")
    svc.record_version(db, scene_id=scene.id, owner_id=A, image_key="k/2.png")
    db.commit()

    assert db.get(OmmiScene, scene.id).image_key == "k/2.png"
    history = svc.versions(db, scene.id, A)
    assert [v.image_key for v in history] == ["k/2.png", "k/1.png"]


def test_rerunning_one_scene_leaves_the_others_alone(db):
    board = _board(db)
    one = _scene(db, board, title="Một")
    two = _scene(db, board, title="Hai")
    svc.record_version(db, scene_id=one.id, owner_id=A, image_key="k/1.png")
    db.commit()
    assert db.get(OmmiScene, two.id).image_key == ""
    assert db.get(OmmiScene, two.id).version == 1


def test_restoring_a_version_does_not_erase_history(db):
    board = _board(db)
    scene = _scene(db, board)
    svc.record_version(db, scene_id=scene.id, owner_id=A, image_key="k/1.png")
    svc.record_version(db, scene_id=scene.id, owner_id=A, image_key="k/2.png")
    db.commit()
    svc.restore_version(db, scene_id=scene.id, owner_id=A, version=1)
    db.commit()
    assert db.get(OmmiScene, scene.id).image_key == "k/1.png"
    assert len(svc.versions(db, scene.id, A)) == 2


def test_versions_of_another_user_are_not_readable(db):
    board = _board(db)
    scene = _scene(db, board)
    svc.record_version(db, scene_id=scene.id, owner_id=A, image_key="k/1.png")
    db.commit()
    with pytest.raises(svc.StoryboardNotFound):
        svc.versions(db, scene.id, B)


# ── tài nguyên gắn vào cảnh ────────────────────────────────────────────────

def test_a_scene_only_keeps_resources_the_owner_holds(db):
    """Danh sách này đi thẳng vào tham số job. ID của người khác lọt vào là ép
    provider đọc ảnh riêng tư của họ."""
    board = _board(db)
    mine = rsvc.create(db, owner_id=A, kind="character", name="Của tôi")
    theirs = rsvc.create(db, owner_id=B, kind="character", name="Của người khác")
    db.commit()

    scene = _scene(db, board, resource_ids=[mine.id, theirs.id, "khong-co-that"])
    assert scene.resource_ids == [mine.id]


def test_updating_resources_applies_the_same_filter(db):
    board = _board(db)
    scene = _scene(db, board)
    theirs = rsvc.create(db, owner_id=B, kind="character", name="Của người khác")
    db.commit()
    svc.update_scene(db, scene_id=scene.id, owner_id=A,
                     resource_ids=[theirs.id])
    db.commit()
    assert db.get(OmmiScene, scene.id).resource_ids == []


# ── ghép prompt ────────────────────────────────────────────────────────────

def test_prompt_puts_style_first_then_resources_then_the_scene(db):
    board = _board(db)
    style = OmmiStyle(owner_id=A, name="Điện ảnh", body="anh sang dien anh")
    db.add(style); db.commit()
    svc.update_board(db, board_id=board.id, owner_id=A, style_id=style.id)

    hero = rsvc.create(db, owner_id=A, kind="character", name="Nam chính",
                       prompt_text="ao khoac nau")
    db.commit()
    scene = _scene(db, board, prompt="dung truoc quan ca phe",
                   camera="trung canh", resource_ids=[hero.id])
    svc.update_scene(db, scene_id=scene.id, owner_id=A, continuity="giu anh sang")
    db.commit()

    composed = svc.compose_prompt(db, scene_id=scene.id, owner_id=A)
    assert composed.splitlines() == [
        "anh sang dien anh",
        "Nam chính: ao khoac nau",
        "dung truoc quan ca phe",
        "trung canh",
        "giu anh sang",
    ]


def test_prompt_ignores_a_style_owned_by_someone_else(db):
    board = _board(db)
    stolen = OmmiStyle(owner_id=B, name="Của người khác", body="bi mat cua ho")
    db.add(stolen); db.commit()
    # Gán thẳng vào CSDL để mô phỏng ID lọt qua đường khác.
    board.style_id = stolen.id
    db.commit()
    scene = _scene(db, board, prompt="noi dung canh")
    assert svc.compose_prompt(db, scene_id=scene.id, owner_id=A) == "noi dung canh"


def test_catalog_style_is_allowed(db):
    board = _board(db)
    catalog = OmmiStyle(owner_id=None, name="Mẫu", body="phong cach mau",
                        is_catalog=True)
    db.add(catalog); db.commit()
    svc.update_board(db, board_id=board.id, owner_id=A, style_id=catalog.id)
    scene = _scene(db, board, prompt="canh")
    db.commit()
    assert svc.compose_prompt(db, scene_id=scene.id, owner_id=A) == (
        "phong cach mau\ncanh")


def test_reference_keys_come_from_the_owners_resources_only(db):
    board = _board(db)
    hero = rsvc.create(db, owner_id=A, kind="character", name="Nam chính")
    rsvc.add_variant(db, resource_id=hero.id, owner_id=A, storage_key="ommi/a/1.png")
    db.commit()
    scene = _scene(db, board, resource_ids=[hero.id])
    assert svc.reference_keys(db, scene_id=scene.id, owner_id=A) == ["ommi/a/1.png"]
