"""`/health/version` phải nói được **bản nào đang chạy**.

## Sự cố sinh ra tệp này

Ngày 05/09/2026: kho ghi `TRAN_KY_TU_CONG_KHAI = 100_000`, trang web hiện
`0 / 1500 ký tự`. Gần trọn một buổi trôi qua trước khi biết vì sao, và câu trả
lời hoá ra tầm thường — `C:\\LTTPlatform\\app\\` giữ một bản chép từ thời
`master`, trong khi nhánh làm việc đã đi trước **94 lượt commit**.

⛔ Không có cache nào dính dáng. Nhưng để chứng minh điều đó phải so `md5sum`
   của `/static/voice.js` giữa hai thư mục — vì **không endpoint nào trả lời
   được "máy chủ đang chạy mã nào"**. `/health/version` khi ấy trả `"v1.0"`,
   đọc từ `version.py` của *LTTStudios VideoBot*, một hằng số gõ tay từ 2025
   không đổi qua bất kỳ lần deploy nào.

⭐ Bài học không phải "nhớ deploy". Là: **một hệ thống không tự nói được nó là
   bản nào thì mọi câu hỏi về nó đều phải trả lời bằng suy luận**, và suy luận
   trên chứng cứ gián tiếp là chỗ mà `docs/` của dự án này đã ghi lại nhiều
   lần rằng người ta đi sai.

## Ba trường, ba kiểu trôi ĐỘC LẬP

    `commit`     mã nguồn trôi     (bản deploy cũ hơn kho)
    `asset_ver`  tài sản tĩnh trôi (Cloudflare giữ CSS/JS cũ)
    `ltt_voice`  hợp đồng trôi     (trần sản phẩm nói một đằng, chạy một nẻo)

Chúng hỏng riêng rẽ — deploy đúng mà CF giữ CSS cũ là một ca; deploy cũ mà CF
sạch là ca khác. Gộp lại một trường thì không phân biệt được, mà phân biệt
chính là toàn bộ giá trị của endpoint.
"""
from __future__ import annotations

import json

import pytest


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'vt.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-dau-van-tay")

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    from fastapi.testclient import TestClient

    from server.app import create_app
    c = TestClient(create_app(), base_url="https://testserver")
    try:
        yield c
    finally:
        c.close()
        dbmod.reset_engine()


def test_version_tra_ba_kieu_troi(client):
    """Ba trường phải CÓ MẶT, kể cả khi giá trị rỗng.

    ⚠️ Vắng mặt và rỗng là hai câu trả lời khác nhau. Một khoá vắng đọc thành
       "phiên bản này không biết khái niệm ấy"; một khoá rỗng đọc thành "biết,
       nhưng không tra được" — và chỉ cái thứ hai mới bảo người đọc đi sửa
       marker.
    """
    r = client.get("/health/version")
    assert r.status_code == 200
    d = r.json()
    for k in ("version", "commit", "commit_nguon", "asset_ver", "hop_dong"):
        assert k in d, f"thieu khoa {k!r} — xem docstring ve ba kieu troi"


def test_tran_lay_TU_MODULE_khong_go_lai(client):
    """⛔ Con số ở endpoint phải là con số app đang dùng, không phải bản sao.

    Một hằng số gõ lại trong chính công cụ dựng ra để phát hiện trôi thì sẽ
    trôi cùng — và khi đó nó xác nhận trạng thái sai một cách rất thuyết phục.
    """
    from apps.ltt_voice.tham_so_cong_khai import (TRAN_KY_TU_CONG_KHAI,
                                                  TRAN_MOI_LUOT_SINH)
    hd = client.get("/health/version").json()["hop_dong"]
    assert hd is not None, "doc hop dong HONG — khac han voi khong app nao khai"
    d = hd.get("ltt_voice")
    assert d, "app ltt_voice co trong ban build, phai bao cao tran"
    assert d["tran_ky_tu_cong_khai"] == TRAN_KY_TU_CONG_KHAI
    assert d["tran_moi_luot_sinh"] == TRAN_MOI_LUOT_SINH


