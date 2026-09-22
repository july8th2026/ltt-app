# L-OCR — Nguon loi thoai: phu de nhung -> hardsub (OCR) -> ASR

> Lan `ocr` cua phien `asv-final`. Nhanh `phien/asv-final-ocr`.
> Do tren 4 clip Douyin that cua chu du an (`Desktop\TEST VIDEO`), 22-23/09/2026.
> Moi con so duoi day deu do tren may A (RTX 5060 Ti, 20 loi), lenh nang qua
> `chay_nang.py`. Du lieu tho: scratch cua phien (khong commit — 1,4 MB JSON).

## 0. Ket luan (doc cai nay truoc)

| Cau hoi | Tra loi | Bang chung |
|---|---|---|
| Engine OCR | **RapidOCR 3.9.2 + PP-OCRv6 small (ONNX)** — code va weights Apache-2.0 | §1 |
| PaddleOCR 3.x | **Khong dung** — chu dung hon (CER 0,000) nhung **cham 20 lan** (1.293 ms/khung vs 66 ms) va keo ca framework Paddle vao venv | §1.3 |
| EasyOCR | Khong dung (weights chua xac minh — audit da chot) | OPEN_SOURCE_METRIC_AUDIT |
| Chu: OCR hay ASR? | **OCR thang ro ret**: CER **0,30%** vs ASR large-v3 **1,81%** (6 lan), dong dung 32/33 vs 28/33 | §4 |
| Ket hop OCR + ASR? | **Khong.** OCR la nguon CHU va nguon THOI GIAN; ASR khong chay tren nhanh OCR | §4 |
| Lay mau | **4 khung/giay** doc dai phu de; 40 khung full-frame de TIM dai | §3 |
| Chay o dau | **CPU**, venv do luong, 4 luong: 66 ms/khung dai. GPU nhanh 1,6 lan nhung phai them CUDA 13 + gianh card voi Voice/VLM ⇒ khong dung | §5 |

## 1. Engine va giay phep

### 1.1 Da xac minh tu nguon goc

- Ma: `RapidAI/RapidOCR` — Apache-2.0 (`LICENSE`).
- Weights: `python/MODEL_LICENSES.md` §4 cua chinh repo: cac artifact o §6 (trong do
  co `PP-OCRv6_det_small.onnx`, `PP-OCRv6_rec_small.onnx`) phat hanh theo **Apache-2.0**,
  ban quyen upstream thuoc Baidu/PaddleOCR, **khong** gioi han phi thuong mai
  ("These permissions are not restricted to non-commercial use").
- §7 doi khi phan phoi lai: kem ban Apache-2.0, giu ghi cong, ghi ro da chuyen doi.
  ⇒ Ta **khong** phan phoi lai model (tai tu ModelScope luc cai), nen chi con nghia vu
  ghi cong — tep nay + `ocr_khung.py` la cho ghi.

### 1.2 Model GHIM (SHA-256 doi chieu moi lan chay)

    $HF_HOME\rapidocr\3.9.2\PP-OCRv6_det_small.onnx  090f04ab…ff94f   9,9 MB
    $HF_HOME\rapidocr\3.9.2\PP-OCRv6_rec_small.onnx  6f327246…14884  21,2 MB

`HF_HOME` mac dinh `C:\LTTPlatform\hf-cache` (giong bo do khac). Thieu tep ⇒ runner
tai DUNG URL ghim (`modelscope…/v3.9.2/onnx/PP-OCRv6/…`) roi kiem SHA-256; sai ⇒
`KHONG_KHA_DUNG`, ⛔ khong chay tiep bang ban khac. `cls` (xoay chu) **tat**: phu de
nam ngang, bat chi ton thoi gian.

### 1.3 PaddleOCR 3.x (ung vien 2) — da cai, da do, KHONG chon

`paddleocr 3.7.0 + paddlepaddle 3.3.1` (CPU, Windows, py3.13), tren DUNG dai va DUNG
khung cua RapidOCR (v2, 0-60 s, 10 fps):

