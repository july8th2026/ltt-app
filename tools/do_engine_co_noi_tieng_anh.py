r"""
do_engine_co_noi_tieng_anh.py — VieNeu có đọc được tiếng Anh không.

    powershell -ExecutionPolicy Bypass -File .\setup\do_engine_co_noi_tieng_anh.ps1

## KẾT QUẢ: CÓ. Và tệp này tồn tại vì tôi đã kết luận ngược lại, hai lần.

Đo 01/09/2026, engine thật, ASR nghe lại ở ba chế độ (ép EN · ép VI · tự dò):

    VAO : The quick brown fox jumps over the lazy dog.
    ASR : The quick brown fox jumps over the lazy dog.          [en 0,996]
    VAO : Our team delivered the project ahead of schedule this quarter.
    ASR : Our team delivered the project ahead of schedule this quarter.  [en 0,87]

Đúng từng chữ. Model card cũng nói thẳng: `language: ["vi", "en"]`, tag
`code-switching`, train **from scratch trên ~10.000 giờ tiếng Anh–tiếng Việt**
(`pnnbao-ump/VieNeu-TTS-10k-ENVI`).

## 🔴 Vì sao tôi kết luận sai — và vì sao nó đáng ghi lại

Tôi đọc trong `sea_g2p/g2p.py`:

    SUPPORTED_LANGS = ("vi", "th", "id")
    if lang not in SUPPORTED_LANGS: raise ValueError(...)

rồi kết luận **"engine không nói được tiếng Anh"**. Tiền đề ngầm: `lang` là
"ngôn ngữ engine phát ra được". Nó không phải. README của chính `sea-g2p` nói:

    "Vietnamese, Thai and Indonesian, all with English code-switching."

`lang` chọn **ngôn ngữ nền Đông Nam Á**; các chuỗi Latin đi qua **một engine
tiếng Anh dùng chung** bên trong cả ba. Danh sách ấy chưa bao giờ là danh sách
ngôn ngữ đầu ra — nó là danh sách các front-end SEA.

⛔ Đây là lần **thứ hai trong cùng một phiên** tôi đọc mã rồi tuyên bố một giới
   hạn sản phẩm. Lần một: `voice_profiles.yaml` ghi `lang: en` trên những cái
   tên tiếng Việt ⇒ tôi viết rằng nhãn không đáng tin (sai; cột `engine` bên
   cạnh mang câu trả lời, ASR xác nhận 24/24). Lần hai là đây.

⭐ Cùng một hình dạng ở cả hai lần: **một hằng số đọc rất thuyết phục, cộng một
   tiền đề ngầm chưa ai kiểm.** Bốn dòng mã thật, một câu kết luận sai. Và cả
   hai lần, phép đo bác bỏ nó **trong chưa tới năm phút**.

⇒ Luật rút ra, và nó cụ thể hơn "đừng đoán": **một khẳng định về thứ hệ thống
  LÀM ĐƯỢC hay KHÔNG LÀM ĐƯỢC thì phải đến từ việc bắt nó làm thử.** Đọc mã
  cho biết nó được viết thế nào, không cho biết nó chạy ra sao.

## Ba kết quả mà tệp này phân biệt được

  · ASR tiếng Anh đọc đúng câu ⇒ engine nói được tiếng Anh. **(đây là thực tế)**
  · ASR tiếng Việt ra một chuỗi chữ Việt na ná ⇒ engine **đánh vần chữ Anh theo
    lối Việt**. Dùng được cho từ mượn, không bán được như "giọng tiếng Anh".
  · Cả hai ra rác ⇒ không dùng được kiểu nào.

⭐ Hai kết quả sau nghe **giống nhau** với người không biết trước, nhưng dẫn tới
   hai quyết định sản phẩm ngược nhau. Đó là lý do phải ép ASR ở cả hai ngôn ngữ
   thay vì chỉ nghe thử.

⚠️ Câu tiếng Việt đối chiếu trong `CAU_VI` cố ý viết **không dấu**, và kết quả
   ra sai thanh điệu ("dây là một cạo tiền viết") — đó là hành vi ĐÚNG, không
   phải lỗi: tiếng Việt không dấu là văn bản nhập nhằng. Đừng đọc dòng ấy thành
   một khuyết tật.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

CAU_EN = [
    "The quick brown fox jumps over the lazy dog.",
    "Please confirm your appointment for tomorrow morning at nine.",
    "Our team delivered the project ahead of schedule this quarter.",
]
CAU_VI = "Xin chao, day la mot cau tieng Viet de doi chieu."


def _nghe(duong: str, lang: str) -> dict:
    """ASR một tệp, ÉP ngôn ngữ `lang`. Chạy ở venv NỀN TẢNG."""
    py = os.environ.get("LTT_PLATFORM_PYTHON",
                        r"C:\LTTPlatform\venv\Scripts\python.exe")
    if not os.path.isfile(py):
        return {"loi": f"khong thay {py}"}
    ma = (
        "import sys,json\n"
        "from faster_whisper import WhisperModel\n"
        "m=WhisperModel(sys.argv[3], device='cpu', compute_type='int8')\n"
        "lg=None if sys.argv[2]=='auto' else sys.argv[2]\n"
        "seg,info=m.transcribe(sys.argv[1], language=lg, beam_size=5,\n"
        "                      condition_on_previous_text=False)\n"
        "print(json.dumps({'lang':info.language,\n"
        "                  'p':info.language_probability,\n"
        "                  'text':' '.join(s.text for s in seg)}))\n"
    )
    try:
        r = subprocess.run([py, "-c", ma, duong, lang,
                            os.environ.get("LTT_ASR_MODEL", "small")],
                           capture_output=True, text=True, encoding="utf-8",
                           timeout=600)
    except (subprocess.TimeoutExpired, OSError) as e:
        return {"loi": f"{type(e).__name__}: {e}"}
    if r.returncode != 0:
        return {"loi": (r.stderr or "")[-200:]}
    try:
        d = json.loads(r.stdout.strip().splitlines()[-1])
        return {"ngon_ngu": d["lang"], "do_tin": round(float(d["p"]), 3),
                "text": (d["text"] or "").strip()}
    except (ValueError, IndexError, KeyError) as e:
        return {"loi": f"khong doc duoc ket qua ASR: {e}"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ra", default="tmp/engine_tieng_anh.json")
    a = ap.parse_args(argv)

    from apps.ltt_voice import sidecar_client

    # ── 1. G2P có nhận `lang="en"` không ────────────────────────────────────
    try:
        from sea_g2p.g2p import SUPPORTED_LANGS
        ho_tro = list(SUPPORTED_LANGS)
    except Exception as e:                                # noqa: BLE001
        ho_tro = [f"khong doc duoc: {e}"]
    print(f"sea_g2p ho tro: {ho_tro}")
    print(f"co 'en' khong : {'CO' if 'en' in ho_tro else 'KHONG'}\n")

    ket = {"sea_g2p_ho_tro": ho_tro, "cau": []}
    for i, c in enumerate(CAU_EN + [CAU_VI], 1):
        try:
            raw, dau = sidecar_client.noi(c)
        except Exception as e:                            # noqa: BLE001
            print(f"  [hong] cau {i}: {type(e).__name__}: {e}")
            continue
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        tmp.write(raw)
        tmp.close()
        try:
            m = {"vao": c,
                 "asr_ep_en": _nghe(tmp.name, "en"),
                 "asr_ep_vi": _nghe(tmp.name, "vi"),
                 "asr_tu_do": _nghe(tmp.name, "auto")}
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass
        ket["cau"].append(m)
        print(f"[{i}] VAO      : {c}")
        print(f"    ep EN    : {m['asr_ep_en'].get('text')}")
        print(f"    ep VI    : {m['asr_ep_vi'].get('text')}")
        td = m["asr_tu_do"]
        print(f"    tu do    : [{td.get('ngon_ngu')} {td.get('do_tin')}] "
              f"{td.get('text')}\n")

    os.makedirs(os.path.dirname(a.ra) or ".", exist_ok=True)
    with open(a.ra, "w", encoding="utf-8", newline="\n") as f:
        json.dump(ket, f, ensure_ascii=False, indent=2)
    print(f"Da ghi: {a.ra}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
