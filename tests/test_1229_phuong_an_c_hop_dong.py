"""test_1229 — hợp đồng PHƯƠNG ÁN C, phía máy A (bước 1 + 2, 17/09/2026).

Kế hoạch: `docs/ltt_llm_dual/KE_HOACH_PHUONG_AN_C.md` §3.3. Tệp này giữ các mục
MÁY A tự trả lời được, đọc NGUỒN THẬT (không bản sao):

  1. `llama-swap.yaml` ⇄ `ngan_sach.HO_SO`: `-c`, `-np`, `seq_cap ≤ -np`,
     `--reasoning-budget < TOKEN_RA_TRAN`, cờ `-kvu`.
  4. (nửa A) `tran_vao_cua(m)` dựng từ `-c` của YAML, cho CẢ HAI model. Nửa B
     (cổng máy B dựng cùng số từ YAML) thuộc bước 3 — `llm_gateway/`.
  6. `AdmissionModel.nguong_whale == NGUONG_WHALE[id]`, và đường thật (stream
     `tien_kiem`, đồng bộ/job `luat_cho`) gắn cờ whale bằng số THEO MODEL, ở MỘT chỗ.
  R-7. Ví dụ chủ dự án chạy QUA `luat_cho` + `admission.xet_va_giu` thật, với giữ
     chỗ đầu ra là THAM SỐ (chính sách `max_tokens` đang chờ chủ dự án — §4.3).
  O-05. `X-LTT-Token-Dat` đi lên máy B ở cửa đồng bộ/job, cùng số với lease.

✅ Chủ dự án chốt 17/09 (L-23): ngưỡng whale 3.8 = 8.192, 3.5 = 16.384 (số chọn
   tường minh, không phải ước đường cong 10.752/18.944), biên pool 8.192 token. Các
   phép kiểm ở đây đọc `NGUONG_WHALE` / `BIEN_POOL_TOKEN`, không gõ lại số.
"""
from __future__ import annotations

import ast
import pathlib
import uuid
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest
import yaml

from apps.ltt_llm import ngan_sach

GOC = pathlib.Path(__file__).resolve().parents[1]
YAML = GOC / "llm_gateway" / "deploy" / "llama-swap.yaml"


def _dong_lenh(cfg: dict, ten: str) -> list[str]:
    cmd = str(cfg["models"][ten]["cmd"])
    for khoa, gt in (cfg.get("macros") or {}).items():
        cmd = cmd.replace("${%s}" % khoa, str(gt))
    return cmd.split()


def _co(dong: list[str], *ten: str) -> str | None:
    for t in ten:
        if t in dong:
            i = dong.index(t)
            return dong[i + 1] if i + 1 < len(dong) else ""
    return None


@pytest.fixture(scope="module")
def cfg() -> dict:
    return yaml.safe_load(YAML.read_text(encoding="utf-8"))


# ── Mục 1: YAML ⇄ HO_SO ─────────────────────────────────────────────────────

def test_1_yaml_va_ho_so_CUNG_mot_bo_so(cfg):
    ho_so_yaml = set(cfg.get("models") or {})
    assert ho_so_yaml == set(ngan_sach.HO_SO), (
        f"yaml khai {sorted(ho_so_yaml)} nhung HO_SO khai {sorted(ngan_sach.HO_SO)}")
    for ten, h in ngan_sach.HO_SO.items():
        dong = _dong_lenh(cfg, ten)
        assert int(_co(dong, "-c", "--ctx-size") or 0) == h.engine_ctx, ten
        assert int(_co(dong, "-np", "--parallel") or 0) == h.np, ten
        assert 1 <= h.seq_cap <= h.np, ten
        ngan = _co(dong, "--reasoning-budget")
        assert ngan is not None and int(ngan) < ngan_sach.TOKEN_RA_TRAN, (
            f"{ten}: reasoning-budget {ngan} khong nho hon tran ra "
            f"{ngan_sach.TOKEN_RA_TRAN} — suy nghi nam TRONG n_predict (§6 R-1)")
        assert "-kvu" in dong or "--kv-unified" in dong, (
            f"{ten}: thieu -kvu — bo KV chung la gia dinh cua ngan sach dat cho")


