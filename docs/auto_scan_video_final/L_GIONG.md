# L-GIỌNG — giai đoạn đo bằng model (`qc_do_luong`) + đo giọng đọc

> Làn `giong` của phiên `asv-final` (22–23/09/2026). Nhánh `phien/asv-final-giong`.
> Mọi con số dưới đây **đo thật** trên máy A (RTX 5060 Ti 16 GiB, đang phục vụ
> khách), tiếng thật của LTT Voice (`:8120`), video thật `Desktop\TEST VIDEO`.

## 1. Giai đoạn mới: `qc_do_luong` (làn `gpu`)

```
RENDER → QC (ffmpeg, tất định) → QC_DO_LUONG (model, card) → QC_AI (LLM/VLM)
```

| thứ | ở đâu |
|---|---|
| Vị trí trong chuỗi | `apps/auto_scan_video/pipeline.py` — `GiaiDoan(QC_DO_LUONG, "asv_gpu", "asv_gpu.qc_do_luong", sau=(QC,))`, `QC_AI.sau = (QC_DO_LUONG,)` |
| Thân giai đoạn | `apps/auto_scan_video/giai_doan_qc_do_luong.py` |
| Sổ đăng ký bộ đo | `apps/asv_gpu/do_luong/bo_do.py` (`DauVao`, `BO_DO`, `chay_tat_ca`, `phien_ban`) |
| Bộ đo giọng | `apps/asv_gpu/do_luong/giong.py` + `giong_runner.py` |
| Bộ đo chất lượng tiếng | `apps/asv_gpu/do_luong/squim.py` + `squim_runner.py` |
| Chuẩn hoá + chấm | `apps/asv_gpu/do_luong/chuan_hoa_loi.py` |
| Bề mặt liên-app | `apps/asv_gpu/__init__.py` (`BE_MAT_CONG_KHAI`) + `tools/lint_app_contract.py` |

**Cắm thêm một bộ đo = một dòng trong `BO_DO`** (kèm một hàm `_chay_*` bọc module
của nó). Bộ đo dịch của làn "dich" đã có **chỗ cắm mang tên**: `bo_do._chay_dich`
gọi `do_luong/metricx.py::do_dich(cap, ngon_ngu_nguon, ngon_ngu_dich, gpu_uuid)
-> {ma: điểm}`. Ở thời điểm viết, module đó **chưa có trong cây này** ⇒ bộ đo
`dich` trả `khong_kha_dung` (`tests/test_2021` chốt cả hai chiều: thiếu module ⇒
`khong_kha_dung`; có module ⇒ kết quả vào báo cáo, không sửa thêm dòng nào).

**Mỗi bộ đo một tiến trình con, chạy lần lượt** (`venv.chay` → `C:\LTTPlatform\qc-venv`).
Tiến trình thoát là cách chắc chắn trả VRAM: đo thật thấy card về đúng mức nền
(1.859 MiB) sau mỗi bộ đo. Đỉnh VRAM của giai đoạn = đỉnh của bộ đo nặng nhất,
không phải tổng.

⛔ Một bộ đo thiếu venv/model ⇒ `khong_kha_dung`; hỏng ⇒ `loi`. Giai đoạn vẫn
`succeeded`, và vòng sửa chỉ hành động trên kết quả `xong` — "không biết" không
được đọc thành "đạt", cũng không thành "có lỗi".

## 2. Đo cái gì: từng đoạn TTS, đã co giãn, không phải bản trộn cuối

Đầu vào mỗi bộ đo tiếng = tệp WAV của **từng đoạn** (`voice_synthesis`), qua đúng
hệ số `atempo` bản phối áp cho đoạn đó (`voice_index.json.he_so_co_gian`), đổi về
16 kHz mono. Tức: đúng câu khán giả nghe, **trừ nền**.

