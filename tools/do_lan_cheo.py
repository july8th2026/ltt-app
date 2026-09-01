r"""
do_lan_cheo.py — BẢNG 2×2: giọng nguồn VI/EN × văn bản VI/EN.

    powershell -ExecutionPolicy Bypass -File .\setup\xuat_ref_kho_chung.ps1
    powershell -ExecutionPolicy Bypass -File .\setup\do_lan_cheo.ps1

## Câu hỏi

Chủ sản phẩm chốt 01/09/2026: kho giọng **tách làn theo ngôn ngữ của clip
NGUỒN** — clip tiếng Việt phục vụ văn bản tiếng Việt, clip tiếng Anh phục vụ
văn bản tiếng Anh. Luật ấy đến từ cách kho cũ được xây (F5 train giọng Việt,
XTTS train giọng Anh), tức từ **kinh nghiệm của một hệ hai engine**.

Hệ mới chỉ có **một** engine, và nó **song ngữ thật**: model card khai
`language: ["vi","en"]`, train from scratch trên ~10.000 giờ EN–VI, và đo thật
qua ASR thì nó đọc tiếng Anh đúng từng chữ (`[en 0,996]`).

⇒ Nên luật tách làn **không phải một ràng buộc kỹ thuật**. Nó là một giả thuyết
  về **chất lượng**, và giả thuyết thì đo được:

      · Giọng nguồn EN đọc tiếng Việt có tệ hơn giọng nguồn VI không?
      · Giọng nguồn VI đọc tiếng Anh có tệ hơn giọng nguồn EN không?

⭐ Hai câu ấy độc lập, và câu trả lời hoàn toàn có thể lệch nhau — embedding
   người nói mô tả bộ máy phát âm, nhưng **tiếng Việt có thanh điệu còn tiếng
   Anh thì không**. Một giọng nguồn không thanh điệu đọc tiếng Việt là bài toán
   khó hơn chiều ngược lại.

## Đọc bảng thế nào

Thứ phân xử là **CER/WER của ASR ở đúng ngôn ngữ của văn bản**. Nếu âm sắc lệch
làn làm sai thanh điệu (VI) hay sai trọng âm (EN), bộ ASR nghe ra chữ khác — và
CER nói ra bằng một con số thay vì để ta cãi nhau bằng cảm nhận.

⛔ ĐỌC THEO **CHÊNH LỆCH GIỮA HAI Ô CÙNG HÀNG**, đừng đọc con số tuyệt đối. CER
   trên tiếng Anh và CER trên tiếng Việt là hai bộ ASR khác nhau, hai thứ tiếng
   khác nhau; so chúng với nhau không có nghĩa. Thứ có nghĩa là: *cùng một câu,
   giọng cùng làn so với giọng lệch làn*.

⚠️ Và nhớ sàn nhiễu: hai lượt sinh bình thường của **cùng một giọng** đã lệch
   nhau. Đo 01/09 với n=24, `cer` có tb 0,033 và độ lệch 0,018 — tức **55%
   tương đối**. Một chênh lệch nhỏ hơn thế thì chưa nói được gì, và bảng này in
   kèm độ lệch của chính nó để người đọc thấy điều đó.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    # `reconfigure`, không phải `io.TextIOWrapper` — xem test_353.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace",
                           line_buffering=True)

#: Câu tiếng Việt — chọn để **thanh điệu mang nghĩa**. Mỗi câu có ít nhất một
#: cặp chữ chỉ khác nhau ở dấu, vì thanh điệu đúng là chỗ một âm sắc nguồn
#: không-thanh-điệu được cho là sẽ hỏng.
CAU_VI = [
    "Ba tôi bảo bà ấy bán bánh ở bãi biển vào buổi sáng.",
    "Cô ấy cố gắng có được một cỗ máy mới cho công việc.",
    "Mẹ dặn mà tôi mải mê nên quên mất lời mẹ nói.",
    "Tôi thấy thầy giáo đứng ở cửa lớp từ sáng sớm.",
]

#: Câu tiếng Anh — chọn để **trọng âm và nguyên âm dài/ngắn mang nghĩa**.
CAU_EN = [
    "Please confirm your appointment for tomorrow morning at nine.",
    "Our team delivered the project ahead of schedule this quarter.",
    "The report shows a significant increase in customer retention.",
    "She recorded the record in a single afternoon session.",
]


def _do_mot(ref_b64: str, cau: str, lang: str) -> dict:
    from apps.ltt_voice import sidecar_client
    from voice_sidecar import do_chat_luong

    raw, dau = sidecar_client.noi(cau, ref_b64=ref_b64)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    try:
        tmp.write(raw)
        tmp.close()
        # ⛔ ASR phải chạy ở ĐÚNG ngôn ngữ của VĂN BẢN, không phải của giọng.
        #    Nghe một câu tiếng Anh bằng ASR tiếng Việt sẽ ra CER khủng khiếp
        #    cho mọi giọng, và bảng sẽ "chứng minh" một điều không có thật.
        kq = do_chat_luong.do_tat_ca(tmp.name, text=cau, ngon_ngu=lang)
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
    dh = kq.get("de_hieu") or {}
    return {
        "cer": dh.get("cer"), "wer": dh.get("wer"),
        "doc_duoc": (dh.get("text") or "").strip()[:120],
        "dnsmos_ovrl": ((kq.get("tin_hieu") or {}).get("dnsmos") or {}).get("ovrl"),
        "on_dinh_giong": (kq.get("troi_giong") or {}).get("cosine_trung_binh"),
    }


def _tb(gia, k):
    v = [x[k] for x in gia if x.get(k) is not None]
    if not v:
        return None, None, 0
    return (statistics.mean(v),
            (statistics.pstdev(v) if len(v) > 1 else 0.0), len(v))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default="tmp/ref_kho_chung.json")
    ap.add_argument("--moi-lan", type=int, default=4,
                    help="So giong LAY MAU cho moi lan nguon.")
    ap.add_argument("--chi-text", default="", choices=["", "vi", "en"],
                    help="Chi do MOT hang cua bang, de don phan giai vao do.")
    ap.add_argument("--cau-lap", type=int, default=1,
                    help="Lap moi cau bao nhieu lan (tang n, giam sai so).")
    ap.add_argument("--ra", default="tmp/lan_cheo.json")
    a = ap.parse_args(argv)

    if not os.path.isfile(a.ref):
        print(f"THIEU {a.ref} — chay `xuat_ref_kho_chung.ps1` truoc.",
              file=sys.stderr)
        return 2
    with open(a.ref, encoding="utf-8") as f:
        cac = json.load(f)

    theo_lan = {"vi": [], "en": []}
    for g in cac:
        if g.get("ngon_ngu_khai") in theo_lan:
            theo_lan[g["ngon_ngu_khai"]].append(g)
    for k in theo_lan:
        # ⛔ Lấy mẫu ĐỀU theo danh sách đã sắp, không lấy ngẫu nhiên: phép đo
        #    phải lặp lại được. Một lô ngẫu nhiên khác nhau mỗi lượt thì hai
        #    lượt đo không so được với nhau, và đó đúng là thứ đã làm K3 mất
        #    hai vòng.
        ds = sorted(theo_lan[k], key=lambda x: x["public_id"])
        buoc = max(1, len(ds) // a.moi_lan)
        theo_lan[k] = ds[::buoc][:a.moi_lan]

    thieu = [k for k, v in theo_lan.items() if not v]
    if thieu:
        print(f"KHONG CO GIONG O LAN {thieu}", file=sys.stderr)
        return 2

    BO = {"vi": CAU_VI, "en": CAU_EN}
    if a.chi_text:
        # ⭐ Dồn phân giải vào ĐÚNG hàng còn mập mờ, thay vì đo lại cả bảng.
        #    Lượt đầu (4 giọng × 4 câu) cho hàng `en` một câu trả lời dứt khoát
        #    (0,0208 vs 0,0198 — chênh 5% tương đối) và hàng `vi` một câu chưa
        #    dứt (0,0342 vs 0,0725, nhưng ±0,069). Đo lại cả bảng là tiêu một
        #    nửa thời gian GPU cho một câu hỏi đã trả lời xong.
        BO = {a.chi_text: BO[a.chi_text]}
    print(f"2x2: nguon {[f'{k}:{len(v)}' for k, v in theo_lan.items()]}  x  "
          f"van ban vi:{len(CAU_VI)} en:{len(CAU_EN)}\n")

    o = {}
    for lan_nguon, ds in theo_lan.items():
        for lan_text, cau_ds in BO.items():
            gia = []
            for g in ds:
                for c in cau_ds * max(1, a.cau_lap):
                    try:
                        m = _do_mot(g["ref_b64"], c, lan_text)
                    except Exception as e:              # noqa: BLE001
                        # Một câu hỏng là một SỐ ĐO, không phải lý do dừng.
                        print(f"  [hong] {g['ten'][:22]} / {lan_text}: "
                              f"{type(e).__name__}: {e}")
                        continue
                    gia.append({**m, "giong": g["ten"], "cau": c})
                    print(f"  nguon={lan_nguon} text={lan_text} "
                          f"{g['ten'][:24]:24} CER "
                          f"{(m['cer'] if m['cer'] is not None else -1):.4f}")
            o[f"{lan_nguon}->{lan_text}"] = gia

    print("\n" + "=" * 74)
    print("  BANG 2x2 — doc theo CHENH LECH GIUA HAI O CUNG HANG")
    print("=" * 74)
    print(f"  {'van ban':10} {'nguon VI':>22} {'nguon EN':>22}   {'ket luan':>12}")
    for lan_text in BO:
        dong = []
        for lan_nguon in ("vi", "en"):
            c, s, n = _tb(o[f"{lan_nguon}->{lan_text}"], "cer")
            dong.append((c, s, n))
        (cv, sv, nv), (ce, se, ne) = dong
        cung = cv if lan_text == "vi" else ce
        lech = ce if lan_text == "vi" else cv
        san = max(sv or 0, se or 0)
        kl = ("cung lan TOT hon" if lech - cung > san
              else "lech TOT hon" if cung - lech > san
              else "KHONG PHAN BIET")
        print(f"  {lan_text:10} "
              f"CER {cv:.4f} ±{sv:.4f} n={nv:<3}  "
              f"CER {ce:.4f} ±{se:.4f} n={ne:<3}  {kl}")
    print("\n  'KHONG PHAN BIET' = chenh lech nho hon do lech giua cac lan sinh.")
    print("  Do KHONG phai 'hai ben bang nhau' — no la 'phep do nay chua du "
          "phan giai de noi'.")

    os.makedirs(os.path.dirname(a.ra) or ".", exist_ok=True)
    with open(a.ra, "w", encoding="utf-8", newline="\n") as f:
        json.dump(o, f, ensure_ascii=False, indent=2)
    print(f"\nDa ghi: {a.ra}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