- `enable_mkldnn=True` (mac dinh) ⇒ **sap**:
  `NotImplementedError: (Unimplemented) ConvertPirAttribute2RuntimeAttribute not
  support [pir::ArrayAttribute<pir::DoubleAttribute>]` (`onednn_instruction.cc:118`).
  Phai tat oneDNN moi chay duoc.
- `enable_mkldnn=False` ⇒ chay, va **doc chuan hon**: CER 0,000, 33/33 dong dung
  (PP-OCRv6 **medium** la mac dinh cua paddleocr 3.7).
- Nhung **1.293 ms/khung** so voi 66 ms cua RapidOCR (PP-OCRv6 small, onnxruntime,
  cung 4 luong) — **cham 20 lan**, cong ~1,5 GB framework vao venv do luong.

⇒ Mot ky tu dung hon tren 60 s khong mua duoc cai gia do. Neu sau nay can chinh xac
hon: **doi model trong RapidOCR** (PP-OCRv6 medium qua onnxruntime) re hon nhieu so
voi doi engine — nhung phai xac minh giay phep cua artifact medium truoc (§4.1).

## 2. Bon clip: hardsub co that o CA BON

⚠️ Brief noi *"3/4 clip co hardsub, v1 chi co logo goc"* — **sai**. `廉价的牛肠…`
cung co hardsub trang o day khung (`一份售价3万韩元`, `直至蔬菜软烂`…). Bo do phat
hien dung ca bon.

| Clip | Khung | Dai tim duoc (y0-y1) | Tam dai (theo H) | Cao chu | % khung co phu de |
|---|---|---|---|---|---|
| v1 `廉价的牛肠…` | 1024x576 | 494-576 | 0,953 | 50 px | 92% |
| v2 `暴雨天野外露营…` | 864x576 | 461-576 | 0,938 | 53 px | 95% |
| v3 `深度解析丨跳伞…` | 836x576 | 413-496 | 0,779 | 31 px | 75% |
| v4 `真人气枪游戏…` | 1024x576 | 466-576 | 0,929 | 52 px | 66% |

Khong clip nao co **luong phu de nhung** (ffprobe: chi video + audio) ⇒ nhanh
`embedded` duoc kiem bang mp4 tu mux `mov_text` trong `test_2041`.

Thu KHONG duoc doc nham, va da khong bi doc nham: logo kenh goc tren (`中国 一味`),
watermark giua hinh (`千奇百战`), HUD game (`剩余97`, la ban `195 210 西南`), dong bao
ha guc (`你使用UMP45…击倒了…`), nut `自动`/`关门`, ma tran dau o day khung.

### 2.1 Ba bay da tra gia (ghi lai vi chung KHONG hien ra qua test tong hop)

1. **Cat dai cao SO LE** (v2: 115 px): `ffmpeg … crop=…:115 -f rawvideo` tren khung
   yuv420p bi lam tron, con trinh doc lay `w*h*3` byte ⇒ **truot mot hang moi khung**:
   chu "troi" len dan va lap lai o mep tren. CER 0,3% -> 2,1% -> (khi "sua" theo hien
   tuong) 20-27%. Runner nay ep kich thuoc cat **chan**. Bai hoc: mot artifact giai ma
   trong nhu mot hien tuong cua model.
2. **Nguong cao chu tuyet doi** khong tach duoc HUD game khoi phu de: `自动` (19 px) va
   dong bao ha guc (21 px) nam TRONG dai phu de v3 (34 px) va bi ghep vao loi thoai.
   Nay chon theo **hang chinh** cua tung khung (hop lon nhat, can giua), giu hop >= 80%
   cao hang chinh.
3. **Lop phu chen ngang** lam vo mot dong thanh ba (`把楼给守住` / `把楼给守住你使用…` /
   `你使用…`). Nay: hai nhom lien ke ma chu nhom nay CHUA chu nhom kia ⇒ mot dong, giu
   chu NGAN (lop phu chi them chu). v3: 134 -> 99 dong, v4: 186 -> 120 dong.