Vì sao không cắt từ `master.wav`/mp4: bản trộn có nhạc/tiếng động của video gốc
(ASR chép cả lời còn sót trong nền, SQUIM chấm nền là "nhiễu"); ranh giới đoạn
trên bản trộn là vị trí **kế hoạch**, cắt theo đó sẽ cắt vào đầu/cuối câu khi hai
đoạn sát nhau ⇒ lỗi xoá/chèn giả ở biên. Đơn vị sửa cũng là **đoạn**, nên đo theo
đoạn gắn thẳng vào đơn vị sửa.
⚠️ Cái **không** đo được theo cách này: lỗi sinh ra ở bước trộn (amix, loudnorm,
fade). Bốn thứ đó tất định và đã có cổng QC riêng (T4/T5 loudnorm, T7/T11 trôi).

`voice_index.json` nay ghi thêm `chu` = **câu cuối cùng máy đã đọc** (sau bậc
thang nắn). Trước đó bản kê không có, nên chấm WER sẽ chấm nhầm câu trước khi nắn.

## 3. Bộ đo giọng: ASR lượt cuối + JiWER

* **ASR**: `faster-whisper` **cùng hằng số sản phẩm** `giai_doan_chep_loi.MODEL_ASR`
  (`large-v3`), ghim commit HF `Systran/faster-whisper-large-v3@edaa852e…` (bảng
  `giong.MODEL_GHIM`; tên model không có trong bảng ⇒ `khong_kha_dung`, không tải
  bản trôi nổi). Tham số: `beam_size=5`, `vad_filter=False` (đoạn đã cắt sẵn; VAD
  có thể cắt mất âm đầu yếu ⇒ sinh lỗi **xoá giả** đúng loại lỗi đang đo),
  `condition_on_previous_text=False`, ép `language` = ngôn ngữ đích.
* **Chuẩn hoá — một hàm cho CẢ HAI vế** (`chuan_hoa_loi.chuan_hoa`):
  * `vi`: `apps.ltt_voice.text_pipeline.chuan_hoa(doc_so_tran=True, tu_dien_rieng=…)`
    — **chính** bề mặt LTT Voice mà ASV gọi trước khi đưa chữ cho máy đọc
    (`giong_noi.chuan_hoa_van_ban`), bật đọc số tràn để `23` ≡ "hai mươi ba" ở cả
    hai vế; rồi lõi của `BasicTextNormalizer` (Whisper): NFKC, chữ thường, bỏ loại
    Unicode M/S/P. Khác Whisper đúng một điểm, có chủ ý: **không** xoá nội dung
    trong ngoặc — kịch bản có "(Hà Nội)" và máy **đọc** nó. Token sau bước này là
    **âm tiết** ⇒ WER tiếng Việt ở đây là WER trên âm tiết. Giữ dấu thanh.
  * `en`: `EnglishTextNormalizer` của Whisper (bảng chính tả Anh-Mỹ để rỗng).
* **Chấm**: `jiwer` 4.0.0 — WER (+ CER cho `vi`), kèm số thay/xoá/chèn.

## 4. Hiệu chỉnh ngưỡng — số thật, không phải số nghĩ ra

**Kho hiệu chỉnh** (`tools/do_giong_hieu_chinh.py thu`, chạy nâng quyền qua
`setup\do_on_dinh.ps1 -Do do-giong`; kho nằm ở `C:\lttinf\asvf_giong`, **không
commit**): 4 video Douyin tiếng Trung → ASR sản phẩm → **dịch bằng model nhà thật**
(`long_tieng.loi_nhac` + `ai.goi`, khoá pool thật) → **đọc bằng LTT Voice thật**
(`giong_noi.doc_mot_doan`, 6 giọng mẫu vi + một giọng nhân bản en mức engine).

    50 đoạn tiếng thật:  36 vi (v1,v2,v3,v4 · 6 giọng) + 14 en (v2,v3)