def test_1_doi_chung_yaml_lech_thi_phep_kiem_BAT_duoc(cfg):
    """Đối chứng: tiêm một `-c` lệch vào bản sao YAML ⇒ phép so ở trên phải lệch."""
    lech = yaml.safe_load(yaml.safe_dump(cfg))
    ten = ngan_sach.MODEL_MAC_DINH
    lech["models"][ten]["cmd"] = str(lech["models"][ten]["cmd"]).replace(
        f"-c {ngan_sach.HO_SO[ten].engine_ctx}", "-c 131072")
    assert int(_co(_dong_lenh(lech, ten), "-c") or 0) != ngan_sach.HO_SO[ten].engine_ctx


# ── Mục 4 (nửa A): trần vào dựng từ YAML ────────────────────────────────────

def test_4_tran_vao_A_dung_tu_c_cua_YAML_cho_CA_HAI_model(cfg):
    for ten, h in ngan_sach.HO_SO.items():
        c_yaml = int(_co(_dong_lenh(cfg, ten), "-c") or 0)
        assert ngan_sach.tran_vao_cua(ten) == (
            c_yaml - ngan_sach.TOKEN_RA_TRAN - h.dem_uoc), ten
    # O-02: hai model, hai trần — không phải 186.368 cho cả hai.
    assert (ngan_sach.tran_vao_cua("qwen38-api")
            != ngan_sach.tran_vao_cua("qwen35-api"))


def test_bat_bien_1_vao_hop_le_dai_nhat_dat_cho_VUA_pool_that():
    """`vào ≤ tran_vao ⇒ đặt chỗ ≤ pool` — trên bản khai THẬT, qua `luat_cho` thật."""
    from apps.ltt_llm.executor import EXECUTOR
    from apps.ltt_llm.manifest import MANIFEST
    from platform_core.llm import luat_nhan, tham_so_da_luot
    from platform_core.llm.canonical import ALIAS_SANG_ID

    tool = MANIFEST.tools[0]
    for alias, id_nb in ALIAS_SANG_ID.items():
        suc = tool.admission_cho(alias)
        vao = EXECUTOR.input_cap(alias)
        ra = EXECUTOR.context_output_cap(vao, alias)
        luat = tham_so_da_luot.luat_cho(suc, lop=luat_nhan.TUONG_TAC,
                                        token_vao_uoc=vao, xin_ra=ra)
        assert luat["token_dat_truoc"] <= suc.token_pool, alias
        assert suc.token_pool <= ngan_sach.HO_SO[id_nb].engine_ctx, alias


# ── Mục 6: ngưỡng whale THEO MODEL, gắn ở MỘT chỗ cho mọi cửa ────────────────

def test_6_ban_khai_mang_nguong_whale_CHU_DU_AN_CHON():
    from apps.ltt_llm.manifest import MANIFEST
    from platform_core.llm.canonical import ALIAS_SANG_ID

    tool = MANIFEST.tools[0]
    for alias, id_nb in ALIAS_SANG_ID.items():
        am = tool.admission_cho(alias)
        assert am.nguong_whale == ngan_sach.NGUONG_WHALE[id_nb], alias
        assert am.nguong_whale == ngan_sach.HO_SO[id_nb].nguong_whale, alias
        assert (am.dem_uoc, am.token_giu_moi_anh) == (
            ngan_sach.HO_SO[id_nb].dem_uoc, ngan_sach.HO_SO[id_nb].token_giu_moi_anh)


@pytest.mark.parametrize("alias", ["ltt-3.8", "ltt-3.5"])
def test_6_cua_dong_bo_va_job_gan_whale_theo_nguong_CUA_MODEL(alias):
    """Cửa không có lịch sử tiền tố (đồng bộ, job, planner) dùng `vào_ước`."""
    from apps.ltt_llm.manifest import MANIFEST
    from platform_core.llm import luat_nhan, tham_so_da_luot

    suc = MANIFEST.tools[0].admission_cho(alias)
    n = suc.nguong_whale
    duoi = tham_so_da_luot.luat_cho(suc, lop=luat_nhan.NEN, token_vao_uoc=n - 1,
                                    xin_ra=100)
    tai = tham_so_da_luot.luat_cho(suc, lop=luat_nhan.NEN, token_vao_uoc=n,
                                   xin_ra=100)
    assert (duoi["la_whale"], tai["la_whale"]) == (False, True), alias