## 3. Lay mau: 40 khung de TIM dai, 4 khung/giay de DOC

Do tren ca 4 clip, lay dong thoi gian 10 fps lam moc so sanh:

| fps doc | v1 | v2 | v3 | v4 | Lech moc tb / p95 | CER v2 (60 s doi chieu tay) |
|---|---|---|---|---|---|---|
| 10 | 105 dong | 107 | 99 | 120 | — (moc goc) | **0,003** |
| 5 | -1 dong | 0 | -4 | -1 | 0,04-0,13 s / 0,1-0,6 s | 0,003 |
| 4 | -1 | 0 | -4 | -1 | 0,04-0,14 s / 0,1-0,65 s | 0,003 |
| 3 | -1 | 0 | -11 | -1 | 0,10-0,19 s / 0,2-0,83 s | 0,003 |
| 2 | -4 | -2 | -33 | -7 | 0,18-0,25 s / 0,4-0,7 s | 0,003 |
| 1 | — | — | — | — | — | 0,22 (mat 12/33 dong) |

⇒ **4 fps**: mat 0-4 dong ngan tren mot clip game so voi 10 fps, lech moc trung binh
< 0,15 s (TIMING lam viec o muc 0,25 s), va re hon 10 fps 2,5 lan. 2 fps bat dau mat
dong that (dong ngan nhat that su la 0,8-1,0 s o v1/v2/v4; v3 co dong 0,4 s).

Pass 1 (tim dai) lay **40 khung** rai deu: dai tim duoc khop voi ban 1 fps (265 khung)
trong 1-3 px tren ca 4 clip, va re hon 6 lan.

## 4. OCR hay ASR? (60 s doi chieu TAY cua v2)

Ban doi chieu: `docs/auto_scan_video_final/l_ocr_gt_v2.json` — 33 dong, doc tay tu anh
cat dai moi 0,5 s (khong qua OCR).

| Nguon | CER | Dong dung tuyet doi | Thoi gian |
|---|---|---|---|
| OCR (RapidOCR, 4-10 fps) | **0,003** | 32/33 | §5 |
| ASR faster-whisper large-v3 (tham so san pham: beam 5, VAD, word ts) | **0,018** | 28/33 | 417 s CPU int8 4 luong cho 190 s tieng |
| PaddleOCR 3.7 (PP-OCRv6 **medium**, CPU) | 0,000 | 33/33 | 1.293 ms/khung |

### 4.1 Doc them tu phep do

- **Do phu**: trong 60 s dau v2, ASR noi 57,4 s co tieng, OCR co phu de 57,7 s ⇒ hardsub
  **phu het** phan co loi thoai; khong co doan noi ma khong co phu de. (Neu co, `auto`
  van cho ra ban ghi OCR thieu — xem §7.)
- **Moc thoi gian**: khop 33/33 dong, OCR bat dau **cham hon ASR trung binh 0,34 s**
  (p95 |lech| 0,46 s) — phu de hien sau khi bat dau noi, dung nhu nguoi bien tap lam.
  Do lech nay **nho hon mot nhip TIMING** va khong doi chieu duoc tot hon: chinh ban
  doi chieu tay cung chi co luoi 0,5 s.
- 1 dong sai duy nhat cua OCR o 60 s dau: `一` dung dau dong bi det bo sot (§7).
- PaddleOCR *medium* dung hon **mot ky tu** so voi PP-OCRv6 *small* tren 60 s — khong
  du de tra gia 20 lan thoi gian + mot framework. (Ban *medium* cung KHONG nam trong
  danh sach artifact ma `MODEL_LICENSES.md` §6 xac minh, nen muon dung phai kiem giay
  phep rieng.)

### 4.2 Vi sao KHONG tron OCR voi ASR

- Hardsub cua Douyin **la** ban loi thoai da bien tap (dung chu, tach dong theo y).
- Moc thoi gian hien phu de = moc noi trong vong mot khung lay mau (lech tb < 0,15 s
  o 4 fps). Khong co gi de ASR "canh lai" cho tot hon.
