r"""
do_ho_so_giong.py — đo TỐC ĐỘ ĐỌC của từng giọng, sinh `ho_so_giong.json`.

    powershell -ExecutionPolicy Bypass -File .\setup\do_ho_so_giong.ps1
    py tools\do_ho_so_giong.py --luot 3 --giong "Adam,Mai Anh"

🔴 VÌ SAO CẦN, KHI `gia.py` ĐÃ CÓ HAI HẰNG SỐ ĐO THẬT

   Hai hằng số ấy đo ngày 30/08 trên RTX 5060 Ti, và chính chú thích của chúng
   nói ra giới hạn: *"Số đo là của MỘT bộ giọng trên MỘT card; một giọng đọc
   chậm hơn là hoàn toàn bình thường."*

   Một hệ khác giữ bảng tương đương cho 61 giọng (`D:\Viral`,
   `capcut_tts.TOC_DOC`) và chênh lệch giữa hai giọng **cùng ngôn ngữ** lên tới
   **43 %**. Một hằng số phẳng bắt mọi bài trả giá cho giọng chậm nhất — hoặc
   giữ thiếu ở đúng giọng ấy, và giữ thiếu là một lỗi **sổ sách**.

## ⛔ BA LƯỢT, KHÔNG PHẢI MỘT

Một lượt cho một **con số**; ba lượt cho một **dải**. Không có dải thì không rút
được `do_lech_chuan`, tức không biết phải ước thừa bao nhiêu — và `ho_so_giong`
cần đúng con số ấy để tính cận dưới an toàn.

`tham_so_cong_khai.py` đã ghi lời cảnh báo này cho một phép đo khác, và nó vẫn
đúng ở đây: *"một vòng đo, không phải nhiều vòng như `cong_chat_luong_voice.py`
đòi để rút dung sai từ chính số đo."*

## ⛔ ĐO KHI MÁY RẢNH, VÀ CÔNG CỤ NÀY TỰ KIỂM

Một lượt đo trên máy đang chạy gate cho ra `do_lech_chuan` phồng lên, và hệ quả
đi **thẳng vào tiền**: σ lớn ⇒ cận dưới thấp ⇒ ước thừa nhiều ⇒ giữ chỗ nhiều
hơn cần. Không ai mất tiền (phần dư được hoàn), nhưng khách thấy số dư tụt sâu
hơn thực tế, và đó là một trải nghiệm tệ sinh ra từ một phép đo cẩu thả.

⇒ Công cụ **từ chối chạy** khi thấy tiến trình gate/test đang sống, trừ khi có
  `--bo-qua-kiem-may`.

## ⚠️ Nó CHIẾM GPU

Mỗi giọng × mỗi bậc × mỗi lượt là một lượt `infer` thật. Với 20 preset × 2 bậc
× 3 lượt là 120 lượt sinh — khoảng mười lăm phút GPU liên tục. Chạy nó trong
giờ có khách là lấy GPU của họ.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import statistics
import subprocess
import sys
import time

GOC = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC))

RA = GOC / "apps" / "ltt_voice" / "ho_so_giong.json"

#: Hai bậc độ dài. Cần **hai** để tách phí khởi động khỏi tốc độ đọc:
#: một bậc chỉ cho một điểm, và một điểm không dựng được đường thẳng.
#:
#: ⛔ Bậc ngắn phải đủ ngắn để phí khởi động **chiếm tỉ trọng lớn**, nếu không
#:    phép giải hai ẩn sẽ rất nhạy với nhiễu.
#: Hai bac do dai. Mot bac cho MOT diem, va mot diem khong dung duoc mot duong
#: thang - nen khong tach duoc phi khoi dong khoi toc do doc.
#:
#: [!] Bac "dai" dung `_van_ban_dai()` chu KHONG phai mot hang so o day. Ban dau
#:     ghi `("dai", None)` cho co cho, va cai `None` ay lam kieu cua CA BANG
#:     thanh `str | None` - roi `len(t)` o vong do bi mypy bat dung. Mot cho
#:     trong de ghi chu khong dang lam yeu kieu cua thu that.
BAC: list[tuple[str, str]] = [
    ("ngan", "Xin chao, day la mot cau ngan de do phi khoi dong."),
]
DAI_MUC_TIEU = 1200


def _van_ban_dai() -> str:
    mau = ("Hom nay chung ta noi ve mot chu de moi, va toi se doc that ro rang "
           "de phep do co y nghia. ")
    s = ""
    while len(s) < DAI_MUC_TIEU:
        s += mau
    return s[:DAI_MUC_TIEU]


def _may_ban() -> list:
    """PID của tiến trình gate/test đang chạy. Rỗng = máy rảnh.

    ⛔ Hỏi `Win32_Process`, không hỏi `ps` của Git Bash — `ps` KHÔNG thấy tiến
       trình Windows và đã một lần báo "đã xong" cho một tiến trình còn sống.
    """
    ma = ("Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
          "Where-Object { $_.CommandLine -like '*gate.py*' -or "
          "$_.CommandLine -like '*test_nhanh*' -or $_.CommandLine -like '*pytest*' } | "
          "ForEach-Object { $_.ProcessId }")
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", ma],
                           capture_output=True, text=True, timeout=60)
        return [d.strip() for d in r.stdout.splitlines() if d.strip()]
    except Exception as e:  # noqa: BLE001 - hoi may la viec phu, khong duoc nem
        # [!] NOI RA. Khong hoi duoc thi ta tra ve "coi nhu may DANG BAN", tuc
        #     cong cu tu tu choi chay - dung huong an toan. Nhung im lang o day
        #     bien mot loi moi truong (thieu powershell, timeout) thanh mot
        #     "may dang ban" khong bao gio giai thich duoc, va nguoi dung se di
        #     tim mot tien trinh khong ton tai.
        print(f"  [kiem may] khong hoi duoc Win32_Process: "
              f"{type(e).__name__}: {e}")
        return ["(khong hoi duoc)"]


def _do_mot(sidecar_client, text: str, preset: str) -> float:
    """Một lượt sinh, trả **số giây tiếng** đo từ header của cổng."""
    _wav, dau = sidecar_client.noi(text, preset=preset)
    g = dau.get("X-Duration-S")
    if g is None:
        raise RuntimeError("cong khong tra X-Duration-S")
    return float(g)


def do_mot_giong(sidecar_client, preset: str, luot: int) -> dict:
    """Hồ sơ của một giọng, hoặc `{}` nếu không đo được."""
    dai = _van_ban_dai()
    mau: dict[str, list[tuple[int, float]]] = {"ngan": [], "dai": []}
    for _ in range(luot):
        for ten, t in (("ngan", BAC[0][1]), ("dai", dai)):
            try:
                mau[ten].append((len(t), _do_mot(sidecar_client, t, preset)))
            except Exception as e:  # noqa: BLE001
                print(f"    [{preset}/{ten}] loi: {type(e).__name__}: {e}")
                return {}

    # Giai he hai an tu TRUNG BINH cua hai bac:
    #     giay = khoi_dong + ky_tu / toc_do
    gn = statistics.mean(g for _, g in mau["ngan"])
    gd = statistics.mean(g for _, g in mau["dai"])
    nn, nd = mau["ngan"][0][0], mau["dai"][0][0]
    if gd <= gn or nd <= nn:
        print(f"    [{preset}] bac dai KHONG dai hon bac ngan - bo qua")
        return {}
    toc_do = (nd - nn) / (gd - gn)
    khoi_dong = gn - nn / toc_do

    # `do_lech_chuan` rut tu chinh cac luot cua BAC DAI: do la bac quyet dinh
    # gia cua moi bai that, va no it nhay voi nhieu hon bac ngan.
    if luot >= 2:
        tocs = [nd / max(1e-6, g - khoi_dong) for _, g in mau["dai"]]
        sd = statistics.stdev(tocs)
    else:
        sd = 0.0

    return {
        "ky_tu_moi_giay": round(toc_do, 3),
        "do_lech_chuan": round(sd, 3),
        "giay_khoi_dong": round(max(0.0, khoi_dong), 3),
        "so_luot": luot,
        "mau_giay_dai": [round(g, 3) for _, g in mau["dai"]],
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--luot", type=int, default=3,
                    help="So luot moi bac (>=3 de rut duoc do lech chuan).")
    ap.add_argument("--giong", default="",
                    help="Danh sach preset, phay ngan cach. Rong = tat ca.")
    ap.add_argument("--bo-qua-kiem-may", action="store_true")
    ap.add_argument("--ra", default=str(RA))
    args = ap.parse_args(argv)

    ban = [] if args.bo_qua_kiem_may else _may_ban()
    if ban:
        print(f"MAY DANG BAN (gate/test: {', '.join(ban)}). "
              "Do luc nay cho `do_lech_chuan` phong len, va con so ay di thang "
              "vao phep giu cho credit. Cho may ranh, hoac dung --bo-qua-kiem-may.",
              file=sys.stderr)
        return 2

    from apps.ltt_voice import giong_mau, sidecar_client
    from voice_sidecar import tham_so

    if not sidecar_client.san_sang():
        print("Cong giong chua san sang (thieu LTT_VOICE_SIDECAR_TOKEN).",
              file=sys.stderr)
        return 2

    ten_giong = ([t.strip() for t in args.giong.split(",") if t.strip()]
                 or [g.ma for g in giong_mau.DANH_SACH])
    print(f"Do {len(ten_giong)} giong x 2 bac x {args.luot} luot "
          f"= {len(ten_giong) * 2 * args.luot} luot sinh\n")

    ra = {}
    t0 = time.time()
    for i, ten in enumerate(ten_giong, 1):
        print(f"[{i}/{len(ten_giong)}] {ten} ...", flush=True)
        ho_so = do_mot_giong(sidecar_client, ten, args.luot)
        if ho_so:
            ra[ten] = ho_so
            print(f"    {ho_so['ky_tu_moi_giay']} ky tu/giay "
                  f"(sd {ho_so['do_lech_chuan']}), khoi dong "
                  f"{ho_so['giay_khoi_dong']}s")

    # ⛔ KHONG DO DUOC GI THI KHONG GHI GI. Do 10/09/2026: mot luot hong 20/20
    #    (loi header, xem `DauPhanHoi` o sidecar_client) van ghi de tep bang
    #    chung -- dat `phien_ban: do-2026-09-10`, XOA khoa `_chua_do`, va de
    #    `giong` rong. Tuc tep khai DA DO ma khong co mot con so nao, va dong
    #    duy nhat giai thich "rong = chua do" thi bien mat.
    #
    # 🔑 Mot ban ghi "da do" rong TE HON khong ghi gi: no bien mot khoang
    #    trong THANH THAT thanh mot loi bao dam sai, va nguoi doc sau khong con
    #    cach nao phan biet "da do, giong nao cung hong" voi "chua chay bao gio".
    if not ra:
        print(f"\nKHONG do duoc giong nao (0/{len(ten_giong)}) "
              f"({time.time() - t0:.0f}s)")
        print(f"  -> KHONG ghi {args.ra}. Tep cu giu nguyen.")
        print("  -> Sua nguyen nhan roi chay lai; dung ha ky vong xuong.")
        return 1

    cu = {}
    try:
        cu = json.loads(pathlib.Path(args.ra).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass

    d = {
        "_ghi_chu": ("Ho so toc do doc DO DUOC cua tung giong. SINH RA bang "
                     "tools/do_ho_so_giong.py, dung sua tay."),
        "_cach_doc": ("ky_tu_moi_giay = trung binh; do_lech_chuan rut tu chinh "
                      "cac luot do; giay_khoi_dong = chan tuyen tinh. "
                      "`ho_so_giong.ky_tu_moi_giay_an_toan` tra CAN DUOI "
                      "(tb - 2*sd) vi con so nay dung de GIU CHO credit."),
        "phien_ban": time.strftime("do-%Y-%m-%d"),
        "engine_tham_so": tham_so.PHIEN_BAN_THAM_SO,
        "giong": ra,
    }
    thieu = [t for t in ten_giong if t not in ra]
    if thieu:
        # Ghi ra AI thieu, khong chi ghi BAO NHIEU: mot lan sau con nguoi phai
        # biet giong nao dang lui ve hang so chung ma khong phai do lai het.
        d["_thieu"] = (f"Chua do duoc {len(thieu)}/{len(ten_giong)} giong; "
                       f"chung lui ve hang so chung trong gia.py: "
                       f"{', '.join(thieu)}")
    elif "_chua_do" in cu:
        pass  # do du het -> khoa `_chua_do` khong con nghia, bo di

    # ⛔ `newline="\n"` BAT BUOC tren Windows. `write_text` mac dinh dich moi
    #    `\n` thanh `\r\n`, va `ho_so_giong.json` trong git LA LF -> lan chay
    #    10/09 lam `check_xuong_dong` DO voi "HEAD=LF -> hien tai=CRLF, 232 dong".
    #
    # 🔑 Hong o day ton kem hon binh thuong: tep bi ghi lai TOAN BO nen
    #    `git diff` khong con doc duoc, va nguoi doc sau khong phan biet duoc
    #    "phep do ra so khac" voi "chi doi ket dong".
    pathlib.Path(args.ra).write_text(
        json.dumps(d, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8", newline="\n")
    print(f"\nDa ghi {len(ra)}/{len(ten_giong)} ho so vao {args.ra} "
          f"({time.time() - t0:.0f}s)")
    if thieu:
        print(f"⚠ {len(thieu)} giong KHONG do duoc - chung se lui ve hang so "
              f"chung. Da ghi danh sach vao khoa `_thieu`.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