def test_server_KHONG_import_ten_app_nao(client):
    """⛔ `/health/version` phải app-agnostic. Đây là chốt kiến trúc.

    🔴 BẢN VÁ ĐẦU CỦA TÔI PHÁ LUẬT NÀY, và `tests/test_147_layering.py` bắt
       được: `health.py` viết `from apps.ltt_voice.tham_so_cong_khai import ...`.

    ⭐ Phép kiểm ấy không chỉ chặn — nó chỉ ra bản sửa **tốt hơn**. Một endpoint
       biết tên `ltt_voice` là một endpoint phải sửa mỗi lần thêm app; đọc qua
       `AppManifest.hop_dong_cong_khai` thì app nào khai, app ấy hiện — kể cả
       app viết sau `health.py`.

    ⚠️ `test_147` đã chốt điều này cho cả cây `server/`. Phép kiểm ở đây hẹp hơn
       nhưng nằm CẠNH thứ nó bảo vệ, nên người sửa `health.py` đọc được lý do mà
       không phải đi tìm.
    """
    import pathlib
    ma = (pathlib.Path(__file__).resolve().parents[1]
          / "server" / "routes" / "health.py").read_text(encoding="utf-8")
    dong_ma = [d for d in ma.splitlines()
               if not d.strip().startswith("#") and "import apps." in d
               or (not d.strip().startswith("#") and "from apps." in d)]
    assert not dong_ma, (
        f"health.py import thang tu apps/: {dong_ma}. Khai vao "
        "`AppManifest.hop_dong_cong_khai` roi doc qua `registry.discover()`.")


def test_asset_ver_khop_thu_trang_thuc_su_dinh_kem(client):
    """`asset_ver` phải là ĐÚNG chuỗi mà trang HTML gắn vào `?v=`.

    Nếu hai chỗ lệch nhau thì endpoint này trở thành nguồn thứ hai của cùng
    một sự thật — và bản sai sẽ là bản không ai nhớ cập nhật.
    """
    from server.templating import ASSET_VER
    assert client.get("/health/version").json()["asset_ver"] == ASSET_VER
    assert ASSET_VER, "asset_ver rong thi cache-bust khong con hoat dong"


# ── Bản thân bộ đọc dấu vân tay ────────────────────────────────────────────

def test_marker_hong_khong_lam_sap_endpoint(tmp_path, monkeypatch):
    """Marker rác phải cho `khong-ro`, KHÔNG được ném.

    ⛔ Một endpoint chẩn đoán mà chết vì thứ nó chẩn đoán là một endpoint chỉ
       hoạt động khi không ai cần tới nó.
    """
    from platform_core import dau_van_tay
    monkeypatch.setattr(dau_van_tay, "GOC", tmp_path)
    (tmp_path / dau_van_tay.TEN_TEP).write_text("{khong phai json",
                                                encoding="utf-8")
    assert dau_van_tay.doc()["nguon"] == "khong-ro"


def test_marker_doc_duoc_va_cat_ngan_sha(tmp_path, monkeypatch):
    """SHA cắt còn 12 ký tự — đủ để đối chiếu `git log`, không hơn."""
    from platform_core import dau_van_tay
    monkeypatch.setattr(dau_van_tay, "GOC", tmp_path)
    (tmp_path / dau_van_tay.TEN_TEP).write_text(
        json.dumps({"commit": "0123456789abcdef0123456789abcdef01234567",
                    "luc": "2026-09-05T12:00:00"}), encoding="utf-8")
    d = dau_van_tay.doc()
    assert d == {"commit": "0123456789ab", "luc": "2026-09-05T12:00:00",
                 "nguon": "marker"}


def test_marker_thieu_commit_bi_coi_la_khong_co(tmp_path, monkeypatch):
    """JSON hợp lệ nhưng không có `commit` thì vẫn là không có câu trả lời.

    ⚠️ Đây là ca mà `json.loads` **thành công** — nên nếu chỉ bắt ngoại lệ thì
       hàm sẽ trả `{"commit": "", "nguon": "marker"}`, tức nó khẳng định đã đọc
       được một dấu vân tay rỗng. Rỗng-mà-tự-tin là dạng sai tệ nhất ở đây.
    """
    from platform_core import dau_van_tay
    monkeypatch.setattr(dau_van_tay, "GOC", tmp_path)
    (tmp_path / dau_van_tay.TEN_TEP).write_text('{"luc": "hom qua"}',
                                                encoding="utf-8")
    assert dau_van_tay.doc()["nguon"] != "marker"