| phép đo | n | min | p50 | p90 | p95 | max |
|---|---|---|---|---|---|---|
| **vi WER** (âm tiết) | 36 | 0,000 | 0,102 | 0,309 | 0,362 | **0,407** |
| **vi CER** | 36 | 0,000 | 0,043 | 0,121 | 0,152 | **0,213** |
| **en WER** | 14 | 0,000 | 0,023 | 0,058 | 0,067 | **0,074** |

**Đối chứng** (cùng đoạn tiếng, biến đổi bằng ffmpeg rồi đo lại thật):

| đối chứng | vi WER p50 (min) | vi CER p50 (min) | en WER p50 (min) |
|---|---|---|---|
| lệch cặp (tiếng đoạn i vs kịch bản đoạn i+1) | 0,989 (0,914) | 0,774 (0,676) | 0,957 (0,893) |
| **nuốt chữ thật** — cắt 1/3 cuối | 0,409 (**0,308**) | 0,369 (**0,248**) | 0,341 (**0,273**) |
| nhiễu trắng SNR ~10 dB | 0,127 (0,000) | 0,071 (0,000) | 0,023 (0,000) |
| chèn khoảng lặng 0,4 s giữa câu | 0,122 (0,000) | 0,053 (0,000) | 0,023 (0,000) |

🔴 **WER một mình KHÔNG tách được hai đám ở tiếng Việt**: đọc đúng có đoạn lên
0,407, còn nuốt 1/3 chữ có đoạn chỉ 0,308 — hai đám chồng nhau. **CER thì tách
sạch**: đọc đúng cao nhất 0,213, nuốt chữ thấp nhất 0,248. (Lý do: WER âm tiết
phạt rất nặng một khác biệt chính tả/ghép âm nhỏ; CER thì không.)

⇒ **Ngưỡng chốt** (`sua_chua.NGUONG_DOC_SAI`) — phải vượt **MỌI** chỉ số:

```
vi:  WER > 0,30  VÀ  CER > 0,23        en:  WER > 0,15
```

Kiểm lại trên chính dữ liệu đó:

| tập | vi | en |
|---|---|---|
| đọc ĐÚNG (báo động giả) | **0/36** | **0/14** |
| nuốt 1/3 chữ (phải bắt) | **35/35** | **14/14** |
| lệch cặp (phải bắt) | 100% (min WER 0,914 / CER 0,676) | 100% |
| nhiễu SNR 10 dB | 2/35 bị cờ | 0/14 |
| khoảng lặng 0,4 s | 0/35 | 0/14 |

⚠️ **Giới hạn phải nói ra**: (a) `en` mới có 14 đoạn, và giọng en là **nhân bản
mức engine** — kho giọng mẫu chưa có làn `en` (F-03), nên số en phải đo lại khi
có giọng `en` thật; (b) không đoạn nào trong kho là **lỗi đọc tự nhiên của TTS**
(kho đọc đúng hết) — "nuốt chữ" là đối chứng dựng bằng cách cắt tiếng, tức nó mô
phỏng hậu quả chứ không phải nguyên nhân; (c) ngôn ngữ **không có trong bảng ⇒
không sinh việc sửa** (kết quả vẫn ghi vào báo cáo).

## 5. Bộ đo chất lượng tiếng: torchaudio SQUIM_OBJECTIVE

* **License đã xác minh trên bản CÀI THẬT** (`qc-venv`, `torchaudio 2.8.0+cu128`,
  `torchaudio/pipelines/_squim_pipeline.py`): *"The weights are under Creative
  Commons Attribution 4.0 International License"* (dẫn `microsoft/DNS-Challenge`),
  code BSD-2-Clause. ⛔ `SQUIM_SUBJECTIVE` (cùng tệp) là **CC BY-NC 4.0 — không dùng**.
