r"""
do_nhan_ban_tu_kho_cu.py — giọng nhân bản từ kho cũ có GIỐNG người nói không?

    powershell -ExecutionPolicy Bypass -File .\setup\do_nhan_ban_tu_kho_cu.ps1

## Câu hỏi

Ghi danh thành công **không** có nghĩa là nhân bản tốt. `ghi_danh` trả về một
embedding cho mọi tệp wav hợp lệ; nó không bao giờ nói "giọng này không học
được". Câu hỏi thật là: bản sinh ra có gần người nói gốc hơn là gần một người
lạ không?

## Cách đo, và vì sao cần CẢ HAI số

Với mỗi giọng đã ghi danh:

    tuong_dong  = cosine( bản sinh ra , clip gốc của CHÍNH giọng đó )
    san_nguoi_la = cosine( bản sinh ra , clip gốc của các giọng KHÁC )

⛔ Một mình `tuong_dong` không nói lên gì. Bộ mã hoá người nói cho hai người
   Việt bất kỳ một cosine khá cao — nó đo giọng, và mọi giọng người đều giống
   nhau hơn là giống tiếng ồn. Con số có nghĩa là **khoảng cách giữa hai số**:
   nhân bản đúng thì `tuong_dong` phải cao hơn `san_nguoi_la` rõ rệt.

⭐ Đây đúng là sai lầm mà `chon_doan` từng mắc ở một lớp khác (chọn đoạn nhiễu
   vì nó "đại diện" cho một clip bẩn), và là sai lầm mà mọi phép đo hôm nay
   tránh bằng cách dựng một sàn để so.

⚠️ Chạm GPU thật, không chạm sổ tiền (gọi thẳng cổng giọng bằng ref đã lưu).
"""
from __future__ import annotations

import argparse
import io
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CAU_VI = ("Hôm nay tôi thử đọc một đoạn ngắn để kiểm tra giọng vừa được nhân "
          "bản, xem nó có còn giống người nói ban đầu không.")
CAU_EN = ("Today I am reading a short passage to check whether the cloned "
          "voice still sounds like the original speaker.")


class KhongDoDuoc(RuntimeError):
    """Không đo được thì VỠ, không lặng lẽ thành một con số."""


def _co_ve_en(ten: str) -> bool:
    """Giọng này nên đọc câu tiếng Anh hay tiếng Việt.

    Đọc từ kết quả ASR đã đo (`tmp/kho_giong_cu.json`) nếu có, chứ không đoán
    theo tên: đúng bốn cái tên tiếng Việt (`hoathinh_female`, `meoquan_men`,
    `tamlyhoc_men`, `cg_huong_nam`) lại là giọng **nói tiếng Anh** — tên ở đó
    là tên KÊNH nội dung, không phải ngôn ngữ.
    """
    try:
        d = json.load(open("tmp/kho_giong_cu.json", encoding="utf-8"))
    except (OSError, ValueError):
        return False
    for m in d:
        if m.get("ten") == ten:
            return (m.get("nghe_lai") or {}).get("ngon_ngu") == "en"
    return False


