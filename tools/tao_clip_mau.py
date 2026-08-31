r"""
tao_clip_mau.py — sinh CLIP MẪU để mở khoá đường ghi danh giọng.

    $env:LTT_VOICE_SIDECAR_TOKEN = '<token>'
    C:\LTTPlatform\vieneu-venv\Scripts\python.exe tools\tao_clip_mau.py

⭐ VÌ SAO CẦN, VÀ NÓ CHỨNG MINH ĐƯỢC GÌ

   Đường ghi danh giọng riêng là mắt xích yếu nhất của LTT VOICE: bốn bảng
   `voice_*` đều **0 dòng**, tức nó chưa từng chạy hết một lần. Lý do rất tầm
   thường — không ai có sẵn một clip hợp lệ để thử.

   Dùng chính model sinh clip mẫu gỡ đúng nút đó. Nó kiểm được **toàn bộ đường
   ống**: kiểm định dạng · lưu nguồn · bút toán consent · job ghi danh · trích
   biểu diễn giọng · sinh tiếng bằng giọng đó · cách ly giữa hai khách.

⛔ VÀ ĐÂY LÀ THỨ NÓ **KHÔNG** CHỨNG MINH, nói trước để không ai đọc nhầm:

   Clip mẫu ở đây là tiếng **do máy sinh**, không phải giọng người thu bằng
   micro. Nhân bản từ một bản tổng hợp không cùng bài toán với nhân bản từ một
   bản thu thật: bản tổng hợp đã đi qua bộ mã hoá của chính model, nên nó *dễ*
   hơn đầu vào thật. ⇒ Chỉ số **giữ giọng** đo trên clip này nói về ĐƯỜNG ỐNG
   chạy đúng, KHÔNG nói về chất lượng nhân bản với khách thật.

   Muốn con số kia thì phải có một bản thu người thật, và đó là việc của V10.

⚠️ Clip mẫu KHÔNG phải giọng của một người có thật, nên nó không chạm quyền
   nhân thân của ai. Chỉ dùng cho tài khoản thử đuôi `.local`.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

#: Bốn câu, mỗi câu ~9–11 giây ở 19,8 ký tự/giây (số đo 31/08). Nội dung cố ý
#: giàu ngữ âm: đủ sáu thanh, có phụ âm cuối, có số, không lặp cụm — một clip
#: nghèo ngữ âm cho ra biểu diễn giọng nghèo, và lỗi đó không hiện ra ở đâu
#: ngoài chất lượng bản nhân bản.
CAU_MAU = [
    ("nam_tram", "Xin chào, tôi là giọng đọc mẫu của LTT Studios. Hôm nay là "
                 "ngày ba mươi mốt tháng tám, và tôi đang thử ghi âm một đoạn "
                 "ngắn để hệ thống học cách nói của tôi."),
    ("nam_ke", "Ngày xưa có một người thợ mộc sống ở cuối làng, mỗi sáng ông "
               "dậy từ bốn giờ, pha một ấm trà đặc, rồi ngồi lặng lẽ bên bậu "
               "cửa nhìn ra vườn."),
    ("nam_tin", "Theo số liệu công bố sáng nay, giá vàng trong nước tăng thêm "
                "hai trăm nghìn đồng mỗi lượng, trong khi tỷ giá đô la Mỹ gần "
                "như đứng yên suốt cả tuần."),
]


def _goi(duong: str, body: dict, token: str, timeout: float = 600.0):
    cong = (os.environ.get("LTT_VOICE_SIDECAR_PORT") or "8120").strip()
    req = urllib.request.Request(
        f"http://127.0.0.1:{cong}{duong}",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read(), {k.lower(): v for k, v in r.headers.items()}
    except urllib.error.HTTPError as e:
        raise SystemExit(f"cong tra {e.code}: "
                         f"{e.read()[:300].decode('utf-8', 'replace')}") from e


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--thu-muc", default="tmp/clipmau")
    ap.add_argument("--bo-qua-do", action="store_true",
                    help="Chi sinh, khong do (nhanh hon, it bang chung hon).")
    a = ap.parse_args(argv)

    token = (os.environ.get("LTT_VOICE_SIDECAR_TOKEN") or "").strip()
    if not token:
        print("Thieu LTT_VOICE_SIDECAR_TOKEN.", file=sys.stderr)
        return 2
    os.makedirs(a.thu_muc, exist_ok=True)

    # Ràng buộc thật của cửa nhận clip — ĐỌC TỪ MÃ, không gõ lại.
    from apps.ltt_voice import audio_input

    ra = []
    for ten, text in CAU_MAU:
        wav, headers = _goi("/v1/speech", {"text": text}, token)
        duong = os.path.join(a.thu_muc, f"{ten}.wav")
        with open(duong, "wb") as f:
            f.write(wav)

        # Cho nó đi qua ĐÚNG cửa mà khách đi qua, ngay tại đây. Một clip chỉ
        # "trông có vẻ hợp lệ" thì lỗi sẽ nổ ở giữa luồng ghi danh, xa chỗ này.
        try:
            mo_ta = audio_input.kiem(wav, "audio/wav")
            hop_le, ly_do = True, ""
        except audio_input.LoiAudio as e:
            mo_ta, hop_le, ly_do = {}, False, str(e)

        muc = {
            "ten": ten, "duong": duong, "so_byte": len(wav),
            "so_ky_tu": len(text),
            "giay": round(float(mo_ta.get("giay") or 0.0), 2),
            "hop_le_de_ghi_danh": hop_le,
            "ly_do": ly_do,
            "canh_bao": [str(c) for c in (mo_ta.get("canh_bao") or ())],
        }

        if not a.bo_qua_do:
            from voice_sidecar import do_chat_luong
            kq = do_chat_luong.do_tat_ca(duong, text=text)
            muc["phan_quyet"] = kq["phan_quyet"]["ket_luan"]
            muc["dat_may_muc"] = (f"{kq['phan_quyet']['so_dat']}/"
                                  f"{kq['phan_quyet']['so_muc']}")
            muc["cer"] = kq["de_hieu"].get("cer")
            muc["true_peak_dbtp"] = kq["tin_hieu"].get("true_peak_dbtp")
            muc["lufs"] = kq["tin_hieu"].get("lufs")
            muc["watermark"] = kq["watermark"].get("doc_lai")

        ra.append(muc)
        print(f"  {ten:<10} {muc['giay']:>6.2f}s  "
              f"{'HOP LE' if hop_le else 'TU CHOI: ' + ly_do}"
              + (f"  {muc.get('phan_quyet', '')} {muc.get('dat_may_muc', '')}"
                 if not a.bo_qua_do else ""))

    duong_json = os.path.join(a.thu_muc, "clip_mau.json")
    with open(duong_json, "w", encoding="utf-8") as f:
        json.dump(ra, f, ensure_ascii=False, indent=2)

    so_dung = sum(1 for m in ra if m["hop_le_de_ghi_danh"])
    print(f"\n{so_dung}/{len(ra)} clip du dieu kien ghi danh "
          f"({audio_input.GIAY_TOI_THIEU:.0f}-{audio_input.GIAY_TOI_DA:.0f}s).")
    print(f"Da ghi: {duong_json}")
    return 0 if so_dung else 1


if __name__ == "__main__":
    raise SystemExit(main())
