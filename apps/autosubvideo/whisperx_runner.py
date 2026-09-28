"""Isolated WhisperX runner. Execute only with the dedicated sidecar Python.

## `initial_prompt` cho tieng Han — ⛔ khong phai mot tinh chinh, la mot TIEN DE

Do that 24/09 (phim v3, whisperx 3.8.6, nhanh `aligned`, 646 moc tu THAT):

    dau cau trong 646 ky tu ASR tra ve:   。0   ，0   ！0   ？0   、0   . 0

**Khong mot dau cau nao.** Hardsub cua chinh phim do cho 95 dong / 0,97 giay mot
dong. ⇒ Moi cach chia doan theo dau cau — cua WhisperX (`align()` goi NLTK
Punkt), cua `SubtitlesProcessor`, cua ta — deu **khong co gi de bam vao**.

⭐ Va khoang lang cung khong cuu duoc: do tren cung ban ghi, **640/640 khe giua
   hai ky tu lien tiep = 0,000 giay** (WhisperX gan span ky tu LIEN TIEP, im lang
   bi nuot vao do dai cua chinh ky tu do). Khong co dau cau VA khong co khoang
   lang thi khong con mot cho ngat HOP LE nao.

Nguon cach sua — `m-bain/whisperX` **issue #645** *"No punctuation for Chinese"*,
tra loi cua `leexinxu` (17/08/2024, 3 👍):

    asr_options = {"initial_prompt": "以下是中文普通话句子。"}
    whisperx.load_model(..., asr_options=asr_options)

Whisper bam theo VAN PHONG cua `initial_prompt`; mot cau mau CO dau cham cau keo
ca ban chep di theo. `asr.py:47-50` nap prompt do vao `all_tokens`, va
`asr.py:401` cho phep ghi de `default_asr_options`.

⚠️ ⛔ Prompt nay **doi ban chep**, nen no doi ca CER — phai do lai, khong duoc
   suy. Va no chi dat cho `zh`: ep mot cau mau tieng Han vao mot phim tieng Anh
   la ep van phong sai.

## `chunk_size` — B13 B5 (29/09/2026): khoi giai ma qua LON, ⛔ khong phai VAD

Ca that `asvr_47327a869a8f4597960048f09064740`: hoi 64,27..94,26 (29,99 giay,
DUNG mot khoi o `chunk_size` mac dinh 30 — `whisperx/asr.py:204,232,410`) mat
TRON — whisper chi nha lai `initial_prompt` roi tat han. Pyannote VAD (dung mot
minh, khong decode) van coi ca hoi la CO TIENG (11 khoi, 89,9% phim). ⇒
⛔ khong phai VAD bo vung — mot khoi giai ma HONG thi MAT TRON khoi do, vi
duong `batched` (`generate_segment_batched`) KHONG co nac lui theo temperature
nhu duong faster-whisper thuong. Nguon loi thuong nguon: Viral gap dung loi nay
(`faster-whisper` issue **#1270**) va va bang `chunk_length=10`
(`D:\\Viral\\resources\\app-src\\localize.py:713-722` — kho DOC, khong sua).

⭐ **Do THAT tren toan phim cua ta** (28-29/09, script mot lan, GPU thue lease),
   ba cau hinh chunk_size — 30 (mac dinh), 10 (Viral), 5 (de thay CHIEU):

       chunk_size |  hoi 65..98s        | phu_song  | lo_hong lon nhat | dau_cau | decode
       30 (goc)   |  trong (chi prompt) |  0,7692   |      32,49 s     |   37    |  29,3 s
       10 (chon)  |  12 cau THAT, co dau|  0,7651   |      11,20 s     |   38    |  13,5 s
       5          |  van co chu, TE hon |  0,7262   |       9,76 s     |   46    |  18,2 s

   `10` KHONG phai chon tuy y: `5` cho `phu_song` TE hon (0,7262 < 0,7692 goc)
   va so doan rot 78->62 — di qua 10 la LO, khong phai LOI. `phu_song` gan nhu
   KHONG doi (0,7692->0,7651) trong khi ho lon nhat giam **32,49->11,20 s** —
   bang chung song CUA A (tong) se KHONG bat duoc ban va nay, chi CUA B (ho don
   le) thay; xem `ban_ghi.do_phu_song`. Dau cau GIU nguyen (37->38, initial_prompt
   van an). Va no **NHANH HON**, khong cham hon nhu ngo truoc: 13,5s < 29,3s
   (chunk nho hon = nhieu batch hon, nhung moi batch RE hon tren GPU du dat).
"""
from __future__ import annotations

import argparse
import json


#: Cau mau CO dau cau, ep Whisper cham cau cho ngon ngu khong co dau cach.
#: ⛔ Nguon: whisperX issue #645, tra loi cua `leexinxu` — khong phai cau ta soan.
MAU_CO_DAU_CAU = {
    "zh": "以下是中文普通话句子。",
    "ja": "以下は日本語の文章です。",
}

#: B13 B5 (29/09) — khoi giai ma cua duong `batched`, giay. Mac dinh goi la
#: 30 (`whisperx/asr.py:204,232,410`) va DUNG mot khoi 30s hong TRON tren
#: `asvr_47327a869a8f4597960048f09064740` (64,27..94,26). Muon tu Viral
#: (`D:\Viral\resources\app-src\localize.py:713-722`, goc `faster-whisper`
#: issue #1270), CHON bang do that tren toan phim cua TA — xem bang so o
#: dau tep — KHONG phai bung theo Viral.
CHUNK_SIZE = 10