def test_6_KHONG_con_ban_sao_nguong_whale_ngoai_luat_cho():
    """Một chỗ gắn cờ: không tệp nào của nền tảng/cửa HTTP tự đọc `nguong_whale`."""
    cho_phep = {GOC / "platform_core" / "llm" / "tham_so_da_luot.py",
                GOC / "platform_core" / "registry.py"}
    pham = []
    for thu_muc in ("platform_core", "server"):
        for tep in (GOC / thu_muc).rglob("*.py"):
            if tep in cho_phep:
                continue
            cay = ast.parse(tep.read_text(encoding="utf-8"))
            if any(isinstance(n, ast.Attribute) and n.attr == "nguong_whale"
                   for n in ast.walk(cay)):
                pham.append(str(tep.relative_to(GOC)))
    assert not pham, f"doc nguong_whale ngoai luat_cho: {pham}"


def test_6_env_cu_DA_GO_khong_con_hieu_luc(monkeypatch):
    """Đặt ba env đã gỡ ⇒ không đổi gì trên đường thật."""
    from apps.ltt_llm.manifest import MANIFEST
    from platform_core.llm import luat_nhan, tham_so_da_luot

    suc = MANIFEST.tools[0].admission_cho("ltt-3.8")
    truoc = tham_so_da_luot.luat_cho(suc, lop=luat_nhan.NEN, token_vao_uoc=20_000,
                                     xin_ra=100, so_anh=2)
    monkeypatch.setenv("LTT_LLM_NGUONG_WHALE", "1")
    monkeypatch.setenv("LTT_LLM_DEM_DAT_TRUOC", "99999")
    monkeypatch.setenv("LTT_LLM_TOKEN_MOI_ANH", "99999")
    sau = tham_so_da_luot.luat_cho(suc, lop=luat_nhan.NEN, token_vao_uoc=20_000,
                                   xin_ra=100, so_anh=2)
    assert sau == truoc


def test_O09_xet_va_giu_truyen_lao_hoa_s_tu_env(monkeypatch):
    """O-09: `LTT_LLM_LAO_HOA_S` từng không có hiệu lực (không được truyền)."""
    from platform_core.llm import luat_nhan, tham_so_da_luot

    monkeypatch.setenv("LTT_LLM_LAO_HOA_S", "7")
    monkeypatch.setenv("LTT_LLM_CHO_BACKFILL_S", "11")
    monkeypatch.setenv("LTT_LLM_CHO_WHALE_S", "13")
    ts = tham_so_da_luot.tham_so_nhan(so_slot=3, pool=100, residency_mo=True)
    assert (ts.lao_hoa_s, ts.cho_backfill_toi_da_s, ts.cho_whale_toi_da_s) == (7, 11, 13)
    # Và lớp đích không còn mặc định số để lặng lẽ điền thay.
    with pytest.raises(TypeError):
        luat_nhan.ThamSo(so_slot=3, pool=100)  # type: ignore[call-arg]


# ── Khung CSDL cho các phép kiểm đi qua đường thật ──────────────────────────

@pytest.fixture()
def db_c(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       "sqlite:///" + (tmp_path / "c.db").as_posix())
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from tests.conftest import mo_cu_tru_3090
    mo_cu_tru_3090()
    gen = dbmod.get_session()
    s = next(gen)
    try:
        yield s
    finally:
        s.close()
        dbmod.reset_engine()


