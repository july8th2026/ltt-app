"""Kho tài nguyên PROMPT AI OMMI — bất biến sở hữu.

Vì sao file này tồn tại trước cả endpoint: module nguồn (`D:\\BOT GEMINI`) khai
ba tầng sở hữu nhưng `scoping.py` lọc mọi truy vấn theo một `master_user_id`
dùng chung, nên trên thực tế mọi khách hàng nhìn chung một kho. Đây là lỗi
loại P0 và nó **không lộ ra khi thử một mình** — chỉ lộ khi có người thứ hai.

Nên bất biến sở hữu phải được chốt từ lúc dựng bảng, không phải sau khi viết
xong API. Hai test dưới đây là khuôn: mọi endpoint kho tài nguyên thêm về sau
phải dùng `assert_cross_user_404` chứ không tự nghĩ cách kiểm riêng.
"""
from __future__ import annotations

import pytest

from platform_core.db import Base
from platform_core.registry import load_app_tables

# Bảng chỉ chứa quan hệ giữa hai bản ghi đã có chủ; chủ sở hữu suy ra từ bảng
# cha, thêm cột owner_id vào đây là dữ liệu trùng lặp có thể lệch nhau.
_JOIN_TABLES = {"ommi_resource_tag", "ommi_collection_item"}


@pytest.fixture(scope="module", autouse=True)
def _load_tables():
    load_app_tables()


def _ommi_tables():
    return {name: table for name, table in Base.metadata.tables.items()
            if name.startswith("ommi_")}


def test_every_ommi_data_table_carries_an_owner():
    """Bảng dữ liệu thiếu `owner_id` thì không có cách nào lọc theo người dùng —
    lập trình viên sau sẽ viết truy vấn không điều kiện và không ai thấy sai."""
    missing = [name for name, table in _ommi_tables().items()
               if name not in _JOIN_TABLES and "owner_id" not in table.c]
    assert missing == [], f"bảng thiếu owner_id: {missing}"


def test_owner_column_is_indexed():
    """Mọi truy vấn kho đều lọc theo owner_id. Không index thì kho lớn phải quét
    toàn bảng, và người dùng đông lên là chậm cho tất cả cùng lúc."""
    unindexed = []
    for name, table in _ommi_tables().items():
        if name in _JOIN_TABLES or "owner_id" not in table.c:
            continue
        column = table.c["owner_id"]
        covered = column.index or any(
            index.columns.keys()[:1] == ["owner_id"] for index in table.indexes)
        if not covered:
            unindexed.append(name)
    assert unindexed == [], f"owner_id chưa được index: {unindexed}"


def test_catalog_tables_allow_a_null_owner():
    """Mẫu catalog do admin publish có `owner_id` NULL. Bảng khai NOT NULL thì
    không publish mẫu được, và người ta sẽ lách bằng cách gán bừa cho một tài
    khoản admin — đúng cái namespace dùng chung mà ta đang tránh."""
    catalog = ("ommi_meta_prompt", "ommi_prompt_snippet", "ommi_style",
               "ommi_resource")
    wrong = [name for name in catalog
             if not _ommi_tables()[name].c["owner_id"].nullable]
    assert wrong == [], f"bảng catalog không cho owner_id NULL: {wrong}"


def assert_cross_user_404(client_b, token_b, paths):
    """Khuôn dùng lại: user B chạm tài nguyên của user A phải nhận 404.

    404 chứ không phải 403 — 403 xác nhận bản ghi có tồn tại, tức vẫn rò rỉ
    thông tin cho người đi dò ID.
    """
    for method, path in paths:
        response = client_b.request(method, path,
                                    headers={"X-CSRF-Token": token_b})
        assert response.status_code == 404, (
            f"{method} {path} trả {response.status_code}, phải là 404")