def _phien_ban_whisperx() -> str:
    """Phiên bản gói THẬT đang chạy. ⛔ Đừng gõ lại một con số vào mã."""
    try:
        from importlib.metadata import PackageNotFoundError, version

        return str(version("whisperx"))
    except PackageNotFoundError:
        # ⛔ Chi ca "goi khong cai" duoc nuot. Mot `Exception` tran o day tung
        #    lam mot loi nhap khac khai bao thanh "phien ban rong" — va ban ghi
        #    tai lap se noi doi ma khong ai thay.
        return ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--model", default="large-v3")
    parser.add_argument("--language", default="")
    args = parser.parse_args()

    import torch
    import whisperx
    device = "cuda" if torch.cuda.is_available() else "cpu"
    compute = "float16" if device == "cuda" else "int8"
    audio = whisperx.load_audio(args.input)
    model = whisperx.load_model(args.model, device, compute_type=compute,
                                language=args.language or None)

    # 🔴 **Nhan ngon ngu TRUOC, roi moi dat prompt.** ⛔ Doc `args.language` la
    #    sai: ASV goi runner nay voi `--language` RONG khi khach de "tu doan", va
    #    do la ca THUONG GAP. Do that 24/09: ban va doc `args.language` chay xong
    #    mot luot 25,3 giay tren card ma prompt KHONG HE duoc ap — ban chep ra y
    #    het luot truoc, tung chu, va `khoa_chung` khac nhau nen do khong phai
    #    cache. ⭐ Mot thay doi "da ap dung" ma ket qua khong doi MOT KY TU la
    #    dau hieu no chua bao gio chay, khong phai dau hieu no vo dung.
    ngon = (args.language or model.detect_language(audio) or "").lower()
    mau = MAU_CO_DAU_CAU.get(ngon[:2], "")
    if mau:
        # `TranscriptionOptions` la dataclass (faster-whisper), va whisperx giu
        # no o `pipeline.options` (`asr.py:437`). ⛔ Khong sua goi da cai — chi
        # doi tuy chon cua MOT the hien ta vua tao.
        import dataclasses
        model.options = dataclasses.replace(model.options, initial_prompt=mau)

    # 🔴 **B13 B5 (29/09): `chunk_size=CHUNK_SIZE` (10), ⛔ không còn mặc định
    #    30 của gói.** Xem docstring đầu tệp cho bằng số đo trên toàn phim của
    #    TA (không chỉ tin Viral): hố `32,49 → 11,20 s`, `phu_song` gần như
    #    không đổi, dấu câu GIỮ nguyên (37→38), và **NHANH HƠN** (13,5s <
    #    29,3s) — ⛔ đừng "tối ưu" nó về 30 lại vì ngỡ nhỏ hơn = chậm hơn.
    raw = model.transcribe(audio, batch_size=8, language=ngon or None,
                           chunk_size=CHUNK_SIZE)
    language = str(raw.get("language") or args.language or "")
    align_model, metadata = whisperx.load_align_model(language_code=language, device=device)
    aligned = whisperx.align(raw["segments"], align_model, metadata, audio, device,
                             return_char_alignments=False)
    # 🔴 **GHIM THAM SỐ — ⛔ không phải log, là một phần của BẢN GHI.**
    #
    #    Một bản chép lời **không tái lập được** thì mọi con số đo trên nó — CER,
    #    phân đoạn, và mọi điểm DỊCH mà B2 sẽ đo — cũng không tái lập được. Nên
    #    các tham số quyết định đầu ra phải đi **cùng** đầu ra, ⛔ không nằm rải
    #    rác trong mã mà người đọc phải đi tìm.
    #
    from whisperx.alignment import DEFAULT_ALIGN_MODELS_HF, DEFAULT_ALIGN_MODELS_TORCH

    # ⭐ Giá trị ở đây là **MÃ**, ⛔ không phải câu văn: chúng đi vào một bản ghi
    #    JSON để máy `grep` và để đối chiếu giữa các lượt, không hiện ra cho
    #    khách. (Và runner này chạy bằng trình thông dịch sidecar, nơi
    #    `platform_core.i18n` không nhập được.)
    #      viral_faster_whisper_1270_do_lai_toan_phim   `chunk_size` MƯỢN từ
    #        Viral (issue thượng nguồn faster-whisper#1270), CHỌN bằng đo lại
    #        trên phim của TA — ⛔ không phải mặc định gói nữa, ⛔ không phải
    #        bê nguyên số của họ mà chưa đo.
    #      tham_so | detect_language        ngôn ngữ đến từ đâu
    #      whisperx_issue_645               nguồn của `initial_prompt`
    tham_so = {
        "engine": "whisperx", "phien_ban": _phien_ban_whisperx(),
        "model_asr": args.model, "batch_size": 8,
        "chunk_size": CHUNK_SIZE,
        "chunk_size_nguon": "viral_faster_whisper_1270_do_lai_toan_phim",
        "ngon_ngu_yeu_cau": args.language or "", "ngon_ngu_dung": language,
        "ngon_ngu_do_bang": "tham_so" if args.language else "detect_language",
        "initial_prompt": mau or "",
        "initial_prompt_nguon": ("whisperx_issue_645" if mau
                                 else "khong_ap_ngon_ngu_co_dau_cach"),
        "model_can_chinh": (DEFAULT_ALIGN_MODELS_HF.get(language[:2])
                            or DEFAULT_ALIGN_MODELS_TORCH.get(language[:2]) or ""),
        "return_char_alignments": False,
    }
    payload = {"segments": aligned.get("segments") or [], "language": language,
               "engine": "whisperx", "alignment_status": "aligned",
               "fallback_reason": "", "tham_so": tham_so}
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, allow_nan=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