- Chay ASR them tren nhanh OCR = mot luot whisper large-v3 tren GPU cho moi video, de
  lay mot ban chu **te hon**.
⇒ `nguon_loi=ocr` ⇒ khong goi ASR. `nguon_loi=asr` (khach ep, hoac khong co hardsub)
⇒ duong cu nguyen ven.

## 5. Toc do (RTX 5060 Ti / 20 loi; 100 khung dai v2 + 20 khung full)

| Cau hinh | Khung DAI (864x115) | trong do det | Khung FULL (864x576) | trong do det |
|---|---|---|---|---|
| CPU 2 luong | 105 ms | 77 ms | 620 ms | 556 ms |
| **CPU 4 luong** | **66 ms** | 47 ms | **410 ms** | 367 ms |
| CPU 8 luong | 48 ms | 32 ms | 295 ms | 259 ms |
| CUDA (onnxruntime-gpu 1.30, CUDA 13) | 40 ms | 9,9 ms | 104 ms | 56 ms |

⇒ Chon **CPU 4 luong** (`LTT_OCR_LUONG`, `intra_op_num_threads`), vi:
- ca lan chay chi ton `40 khung x 0,41 s + 4 fps x thoi_luong x 0,066 s`
  ≈ **16 s + 0,26 x thoi luong video** (clip 4,5 phut ⇒ ~90 s);
- GPU chi nhanh 1,6 lan o pha ton nhieu thoi gian nhat (dai), doi lai phai cai CUDA 13
  + cuDNN 9 vao venv do luong (onnxruntime-gpu khong tu thay DLL: phai
  `onnxruntime.preload_dlls()`), va **gianh card** voi LTT Voice / VLM — thu ma ca
  `manifest` lan hop dong deu muon tranh.
- ⛔ `intra_op_num_threads` mac dinh cua onnxruntime la **moi loi**: tren may production
  do la 20 loi cho mot viec nen. Runner ghim 4 (`SO_LUONG`).

### 5.1 Vien den quanh dai: DA THU, KHONG DUNG

Det bo sot `一` dung dau dong khi dai cat sat chu (v1). Vien den 96 px lam no doc dung
tren hai khung thu tay, nhung tren CA clip: v1 102 dong (2 -> 3 dong bat dau bang `一`),
v2 CER **khong doi** (0,003), con **thoi gian gap doi** (167-176 ms/khung). ⇒ giu
`dem=0`; tham so con trong runner de doi sau co bang chung tot hon.

### 5.2 Do that tren duong DA NOI (khong phai script benchmark)

`nguon_loi.dinh_tuyen()` + runner that (venv OCR), clip v2 cat 20 s:

    26,1 s tong (pass1 20 khung x 584 ms + pass2 80 khung x 83 ms)
    nguon_loi=ocr · ti_le_han=1,0 · dai y=463-576 · 12 dong
    12/12 dong TRUNG TUYET DOI ban doi chieu tay, moc lech <= 0,25 s

## 6. Da noi vao san pham the nao

```
TRANSCRIBE (apps/auto_scan_video/giai_doan_chep_loi.py)
  cai.nguon_loi: auto | embedded | ocr | asr           (cai_dat.py, routes Form `nguon_loi`)
    auto     : luong phu de CHU -> hardsub chu Han -> ASR, ghi `ly_do` moi buoc lui
    embedded : khong co luong phu de chu ⇒ BAO KHACH (khong lui im lang)
    ocr      : khong co hardsub / bo OCR chua cai ⇒ BAO KHACH
    asr      : khong doc video (duong cu)
  ban ghi chinh tac: them `nguon_loi` (ban ghi) + `do_tin` (moi doan, chi khi nguon
    co do tin — ASR khong tra do tin theo doan, va ta KHONG bia mot con so)
  tom tat giai doan: `dinh_tuyen = {che_do, nguon_loi, ly_do[]}`
```

