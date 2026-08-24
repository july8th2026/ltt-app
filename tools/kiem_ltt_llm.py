"""kiem_ltt_llm.py — kiểm TOÀN TUYẾN nền tảng → máy B. (H38)

    python tools/kiem_ltt_llm.py

Khác `llm_gateway/deploy/nghiem_thu.py` ở chỗ: bài kia chạy **trên máy B** và gọi
thẳng cổng. Bài này chạy **trên máy A** và đi qua **đúng đường mà app sẽ đi**:

    dieu_phoi.goi()
      -> api_pool.chon_key(category=chat)     <- khoa co trong CSDL chua?
      -> api_keys.lay_credential()            <- giai ma duoc khong?
      -> providers.REGISTRY['ltt_llm']        <- base_url dung chua?
      -> HTTP toi may B
      -> KetQuaChat + SuDung                  <- co du so de tinh tien khong?
      -> gia_token.tinh()                     <- ra bao nhieu credit?

Cần biến môi trường `LTT_DATABASE_URL` và `LTT_TOKEN_ENCRYPTION_KEY` (trên máy chủ
nằm ở `secrets\\app.env`).

⛔ Script này **không in credential**. Nó chỉ in id khoá rút gọn.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Console Windows la CP1252; model tra loi tieng Viet. Kiem thuoc tinh thay vi
# boc try/except: `reconfigure` co tu Python 3.7 va khong nem gi khi co that.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_dat = 0
_hong = 0


def bao(ten: str, ok: bool, chi_tiet: str = "") -> None:
    global _dat, _hong
    if ok:
        _dat += 1
        print(f"  [DAT ] {ten}" + (f" - {chi_tiet}" if chi_tiet else ""))
    else:
        _hong += 1
        print(f"  [HONG] {ten}" + (f" - {chi_tiet}" if chi_tiet else ""))


def main() -> int:
    from platform_core import api_keys, api_pool, providers
    from platform_core.db import get_session
    from platform_core.llm import dieu_phoi, gia_token
    from platform_core.models import APIKEY_CAT_CHAT

    print("\n" + "=" * 62)
    print("  KIEM TOAN TUYEN: nen tang (may A) -> cong VLM (may B)")
    print("=" * 62)

    print("\n1. Registry")
    prov = providers.get("ltt_llm")
    bao("provider 'ltt_llm' co trong REGISTRY", prov is not None)
    if prov is None:
        return 1
    bao("category la 'chat'", APIKEY_CAT_CHAT in prov.categories, str(prov.categories))
    bao("dong bo, khong async_poll", prov.async_poll is False)
    ten_model = [m.id for m in providers.models_for("ltt_llm", APIKEY_CAT_CHAT)]
    bao("khai model", bool(ten_model), str(ten_model))

    gen = get_session()
    db = next(gen)
    try:
        print("\n2. So khoa")
        try:
            key = api_pool.chon_key(db, category=APIKEY_CAT_CHAT,
                                    thu_tu_provider=["ltt_llm"])
            bao("api_pool cap duoc khoa", True, f"id={key.id[:8]} priority={key.priority}")
        except Exception as e:
            bao("api_pool cap duoc khoa", False, f"{type(e).__name__}: {e}")
            print("\n   Chua co khoa. Chay:  python tools/them_key_ltt_llm.py --token <BEARER>")
            return 1
        cred = api_keys.lay_credential(db, key)
        bao("giai ma credential", bool(cred), f"{len(cred)} ky tu (khong in ra)")
        cred = ""

        print("\n3. Goi that qua dieu_phoi (dung duong ma app se di)")
        try:
            kq = dieu_phoi.goi(
                db,
                messages=[{"role": "user",
                           "content": "Tra loi dung mot tu: thu do Viet Nam?"}],
                thu_tu_provider=["ltt_llm"],
                model_theo_provider={"ltt_llm": "ltt_llm"},
                max_tokens=200, timeout_s=300.0,
            )
            bao("goi duoc", True, (kq.noi_dung or "")[:60].replace("\n", " "))
            bao("usage dang tin (tinh tien duoc)", kq.su_dung.dang_tin,
                f"vao={kq.su_dung.token_vao} ra={kq.su_dung.token_ra} "
                f"cache={kq.su_dung.token_vao_cache}")
        except dieu_phoi.KhongCoProviderNao as e:
            bao("goi duoc", False, str(e))
            return 1
        except Exception as e:
            bao("goi duoc", False, f"{type(e).__name__}: {e}")
            return 1

        print("\n4. Tinh tien")
        try:
            cp = gia_token.tinh(kq.su_dung)
            bao("tinh duoc chi phi", True,
                f"{cp.tong_mcredit} mcredit = {cp.tong_credit_lam_tron_len} credit "
                f"(C1 lam tron len) | {cp.phien_ban_gia}")
        except gia_token.KhongDoDuocError as e:
            bao("tinh duoc chi phi", False, str(e))

        print("\n5. Cascade khi may B ban")
        print("    (khong ep may B ban o day - da neo bang test_255)")
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    print("\n" + "=" * 62)
    print(f"  DAT {_dat} | HONG {_hong}")
    print("=" * 62)
    return 0 if _hong == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