* **Weights ghim**: `https://download.pytorch.org/torchaudio/models/squim_objective_dns2020.pth`
  · sha256 `2c54586fea83fb5eb5394d710038ee89f55cab7011a5bf730bebed4c8777e828`
  · 29.584.237 byte. Runner tự tải vào `TORCH_HOME/hub/torchaudio/models/` và
  **kiểm sha256 trước khi nạp** (`download_asset` không kiểm gì khi tệp đã có).
* **Ghi công (CC BY 4.0)**: *"Speech quality estimates use torchaudio
  SQUIM_OBJECTIVE (`squim_objective_dns2020`), weights © Microsoft DNS-Challenge,
  licensed CC BY 4.0."* — phải xuất hiện ở tài liệu vận hành/phát hành khi công bố.
* Mỗi đoạn: STOI/PESQ/SI-SDR **cả đoạn** + **thấp nhất trên cửa sổ trượt 2 s /
  bước 1 s** (một tiếng click 200 ms bị pha loãng trong trung bình của câu 8 s).

Số thật trên 50 đoạn sạch: PESQ min **2,719** · p50 3,28 (vi) / 3,41 (en);
SI-SDR min **15,31 dB**; STOI min 0,959. Nhiễu SNR 10 dB: PESQ p50 **1,19**.

⇒ **Ngưỡng CẢNH BÁO** (`giai_doan_qc_do_luong.NGUONG_CANH_BAO_TIENG`):
`PESQ < 2,0` hoặc `SI-SDR < 10 dB` ⇒ ghi `canh_bao_tieng` trong `tom_tat`.
⛔ **Không sinh việc sửa**: một đoạn "nghe hơi đơn" vẫn giao được, còn đọc lại thì
tốn tiền. `sua_chua` không đọc khoá này (`test_2022` chốt).

⚠️ **Đã đo và KHÔNG đúng**: SQUIM **không thấy** khoảng lặng 0,4 s chèn giữa câu
(SI-SDR cửa sổ thấp nhất 15,96 so với 16,58 của bản sạch). Đứt quãng kiểu đó phải
bắt bằng phép đo khác — đừng đọc bằng chứng này thành "đã có cổng gác cho đứt quãng".

## 6. Xoá Dice, nối vòng sửa vào phép đo thật

* **XOÁ**: `sua_chua.khop_van_ban` (công thức Dice tập từ), `NGUONG_KHOP_DOC = 0,80`
  ("CHƯA ĐO"), `qc_ai.so_khop_doc` (bộ ghép đầu vào của nó) và 5 bài test của
  chúng. `M-01` trong `LOI_TONG.md` đóng.
* **NỐI**: `jobs._sua_chua_neu_can` nay truyền `qc_giong=_qc_giong(theo_ten)` —
  đọc `qc_giong_khong_dat` từ `stage.outputs` của `qc_do_luong` (không mở kho).
  `tests/test_482` chốt tập nguồn ĐÃ NỐI = `{cac_nan, qc_giong, qc_ngu_nghia}`.
* **Hành động sửa**: `DOC_SAI → voice_synthesis`, **đúng đoạn đó** (`gon_theo_don_vi`
  + `su_dung.mo_lai_don_vi`), không phải cả video.

🔴 **Và một lỗ đã bịt**: giai đoạn giọng dùng lại tệp cũ theo **vân tay đoạn**
(chữ + giọng + preset). Vân tay không đổi ⇒ "đọc lại" trả về **đúng bản vừa bị
báo sai**, tức vòng sửa chạy mà không sửa gì. Nay `_van_tay(..., lan=n)` muối vân
tay bằng **số vòng sửa đã đẩy đoạn đó về `voice_synthesis`** (đếm từ SỔ CÁI:
`sua_chua.lan_doc_lai`), nên đoạn bị sửa lấy một **lượt đọc mới**; `lan=0` giữ
nguyên vân tay cũ nên mọi đoạn lành vẫn dùng lại cache y như trước.
`tests/test_2023` chạy thật trên hàng đợi: 1 đoạn bị báo sai ⇒ máy đọc được gọi
đúng `N+1` lần (không phải `2N`), sổ cái có 2 `ma_dispatch` cho riêng đoạn đó, lần
đo thứ hai đạt, run về `done`.

