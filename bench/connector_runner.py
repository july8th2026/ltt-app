"""Đo tải runner connector + diễn tập lỗi — điều kiện ra P6 (spec §18.6/§18.7).

    python bench\\connector_runner.py --lan 20 --song-song 2

⚠️ **Chạy qua `chay_nang.py`**: nó phóng tới 2 tiến trình Node cùng lúc trên
   máy production. `python "C:\\Users\\Thang Tuong\\.claude\\ltt\\chay_nang.py"
   --phien <lan> -- python bench\\connector_runner.py`

## Nó đo cái gì, và ⛔ không đo cái gì

- ✅ **Độ trễ một lệnh** (từ lúc Python gọi tới lúc đọc xong `ra.json`) — tức
  đã gồm dựng vỏ, `CreateProcessW`, Node khởi động, nạp piece, chạy action.
- ✅ **RAM đỉnh và CPU** lấy từ **Job Object**, ⛔ không lấy mẫu bằng `psutil`:
  lấy mẫu thì phải trúng lúc đỉnh, còn job object **kế toán** cả cây tiến
  trình và đọc được sau khi tiến trình đã chết.
- ⛔ **Không** đo thông lượng của một provider thật: mọi action ở đây là piece
  giả, không ra mạng. Số ở đây là **chi phí của cái vỏ**, không phải của việc.

## Diễn tập lỗi (§18.7)

Mỗi ca hỏi một câu khác nhau, và câu trả lời phải là **một mã lỗi đọc được**,
⛔ không phải một lượt treo hay một `ok: true` rỗng.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from platform_core.workflow import connector  # noqa: E402

TEN_VO = "ltt-conn-bench"
MOI = {"LTT_TEST": "1"}


def _chay(ten, props=None, han_ms=30_000):
    return connector.chay(
        "run_action", piece="@ltt/piece-gia", version="0.0.0", name=ten,
        props=props or {}, auth="x", han_ms=han_ms, ten_vo=TEN_VO,
        moi_truong_them=MOI)


def do_tai(lan: int, song_song: int) -> dict:
    do_tre, ram, cpu = [], [], []

    def mot(_i):
        t0 = time.monotonic()
        kq = _chay("thanh_cong", {"i": _i})
        ms = (time.monotonic() - t0) * 1000
        return kq, ms

    # Tuần tự trước: số sạch, không ai tranh CPU.
    for i in range(lan):
        kq, ms = mot(i)
        if not kq.ok:
            raise SystemExit(f"lenh tuan tu {i} hong: {kq.ma_loi} {kq.thong_diep}")
        do_tre.append(ms)
        ram.append(int(kq.do.get("dinh_bo_nho_byte", 0)))
        cpu.append(int(kq.do.get("cpu_user_100ns", 0))
                   + int(kq.do.get("cpu_kernel_100ns", 0)))

    # Rồi song song đúng trần lane (spec §11.2: 2 suất).
    t0 = time.monotonic()
    with ThreadPoolExecutor(max_workers=song_song) as ex:
        ket = list(ex.map(mot, range(lan)))
    tong_ss = (time.monotonic() - t0) * 1000
    ss = [ms for _kq, ms in ket]
    hong = [k.ma_loi for k, _ in ket if not k.ok]

    return {
        "so_lenh": lan,
        "tuan_tu": {
            "do_tre_ms_trung_vi": round(statistics.median(do_tre), 1),
            "do_tre_ms_p95": round(sorted(do_tre)[int(len(do_tre) * 0.95) - 1], 1),
            "do_tre_ms_min": round(min(do_tre), 1),
            "do_tre_ms_max": round(max(do_tre), 1),
        },
        "song_song": {
            "muc": song_song,
            "do_tre_ms_trung_vi": round(statistics.median(ss), 1),
            "tong_ms": round(tong_ss, 1),
            "thong_luong_lenh_moi_giay": round(lan / (tong_ss / 1000), 2),
            "hong": hong,
        },
        "ram_dinh_mb_trung_vi": round(statistics.median(ram) / 1024 / 1024, 1),
        "ram_dinh_mb_max": round(max(ram) / 1024 / 1024, 1),
        "cpu_ms_trung_vi": round(statistics.median(cpu) / 10_000, 1),
    }


def dien_tap_loi() -> list:
    """§18.7 — mỗi ca một câu hỏi, câu trả lời phải ĐỌC ĐƯỢC."""
    ra = []

    def ghi(ten, cau_hoi, kq, mong_doi):
        dat = mong_doi(kq)
        ra.append({"ca": ten, "cau_hoi": cau_hoi, "ok": kq.ok,
                   "ma_loi": kq.ma_loi, "status": kq.status,
                   "do_tre_ms": kq.do.get("do_tre_ms"),
                   "dat": bool(dat),
                   "thong_diep": kq.thong_diep[:120]})

    ghi("provider_429", "piece bi rate-limit thi mã lỗi có ĐỌC ĐƯỢC status?",
        _chay("loi_429"), lambda k: (not k.ok and k.status == 429))

    ghi("dau_vao_sai", "piece nem loi thuong thi co thanh `ok: true` khong?",
        _chay("loi_dau_vao"), lambda k: not k.ok)

    ghi("het_gio", "piece treo lau hon `han_ms` thi co bi GIET khong?",
        _chay("cham", {"ms": 20_000}, han_ms=3_000),
        lambda k: (not k.ok and k.ma_loi == "het_gio"))

    ghi("ket_qua_mo_ho", "job xong ma noi dung RONG thi co lo ra khong?",
        _chay("mo_ho"), lambda k: k.ok and k.output == {"content": ""})

    ghi("bi_mat_khong_ro", "token trong output co bi CHE khong?",
        _chay("che_bi_mat"),
        lambda k: k.ok and "bi-mat" not in json.dumps(k.output))

    ghi("egress_chan", "piece goi thang ra Internet thi bi chan the nao?",
        _chay("thoat_truc_tiep", {"url": "https://example.com/"}),
        lambda k: k.ok and "BLOCKED" in json.dumps(k.output))

    ghi("waitpoint_cam", "action dung `run.pause` thi co treo im lang khong?",
        _chay("dung_waitpoint"),
        lambda k: not k.ok and "waitpoint" in k.thong_diep)

    # Ngoài allowlist / lệch bản: hai cửa chặn của chuỗi cung ứng (§11.3).
    kq = connector.chay("run_action", piece="@activepieces/piece-khong-co",
                        version="9.9.9", name="x", han_ms=20_000,
                        ten_vo=TEN_VO, moi_truong_them=MOI)
    ghi("ngoai_allowlist", "piece khong trong allowlist co nap duoc khong?",
        kq, lambda k: not k.ok)

    kq = connector.chay("run_action", piece="@activepieces/piece-slack",
                        version="0.0.1-sai", name="send_direct_message",
                        han_ms=20_000, ten_vo=TEN_VO, moi_truong_them=MOI)
    ghi("lech_ban", "yeu cau mot ban KHAC ban da ghim thi sao?",
        kq, lambda k: not k.ok)

    return ra


def main() -> int:
    # Console Windows mac dinh cp1252 => mot dau tieng Viet lam ca lan do NEM
    # sau khi da chay xong. Ket qua mat trang, va no mat o dong CUOI CUNG.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    p = argparse.ArgumentParser()
    p.add_argument("--lan", type=int, default=20)
    p.add_argument("--song-song", type=int, default=2)
    p.add_argument("--chi-dien-tap", action="store_true")
    p.add_argument("--ra", default="", help="ghi JSON ket qua vao tep")
    a = p.parse_args()

    connector.chuan_bi_vo(TEN_VO)
    try:
        ket = {}
        if not a.chi_dien_tap:
            ket["tai"] = do_tai(a.lan, a.song_song)
        ket["dien_tap"] = dien_tap_loi()
        tho = json.dumps(ket, ensure_ascii=False, indent=1)
        if a.ra:
            pathlib.Path(a.ra).write_text(tho, encoding="utf-8")
        print(tho)
        chua_dat = [c["ca"] for c in ket["dien_tap"] if not c["dat"]]
        print(f"\nDIEN TAP: {len(ket['dien_tap']) - len(chua_dat)}/"
              f"{len(ket['dien_tap'])} dat"
              + (f" | CHUA DAT: {chua_dat}" if chua_dat else ""))
        return 1 if chua_dat else 0
    finally:
        connector.go_vo(TEN_VO)


if __name__ == "__main__":
    sys.exit(main())