def _kien_nhan(ham, *, lan: int = 20):
    """Chạy `ham`, và **chờ** khi cổng giọng báo bận.

    🔴 BẬN KHÔNG PHẢI HỎNG. Cổng giọng có một suất GPU; hai phép đo chạy chồng
       nhau thì lượt sau nhận `429` → `SidecarBan`. Bản đầu để nó bay lên, và
       một lượt đo **24 giọng × 5 cửa sổ** chết ở giọng đầu tiên sau khi đã tiêu
       hàng chục phút GPU.

    ⭐ Đây đúng là phân biệt mà `features._goi_va_dich_loi` đã phải làm ở tầng
       job (`SidecarBan` → `DangBanTam`, xếp lại chứ không đánh dấu hỏng). Một
       công cụ đo cũng cần nó, chỉ là nó tự chờ thay vì nhờ hàng đợi.
    """
    import time as _t

    from apps.ltt_voice.sidecar_client import SidecarBan

    for i in range(lan):
        try:
            return ham()
        except SidecarBan as e:
            cho = max(2.0, float(getattr(e, "retry_after_s", 5.0) or 5.0))
            print(f"    (cong giong ban, cho {cho:.0f}s — lan {i + 1}/{lan})")
            _t.sleep(cho)
    raise KhongDoDuoc(f"cong giong ban suot {lan} lan thu — bo cuoc")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--email", default="thu.giongnoi@lttstudios.local")
    ap.add_argument("--clip-dir", default="tmp/giong_cu")
    ap.add_argument("--ra", default="tmp/nhan_ban_kho_cu.json")
    ap.add_argument("--kho", type=int, default=0,
                    help="So cua so trong kho tham chieu (K2). 0 = duong cu, "
                         "mot cua so. >1 = gop speaker_emb qua ca kho.")
    a = ap.parse_args(argv)

    import numpy as np
    import soundfile as sf

    from apps.ltt_voice import sidecar_client
    from voice_sidecar.do_chat_luong import _bo_ma_hoa_giong, _cosine, _embed

    bo = _bo_ma_hoa_giong()
    if bo is None:
        print("khong nap duoc bo ma hoa nguoi noi", file=sys.stderr)
        return 2

    # ⛔ KHÔNG đi qua CSDL. Bản đầu đọc `VoiceProfile` rồi `features.giai_giong`,
    #    và `features` kéo theo `sqlalchemy` — thứ **không có** trong venv giọng
    #    (nơi duy nhất có `librosa` + bộ mã hoá người nói). Hai venv, hai bộ thư
    #    viện, và phép đo này cần đúng cái venv không có CSDL.
    #
    # ⭐ Hoá ra bỏ CSDL đi lại đo được thứ SẠCH HƠN: ghi danh thẳng từ clip đo
    #    đúng chuỗi *clip → embedding → sinh tiếng*, không phụ thuộc một hồ sơ
    #    nào đã lưu. Một ràng buộc kỹ thuật đẩy phép đo về gần hơn với thứ nó
    #    định hỏi.

    # Nhúng của MỌI clip gốc — dùng làm sàn "người lạ".
    goc = {}
    for f in sorted(os.listdir(a.clip_dir)):
        if not f.endswith(".wav"):
            continue
        w, sr = sf.read(os.path.join(a.clip_dir, f), dtype="float32",
                        always_2d=False)
        e = _embed(bo, np.asarray(w, dtype=np.float32), int(sr))
        if e is not None:
            goc[f[:-4]] = e
    if len(goc) < 3:
        raise KhongDoDuoc(f"chi co {len(goc)} clip goc — khong dung san duoc")
    print(f"{len(goc)} clip goc lam san so sanh\n")

    ra = []
    for ten in sorted(goc):
        # ⛔ ĐƯỜNG DẪN TUYỆT ĐỐI. Cổng giọng chạy như một dịch vụ, thư mục làm
        #    việc của nó là `C:\LTTPlatform\app` — nên một đường dẫn tương đối
        #    ở đây trỏ tới một chỗ không tồn tại bên đó.
        #
        #    Triệu chứng: `400 khong thay tep: tmp/giong_cu\...`. Đọc lên như
        #    một lỗi của ta, và nó đúng là lỗi của ta, chỉ không phải lỗi mình
        #    tưởng: tệp có thật, chỉ là hai tiến trình đứng ở hai chỗ khác nhau.
        duong = os.path.abspath(os.path.join(a.clip_dir, ten + ".wav"))
        ghi = _kien_nhan(
            lambda: (sidecar_client.ghi_danh_kho(duong, denoise=True,
                                                 so_clip=a.kho)
                     if a.kho > 1
                     else sidecar_client.ghi_danh(duong, denoise=True)))
        ref_b64 = ghi.get("ref_b64")
        if not ref_b64:
            raise KhongDoDuoc(f"{ten}: ghi_danh khong tra ve ref_b64")
        cau = CAU_EN if _co_ve_en(ten) else CAU_VI
        raw, dau = _kien_nhan(lambda: sidecar_client.noi(cau, ref_b64=ref_b64))
        w, sr = sf.read(io.BytesIO(raw), dtype="float32", always_2d=False)
        e = _embed(bo, np.asarray(w, dtype=np.float32), int(sr))
        if e is None:
            raise KhongDoDuoc(f"{ten}: khong nhung duoc ban sinh ra")

        diem = {k: _cosine(e, v) for k, v in goc.items()}
        ban_than = diem[ten]
        la = sorted((v for k, v in diem.items() if k != ten), reverse=True)
        ra.append({
            "ten": ten,
            "tuong_dong": round(ban_than, 4) if ban_than is not None else None,
            "san_nguoi_la_cao_nhat": round(la[0], 4) if la else None,
            "san_nguoi_la_trung_binh": round(statistics.mean(la), 4) if la else None,
            "gan_nhat": max(diem, key=diem.get),
        })
        d = ra[-1]
        print(f"  {ten[:34]:34} tuong dong {d['tuong_dong']}  "
              f"san la {d['san_nguoi_la_trung_binh']} "
              f"(cao nhat {d['san_nguoi_la_cao_nhat']})  gan nhat: {d['gan_nhat']}")

    print("\n" + "=" * 74)
    print("  NHAN BAN CO GIONG NGUOI NOI KHONG")
    print("=" * 74)
    for d in ra:
        if d["tuong_dong"] is None:
            print(f"  {d['ten'][:38]:38} — khong khop duoc clip goc")
            continue
        bien = d["tuong_dong"] - (d["san_nguoi_la_trung_binh"] or 0)
        dung = d["gan_nhat"] == d["ten"]
        print(f"  {d['ten'][:38]:38} bien {bien:+.4f}  "
              f"{'DUNG NGUOI' if dung else 'SAI NGUOI'}")
    print("\n  ⛔ `bien` la thu duy nhat co nghia: tuong dong tru san nguoi la.")
    print("     Bo ma hoa cho hai giong nguoi bat ky mot cosine kha cao, nen")
    print("     mot so `tuong_dong` 0,9 tu no khong chung minh dieu gi.")

    os.makedirs(os.path.dirname(a.ra) or ".", exist_ok=True)
    with open(a.ra, "w", encoding="utf-8", newline="\n") as f:
        json.dump(ra, f, ensure_ascii=False, indent=2)
    print(f"\nDa ghi: {a.ra}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
