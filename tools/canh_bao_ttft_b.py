"""canh_bao_ttft_b.py — R-16: cảnh báo TTFT stream và nạp nguội của máy B, theo NGÀY.

    python tools\\canh_bao_ttft_b.py                          # hôm qua, đọc B qua SSH, CHỈ IN (chạy thử)
    python tools\\canh_bao_ttft_b.py --gui                    # gửi thư nếu vượt — mỗi điều kiện MỘT lần
    python tools\\canh_bao_ttft_b.py --ngay 2026-09-18        # một ngày cụ thể (giờ máy B)
    python tools\\canh_bao_ttft_b.py --so a.log b.log --ngay 2026-09-18   # đọc tệp cục bộ, không SSH

Đặt lịch trên máy A (mỗi sáng 07:15, sau khi ngày hôm qua đã khép; chạy bằng tài khoản
đọc được `secrets\\app.env` và có khoá `~\\.ssh\\nexus_b`) — ⛔ công cụ KHÔNG tự đặt lịch:

    schtasks /Create /TN "LTT canh bao TTFT B" /SC DAILY /ST 07:15 ^
      /TR "C:\\LTTPlatform\\venv\\Scripts\\python.exe C:\\LTTPlatform\\app\\tools\\canh_bao_ttft_b.py --gui"

Ngưỡng (đề xuất R-16, `KET_QUA_NEEDLE_MTP_18_09.md` §3 — giữ nguyên):
  * TTFT stream **ấm** p95 trong ngày > 45 s (mỗi model), và
  * > 5 lượt nạp nguội trong ngày mỗi model có TTFT > 20 s.

Nguồn số — dùng lại `tong_hop_ttft_b.py` (cùng bộ đọc sổ, cùng phân vị nearest-rank, cùng TTL
đọc từ `llama-swap.yaml`), không đếm lại theo cách khác:
  * Sổ lượt cổng B (`llm_gateway.so`, một dòng JSON/lượt trong `H:\\LTT_LLM\\logs\\gateway_err*.log`),
    đọc CHỈ ĐỌC qua đường vào chính của RUNBOOK §1 (`ssh -i ~/.ssh/nexus_b lengo@192.168.2.66`,
    `Select-String` phía B — không ghi, không dừng gì).
  * Nạp nguội SUY TỪ SỔ (lượt đầu của model sau khoảng lặng > TTL). `llamaswap.log` không dùng được
    để đếm THEO NGÀY: llama-swap v250 chỉ in giờ khi đặt `logTimeFormat` (mặc định "" — tắt;
    `config.example.yaml` v250, `internal/logmon/logging.go::formatMessage`), và yaml của ta không đặt.
    Dòng nạp xong của v250 là `<id> Health check passed on …` (`internal/process/process_command.go`).

Tách chờ hàng (L-29, Task 17): `ttft_s` của sổ B đo từ lúc CỔNG B nhận lượt (`api.py`, `t0`); cổng B
không xếp hàng (đầy ⇒ 429). Chờ ở máy A (`llm_waiters`, `whale_cho_prefill`) xảy ra TRƯỚC khi lượt tới
B ⇒ KHÔNG nằm trong số này. p95 ở đây là TTFT sau hàng đợi A (nạp/dọn card + prefill + chen slot
trong engine) — tức đúng phần L-29 đổi được, không lẫn thời gian chờ.

Chỉ tính cửa **stream** cho cả hai ngưỡng: cửa đồng bộ ghi `ttft_s` = CẢ lượt, nên "> 20 s" ở đó
không phân biệt nạp nguội với một câu trả lời dài. Nạp nguội cửa đồng bộ vẫn in ra để tham khảo.

Chống spam: trạng thái ở `data_path("canh_bao", "ttft_b.json")`; một điều kiện (ngày, model, loại)
đã gửi thành công thì không gửi lại. Chạy thử (mặc định) không gửi và không ghi trạng thái.
Kênh: đúng kênh người trực của `platform_core/public_api/ops_alerts.py` — `platform_core.mailer`
tới `LTT_OPS_ALERT_EMAIL`; vắng biến đó ⇒ tắt mềm như ở đó.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import os
import pathlib
import subprocess
import sys

GOC = pathlib.Path(__file__).resolve().parent.parent
if str(GOC) not in sys.path:
    sys.path.insert(0, str(GOC))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from tools import tong_hop_ttft_b as T  # noqa: E402

#: Ngưỡng R-16 — số chủ dự án được đề xuất 18/09, không đổi ở đây.
NGUONG_P95_AM_S = 45.0
NGUONG_NGUOI_LAN = 5          # vượt khi > 5
NGUONG_NGUOI_TTFT_S = 20.0
#: p95 nearest-rank trên dưới 20 lượt chính là max ⇒ một lượt xấu thành "p95". Ngày ít lượt hơn thế
#: vẫn in số, nhưng không kích ngưỡng p95 (ngưỡng nạp nguội vẫn xét — nó đếm sự kiện).
TOI_THIEU_LUOT_P95 = 20

MAY_B = "lengo@192.168.2.66"
THU_MUC_LOG_B = r"H:\LTT_LLM\logs"
APP_ENV = pathlib.Path(r"C:\LTTPlatform\secrets\app.env")


# ── đọc sổ từ máy B (chỉ đọc) ────────────────────────────────────────────────
def lenh_ps_doc_so(ngay: dt.date) -> str:
    """Script PowerShell CHỈ ĐỌC: dòng sổ của ngày `ngay` và ngày trước đó (để biết lượt đầu ngày có nguội không)."""
    truoc = ngay - dt.timedelta(days=1)
    return (
        "[Console]::OutputEncoding = New-Object Text.UTF8Encoding($false)\n"
        f"$tu = [datetime]'{truoc.isoformat()}'\n"
        f"Get-ChildItem -LiteralPath '{THU_MUC_LOG_B}' -Filter 'gateway_err*.log' | "
        "Where-Object { $_.LastWriteTime -ge $tu } | ForEach-Object {\n"
        "  Select-String -LiteralPath $_.FullName -SimpleMatch -Pattern ' llm_gateway.so {' | "
        f"Where-Object {{ $_.Line -match '^({truoc.isoformat()}|{ngay.isoformat()}) ' }} | "
        "ForEach-Object { $_.Line } }\n"
    )


def doc_tu_b(ngay: dt.date, *, chay=subprocess.run) -> list[str]:
    """Dòng sổ từ B qua SSH. Lỗi SSH ⇒ `RuntimeError` (không coi "không đọc được" là "0 lượt")."""
    ma = base64.b64encode(lenh_ps_doc_so(ngay).encode("utf-16-le")).decode("ascii")
    khoa = pathlib.Path.home() / ".ssh" / "nexus_b"
    r = chay(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "-i", str(khoa), MAY_B,
              f"powershell -NoProfile -NonInteractive -EncodedCommand {ma}"],
             capture_output=True, timeout=300)
    if r.returncode != 0:
        # stderr của OpenSSH có cảnh báo post-quantum vô hại (RUNBOOK §1) — chỉ báo mã, không in stderr.
        raise RuntimeError(f"ssh toi may B that bai (ma {r.returncode})")
    return r.stdout.decode("utf-8", "replace").splitlines()


# ── đánh giá một ngày (thuần) ────────────────────────────────────────────────
def danh_gia_ngay(luot: list[dict], ngay: dt.date, ttl: int) -> dict:
    """Số liệu ngày `ngay` theo model + danh sách điều kiện vượt ngưỡng.

    `luot` nên gồm cả ngày trước (ngữ cảnh). Lượt đầu tiên của model trong cửa sổ đọc mà không có
    lượt trước (`nguoi=None`) được coi là nguội: cửa sổ bắt đầu từ 00:00 ngày trước, dài hơn TTL.
    """
    T.danh_dau_nguoi(luot, ttl)
    trong_ngay = [r for r in luot if r["_luc"].date() == ngay]
    if ttl < 86400:
        for r in trong_ngay:
            if r.get("nguoi") is None:
                r["nguoi"] = True
    theo_model: dict[str, dict] = {}
    for r in trong_ngay:
        m = r.get("model") or "?"
        s = theo_model.setdefault(m, {"luot_stream": 0, "am": [], "nguoi_cham": [],
                                      "nguoi_stream": 0, "nguoi_dong_bo": 0})
        ok = r.get("ma_http") == 200 and r.get("ttft_s") is not None
        if r.get("stream"):
            s["luot_stream"] += 1
            if r.get("nguoi"):
                s["nguoi_stream"] += 1
                if ok and float(r["ttft_s"]) > NGUONG_NGUOI_TTFT_S:
                    s["nguoi_cham"].append(round(float(r["ttft_s"]), 2))
            elif ok:
                s["am"].append(float(r["ttft_s"]))
        elif r.get("nguoi"):
            s["nguoi_dong_bo"] += 1
    ket = {}
    vuot = []
    for m, s in sorted(theo_model.items()):
        p95 = T.phan_vi(s["am"], 95)
        ket[m] = {"luot_stream": s["luot_stream"], "luot_am_co_ttft": len(s["am"]),
                  "ttft_am_p95_s": p95, "nguoi_stream": s["nguoi_stream"],
                  "nguoi_stream_ttft_tren_20s": len(s["nguoi_cham"]),
                  "ttft_nguoi_cham": s["nguoi_cham"], "nguoi_dong_bo_tham_khao": s["nguoi_dong_bo"]}
        if p95 is not None and len(s["am"]) >= TOI_THIEU_LUOT_P95 and p95 > NGUONG_P95_AM_S:
            vuot.append({"model": m, "loai": "p95_am", "gia_tri": p95, "nguong": NGUONG_P95_AM_S,
                         "mo_ta": f"TTFT stream am p95 {p95:.1f} s > {NGUONG_P95_AM_S:.0f} s "
                                  f"({len(s['am'])} luot)"})
        if len(s["nguoi_cham"]) > NGUONG_NGUOI_LAN:
            vuot.append({"model": m, "loai": "nguoi", "gia_tri": len(s["nguoi_cham"]),
                         "nguong": NGUONG_NGUOI_LAN,
                         "mo_ta": f"{len(s['nguoi_cham'])} lan nap nguoi TTFT > "
                                  f"{NGUONG_NGUOI_TTFT_S:.0f} s (> {NGUONG_NGUOI_LAN}/ngay)"})
    return {"ngay": ngay.isoformat(), "ttl_s": ttl, "theo_model": ket, "vuot": vuot}


# ── chống spam ───────────────────────────────────────────────────────────────
def duong_trang_thai() -> pathlib.Path:
    from platform_core.runtime_paths import data_path
    return pathlib.Path(data_path("canh_bao", "ttft_b.json"))


def khoa(ngay: str, v: dict) -> str:
    return f"{ngay}|{v['model']}|{v['loai']}"


def doc_trang_thai(p: pathlib.Path) -> dict:
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return d if isinstance(d.get("da_gui"), dict) else {"da_gui": {}}
    except (OSError, ValueError, AttributeError):
        return {"da_gui": {}}


def ghi_trang_thai(p: pathlib.Path, tt: dict, hom_nay: dt.date) -> None:
    han = (hom_nay - dt.timedelta(days=60)).isoformat()
    tt["da_gui"] = {k: v for k, v in tt["da_gui"].items() if k.split("|", 1)[0] >= han}
    p.parent.mkdir(parents=True, exist_ok=True)
    tam = p.with_suffix(".tmp")
    tam.write_text(json.dumps(tt, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    os.replace(tam, p)


# ── gửi qua kênh người trực của ops_alerts ───────────────────────────────────
def than_thu(kq: dict, moi: list[dict]) -> str:
    dong = [f"  - {v['model']}: {v['mo_ta']}" for v in moi]
    bang = [f"  {m}: stream {s['luot_stream']} luot, am p95 {s['ttft_am_p95_s']}, "
            f"nguoi stream {s['nguoi_stream']} (>20 s: {s['nguoi_stream_ttft_tren_20s']}), "
            f"nguoi dong bo {s['nguoi_dong_bo_tham_khao']}"
            for m, s in kq["theo_model"].items()]
    return (f"May B - nguong R-16 bi vuot ngay {kq['ngay']} (gio may B):\n\n" + "\n".join(dong)
            + "\n\nSo lieu ca ngay:\n" + "\n".join(bang) + "\n\n"
            "TTFT do tu luc cong B nhan luot: KHONG gom thoi gian cho o may A (llm_waiters, L-29).\n"
            f"Nap nguoi suy tu so luot (khoang lang > TTL {kq['ttl_s']} s).\n"
            "Chay lai: python tools\\canh_bao_ttft_b.py --ngay " + kq["ngay"] + "\n"
            "Moi dieu kien chi gui MOT lan cho mot ngay.\n")


def gui(kq: dict, *, tt_path: pathlib.Path, to: str = "", mailer=None,
        hom_nay: dt.date | None = None) -> list[dict]:
    """Gửi MỘT thư cho các điều kiện CHƯA gửi. Trả các điều kiện đã gửi (rỗng nếu không gửi gì)."""
    from html import escape

    from platform_core.public_api.ops_alerts import EMAIL_ENV

    nguoi_nhan = (to or os.environ.get(EMAIL_ENV, "")).strip()
    if not nguoi_nhan:
        print(f"[canh_bao_ttft_b] {EMAIL_ENV} chua dat - tat mem, khong gui.")
        return []
    tt = doc_trang_thai(tt_path)
    moi = [v for v in kq["vuot"] if khoa(kq["ngay"], v) not in tt["da_gui"]]
    if not moi:
        return []
    from platform_core.mailer import Email, get_mailer

    than = than_thu(kq, moi)
    (mailer or get_mailer()).send(Email(
        to=nguoi_nhan,
        subject=f"[LTT] Nguong van hanh bi vuot: may B TTFT {kq['ngay']} "
                + ", ".join(f"{v['model']}/{v['loai']}" for v in moi),
        html=f"<pre>{escape(than)}</pre>", text=than))
    luc = dt.datetime.now().isoformat(timespec="seconds")
    for v in moi:
        tt["da_gui"][khoa(kq["ngay"], v)] = luc
    ghi_trang_thai(tt_path, tt, hom_nay or dt.date.today())
    return moi


def _nap_app_env() -> None:
    """Biến gửi thư của production (không in giá trị). Có sẵn trong môi trường thì giữ."""
    try:
        text = APP_ENV.read_text(encoding="utf-8")
    except OSError:
        return
    for dong in text.splitlines():
        if "=" in dong and not dong.lstrip().startswith("#"):
            k, v = dong.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ngay", type=dt.date.fromisoformat,
                    default=dt.date.today() - dt.timedelta(days=1), help="YYYY-mm-dd (mặc định hôm qua)")
    ap.add_argument("--so", nargs="+", type=pathlib.Path, help="đọc tệp sổ cục bộ thay vì SSH")
    ap.add_argument("--yaml", type=pathlib.Path)
    ap.add_argument("--gui", action="store_true", help="gửi thư thật (mặc định: chạy thử, chỉ in)")
    ap.add_argument("--trang-thai", type=pathlib.Path, help="tệp chống spam (mặc định data_path)")
    a = ap.parse_args(argv)

    ttl = T.ttl_yaml(a.yaml)
    try:
        dong = [d for p in a.so for d in T._dong(p)] if a.so else doc_tu_b(a.ngay)
    except (RuntimeError, OSError, subprocess.SubprocessError) as e:
        print(f"[canh_bao_ttft_b] KHONG doc duoc so: {e}")
        return 2
    kq = danh_gia_ngay(T.doc_so(dong), a.ngay, ttl)
    print(json.dumps(kq, ensure_ascii=False, indent=1))
    if not kq["vuot"]:
        print("[canh_bao_ttft_b] khong vuot nguong.")
        return 0
    if not a.gui:
        print(f"[canh_bao_ttft_b] CHAY THU: {len(kq['vuot'])} dieu kien vuot - khong gui, khong ghi trang thai.")
        return 1
    _nap_app_env()
    try:
        da = gui(kq, tt_path=a.trang_thai or duong_trang_thai())
    except Exception as e:                                   # noqa: BLE001
        print(f"[canh_bao_ttft_b] gui thu that bai ({type(e).__name__}) - chua ghi trang thai, lan sau gui lai.")
        return 2
    print(f"[canh_bao_ttft_b] da gui {len(da)} dieu kien moi"
          + ("" if da else " (tat ca da gui truoc do hoac kenh tat)") + ".")
    return 1


if __name__ == "__main__":
    sys.exit(main())
