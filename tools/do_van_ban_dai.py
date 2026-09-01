r"""
do_van_ban_dai.py — ĐO chất lượng bản GHÉP ở 3.000 và 5.000 ký tự.

    $env:LTT_VOICE_SIDECAR_TOKEN = '<token>'
    C:\LTTPlatform\vieneu-venv\Scripts\python.exe tools\do_van_ban_dai.py

⭐ Đây là số liệu để quyết định có nới `TRAN_KY_TU_CONG_KHAI` hay không. Đường
   đã xây (chia đoạn + `/v1/speech-dai`), cổng vẫn đóng ở 1.500 — và thứ tự đó
   là có chủ ý: **hạ tầng chạy được không phải bằng chứng chất lượng.**

## Ba câu hỏi, ba con số

  ① Còn là một người nói không?   -> `troi_giong` (cửa sổ 3 giây)
  ② Mối nối có nghe thấy không?   -> khoảng lặng dài nhất + nhịp nghỉ đã dùng
  ③ Đọc có đúng chữ không?        -> CER/WER/sai dấu qua ASR

## Vì sao chạy trong VENV GIỌNG chứ không venv nền tảng

`do_chat_luong` cần onnxruntime + perth + faster-whisper — chúng ở venv giọng.
`apps/ltt_voice/text_pipeline.py` thì **chỉ dùng `re`** (cố ý), nên nhập được
vào đây mà không kéo theo `platform_core`. Còn cổng thì gọi qua HTTP loopback.

⛔ KHÔNG đi qua hàng đợi job: đây là phép đo MODEL, không phải phép đo hệ thống.
   Đường đầu-tới-cuối đã có `tools/chay_thu_ltt_voice.py` lo.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# `reconfigure`, khong phai boc mot TextIOWrapper moi — xem chu thich day du o
# `voice_sidecar/do_chat_luong.py`. Hai lop boc tren cung mot buffer se dong
# buffer do khi lop thu nhat bi thu hoi.
if hasattr(sys.stdout, "reconfigure"):
    # 🔴 `line_buffering=True` KHÔNG phải chuyện gọn gàng — nó là thứ quyết định
    #    một phép đo dài có theo dõi được hay không.
    #
    #    Khi stdout đi ra MÀN HÌNH, Python tự đệm theo dòng. Khi nó đi ra một
    #    TỆP — tức mọi lần chạy qua trình bọc PowerShell với `*> log.txt` — nó
    #    chuyển sang đệm KHỐI, và tệp log nằm im ở 0 byte suốt hàng chục phút.
    #
    # ⛔ Hệ quả không phải bất tiện: tôi mất hai lượt chờ vì không phân biệt được
    #    "đang chạy" với "đã treo", và phải đi hỏi `nvidia-smi` để biết tiến
    #    trình còn sống. Một công cụ đo mà không nói nó đang ở đâu thì mọi sự cố
    #    của nó đều trông giống nhau.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace",
                           line_buffering=True)

#: Văn bản nguồn. Câu dài ngắn xen kẽ, có số, có tên riêng, có dấu thanh dày —
#: giống một bài đọc thật hơn là một câu lặp lại. Một câu lặp lại sẽ cho CER
#: đẹp giả tạo, vì ASR chỉ phải đoán đúng một lần rồi lặp.
KHOI = [
    "Buổi sáng ở thành phố bắt đầu bằng tiếng còi xe và mùi cà phê từ những "
    "quán nhỏ ven đường.",
    "Chị Lan mở cửa hàng lúc sáu giờ ba mươi, sắp lại từng chiếc ghế, rồi ngồi "
    "đợi người khách đầu tiên.",
    "Năm 2019, khu phố này còn vắng.",
    "Bây giờ thì khác hẳn: mười bảy hàng quán chen nhau trên đúng một trăm mét "
    "đường, và buổi tối người ta phải gửi xe cách đó hai dãy nhà.",
    "Ông Tám bán bánh mì ở góc đường nói rằng ông đã đứng ở đó ba mươi hai năm, "
    "và chưa từng nghỉ một ngày nào ngoài mùng một Tết.",
    "Có những thay đổi đến chậm tới mức không ai kịp nhận ra chúng đang xảy ra.",
    "Con hẻm nhỏ phía sau chợ giờ đã thành một dãy quán cà phê, nơi những người "
    "trẻ ngồi làm việc với máy tính xách tay suốt cả buổi chiều.",
    "Nhưng vẫn còn đó tiếng rao quen thuộc mỗi tối, và tiếng chuông nhà thờ lúc "
    "năm giờ sáng.",
]


def _van_ban(so_ky_tu: int) -> str:
    ra, n, i = [], 0, 0
    while n < so_ky_tu:
        c = KHOI[i % len(KHOI)]
        ra.append(c)
        n += len(c) + 1
        i += 1
    cat = " ".join(ra)[:so_ky_tu]
    return (cat.rsplit(".", 1)[0] + ".") if "." in cat else cat


def _goi(duong: str, body: dict, token: str, timeout: float = 1800.0):
    cong = (os.environ.get("LTT_VOICE_SIDECAR_PORT") or "8120").strip()
    url = f"http://127.0.0.1:{cong}{duong}"
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            # ⚠️ Khoá viết THƯỜNG. HTTP/1.1 không phân biệt hoa thường ở tên
            #    header, và FastAPI phát ra chữ thường — nên tra `X-Gen-S`
            #    trên `dict(r.headers)` trả None và mọi cột hiện `-`, trông
            #    y như cổng không gửi gì.
            return r.read(), {k.lower(): v for k, v in r.headers.items()}
    except urllib.error.HTTPError as e:
        chi_tiet = e.read()[:400].decode("utf-8", "replace")
        raise SystemExit(f"cong tra {e.code}: {chi_tiet}") from e


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--do-dai", type=int, nargs="+", default=[1500, 3000, 5000])
    ap.add_argument("--thu-muc", default="tmp/vdai")
    a = ap.parse_args(argv)

    token = (os.environ.get("LTT_VOICE_SIDECAR_TOKEN") or "").strip()
    if not token:
        print("Thieu LTT_VOICE_SIDECAR_TOKEN.", file=sys.stderr)
        return 2

    os.makedirs(a.thu_muc, exist_ok=True)

    from apps.ltt_voice import text_pipeline
    from apps.ltt_voice.tham_so_cong_khai import TRAN_MOI_LUOT_SINH
    from voice_sidecar import do_chat_luong

    bang = []
    for n in a.do_dai:
        chuan = text_pipeline.chuan_bi(_van_ban(n),
                                       tran_moi_doan=TRAN_MOI_LUOT_SINH)
        doan = chuan.doan or [chuan.da_chuan_hoa]
        print(f"\n{'=' * 70}")
        print(f"  {len(chuan.da_chuan_hoa)} ky tu -> {len(doan)} doan "
              f"{[len(d) for d in doan]}")
        print("=" * 70)

        if len(doan) > 1:
            wav, headers = _goi("/v1/speech-dai", {"texts": doan}, token)
        else:
            wav, headers = _goi("/v1/speech", {"text": doan[0]}, token)

        duong = os.path.join(a.thu_muc, f"dai_{n}.wav")
        with open(duong, "wb") as f:
            f.write(wav)
        with open(os.path.join(a.thu_muc, f"dai_{n}.txt"), "w",
                  encoding="utf-8") as f:
            f.write(chuan.da_chuan_hoa)

        print(f"  ghi   : {duong} ({len(wav)} byte)")
        print(f"  sinh  : {headers.get('x-gen-s', '-')}s  RTF "
              f"{headers.get('x-rtf', '-')}")
        print(f"  nghi  : {headers.get('x-nghi-s', '-')}s "
              f"({headers.get('x-nguon-nghi', '-')})")

        kq = do_chat_luong.do_tat_ca(duong, text=chuan.da_chuan_hoa)
        do_chat_luong._in_dep(kq)

        bang.append({
            "so_ky_tu": len(chuan.da_chuan_hoa),
            "so_doan": len(doan),
            "nghi_s": headers.get("x-nghi-s"),
            "nguon_nghi": headers.get("x-nguon-nghi"),
            "gen_s": headers.get("x-gen-s"),
            "rtf": headers.get("x-rtf"),
            "ha_tran_db": headers.get("x-ha-tran-db"),
            "duong": duong,
            "do": kq,
        })

    # ── bảng tóm tắt: đây là thứ để quyết định ───────────────────────────────
    def _o(d, *khoa, mac_dinh="-"):
        for k in khoa:
            d = (d or {}).get(k) if isinstance(d, dict) else None
        return mac_dinh if d is None else d

    print(f"\n{'=' * 84}")
    print("  BANG SO DE QUYET DINH CO NOI TRAN HAY KHONG")
    print("=" * 84)
    print(f"  {'ky tu':>6} {'doan':>4} {'troi tb':>8} {'troi min':>9} "
          f"{'lang max':>9} {'CER%':>6} {'dau%':>6} {'dBTP':>7} {'LUFS':>7} "
          f"{'RTF':>7}")
    for m in bang:
        d = m["do"]
        print(f"  {m['so_ky_tu']:>6} {m['so_doan']:>4} "
              f"{_o(d, 'troi_giong', 'cosine_trung_binh'):>8} "
              f"{_o(d, 'troi_giong', 'cosine_thap_nhat'):>9} "
              f"{_o(d, 'khoang_lang', 'im_giua_dai_nhat_s'):>9} "
              f"{_o(d, 'de_hieu', 'cer'):>6} "
              f"{_o(d, 'de_hieu', 'ter_sai_dau'):>6} "
              f"{_o(d, 'tin_hieu', 'true_peak_dbtp'):>7} "
              f"{_o(d, 'tin_hieu', 'lufs'):>7} "
              f"{m.get('rtf') or '-':>7}")
    print()
    print("  Doc bang the nao: dong 1.500 ky tu la DOI CHUNG — do la cau hinh")
    print("  dang ban hom nay: mot luot sinh, khong co moi noi nao. Cac dong")
    print("  duoi chi dang tin neu chung KHONG te hon dong do mot cach he thong.")

    duong_json = os.path.join(a.thu_muc, "tom_tat.json")
    with open(duong_json, "w", encoding="utf-8") as f:
        json.dump(bang, f, ensure_ascii=False, indent=2)
    print(f"\nDa ghi: {duong_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