def test_6_cua_STREAM_tien_kiem_gan_whale_theo_nguong_CUA_MODEL(db_c):
    """`tien_kiem` (stream/ChatLTT) đọc ngưỡng THEO MODEL qua `luat_cho`.

    Cùng một prompt ~40K token: trên 3.8 (ngưỡng thấp hơn) là whale, trên 3.5
    (prefill nhanh hơn, ngưỡng cao hơn) thì không — chỉ đúng khi hai ngưỡng
    khác nhau thật và cửa đọc đúng ngưỡng của model khách xin.
    """
    from platform_core import credit
    from platform_core.runtime_noi_bo import luong
    from platform_core.users import tao_nguoi_dung

    n38 = ngan_sach.NGUONG_WHALE["qwen38-api"]
    n35 = ngan_sach.NGUONG_WHALE["qwen35-api"]
    assert n38 < n35, "phep kiem nay can nguong 3.8 thap hon 3.5"
    muc_tieu = (n38 + n35) // 2
    u = tao_nguoi_dung(db_c, email=f"c-{uuid.uuid4().hex[:8]}@example.com",
                       password="a-good-password-12")
    db_c.flush()
    credit.cap_tay(db_c, u.id, 100_000, by="test")
    db_c.commit()

    ket = {}
    for alias in ("ltt-3.8", "ltt-3.5"):
        noi_dung = "x" * int(muc_tieu * ngan_sach.KY_TU_MOI_TOKEN)
        # Mỗi model một nội dung khác nhau: `uoc_moi` nhớ tiền tố theo người dùng.
        noi_dung = alias + noi_dung
        tk = luong.tien_kiem(db_c, user_id=u.id, tool_name="text.chat",
                             than={"model": alias, "max_tokens": 1_000,
                                   "messages": [{"role": "user", "content": noi_dung}]},
                             duong="/v1/messages")
        assert n38 <= tk.token_prefill_moi < n35, (alias, tk.token_prefill_moi)
        ket[alias] = tk.la_whale
    assert ket == {"ltt-3.8": True, "ltt-3.5": False}, ket


# ── R-7: ví dụ chủ dự án QUA ĐƯỜNG THẬT ─────────────────────────────────────
#
# Chủ dự án 17/09: trên 3.8, lượt 15K + 100K đang chạy; 110K tới ⇒ CHỜ (không
# 429); 55K tới sau ⇒ được phục vụ TRƯỚC 110K (backfill); nhả ngân sách ⇒ 110K chạy.
#
# 🔑 Có backfill hay không phụ thuộc HAI số chưa chốt (§4.3 + số đo 17/09):
#    * giữ chỗ đầu ra mỗi lượt (`out_giu` = `max_tokens` LTTCODE gửi);
#    * biên pool (`BIEN_POOL_TOKEN`).
#    dat(l) = vào + out_giu + DEM_UOC; backfill ⇔ 170K + 3·(out_giu + 2.048) ≤ pool.
#      biên 0      (pool 221.184): out_giu ≤ 15.013  ⇒ 14.000 backfill, 32.768 không
#      biên 8.192  (pool 212.992): out_giu ≤ 12.282  ⇒ 12.000 backfill, 14.000 KHÔNG
#    ✅ Chủ dự án chốt 17/09: biên 8.192 và LTTCODE `max_tokens` 24.000 ⇒ ví dụ
#       KHÔNG backfill trên 3.8 (số cụ thể ở ca tham số 24.000 bên dưới).
#    32.768 (mặc định cửa stream hôm nay) KHÔNG BAO GIỜ backfill: 15K+100K đã giữ
#    184.632, 55K cần 89.816 ⇒ 274.448 > pool. Ví dụ của chủ dự án chỉ đạt khi
#    LTTCODE gửi `max_tokens` thật (§4.3 lựa chọn 1).
#
# 🔴 VÀ BƯỚC CUỐI CỦA VÍ DỤ ("nhả 100K ⇒ 110K chạy cạnh 15K + 55K") CÒN CHẶT HƠN:
#    180K + 3·(out_giu + 2.048) ≤ pool ⇔ out_giu ≤ 11.680 (biên 0) / ≤ 8.949 (biên
#    8.192). Viết "15K + 55K + 110K = 180K ≤ pool" là quên phần giữ chỗ đầu ra. Ở
#    out_giu lớn hơn, 110K chờ thêm tới khi 15K hoặc 55K xong — vẫn không 429, và
#    vẫn có cận trên nhờ backfill có chặn (120 s).

_T0 = datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc)


def _xin(db, suc, *, ten: str, vao: int, out_giu: int, waiter_id: str = "",
         tuoi_s: float = 0.0):
    from platform_core.llm import admission, luat_nhan, tham_so_da_luot

    luat = tham_so_da_luot.luat_cho(suc, lop=luat_nhan.TUONG_TAC,
                                    token_vao_uoc=vao, xin_ra=out_giu)
    lease, ly_do = admission.xet_va_giu(
        db, resource=suc.resource, slots=suc.slots, user_id=f"u-{ten}",
        mode="stream", holder_id=ten, waiter_id=waiter_id, tuoi_cho_s=tuoi_s,
        now=_T0, **luat)
    db.commit()
    return lease, ly_do, luat


