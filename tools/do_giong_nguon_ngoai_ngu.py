r"""
do_giong_nguon_ngoai_ngu.py — giọng nhân bản từ clip TIẾNG ANH có đọc được
tiếng Việt không, và tốt kém thế nào so với giọng nhân bản từ clip tiếng Việt.

    powershell -ExecutionPolicy Bypass -File .\setup\do_giong_nguon_ngoai_ngu.ps1

## Vì sao phải đo, chứ không suy

Kho giọng cũ (`D:\Voiceclone_TTS`) có **hai lớp tách bạch**, và cách hệ cũ được
xây quyết định điều đó: **F5-TTS train bằng giọng tiếng Việt (7 giọng), XTTS
bằng giọng tiếng Anh (17 giọng)**. Chấm lại bằng ASR: 24/24 khớp nhãn, độ tin
0,987–1,000. Không có ngoại lệ nào.

⛔ ĐOẠN NÀY TỪNG GHI: *"VieNeu không nói được tiếng Anh"*, dẫn chứng
   `vieneu_utils/phonemize_text.py` khoá cứng `SEAPipeline(lang="vi")` +
   `G2P(lang="vi")`. **Khẳng định ấy SAI**, và nó đã bị bác bỏ bằng phép đo
   cùng ngày — xem `tools/do_engine_co_noi_tieng_anh.py`:

       VAO : The quick brown fox jumps over the lazy dog.
       ASR : The quick brown fox jumps over the lazy dog.       [en 0,996]

   `lang` của `sea-g2p` chọn **ngôn ngữ nền Đông Nam Á**, không phải danh sách
   ngôn ngữ đầu ra; chuỗi Latin đi qua một engine tiếng Anh dùng chung bên
   trong. Model được train from scratch trên ~10.000 giờ Anh–Việt.

⭐ Giữ lại đoạn sai thay vì xoá, vì bản thân hình dạng của nó mới là bài học:
   **một hằng số đọc rất thuyết phục, cộng một tiền đề ngầm chưa ai kiểm.**

⇒ Nhưng CÂU HỎI của tệp này thì KHÔNG đổi, và đó là lý do nó vẫn đứng: *"mượn
  âm sắc từ một người nói tiếng Anh thì **tiếng Việt** sinh ra có dùng được
  không"*. Engine đọc được tiếng Anh không trả lời câu ấy. Nó là một câu
  **thực nghiệm**, không phải một câu suy luận:

  · Lập luận nói ĐƯỢC: embedding người nói của VieNeu là một vector 192 chiều
    mô tả **bộ máy phát âm** (thanh quản, khoang cộng hưởng), không mô tả ngôn
    ngữ. Về nguyên tắc nó bất biến với thứ tiếng người ấy đang nói.
  · Lập luận nói KHÔNG: embedding ấy trích từ tiếng nói thật, và tiếng Anh có
    tập âm vị, nhịp trọng âm, và **không có thanh điệu**. Nếu embedding hấp thụ
    bất cứ phần nào của những thứ đó, tiếng Việt sinh ra sẽ lệch — và lệch ở
    đúng chỗ tiếng Việt không tha thứ: **thanh điệu**.

⭐ Thứ phân xử: **CER/WER của một bộ ASR tiếng Việt**. Nếu âm sắc ngoại ngữ làm
   sai thanh điệu, ASR sẽ nghe ra chữ khác — và CER nói ra điều đó bằng một con
   số, thay vì để ta tranh luận bằng cảm nhận.

⛔ KHÔNG kết luận từ một câu. Thanh điệu hỏng lộ ra ở những chữ cụ thể, nên phải
   đủ câu và đủ lượt để phân biệt "giọng này kém" với "câu này khó".
"""
from __future__ import annotations

import argparse
import io
import json
import os
import statistics
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    # Đệm theo DÒNG. Khi stdout ra tệp (mọi lần chạy qua trình bọc PowerShell
    # với `*> log.txt`) Python chuyển sang đệm KHỐI và tệp log nằm im ở 0 byte
    # suốt hàng chục phút — "đang chạy" và "đã treo" trông giống hệt nhau.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

#: Câu thử — chọn để **thanh điệu mang nghĩa**, vì đó là chỗ một âm sắc ngoại
#: ngữ được cho là sẽ hỏng. Mỗi câu có ít nhất một cặp chữ chỉ khác nhau ở dấu.
CAU = [
    "Ba tôi bảo bà ấy bán bánh ở bãi biển vào buổi sáng.",
    "Cô ấy cố gắng có được một cỗ máy mới cho công việc.",
    "Mẹ dặn mà tôi mải mê nên quên mất lời mẹ nói.",
    "Anh ta đánh rơi cái đàn xuống dòng sông lạnh.",
    "Tôi thấy thầy giáo đứng ở cửa lớp từ sáng sớm.",
    "Hôm nay trời hơi lạnh, nhớ mặc áo ấm khi ra ngoài.",
]


