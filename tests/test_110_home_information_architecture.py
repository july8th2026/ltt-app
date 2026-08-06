"""H15.S3 HOME-002 — My Apps thật; nav chưa có backend phải defer rõ."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_my_apps_dung_toan_bo_lich_su_khong_chi_nam_job_gan_nhat(
        tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'home-ia.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", url)

    import platform_core.db as dbmod
    from platform_core.models import Job
    from platform_core.users import tao_nguoi_dung
    from server.routes.dashboard import _workspace_data

    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session(); db = next(gen)
    try:
        user = tao_nguoi_dung(
            db, email="home-ia@example.com", password="matkhau-tot-12",
            is_verified=True,
        )
        old = datetime(2026, 1, 1, tzinfo=timezone.utc)
        db.add(Job(
            user_id=user.id, app_slug="taoanh", job_type="taoanh.generate",
            created_at=old,
        ))
        for offset in range(1, 6):
            db.add(Job(
                user_id=user.id, app_slug="thumbnail",
                job_type="thumbnail.generate",
                created_at=old + timedelta(days=offset),
            ))
        db.commit()
        visible = [
            SimpleNamespace(manifest=SimpleNamespace(
                slug="taoanh", display_name="Tạo ảnh", icon="A")),
            SimpleNamespace(manifest=SimpleNamespace(
                slug="thumbnail", display_name="Thumbnail", icon="T")),
        ]

        result = _workspace_data(visible, user)

        assert len(result["recent"]) == 5
        assert {job.app_slug for job in result["recent"]} == {"thumbnail"}
        assert result["used_slugs"] == {"taoanh", "thumbnail"}
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
        dbmod.reset_engine()


def test_global_navigation_khong_con_link_gia():
    home = _read("server/templates/home.html")

    assert "> Agent Canvas</a>" in home
    assert 'href="/agent/canvas"><span aria-hidden="true">▱</span> Templates' not in home
    # H24: chu gio di qua catalog dich nen khong chot mat chu tho nua. Van chot
    # DIEU test nay sinh ra de chot: ba muc chua phat hanh phai bi vo hieu hoa
    # va co giai thich, chu khong phai link song dan toi trang trong.
    assert "_('Thư viện mẫu toàn nền tảng chưa được phát hành')" in home
    assert "_('Kho tài nguyên cá nhân chưa được phát hành')" in home
    assert home.count('class="market-deferred" disabled aria-disabled="true"') == 3
    for nhan in ("Mẫu", "Tài nguyên", "Cộng đồng"):
        assert f'_("{nhan}") }}}} <small>' in home, nhan
    assert home.count('<small>{{ _("Chưa có") }}</small>') == 3


def test_my_apps_co_empty_state_rieng():
    home = _read("server/templates/home.html")

    # H24: chuoi nay gio di qua catalog dich, va "Marketplace" tieng Anh giua
    # trang tieng Viet la LOI da sua. Van chot rang MY APPS co empty state RIENG
    # — do moi la dieu test nay canh.
    assert '_("Bạn chưa dùng app nào.")' in home
    assert '_("Quay lại kho ứng dụng và mở app đầu tiên.")' in home
    assert "emptyTitle.textContent=view==='mine'" in home
    assert "T_NO_MINE" in home and "T_NO_MATCH" in home