def _vao_hang(db, suc, *, ten: str, vao: int, out_giu: int, tuoi_s: float) -> str:
    from platform_core.llm import luat_nhan, phong_cho, tham_so_da_luot

    luat = tham_so_da_luot.luat_cho(suc, lop=luat_nhan.TUONG_TAC,
                                    token_vao_uoc=vao, xin_ra=out_giu)
    wid = phong_cho.vao(db, phong_cho.YeuCauCho(
        resource=suc.resource, slots=suc.slots, token_pool=suc.token_pool,
        user_id=f"u-{ten}", mode="stream", holder_id=ten, request_id=ten,
        cua="stream", lop=luat_nhan.TUONG_TAC, token_dat_truoc=luat["token_dat_truoc"],
        token_prefill_moi=luat["token_prefill_moi"], la_whale=luat["la_whale"],
        model="qwen38-api"), now=_T0 - timedelta(seconds=tuoi_s))
    from platform_core.models import LlmWaiter
    db.get(LlmWaiter, wid).heartbeat_at = _T0
    db.commit()
    return wid


@pytest.mark.parametrize("bien_pool_token,out_giu,backfill", [
    (0, 11_000, True),
    (0, 14_000, True),
    (0, 32_768, False),
    (ngan_sach.BIEN_POOL_TOKEN, 12_000, True),
    (ngan_sach.BIEN_POOL_TOKEN, 14_000, False),
    # ✅ Chốt 17/09: LTTCODE gửi `max_tokens` 24.000, biên 8.192 (pool 212.992).
    #    15K+24K+2.048 = 41.048 · 100K+… = 126.048 ⇒ đang giữ 167.096.
    #    110K cần 136.048 ⇒ 303.144 > 212.992: CHỜ (không 429).
    #    55K  cần  81.048 ⇒ 248.144 > 212.992: KHÔNG backfill (thiếu 35.152).
    #    Nhả 100K ⇒ 41.048 + 136.048 = 177.096 ≤ 212.992: 110K chạy cạnh 15K.
    (ngan_sach.BIEN_POOL_TOKEN, 24_000, False),
    (ngan_sach.BIEN_POOL_TOKEN, 32_768, False),
])
def test_R7_vi_du_chu_du_an_QUA_luat_cho_va_xet_va_giu_that(
        db_c, monkeypatch, bien_pool_token, out_giu, backfill):
    from apps.ltt_llm.manifest import MANIFEST
    from platform_core.llm import admission, luat_nhan

    # Bản khai THẬT của 3.8, chỉ thay biên pool theo tham số (số chưa chốt).
    h = replace(ngan_sach.HO_SO["qwen38-api"], bien_pool_token=bien_pool_token)
    suc = replace(MANIFEST.tools[0].admission_cho("ltt-3.8"),
                  token_pool=h.token_budget)
    # Không whale nào trong ví dụ này: nó đo NGÂN SÁCH, không đo luật 5.
    suc = replace(suc, nguong_whale=10**9)

    j1, _, _ = _xin(db_c, suc, ten="j1", vao=15_000, out_giu=out_giu)
    j2, _, _ = _xin(db_c, suc, ten="j2", vao=100_000, out_giu=out_giu)
    assert j1 is not None and j2 is not None, "15K + 100K phai chay duoc"

    w3 = _vao_hang(db_c, suc, ten="j3", vao=110_000, out_giu=out_giu, tuoi_s=20)
    w4 = _vao_hang(db_c, suc, ten="j4", vao=55_000, out_giu=out_giu, tuoi_s=1)

    l3, ly3, _ = _xin(db_c, suc, ten="j3", vao=110_000, out_giu=out_giu,
                      waiter_id=w3, tuoi_s=20)
    assert l3 is None and ly3 == luat_nhan.CHO_NGAN_SACH, "110K phai CHO, khong 429"

    l4, ly4, luat4 = _xin(db_c, suc, ten="j4", vao=55_000, out_giu=out_giu,
                          waiter_id=w4, tuoi_s=1)
    tong = (15_000 + 100_000 + 55_000 + 3 * (out_giu + h.dem_uoc))
    assert (l4 is not None) == backfill == (tong <= suc.token_pool), (
        f"out_giu={out_giu} bien={bien_pool_token}: tong dat cho {tong} / pool "
        f"{suc.token_pool}, nhan={l4 is not None}, ly_do={ly4!r}")

    # Nhả 100K ⇒ 110K chạy nếu vừa cạnh những lượt còn lại (15K, và 55K nếu nó
    # đã backfill) — PHÉP TÍNH quyết định, không phải câu chữ của ví dụ.
    admission.release(db_c, j2.id)
    db_c.commit()
    con = [15_000] + ([55_000] if l4 is not None else [])
    tong_sau = sum(con) + 110_000 + (len(con) + 1) * (out_giu + h.dem_uoc)
    l3b, ly3b, _ = _xin(db_c, suc, ten="j3", vao=110_000, out_giu=out_giu,
                        waiter_id=w3, tuoi_s=200)
    assert (l3b is not None) == (tong_sau <= suc.token_pool), (
        f"sau khi nha 100K: tong {tong_sau} / pool {suc.token_pool}, "
        f"nhan={l3b is not None}, ly_do={ly3b!r}")
    if l3b is None:
        # Chưa vừa ⇒ CHỜ ngân sách (không 429); nhả thêm lượt đang chạy thì vào.
        assert ly3b == luat_nhan.CHO_NGAN_SACH, ly3b
        for lease in ([l4] if l4 is not None else []) + [j1]:
            admission.release(db_c, lease.id)
        db_c.commit()
        l3c, ly3c, _ = _xin(db_c, suc, ten="j3", vao=110_000, out_giu=out_giu,
                            waiter_id=w3, tuoi_s=300)
        assert l3c is not None, f"pool trong ma 110K van cho: {ly3c}"