- **Cache dung chung** (`cache_chung.py`, `PHIEN_BAN_CACHE_CHUNG = 2`): khoa TRANSCRIBE
  mang them `nguon_loi` (che do), `dinh_tuyen` (phien ban logic) va **checksum video
  nguon** khi che do khac `asr` — vi luc do giai doan doc chinh tep video.
- **Phien ban engine** (`thi_hanh.phien_ban_engine`):
  `chep_loi/3+dinh_tuyen/1.1+ocr/rapidocr/3.9.2+PP-OCRv6_small` — nang model OCR la vo
  hieu cache cu, dung nhu nang model ASR.
- **Ranh gioi app**: `auto_scan_video` goi `apps.asv_gpu.do_luong.{venv,ocr_khung}` —
  da khai o `apps/asv_gpu/__init__.py` **va** `tools/lint_app_contract.py` (hai phia).

## 7. Con lai / da biet

- **Dong bao ha guc cua game** doi khi van thanh mot dong rieng khi khong co phu de
  nao trong khung (v3: ~6/99 dong). Muon bo han thi phai biet font size cua phu de
  chuan, tuc mot buoc hoc kieu chu — chua lam.
- **`一` dung dau dong** bi det bo sot (v1: 2-3 dong/102). Vien den khong sua duoc
  (§5.1). Day la loi cua det PP-OCRv6 small, khong phai cua logic dai.
- **Video co loi noi ma KHONG co hardsub cho doan do**: `auto` van chon OCR neu dai
  hardsub dat nguong. Do phu do duoc o v2 la 57,7/57,4 s (ASR) nen chua thay hong
  tren bon clip nay; muon chac thi phai so do phu OCR voi VAD cua ban tieng — mot
  phep do nua, chua lam.
- Hardsub **chu Latin** (en/vi) chua co bang chung ⇒ `auto` chi nhan OCR khi >= 80%
  ky tu la chu Han; con lai ve ASR co ghi ly do.
- Phu de **anh** (PGS/DVD) trong container: bo qua (khong co chu de doc), di tiep.
- `tests/test_448::test_phien_ban_ENGINE_trong_bao_cao_van_dung_HOM_NAY` **da do tu
  truoc lan nay** (bao cao nghiem thu ghi `chep_loi/1`, ma tren `phien/asv-final` da la
  `chep_loi/2`) — phai chay lai nghiem thu e2e, khong phai sua con so.

## 8. Dieu phoi phai lam (cai dat venv do luong)

Runner chay bang `apps/asv_gpu/do_luong/venv.chay` ⇒ **qc-venv** (`C:\LTTPlatform\qc-venv`)
can hai goi. Them DUNG hai dong nay vao `setup/qc_models_requirements.txt` (lan `ocr`
KHONG tu sua tep do de khoi dam nhau voi lan khac):

```
rapidocr==3.9.2
onnxruntime==1.30.0
```

`rapidocr` keo theo: `colorlog, numpy, omegaconf, opencv_python, Pillow, pyclipper,
PyYAML, requests, Shapely, six, tqdm` — deu la goi thuan CPU, tong ~120 MB.
⛔ **Khong** cai `onnxruntime-gpu`: xem §5 (chi de CUDA 13 + gianh card).

Model (31 MB) da nam san o `C:\LTTPlatform\hf-cache\rapidocr\3.9.2\` tren may nay;
may khac thi runner tu tai ban ghim va kiem SHA-256.

Chua cai ⇒ TRANSCRIBE che do `auto` **van chay**: no ghi `ly_do=["ocr_khong_kha_dung"]`
vao tom tat giai doan roi di tiep bang ASR (⛔ khong im lang — nguoi van hanh doc duoc
ly do o `stage.outputs.dinh_tuyen`). Che do `ocr` bi ep thi BAO LOI cho khach.

### 8.1 Giao dien

`routes.tao` da nhan Form `nguon_loi` (`auto|embedded|ocr|asr`, rong = `auto`).
Mau `asv_trang_chinh.html` **chua** co o chon — lan lam giao dien them mot `<select>`
ten `nguon_loi` la du, khong phai sua gi o duoi.
