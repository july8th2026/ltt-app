"""nop_tai.py — đường nộp tải THẬT vào production. Bản giả thay được ở test.

Điểm vào của chương trình: `docs/VAN_HANH_THAT.md`.

⛔ **Đây là tệp DUY NHẤT trong bộ đo gửi request đi.** `soi.py` chỉ đọc,
   `kich_ban.py` là dữ liệu, `bao_cao.py` thuần. Tách như thế để phép kiểm của
   bộ đo **không bao giờ gọi production**: chúng tiêm một bản giả vào đúng chỗ
   này.

## 🔴 Ba thứ học bằng cách vấp

1. **`Idempotency-Key` bắt buộc**, mỗi lượt một giá trị, và **không** đặt trong
   body. Thiếu ⇒ 400.
2. **`max_tokens` ≥ 64** (sàn L-02). Dưới ⇒ 400, và thông báo lỗi nói rõ vì sao.
3. **Job dài phải THẬT dài.** Hàng đợi chỉ quan sát được khi nó kịp hình thành;
   một lượt 3 giây thì người thứ bảy chưa kịp xếp hàng đã có chỗ, và ta đo ra
   một hệ *"không bao giờ phải chờ"* — sai về phía yên tâm.
"""
from __future__ import annotations

import pathlib
import threading
import time
import uuid
from dataclasses import dataclass

from tools.nghiem_thu_van_hanh.kich_ban import KichBan

GOC_API = "http://127.0.0.1:8100"

#: Khoá API sống — NGOÀI kho. Xem `chan_trong_kho()` bên dưới.
DOI_KHOA = pathlib.Path("C:" + chr(92) + "LTTPlatform" + chr(92) + "secrets"
                        + chr(92) + "van_hanh_khoa")

#: Đo 13/09: ~106–123 s trên `ltt-3.8` khi chạy một mình, ~8.000 mảnh SSE.
PROMPT_DAI = ("Count from 1 to 2000. One number per line. "
              "Do not stop early, do not summarise.")
MAX_TOKENS = 8000

#: Sàn L-02 — dưới ngưỡng này cửa trả 400 kèm lời giải thích.
SAN_MAX_TOKENS = 64


def chan_trong_kho(tep: pathlib.Path, goc_kho: str) -> None:
    """⛔ Chặn CƠ HỌC, không phải một lời nhắc.

    Ngày 13/09 tôi chép sáu khoá live vào `tools/nghiem_thu_van_hanh/doi_khoa/`
    cho tiện. Chúng chưa bị commit, nhưng một `git add` rộng tay là lên GitHub.
    Một lệnh cấm bằng văn bản không ngăn được điều đó; một ngoại lệ thì ngăn.
    """
    goc = pathlib.Path(goc_kho).resolve()
    if goc == tep.resolve() or goc in tep.resolve().parents:
        raise SystemExit(f"TU CHOI: khoa API nam TRONG kho ({tep}). "
                         f"Chuyen sang {DOI_KHOA} roi chay lai.")


def doc_khoa(ten: str, *, goc_kho: str) -> str:
    tep = DOI_KHOA / f"{ten}.key"
    chan_trong_kho(tep, goc_kho)
    if not tep.is_file():
        raise SystemExit(f"khong thay khoa {tep}. Tao bang: "
                         "py tools/khoa_thu_api.py --email <...> --che-do live")
    return tep.read_text(encoding="utf-8").strip()


@dataclass
class MotLuot:
    """Một lượt gọi vào production."""

    nhan: str
    model: str
    khoa: str
    tre: float = 0.0
    cat_sau: int = 0
    ma: int = 0
    t_gui: float = 0.0
    t_byte_dau: float = 0.0
    t_xong: float = 0.0
    n_manh: int = 0
    n_queued: int = 0
    loi: str = ""