def _do_mot(ref_b64: str, cau: str) -> dict:
    from apps.ltt_voice import sidecar_client
    from voice_sidecar import do_chat_luong

    # ⛔ `noi()` không nhận `voice_id` — nó nhận thẳng biểu diễn tham chiếu.
    #    Đó là cố ý: sidecar không biết gì về tài khoản, hồ sơ hay quyền, và
    #    giữ nguyên như vậy là thứ khiến nó không cần CSDL.
    raw, dau = sidecar_client.noi(cau, ref_b64=ref_b64)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    try:
        tmp.write(raw)
        tmp.close()
        kq = do_chat_luong.do_tat_ca(tmp.name, text=cau)
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
    dh = kq.get("de_hieu") or {}
    return {
        "cer": dh.get("cer"),
        "wer": dh.get("wer"),
        "doc_duoc": (dh.get("text") or "").strip(),
        "dnsmos_ovrl": ((kq.get("tin_hieu") or {}).get("dnsmos") or {}).get("ovrl"),
        "on_dinh_giong": (kq.get("troi_giong") or {}).get("cosine_trung_binh"),
        "rtf": (dict(dau or {}).get("x-rtf")),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vong", type=int, default=2)
    ap.add_argument("--ra", default="tmp/giong_nguon_ngoai_ngu.json")
    a = ap.parse_args(argv)

    from sqlalchemy import select

    from apps.ltt_voice import tham_chieu
    from apps.ltt_voice.tables import VoiceProfile
    from platform_core.db import get_session

    gen = get_session()
    db = next(gen)
    try:
        ds = list(db.execute(select(VoiceProfile).where(
            VoiceProfile.dung_chung.is_(True),
            VoiceProfile.trang_thai == "active")
            .order_by(VoiceProfile.ten_hien_thi)).scalars())
        giong = []
        for h in ds:
            bd = tham_chieu.tim_repr_active(db, h.id)
            if bd is None:
                print(f"  [bo] {h.ten_hien_thi}: khong co bieu dien active")
                continue
            giong.append({"public_id": h.public_id, "ten": h.ten_hien_thi,
                          "ngon_ngu_khai": h.ngon_ngu,
                          "ref_b64": tham_chieu.nap_ref_b64(bd)})
    finally:
        gen.close()

    if not giong:
        print("KHO CHUNG RONG", file=sys.stderr)
        return 2

    print(f"{len(giong)} giong dung chung, {len(CAU)} cau, {a.vong} vong\n")
    ket = {}
    for g in giong:
        gia = []
        for v in range(a.vong):
            for i, c in enumerate(CAU, 1):
                try:
                    m = _do_mot(g["ref_b64"], c)
                except Exception as e:                    # noqa: BLE001
                    # Một câu hỏng là một SỐ ĐO, không phải một lý do dừng.
                    print(f"  [hong] {g['ten']} v{v + 1} c{i}: "
                          f"{type(e).__name__}: {e}")
                    continue
                gia.append(m)
                print(f"  {g['ten'][:26]:26} v{v + 1} c{i}  "
                      f"CER {(m['cer'] if m['cer'] is not None else -1):.4f}  "
                      f"WER {(m['wer'] if m['wer'] is not None else -1):.4f}  "
                      f"OVRL {(m['dnsmos_ovrl'] or 0):.3f}")
        ket[g["public_id"]] = {**{k: v for k, v in g.items()
                                  if k != "ref_b64"}, "mau": gia}

    def _tb(gia, k):
        v = [x[k] for x in gia if x.get(k) is not None]
        return (statistics.mean(v), statistics.pstdev(v), len(v)) if v else (None, None, 0)

    print("\n" + "=" * 76)
    print("  GIONG NGUON TIENG ANH CO DOC DUOC TIENG VIET KHONG")
    print("=" * 76)
    print(f"  {'giong':30} {'CER':>8} {'WER':>8} {'OVRL':>7} {'on_dinh':>8}")
    for pid, m in ket.items():
        c = _tb(m["mau"], "cer")
        w = _tb(m["mau"], "wer")
        o = _tb(m["mau"], "dnsmos_ovrl")
        s = _tb(m["mau"], "on_dinh_giong")
        print(f"  {m['ten'][:30]:30} "
              f"{(c[0] if c[0] is not None else -1):8.4f} "
              f"{(w[0] if w[0] is not None else -1):8.4f} "
              f"{(o[0] if o[0] is not None else -1):7.3f} "
              f"{(s[0] if s[0] is not None else -1):8.4f}   n={c[2]}")

    os.makedirs(os.path.dirname(a.ra) or ".", exist_ok=True)
    with open(a.ra, "w", encoding="utf-8", newline="\n") as f:
        json.dump(ket, f, ensure_ascii=False, indent=2)
    print(f"\nDa ghi: {a.ra}")
    print("\n⚠️ Doc bang nay canh NHAN NGUON, khong canh cot `ngon_ngu_khai` —")
    print("   ca bon dong hien dang khai 'vi' vi cot ay lay gia tri mac dinh.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