⚠️ Cùng cơ chế này cũng sửa luôn ca `KHONG_VUA` (nắn không vừa khe) — trước đây nó
cũng rơi vào đúng cái bẫy cache trên.

🔴 **Lỗi thứ hai tìm ra khi chạy thật**: `giai_doan_ban_dung` (COMPOSE) gọi
`kiem_toan_ven` (GHI trạng thái toàn vẹn bằng `flush`) rồi gọi `ctx.progress`
(phiên THỨ HAI) khi chưa commit ⇒ trên SQLite là tự khoá chính mình
(`database is locked`). Chỉ lộ ra ở **lượt chạy lại sau vòng sửa** (lượt đầu không
có artifact nào bị vô hiệu). Sửa: `db.commit()` ngay sau `_khoa_con_dung`.

## 7. Benchmark (máy A đang phục vụ khách, card dùng chung)

Một bản lồng tiếng THẬT 1–3 phút (v3, nguồn 106,8 s, 6 đoạn, ~95 s tiếng):

| bộ đo | tường | CPU | RAM đỉnh | VRAM đỉnh (card) | sau khi xong |
|---|---|---|---|---|---|
| `giong` (whisper large-v3 fp16) | 39,1 s (nạp model 9,5 s) | 69 s | 3.531 MB | **+4.265 MiB** | card về mức nền |
| `chat_luong_tieng` (SQUIM) | 6,0 s (nạp 2,5 s) | 14 s | 1.164 MB | **+2.256 MiB** | card về mức nền |
| **cả giai đoạn** | **≈45 s** | ≈83 s | 3,5 GB | **≈4,3 GiB** | 1.859 MiB = mức nền |

Trên cả kho 36 đoạn vi (~9,5 phút tiếng): `giong` 164,6 s, `squim` 15,0 s.

`gpu_vram_mb["asv_gpu.qc_do_luong"] = 5200` = đỉnh đo được + ~20%.
`tai_nguyen="tach_nguon_cuc_bo"` (dùng chung suất với `audio_prepare`/`transcribe`):
ba việc nạp model lên một card dùng chung không được chạy chồng.

⚠️ **Một lần đo đã đổi mã**: bản đầu đưa **cả** khối cửa sổ trượt vào một lượt
SQUIM ⇒ torch giữ **11,2 GiB** trên card đang phục vụ khách. Nay chia lô
`LO_CUA_SO = 4` + `empty_cache()` mỗi đoạn ⇒ đỉnh 2,2 GiB, cùng kết quả.

## 8. Tệp/công cụ để chạy lại

```
setup\cai_qc_models.ps1                     # qc-venv (+ faster-whisper ghim)
tools\do_giong_hieu_chinh.py thu            # dựng kho tiếng thật (nâng quyền)
tools\do_giong_hieu_chinh.py do             # đo + đối chứng (python của qc-venv)
    -> C:\lttinf\asvf_giong\ket_qua_do.json
python -m pytest tests/test_2020..2024 -q   # 2024 là bài NẶNG (LTT_TEST_NANG=1)
```

## 9. Còn lại

* Bộ đo `dich` chờ `do_luong/metricx.py` của làn "dich" (chỗ cắm đã có tên).
* Ngưỡng `en` đo lại khi kho giọng mẫu có làn `en` thật (F-03).
* Chưa có phép đo nào bắt **đứt quãng** trong một đoạn (mục 5) — nếu cần, đo bằng
  năng lượng/VAD chứ không phải SQUIM.
* `qc_do_luong` chạy **mọi lần chạy** và tốn ~45 s GPU cho một video 2 phút; nếu
  muốn tắt theo cấp vận hành thì thêm cờ như `LTT_ASV_QC_AI` — chủ dự án quyết.
