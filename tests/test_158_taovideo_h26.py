"""H26.7 — public name, honest quote and customer-facing Seedance UI."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_public_name_is_tao_video_seedance_without_changing_slug():
    from apps.taovideo.manifest import MANIFEST

    assert MANIFEST.display_name == "Tạo Video Seedance"
    assert MANIFEST.nav[0].label == "Tạo Video Seedance"
    assert MANIFEST.slug == "taovideo"
    assert MANIFEST.route_prefix == "/taovideo"
    assert MANIFEST.job_types == ("taovideo.generate",)


def test_estimate_shows_the_confirmed_cap_for_two_variants(monkeypatch):
    from apps.taovideo.manifest import MANIFEST
    from apps.taovideo.routes import estimate

    monkeypatch.setenv("LTT_SESSION_SECRET", "seedance-quote-test")
    params = {"model": "seedance-2.0-mini", "resolution": "480p", "duration": 5}
    expected = MANIFEST.credit_cost(params) * 2
    response = estimate(None, model=params["model"], resolution=params["resolution"],
                        duration=str(params["duration"]), aspect_ratio="16:9",
                        count="2", quote_has_video="0", user="test")
    body = response.body.decode("utf-8")
    assert f"{expected} credit tối đa" in body
    assert "2 video" in body and "không thu vượt mức xác nhận" in body
    assert 'name="quote_id"' in body


def test_customer_ui_keeps_real_controls_and_hides_advanced_options_by_default():
    page = _read("apps/taovideo/templates/taovideo.html")

    assert '{% block title %}{{ _("Tạo Video Seedance") }} — LTT AI Studio{% endblock %}' in page
    assert '<details class="tv-fieldset tv-assist"' in page
    assert 'name="camera"' in page and 'name="motion"' in page
    assert 'name="visual_style"' in page and 'name="seed"' in page
    assert page.count('class="tv-file-input"') == 3
    assert 'accept="image/*"' in page
    assert 'accept="video/mp4,video/quicktime,video/webm"' in page
    assert 'accept="audio/*"' in page
    assert 'name="ref_videos"' in page and 'name="ref_audios"' in page
    assert 'name="quote_has_video"' in page
    assert 'hx-params="not ref_images, ref_videos, ref_audios, ref_roles, ref_handles"' in page
    assert 'name="duration"' in page and 'name="aspect_ratio"' in page
    assert 'name="resolution"' in page and 'name="count"' in page
    assert 'name="generate_audio"' in page


def test_library_has_owner_history_filters_and_persisted_density_without_fake_actions():
    page = _read("apps/taovideo/templates/taovideo.html")
    routes = _read("apps/taovideo/routes.py")

    assert 'name="model"' in page and 'name="aspect"' in page and 'name="sort"' in page
    assert "('cancelled','Đã hủy')" in page
    assert 'data-view="grid"' in page and 'data-view="list"' in page
    assert "localStorage.setItem('ltt.taovideo.view',view)" in page
    assert '{{ _("Nhật ký") }}' in page and 'href="/jobs/{{j.id}}"' in page
    assert "model_filter in models.MODELS" in routes
    assert "aspect_filter in known_aspects" in routes
    assert "Xóa" not in page and "Retry" not in page


def test_reference_preview_uses_selected_local_file_and_preserves_safe_dom_contract():
    page = _read("apps/taovideo/templates/taovideo.html")

    assert "reader.readAsDataURL(file)" in page
    assert "URL.createObjectURL(file)" in page
    assert "out.replaceChildren()" in page
    assert "title.textContent=file.name" in page
    assert "insertAdjacentHTML" not in page
    assert "selected=selectedFiles()" in page and "files=selected.length" in page
    # Tran tong khong con go trong JS — no den tu server. Phep kiem HANH VI
    # (nop qua tran bi tu choi) nam o tests/test_5200_taovideo_tran_tai_san.py;
    # o day chi giu bat bien cua HOP DONG DOM: JS doc tran tu `data-tran-*`.
    assert "total>4" not in page
    assert 'data-tran-tong="{{ tran_tong }}"' in page
    assert "total>TRAN.tong" in page


def test_empty_library_cannot_force_horizontal_scroll_on_mobile():
    css = _read("server/static/ltt.css")

    assert ".tv-empty{box-sizing:border-box;min-width:0;max-width:100%;" in css
    assert ".tv-grid{grid-template-columns:minmax(0,1fr)}" in css
