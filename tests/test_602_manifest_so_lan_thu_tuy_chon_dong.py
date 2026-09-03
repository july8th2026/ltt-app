"""
test_602 — hai trường hợp đồng mới (H43 Phase 02): `AppManifest.so_lan_thu` và
`ToolSpec.tuy_chon_dong`, và chỗ chúng được ĐỌC.

  1. Registry từ chối bản khai sai NGAY LÚC NẠP (job_type lạ, số < 1, tham số
     không tồn tại, kiểu không phải string, tham chiếu sai hình).
  2. `so_lan_thu_for` mặc định 3, sàn 1.
  3. `apps/ltt_voice` khai cả hai — và `/api/v1` nay đọc `so_lan_thu` thay vì
     mặc định 3 (bất đối xứng web↔API đo được ở Phase 02).
  4. `tai_tham_chieu` không import lúc nạp registry.
"""
from __future__ import annotations

import pytest

from platform_core import registry as reg


def _m(**g):
    goc = dict(slug="appthu602", display_name="x", route_prefix="/appthu602",
               job_types=("appthu602.j",), credit_cost=lambda p: 1)
    goc.update(g)
    return reg.AppManifest(**goc)


def _tool(**g):
    goc = dict(name="text.thu602", job_type="appthu602.j", description="d",
               params_schema={"p": {"type": "string"}, "n": {"type": "int"}},
               returns={"content": "text"})
    goc.update(g)
    return reg.ToolSpec(**goc)


def _validate(m):
    reg._validate(m, set(), set(), set(), set(), set())


# ── 1. Từ chối lúc nạp ───────────────────────────────────────────────────────

def test_so_lan_thu_job_type_la_bi_tu_choi():
    with pytest.raises(reg.RegistryError, match="so_lan_thu"):
        _validate(_m(so_lan_thu={"khac.j": 5}))


@pytest.mark.parametrize("so", [0, -1, True, "5", 2.5])
def test_so_lan_thu_phai_la_so_nguyen_duong(so):
    with pytest.raises(reg.RegistryError, match="so_lan_thu"):
        _validate(_m(so_lan_thu={"appthu602.j": so}))


def test_so_lan_thu_hop_le_nap_duoc():
    _validate(_m(so_lan_thu={"appthu602.j": 5}))


def test_tuy_chon_dong_tham_so_khong_ton_tai_bi_tu_choi():
    with pytest.raises(reg.RegistryError, match="tuy_chon_dong"):
        _validate(_m(tools=(_tool(tuy_chon_dong={"q": "a.b:c"}),)))


def test_tuy_chon_dong_chi_cho_string():
    with pytest.raises(reg.RegistryError, match="string"):
        _validate(_m(tools=(_tool(tuy_chon_dong={"n": "a.b:c"}),)))


@pytest.mark.parametrize("ref", ["", "a.b", ":c", "a b:c", 5, "a.b:c()"])
def test_tuy_chon_dong_tham_chieu_sai_hinh(ref):
    with pytest.raises(reg.RegistryError, match="module:attribute"):
        _validate(_m(tools=(_tool(tuy_chon_dong={"p": ref}),)))


def test_tuy_chon_dong_hop_le_KHONG_import_luc_nap():
    # Module không tồn tại — nếu `_validate` import nó thì đây phải ném.
    _validate(_m(tools=(_tool(tuy_chon_dong={"p": "khong.ton_tai.dau:ham"}),)))


# ── 2. Accessor ──────────────────────────────────────────────────────────────

def test_so_lan_thu_for_mac_dinh_va_san():
    m = _m(so_lan_thu={"appthu602.j": 5})
    assert m.so_lan_thu_for("appthu602.j") == 5
    assert m.so_lan_thu_for("khac") == 3
    assert m.so_lan_thu_for("khac", default=0) == 1
    assert _m().so_lan_thu_for("appthu602.j") == 3


# ── 3. App thật đã khai, và `/api/v1` đọc nó ────────────────────────────────

def test_ltt_voice_khai_so_lan_thu_va_tuy_chon_dong():
    from apps.ltt_voice.manifest import MANIFEST
    from apps.ltt_voice.tham_so_cong_khai import SO_LAN_THU_JOB
    assert MANIFEST.so_lan_thu_for("ltt_voice.synthesize") == SO_LAN_THU_JOB
    assert MANIFEST.so_lan_thu_for("ltt_voice.enroll") == SO_LAN_THU_JOB
    tool = next(t for t in MANIFEST.tools if t.name == "speech.ltt")
    assert tool.tuy_chon_dong == {
        "voice_id": "apps.ltt_voice.tham_chieu:tuy_chon_voice_id",
        # ⭐ THEM 04/09: kho DUNG CHUNG. Truoc do mot tai khoan chua nhan ban
        #    giong nao thay o chon giong RONG — tuc khong co lua chon nao, va do
        #    la trang thai cua gan nhu moi khach moi. Hai khoa nay khac vai:
        #    `voice_id` la giong CUA HO (kiem so huu), `preset` la kho chung
        #    (khong thuoc ai). Gop lam mot la xoa mat ranh gioi do.
        "preset": "apps.ltt_voice.tham_chieu:tuy_chon_preset",
    }
    # Ca hai tham chieu phai NAP DUOC. Mot chuoi `module:ham` go sai chi lo ra
    # luc chay that, va luc do no lam RONG danh sach chu khong bao loi.
    for khoa in ("voice_id", "preset"):
        assert callable(reg.tai_tham_chieu(tool.tuy_chon_dong[khoa])), khoa


def test_invocation_submit_doc_so_lan_thu_cua_manifest(monkeypatch):
    """`_so_lan_thu(tool, lane)` — thứ `invocation.submit` truyền vào `max_attempts`."""
    from types import SimpleNamespace

    from platform_core.public_api import invocation

    m = _m(so_lan_thu={"appthu602.j": 7})
    loaded = reg.LoadedApp(manifest=m, router=None)
    monkeypatch.setattr(reg, "discover", lambda apps_dir=None: [loaded])
    tool = SimpleNamespace(app_slug="appthu602", name="text.thu602",
                           job_type="appthu602.j")
    assert invocation._so_lan_thu(tool, "appthu602.j") == 7
    assert invocation._so_lan_thu(tool, "appthu602.khac") == 3
    assert invocation._so_lan_thu(SimpleNamespace(app_slug="khong_co"), "x") == 3


def test_invocation_submit_goi_submit_with_credit_kem_max_attempts(monkeypatch):
    import inspect

    from platform_core.public_api import invocation
    nguon = inspect.getsource(invocation.submit)
    assert "max_attempts=_so_lan_thu(tool, lane)" in nguon


# ── 4. `tai_tham_chieu` ─────────────────────────────────────────────────────

def test_tai_tham_chieu_giai_dung_va_tu_choi_sai_hinh():
    assert reg.tai_tham_chieu("json:dumps") is __import__("json").dumps
    with pytest.raises(reg.RegistryError):
        reg.tai_tham_chieu("json")
