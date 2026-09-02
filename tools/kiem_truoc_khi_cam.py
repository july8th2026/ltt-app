"""kiem_truoc_khi_cam.py — kiểm đường gọi `ltt_llm` TỪ MỘT MÁY KHÁC.

    python kiem_truoc_khi_cam.py --khoa ltt_sk_...
    python kiem_truoc_khi_cam.py            # đọc khoá từ biến LTT_API_KEY

## Tệp này dùng để chép sang máy khác, nên nó có ba ràng buộc

1. **Chỉ dùng thư viện chuẩn của Python.** Máy đích có thể chưa có `requests`,
   chưa có kho này, chưa có gì. Một bộ kiểm đòi cài thêm thứ gì đó là một bộ
   kiểm sẽ không được chạy.
2. **Một tệp duy nhất.** Chép một tệp thì người ta chép; chép một thư mục thì
   người ta bỏ qua.
3. **Không chạm máy chủ nội bộ.** Mọi phép đo đi qua đúng đường mà máy khách sẽ
   đi: HTTPS công khai, qua Cloudflare. Đo ở loopback là đo một thứ khác —
   `CLAUDE.md` quy tắc 5b đã trả giá cho bài học đó.

## ⛔ MỖI PHÉP KIỂM ĐỀU CÓ ĐỐI CHỨNG, và đối chứng trượt thì DỪNG

Bài học đắt nhất của đợt kiểm 31/08–01/09: **tám lần một dụng cụ cho ra kết quả
đẹp vì nó không đo gì cả.** Nên ở đây, phép kiểm "khoá dùng được" đi kèm phép
kiểm "khoá sai bị từ chối". Nếu cả hai cùng `200` thì bộ kiểm **không** báo
"đạt" — nó báo là chính nó hỏng.

## 🔴 CÁI BẪY `Python-urllib` — và vì sao tệp này tự thử nó

Cloudflare chặn **đúng tiền tố chuỗi `Python-urllib/`, phân biệt hoa-thường**.
Ai viết mười dòng Python để thử API sẽ dùng `urllib`, nhận **403 của
Cloudflare** — không `request_id`, không dòng nào trong sổ, không tra được. Nhìn
y hệt khoá sai, nên họ đi tạo khoá mới rồi vẫn 403.

Đo 30/08, cùng khoá, cùng đường:

    UA "Python-urllib/3.13"  (HOA chu P)  -> 403 CLOUDFLARE
    UA "python-urllib/3.13"  (thuong p)   -> 200
    UA ""  (chuoi RONG)                   -> 200
    UA "curl/8.0"                         -> 200

⇒ Bộ kiểm này đặt User-Agent riêng, **và thử cả biến thể bị chặn** để người chạy
thấy tận mắt cái bẫy thay vì đọc một dòng cảnh báo.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

GOC = "https://app.lttstudios.com"
API = GOC + "/api/v1"
UA = "ltt-preflight/1.0"

XANH, DO, VANG, TAT = "\033[32m", "\033[31m", "\033[33m", "\033[0m"
if os.name == "nt" and not os.environ.get("WT_SESSION"):
    XANH = DO = VANG = TAT = ""

_ket: list = []


def _goi(duong, khoa="", than=None, ua=UA, timeout=180, method=None):
    url = duong if duong.startswith("http") else API + duong
    data = json.dumps(than).encode() if than is not None else None
    req = urllib.request.Request(url, data=data,
                                 method=method or ("POST" if data else "GET"))
    if khoa:
        req.add_header("Authorization", "Bearer " + khoa)
    if ua is not None:
        req.add_header("User-Agent", ua)
    if data:
        req.add_header("Content-Type", "application/json")
    t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace"), round(time.time() - t, 2)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace"), round(time.time() - t, 2)
    except Exception as e:                                      # noqa: BLE001
        return -1, f"{type(e).__name__}: {e}", round(time.time() - t, 2)


def bao(ten, dat, chi_tiet="", bat_buoc=True):
    _ket.append((ten, dat, bat_buoc))
    dau = f"{XANH}[ĐẠT ]{TAT}" if dat else (f"{DO}[HỎNG]{TAT}" if bat_buoc
                                            else f"{VANG}[XEM ]{TAT}")
    print(f"  {dau} {ten}" + (f" — {chi_tiet}" if chi_tiet else ""))


def main() -> int:
    p = argparse.ArgumentParser(description="Kiem duong goi ltt_llm tu may nay.")
    p.add_argument("--khoa", default=os.environ.get("LTT_API_KEY", ""))
    p.add_argument("--bo-qua-tra-tien", action="store_true",
                   help="bo hai phep kiem co TIEU CREDIT that")
    a = p.parse_args()

    print(f"\n{'=' * 66}\n  KIEM DUONG GOI ltt_llm — tu chinh may nay\n{'=' * 66}")
    print(f"  dich: {API}")

    # ── 1. Tới được máy chủ chưa ────────────────────────────────────────────
    print("\n1. Mang va Cloudflare")
    ma, than, giay = _goi(GOC + "/gia-api")
    bao("toi duoc mien cong khai", ma == 200, f"HTTP {ma} trong {giay}s")
    if ma < 0:
        print(f"\n  {DO}Khong ra duoc Internet toi {GOC}.{TAT} "
              f"Kiem DNS, proxy, tuong lua cua may nay.")
        return 2

    # 🔴 Cái bẫy urllib: thử ĐÚNG chuỗi bị chặn để người chạy thấy tận mắt.
    ma_bay, _t, _g = _goi(GOC + "/gia-api", ua="Python-urllib/3.13")
    bao("bay `Python-urllib/` van con (403 la DUNG)", ma_bay == 403,
        f"HTTP {ma_bay} — dat User-Agent rieng thi qua", bat_buoc=False)

    # ── 2. Khoá ─────────────────────────────────────────────────────────────
    print("\n2. Khoa API")
    if not a.khoa:
        print(f"  {DO}Chua co khoa.{TAT} Dat bien LTT_API_KEY hoac dung --khoa.")
        return 2
    if not a.khoa.startswith("ltt_sk_"):
        print(f"  {VANG}Khoa khong bat dau bang `ltt_sk_` — co the chep thieu.{TAT}")

    ma, than, _g = _goi("/tools", a.khoa)
    bao("khoa dung duoc", ma == 200, f"HTTP {ma}")

    # ⛔ ĐỐI CHỨNG. Không có nó thì "khoá dùng được" có thể đúng một cách tầm
    #    thường — ví dụ khi máy chủ đang cho qua mọi thứ.
    ma_sai, _t, _g = _goi("/tools", a.khoa + "sai")
    bao("khoa SAI bi tu choi (doi chung)", ma_sai in (401, 403),
        f"HTTP {ma_sai}")
    if ma == 200 and ma_sai == 200:
        print(f"\n  {DO}DOI CHUNG TRUOT: khoa dung va khoa sai deu duoc nhan.{TAT}")
        print("  Bo kiem nay dang do mot thu khac. DUNG doc ket qua duoi day.")
        return 2

    # ── 3. Model có mở không ────────────────────────────────────────────────
    print("\n3. Model")
    ma, than, _g = _goi("/models", a.khoa)
    ten_model, vi_sao = [], ""
    if ma == 200:
        # !! NOI RA khi than tra ve khong doc duoc. Nuot im lang o day bien
        #    "may chu doi khuon tra loi" thanh "khong thay ltt_llm" -- hai su co
        #    khac han nhau, sua o hai noi khac han nhau.
        try:
            d = json.loads(than)
            ten_model = [m.get("name") for m in d.get("items", [])]
            if not isinstance(d.get("items"), list):
                vi_sao = "than JSON khong co mang `items`"
        except ValueError as e:
            vi_sao = f"than tra ve khong phai JSON ({e})"
    else:
        vi_sao = f"HTTP {ma}"
    bao("ltt_llm co trong danh muc", "ltt_llm" in ten_model,
        ", ".join(t for t in ten_model if t) or vi_sao)

    # ── 4. Cửa Codex thật sự dùng ───────────────────────────────────────────
    print("\n4. Cua /responses — dung cua Codex noi")
    than_thu = {"model": "ltt_llm", "stream": True, "max_output_tokens": 24,
                "input": "Tra loi dung mot tu: OK"}
    ma, than, giay = _goi("/responses", a.khoa, than_thu, timeout=300)
    bao("goi duoc, co luong tra ve", ma == 200, f"HTTP {ma} trong {giay}s")
    if ma != 200:
        print("     " + " ".join(than[:300].split()))

    # 🔴 Đây là chỗ Codex CHẾT nếu hỏng: nó LUÔN khai `shell`/`apply_patch`.
    #    Khuôn Responses phẳng (`type`+`name`+`parameters`), không phải khuôn
    #    Anthropic. Cua nay tung tu choi dung khuon cua chinh no (P08, 01/09).
    than_tool = dict(than_thu)
    than_tool["tools"] = [{"type": "function", "name": "shell",
                           "description": "Chay mot lenh",
                           "parameters": {"type": "object",
                                          "properties": {"cmd": {"type": "string"}}}}]
    ma_t, than_t, _g = _goi("/responses", a.khoa, than_tool, timeout=300)
    bao("NHAN khuon tool cua Codex", ma_t == 200,
        f"HTTP {ma_t}" + ("" if ma_t == 200 else " — Codex se KHONG dung duoc"))
    if ma_t != 200:
        print("     " + " ".join(than_t[:300].split()))

    # ── 5. Tiền ─────────────────────────────────────────────────────────────
    print("\n5. Tien")
    ma, than, _g = _goi("/credits/balance", a.khoa)
    so_du, vi_sao = None, f"HTTP {ma}"
    if ma == 200:
        try:
            so_du = json.loads(than).get("balance")
            vi_sao = "than JSON khong co truong `balance`"
        except ValueError as e:
            vi_sao = f"than tra ve khong phai JSON ({e})"
    bao("doc duoc so du", so_du is not None,
        f"{so_du} credit" if so_du is not None else vi_sao)

    if not a.bo_qua_tra_tien and so_du is not None:
        # ⭐ ĐỐI CHỨNG TIỀN: một lượt gọi thật PHẢI làm số dư giảm. Không giảm
        #    nghĩa là ta đang đo một đường KHÔNG tính tiền, và khi đó mọi kết
        #    luận về "đường gọi thông" đều đúng một cách tầm thường.
        ma, _t, _g = _goi("/responses", a.khoa,
                          {"model": "ltt_llm", "stream": True,
                           "max_output_tokens": 32,
                           "input": "Dem tu 1 den 5."}, timeout=300)
        time.sleep(6)
        _m, than2, _g = _goi("/credits/balance", a.khoa)
        try:
            sau = json.loads(than2).get("balance")
        except ValueError:
            # Doc lai that bai => KHONG ket luan duoc ve tien. Do khac han
            # "khong tru tien", nen phai de `sau = None` va noi ra o nhan.
            sau = None
        bao("mot luot goi that CO tru tien (doi chung)",
            sau is not None and sau < so_du, f"{so_du} -> {sau}")

    # ── Kết ─────────────────────────────────────────────────────────────────
    hong = [t for t, d, bb in _ket if not d and bb]
    print(f"\n{'=' * 66}")
    if hong:
        print(f"  {DO}CHUA THONG — {len(hong)} muc hong:{TAT}")
        for t in hong:
            print(f"    - {t}")
        print(f"\n  Dung cam vao Codex khi con muc hong. Gui ket qua nay cho\n"
              f"  nguoi van hanh — no du de chan doan ma khong can vao may nay.")
        return 1

    print(f"  {XANH}DUONG GOI THONG.{TAT}")
    _soi_cau_hinh_codex()
    return 0


#: Khoa BAT BUOC trong `~/.codex/config.toml`, va vi sao tung khoa co mat.
#:
#: ⛔ CHI TEN KHOA, KHONG GIA TRI. Bo kiem nay KHONG duoc phat ra mot ban sao
#:    cua cau hinh -- do dung la loi da xay ra 01/09: no in mot khoi `config.toml`
#:    tu go, THIEU `stream_idle_timeout_ms` va `model_reasoning_effort`, va nguoi
#:    cam dung ban do roi gap luong bi cat o 62 giay.
#:
#: ⭐ Nguon chan ly la `platform_core/public_api/examples.py` + cong cu chinh
#:    thuc `cam_cli`. `test_393` buoc danh sach nay khop voi chung.
KHOA_BAT_BUOC = {
    "stream_idle_timeout_ms":
        "thieu no thi Codex CAT luong khi model im tieng -- do that 02/09: "
        "mot luot bi cat o dung 62,0 giay",
    "model_reasoning_effort":
        "de mac dinh thi model tieu phan lon max_tokens de SUY NGHI truoc khi "
        "tra loi, nen luong im tieng du lau de bi cat",
    "model_catalog_json":
        "thieu no thi Codex canh bao `Model metadata not found` roi MUON TEN "
        "mot model OpenAI cho luot phu -- cong cua ta tu choi, khach thay im lang",
    "wire_api": "phai la `responses`",
    "base_url": "phai tan cung /api/v1 -- Codex noi /responses vao sau",
}


def _soi_cau_hinh_codex() -> None:
    """Doc cau hinh Codex TREN CHINH MAY NAY va noi thieu gi.

    ⭐ Doc thay vi phat: mot bo kiem phat ra cau hinh la mot ban sao thu hai cua
       mot loi hua, va hai ban se lech. Cong cu chinh thuc moi la thu ghi no.
    """
    import pathlib

    nha = pathlib.Path(os.path.expanduser("~")) / ".codex"
    tep = [nha / "config.toml", nha / "ltt.config.toml"]
    van = ""
    thay = []
    for t in tep:
        if t.exists():
            thay.append(t.name)
            van += t.read_text(encoding="utf-8", errors="replace") + chr(10)

    print()
    if not van:
        print(f"  {VANG}Chua thay cau hinh Codex tren may nay.{TAT}")
        print("  Dung CONG CU CHINH THUC, dung go tay:")
        print(f"    {GOC}/huong-dan/cong-cu")
        return

    print(f"  Da doc: {', '.join(thay)}")
    thieu = [(k, v) for k, v in KHOA_BAT_BUOC.items() if k not in van]
    if not thieu:
        print(f"  {XANH}Du ca {len(KHOA_BAT_BUOC)} khoa bat buoc.{TAT}")
        return
    print(f"  {DO}THIEU {len(thieu)} khoa:{TAT}")
    for k, vi_sao in thieu:
        print(f"    - {k}")
        print(f"        {vi_sao}")
    print()
    print("  ⇒ Dung CONG CU CHINH THUC de ghi lai cho dung, dung sua tay:")
    print(f"    {GOC}/huong-dan/cong-cu")
    print("  Cong cu do biet ca khac biet giua Codex CLI va tien ich VS Code —")
    print("  hai bo doc KHONG cung khuon, va mot cau hinh vua long CLI da tung")
    print("  lam vo tien ich VS Code o moi lan tao chat.")


    return 0


if __name__ == "__main__":
    sys.exit(main())