def _mot_luot(l: MotLuot, t0: float) -> None:
    import httpx

    if l.tre:
        time.sleep(l.tre)
    than = {"model": l.model, "stream": True, "max_tokens": MAX_TOKENS,
            "messages": [{"role": "user", "content": PROMPT_DAI}]}
    l.t_gui = time.monotonic() - t0
    try:
        with httpx.Client(timeout=900.0) as kh:
            with kh.stream("POST", f"{GOC_API}/api/v1/messages", json=than,
                           headers={"Authorization": f"Bearer {l.khoa}",
                                    # ⛔ Mỗi lượt MỘT giá trị, và KHÔNG đặt
                                    #    trong body — cửa từ chối 400 nếu thiếu.
                                    "Idempotency-Key": uuid.uuid4().hex}) as r:
                l.ma = r.status_code
                if r.status_code != 200:
                    l.loi = r.read()[:200].decode("utf-8", "replace")
                    return
                for khoi in r.iter_raw():
                    if not l.t_byte_dau:
                        l.t_byte_dau = time.monotonic() - t0
                    l.n_manh += 1
                    if b"response.queued" in khoi or b"ltt-cho" in khoi:
                        l.n_queued += 1
                    if l.cat_sau and l.n_manh >= l.cat_sau:
                        break      # CẮT thật: rời `with` ⇒ httpx đóng socket
    except Exception as e:  # noqa: BLE001
        l.loi = f"{type(e).__name__}: {e}"[:200]
    finally:
        l.t_xong = time.monotonic() - t0


def nop_that(kb: KichBan, *, goc_kho: str,
             khoa_theo_nhan: dict[str, str] | None = None) -> dict:
    """Nộp tải của một kịch bản, trả các đại lượng `mong_doi` so được.

    `khoa_theo_nhan` ánh xạ nhãn lượt → tên tệp khoá; mặc định dồn hết vào
    `vh1-a`. ⚠️ Kịch bản khai `can_tai_khoan_hai` **phải** truyền ánh xạ nhiều
    tài khoản, nếu không trần tài khoản không bật và số đo không thuộc kịch bản
    nào.
    """
    luot: list[MotLuot] = []
    i = 0
    for model, n in kb.tai:
        for _ in range(n):
            i += 1
            ten_khoa = (khoa_theo_nhan or {}).get(f"L{i}", "vh1-a")
            luot.append(MotLuot(nhan=f"L{i}", model=model,
                                khoa=doc_khoa(ten_khoa, goc_kho=goc_kho)))

    # ⛔ Cat chi ap cho MOT luot (luot cuoi). Cat het thi khong con ai giu suat
    #    de do xem suat co duoc nha khong — ta se do mot he rong.
    if kb.cat_sau and luot:
        luot[-1].cat_sau = kb.cat_sau

    t0 = time.monotonic()
    ts = [threading.Thread(target=_mot_luot, args=(x, t0)) for x in luot]
    for t in ts:
        t.start()
    for t in ts:
        t.join()

    chay_ngay = sum(1 for x in luot if x.ma == 200 and x.n_queued == 0)
    # ⭐ Thoi gian cho LAU NHAT toi byte dau — dai luong ma J8 hoi. Chi tinh
    #    luot that su nhan duoc byte; luot hong khong noi gi ve thoi gian cho.
    cho = [round(x.t_byte_dau - x.t_gui, 2) for x in luot if x.t_byte_dau]
    return {
        "chay_ngay": chay_ngay,
        "queued": sum(1 for x in luot if x.n_queued > 0),
        "khong_429": all(x.ma != 429 for x in luot),
        "co_429_phong_day": any(x.ma == 429 for x in luot),
        "so_200": sum(1 for x in luot if x.ma == 200),
        **({"t_cat_s": round(luot[-1].t_xong, 2)} if kb.cat_sau else {}),
        **({"cho_toi_da_s": max(cho)} if cho else {}),
        "luot": [{"nhan": x.nhan, "model": x.model, "ma": x.ma,
                  "ttfb": round(x.t_byte_dau - x.t_gui, 2) if x.t_byte_dau else -1,
                  "dai": round(x.t_xong - x.t_gui, 2),
                  "manh": x.n_manh, "queued": x.n_queued, "loi": x.loi[:120]}
                 for x in luot],
    }