def test_endpoint_khong_fork_git_moi_luot(client, monkeypatch):
    """⛔ `/health/version` KHÔNG được chạy `git` mỗi lượt gọi.

    🔴 MỘT LỖ MỞ RA RỒI ĐÓNG LẠI TRONG CÙNG MỘT LƯỢT.

       Endpoint này **không có xác thực** — đó là thiết kế, reverse proxy dựa
       vào nó. Bản đầu gọi thẳng `dau_van_tay.doc()`, mà `doc()` có thể chạy
       `subprocess.run(["git", ...])`. Ghép lại: một endpoint công khai **fork
       một tiến trình con mỗi lượt gọi**.

    ⚠️ Trên máy chủ thật `.git` không có nên nhánh git không chạy — nhưng "an
       toàn vì tình cờ thiếu một tệp" không phải an toàn, và một cây nguồn chạy
       production là một cấu hình có thật (chính `commit_nguon` sinh ra để phát
       hiện nó).

    ⭐ Phép kiểm đếm số lần `_tu_git` được gọi qua **năm** lượt HTTP. Nó phải là
       **không** — `lru_cache` đã nạp giá trị từ lượt dựng app.
    """
    from platform_core import dau_van_tay
    dem = {"n": 0}
    that = dau_van_tay._tu_git

    def dem_git():
        dem["n"] += 1
        return that()

    monkeypatch.setattr(dau_van_tay, "_tu_git", dem_git)
    dau_van_tay.doc_da_cache()          # nap cache neu chua
    for _ in range(5):
        assert client.get("/health/version").status_code == 200
    assert dem["n"] == 0, (
        f"_tu_git chay {dem['n']} lan qua 5 luot HTTP — endpoint cong khai "
        "dang fork mot tien trinh con moi luot goi")


def test_cache_tra_ban_KHONG_sua_duoc_tu_ben_ngoai():
    """`lru_cache` trả chính đối tượng đã nhớ ⇒ nó phải bất biến.

    ⛔ Nếu `doc_da_cache()` trả `dict`, người gọi đầu tiên sửa nó là sửa **bộ
       nhớ đệm dùng chung** — và mọi lượt sau nhận bản đã bị sửa. Lỗi ấy hỏng
       im lặng và chỉ hiện ra ở lượt gọi tiếp theo, tức xa chỗ gây ra nó.
    """
    from platform_core import dau_van_tay
    a = dau_van_tay.doc_da_cache()
    assert isinstance(a, tuple), "phai la tuple (bat bien), khong phai dict"
    assert dau_van_tay.doc_da_cache() is a, "phai la CUNG mot doi tuong"
    assert dict(a).keys() >= {"commit", "luc", "nguon"}


def test_deploy_ghi_marker_bang_write_nobom():
    """⛔ `setup/2-cai-dat.ps1` phải ghi marker, và ghi KHÔNG BOM.

    Quy tắc 1 của `CLAUDE.md`: PowerShell 5.1 chèn BOM với `Out-File`/
    `Set-Content`, `json.load()` vỡ, và `/health/ready` trả 503 trong khi dịch
    vụ vẫn chạy bình thường. Lỗi đó **đã thực sự làm sập production** ở dự án
    này — nên một tệp JSON mới do script ghi phải đi qua `Write-NoBom`.
    """
    import pathlib
    ps1 = (pathlib.Path(__file__).resolve().parents[1]
           / "setup" / "2-cai-dat.ps1").read_text(encoding="utf-8")
    assert "dau_van_tay.json" in ps1, "deploy khong ghi dau van tay"
    assert "Write-NoBom $vanTay" in ps1, (
        "marker phai ghi bang Write-NoBom; Out-File/Set-Content cua PS 5.1 "
        "chen BOM va json.load() se vo")
    assert "Remove-Item $vanTay" in ps1, (
        "khong doc duoc commit thi phai XOA marker cu — mot marker cu la mot "
        "cau tra loi SAI ma trong nhu that")