# ── O-05: `X-LTT-Token-Dat` ở cửa đồng bộ/job ───────────────────────────────

def test_O05_dieu_phoi_gui_X_LTT_Token_Dat_khi_co_dat_cho(monkeypatch):
    import httpx

    from platform_core.llm import dieu_phoi
    from platform_core.llm.cong_vlm import BanError

    thay: list[dict] = []

    class ClientGia:
        def __init__(self, *a, **k):
            pass

        def request(self, method, url, *, json=None, headers=None, timeout=None):
            thay.append(dict(headers or {}))

            class R:
                status_code = 429

                @staticmethod
                def json():
                    return {"ly_do": "ban"}
            return R()

        def close(self):
            pass

    monkeypatch.setattr(httpx, "Client", ClientGia)
    than = {"model": "qwen38-api", "messages": [{"role": "user", "content": "hi"}]}
    with pytest.raises(BanError):
        dieu_phoi._goi_openai("http://b", "k", than, 5.0, ma_luot="rid-1")
    with dieu_phoi.mang_dat_cho(12_345), pytest.raises(BanError):
        dieu_phoi._goi_openai("http://b", "k", than, 5.0, ma_luot="rid-2")
    assert "X-LTT-Token-Dat" not in thay[0], "khong co lease ma van bia so dat cho"
    assert thay[1].get("X-LTT-Token-Dat") == "12345"
    assert thay[1].get("X-LTT-Request-Id") == "rid-2"
    assert dieu_phoi.TOKEN_DAT_TRUOC.get() == 0, "ngu canh ro ra ngoai khoi"


def test_O05_cua_JOB_mang_dung_so_dat_cho_cua_lease(db_c, monkeypatch, app_thu):
    """Handler của job thấy `TOKEN_DAT_TRUOC` = `token_dat_truoc` của lease nó giữ."""
    import platform_core.job_runner as jr
    from platform_core import credit
    from platform_core.job_submit import submit_with_credit
    from platform_core.llm import dieu_phoi
    from platform_core.models import ExecutionLease
    from platform_core.registry import AdmissionModel, ToolSpec
    from tests.conftest import APP_THU_JOB, APP_THU_SLUG, bao_dam_user

    def _tool(job_type):
        return ToolSpec(
            name="thu.dat_cho", job_type=job_type, description="tool thu",
            params_schema={"text": {"type": "string"}}, returns={"output": "text"},
            admission_theo_model={"*": AdmissionModel(
                "tn_dat_cho_thu", 1, 100_000, nguong_whale=50_000, dem_uoc=2_048,
                token_giu_moi_anh=2_048)})

    monkeypatch.setattr(jr, "_tool_cua_job", _tool)
    thay: dict = {}

    def _handler(params, ctx):
        import platform_core.db as dbmod
        g = dbmod.get_session()
        s = next(g)
        try:
            thay["lease"] = [int(x.token_dat_truoc or 0)
                             for x in s.query(ExecutionLease).all()]
        finally:
            s.close()
        thay["ngu_canh"] = dieu_phoi.TOKEN_DAT_TRUOC.get()
        return {"output": "ok"}

    monkeypatch.setattr(jr.jobq, "resolve_handler", lambda jt: _handler)
    bao_dam_user(db_c, "u-dat")
    credit.cap_tay(db_c, "u-dat", 100, by="test")
    db_c.commit()
    submit_with_credit(db_c, user_id="u-dat", app_slug=APP_THU_SLUG,
                       job_type=APP_THU_JOB, params={"text": "xin chao"})
    db_c.commit()

    assert jr._chay_mot_job("w-dat") is True
    assert len(thay.get("lease", [])) == 1 and thay["lease"][0] > 0, thay
    assert thay["ngu_canh"] == thay["lease"][0], thay
    assert dieu_phoi.TOKEN_DAT_TRUOC.get() == 0


# ── Mục 2b (nghiệm thu 17/09): cờ whale chỉ xoá khi có DỮ LIỆU thật, không ở nhịp tim ──

def _chay_phat(monkeypatch, cac_khoi):
    """Chạy `luong._phat` với luồng giả; trả (thời điểm xoá cờ tính theo số khối đã phát)."""
    from types import SimpleNamespace

    from platform_core.llm import admission
    from platform_core.runtime_noi_bo import luong

    da_phat: list[bytes] = []
    xoa_luc: list[int] = []
    monkeypatch.setattr(admission, "xoa_co_whale",
                        lambda lease_id: xoa_luc.append(len(da_phat)) or True)
    monkeypatch.setattr(admission, "keep_alive", lambda *a, **k: __import__("contextlib").nullcontext())
    monkeypatch.setattr(luong, "quyet_toan", lambda *a, **k: None)
    cb = SimpleNamespace(la_whale=True, lease_id="L1", request_id="r-12345678",
                         user_id="u", da_giu=0, model_alias="ltt-3.8", waiter_id=None)
    luot = SimpleNamespace(chuan_bi=cb, dem=SimpleNamespace(nhin=lambda k: None, token_ra=0),
                           luc_khoi_cuoi=0.0, ket_thuc=None, da_quyet_toan=False, ket_qua=None)
    mo = SimpleNamespace(luong=iter(cac_khoi), hong=lambda e: None, xong=lambda tokens: None)
    for khoi in luong._phat(mo, luot):
        da_phat.append(khoi)
    return xoa_luc, da_phat


def test_2b_nhip_tim_SSE_KHONG_xoa_co_whale(monkeypatch):
    """B gửi `: ping` mỗi 15 s trong lúc PREFILL. Xoá cờ ở khối đầu tiên (nhịp tim)
    cho whale thứ hai vào prefill chồng (đo production 17/09: chồng 24,9 s)."""
    khoi = [b": ping\n\n", b": ping\n\n", b'data: {"type":"message_start"}\n\n', b"data: x\n\n"]
    xoa_luc, da_phat = _chay_phat(monkeypatch, khoi)
    assert da_phat == khoi, "nhịp tim vẫn phải chuyển nguyên xi cho khách"
    assert xoa_luc == [2], f"cờ phải xoá ở khối dữ liệu thật đầu tiên (chỉ số 2), thấy {xoa_luc}"


def test_2b_khoi_tron_nhip_tim_va_du_lieu_xoa_co(monkeypatch):
    xoa_luc, _ = _chay_phat(monkeypatch, [b': ping\n\ndata: {"a":1}\n\n'])
    assert xoa_luc == [0]


def test_2b_chi_nhip_tim_thi_KHONG_xoa_co(monkeypatch):
    xoa_luc, _ = _chay_phat(monkeypatch, [b": ping\n\n", b"\n"])
    assert xoa_luc == []
