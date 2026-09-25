# L-DO-VUNG (Đ1) — chi phi THAT cua do vung + dien nen

> Lan `asv-do-vung`, nhanh `phien/asv-do-vung`, do 25/09/2026 tren may A (20 loi,
> RTX 5060 Ti 16 GiB). Chot chan cua **V4a · V4b · V4c · V5** trong
> `docs/superpowers/plans/2026-09-25-asv-full-tu-viral.md` §3.
> Du lieu tho: scratchpad cua phien (`ket_qua.jsonl`, `log_*.txt`, `pixel.txt`);
> bo do: `phep.py` (ban chep thuat toan) + `do.py` (bam gio bang Job Object).
> ⛔ Tep nay chi nop SO. Go `DEFER` va ky ADR-V5 la viec cua phien dieu phoi.

## 0. Phan quyet — doc cai nay truoc

| ma | giay CPU / phim 107 s | tuong / phim 107 s | so voi nen **115 s** phan viec cuc bo | RAM dinh | co model? | GPU? | dang lam? |
|---|---|---|---|---|---|---|---|
| **V4a** do logo TINH | **1,7–2,0 s** | 0,32–0,54 s | **+0,3–0,5 %** | 90–94 MB | khong | **0 VRAM** (chi cv2/numpy) | ✅ **A — lam** |
| **V4b** do dai chu (tang OpenCV) | **3,5–3,9 s** | 0,57–0,92 s | **+0,5–0,8 %** | 88–93 MB | khong | **0 VRAM** | ✅ **A — lam** |
| **V4c** logo DI CHUYEN (`bam`) | **8,4–14,2 s** | 3,0–4,5 s | **+2,6–3,9 %** | 137–142 MB | khong | **0 VRAM** | ⛔ **C — khong lay** (§4.3) |
| **V5** dien nen (`che_keo` 1 ben) | **+1,7–3,6 s** so voi `lam_mo` | **−0,5 s** (NHANH HON `lam_mo`) | **−0,4 %** | 118–126 MB | khong | **0 VRAM** (ffmpeg thuan) | ✅ **A — lam** |
| **V5** dien nen bang **LaMa** | — (khong do) | — | — | — | co (~200 MB) | 0 VRAM (`CPUExecutionProvider`) | ⛔ **C — giay phep** (§6) |

⛔ Cot "GPU?" ghi **0 kem ly do**, khong de trong (§3.3 cua plan doi dung the).

⭐ **Hai cot, hai cau hoi khac nhau — dung trung binh chung.** `giay CPU` = suc tinh
phai tra (dung de phan quyet); `dong ho tuong` = khach cho bao lau (doi theo tai may,
o day nen 16–77 %). Cot "so voi nen 115 s" tinh theo **tuong**, vi 115 s la mot so tuong.

## 1. 🔴 Tien de "khong dung VRAM" — **DUNG**, nhung mot cau trong brief thi SAI

Kiem bang `grep` tren `D:\Viral\resources\app-src` (cay CHI DOC) truoc khi do bat cu gi:

| Manh | Bang chung | Ket luan |
|---|---|---|
| `dai_watermark.py` (V4a) | ca tep 201 dong chi `import os`, `time`, `cv2`, `numpy`, `sys`. ⛔ Khong mot chu `onnxruntime`/`torch`/`cuda`/`providers` | **0 VRAM** |
| `dai_sub.py` tang OpenCV (V4b: `:69`, `:188`) | chi `os`, `subprocess`, `cv2`, `numpy`. RapidOCR chi xuat hien qua `import dai_sub_rapid` o **tang tren** (`:308`), khong o tang nay | **0 VRAM** |
| `dai_sub_rapid.py` tang OCR | di qua `ocr_text.ocr_se_dung_gpu()` — `ocr_text.py:310` bat GPU **chi khi** `OCR_DUNG_GPU=1`; mac dinh **CPU** (ho da do: GPU cham 6,8× tren may dev, `:294-308`) | **0 VRAM** o mac dinh |
| `bam_watermark.py` (V4c) | 🔴 xem duoi | **0 VRAM, 0 model** |
| `localize.py` `--che-patch` / `--che-keo` (V5) | chi sinh **chuoi `filter_complex`** cho ffmpeg; khong nap gi | **0 VRAM** |
| `xoa_text.py` LaMa | `ort.InferenceSession(..., providers=["CPUExecutionProvider"])` (`:133`); nguoi goi DUY NHAT la `thumb_tool.py:17,195,212` | **0 VRAM**, nhung §6 |

### 🔴 Sua brief: **`bam()` KHONG nap RapidOCR**

Brief ghi *"V4c ⚠️ nap RapidOCR CPU (`_lay_ocr:227`; 106 MB RAM, 0,8 s/lan, khoa toan
cuc `_OCR_KHOA`)"*. Doc lai ranh gioi ham thi **khong phai**:

```
bam_watermark.py :227 _lay_ocr      :257 _chay_ocr      (dung o :314, :357, :375, :384)
                 :332 tu_do(...)    ← CHI ham nay goi OCR
                 :542 bam(...)      ← thu ta lay; KHONG mot loi goi OCR nao
```

Va `rapidocr_onnxruntime` **chua he co trong venv cua ta** (`find_spec` → None), nen
ban chep cua ta khong the lo keo no vao.

⇒ **Cau hoi Đ1-③ ("RAM cong don khi N luot song song — ta can mot khoa toan cuc
khong?") tu tieu**: khong co model dung chung thi khong co gi phai khoa. Tai nguyen duy
nhat bi tranh la **CPU**, va cai do hang doi job + `cpu_nhieu` da quan roi. RAM dinh do
that: **88–142 MB mot luot**, tuc 4 lan song song ≈ 0,55 GB — khong can khoa vi RAM.

## 2. Phuong phap — vi sao nhung so nay doc duoc

1. ⭐ **Don vi chinh la GIAY CPU CUA CA CAY TIEN TRINH**, khong phai dong ho tuong.
   May nay dung chung (luc do co lan E2E dai chay nen, CPU nen 16–77 %). Do bang
   **Windows Job Object** (`JobObjectBasicAccountingInformation`:
   `TotalUserTime + TotalKernelTime`) — no cong ca tien trinh **da ket thuc**, nen
   55 lan `ffmpeg` song 0,2 s cua V4c duoc tinh du. Cach lay mau bang `psutil` se
   **bo sot** dung nhung tien trinh ngan do. Tien trinh con bi giu o
   `stdin.readline()` cho toi khi da vao job ⇒ khong ro ri giay dau.
2. 🔴 **V5 do bang `-f null -`, ⛔ KHONG encoder.** `TONG-HOP-VAN-DE.md` cua Viral:
   NVENC chay bat dong bo va che **toi 95 %** chi phi filter that. Do bang hieu hai
   luot CO NVENC la sai. ⇒ moi so V5 duoi day la **giai ma + chuoi loc**, khong encode.
3. ⚠️ **⛔ Khong `-hwaccel`.** Cung nguon: filter chay CPU thi moi khung phai tai nguoc
   GPU→CPU, `-hwaccel auto` lam CHAM hon.
4. **3 luot moi phep**, bao **trung vi + khoang**, va ghi **CPU nen** canh moi so.
   Moi so V4* da **tru 0,20 s** khoi dong (python + `import cv2/numpy`, do rieng bang
   phep `khoi_dong`: 0,20 s CPU · 0,32 s tuong · 27,6 MB).
5. **Khong giu khoa** (chu du an cap quyen 25/09) — chinh vi don vi la giay CPU.

⚠️ **Gioi han**: hai phim thu deu **576p** (864×576 va 1024×576). Chi phi chuoi loc
V5 ti le voi SO DIEM ANH, nen §5 do rieng he so khi len 1080×1920.

## 3. So do — hai phim that (`tests/fixtures/asv_e2e_that/`)

phim1 = `暴雨天…露营` 864×576 · 30 fps · **190,0 s** · 5 699 khung ·
phim2 = `真人气枪游戏…` 1024×576 · 29,97 fps · **275,0 s** · 8 242 khung

| ma | phim | giay CPU (trung vi) [khoang] | dong ho tuong [khoang] | CPU nen (3 luot) | RAM dinh | quy ve phim 107 s: CPU / tuong | so loi |
|---|---|---|---|---|---|---|---|
| `v4a` | phim1 | **3,47 s** [3,18..3,57] | 0,96 s [0,96..0,96] | 30·28·25 % | 90 MB | 2,0 / 0,54 s | 0 |
| `v4a` | phim2 | **4,25 s** [4,11..4,28] | 0,81 s [0,81..0,99] | 32·41·38 % | 94 MB | 1,7 / 0,32 s | 0 |
| `v4b` | phim1 | **6,88 s** [6,72..7,77] | 1,63 s [1,46..1,65] | 40·54·38 % | 88 MB | 3,9 / 0,92 s | 0 |
| `v4b` | phim2 | **9,08 s** [7,07..9,35] | 1,47 s [1,46..1,68] | 26·28·44 % | 93 MB | 3,5 / 0,57 s | 0 |
| `v4c` | phim1 | **25,19 s** [24,24..26,49] | 7,91 s [7,90..8,44] | 48·23·77 % | 137 MB | 14,2 / 4,45 s | 0 |
| `v4c` | phim2 | **21,53 s** [20,18..21,86] | 7,78 s [7,48..8,79] | 26·50·30 % | 142 MB | 8,4 / 3,03 s | 0 |
| `v5_giai_ma` (nen: chi giai ma) | phim1 | **9,92 s** [8,69..10,50] | 1,66 s [1,66..1,67] | 33·45·40 % | 105 MB | 5,6 / 0,93 s | 0 |
| `v5_giai_ma` | phim2 | **25,44 s** [23,34..25,86] | 2,82 s [2,79..3,01] | 43·46·34 % | 113 MB | 9,9 / 1,10 s | 0 |
| `v5_lam_mo` (hanh vi HIEN TAI cua ta) | phim1 | **10,08 s** [9,72..11,17] | 3,23 s [3,07..3,41] | 30·28·36 % | 111 MB | 5,7 / 1,82 s | 0 |
| `v5_lam_mo` | phim2 | **25,03 s** [24,47..26,89] | 5,63 s [5,63..5,99] | 31·24·16 % | 120 MB | 9,7 / 2,19 s | 0 |
| `v5_che_keo_1ben` (mac dinh cua Viral) | phim1 | **13,17 s** [12,23..14,00] | 2,33 s [2,32..2,68] | 26·29·25 % | 118 MB | 7,4 / 1,31 s | 0 |
| `v5_che_keo_1ben` | phim2 | **34,38 s** [33,58..36,66] | 4,38 s [3,83..4,75] | 28·26·68 % | 126 MB | 13,4 / 1,70 s | 0 |
| `v5_che_keo_2ben` | phim1 | **16,59 s** [15,78..17,58] | 3,52 s [3,52..3,72] | 66·42·54 % | 124 MB | 9,3 / 1,98 s | 0 |
| `v5_che_keo_2ben` | phim2 | **41,28 s** [39,64..43,39] | 6,27 s [5,71..7,39] | 41·56·53 % | 134 MB | 16,1 / 2,44 s | 0 |
| `v5_che_patch` | phim1 | **13,42 s** [13,12..13,77] | 2,85 s [2,84..3,06] | 46·49·54 % | 118 MB | 7,6 / 1,60 s | 0 |
| `v5_che_patch` | phim2 | **33,09 s** [32,20..34,91] | 5,31 s [4,55..5,87] | 53·50·50 % | 127 MB | 12,9 / 2,07 s | 0 |

"so loi" = so thong diep loi/khong-chac ma thuat toan tu phat ra + `rc != 0`. **0/48 luot
loi**, moi luot ffmpeg `rc=0`.

Ket qua thuat toan (de biet so do la cua duong day DU, khong phai cua mot nhanh cat som):

```
v4a  phim1/phim2 : boxes=[] ca hai (16/16 khung doc duoc) — "da quet, KHONG co logo tinh"
                   ⇒ chi phi do la chi phi DAY DU (moi chang da chay, chi la khong ra hop)
v4b  phim1       : dai y 88,2–99,3 %  -> om_sat 90,1–97,6 %
     phim2       : dai y 87,4–96,7 %  -> om_sat 82,6–98,1 %
v4c  phim1       : 1/55 khung khop (o thu tu ve o goc phai tren) -> tu choi, dung
     phim2       : 12/55 khung khop, 11 cum, diem trung vi 0,594 -> "troi", khong phai neo
```

⚠️ Đo dung/sai **khong thuoc Đ1** (do la V4-① cua lan `asv-vung2`). Cot tren chi de
chung minh cac chang da chay thuc su.

## 4. Phan quyet tung muc — bang SO, so voi cai gi

Nen: mot luot hien tai **~12,5× do dai video**; phan viec **CUC BO** chi **115 s** cho
phim **107 s** (`L_TOC_DO_GPU.md` §0). ⇒ moi so duoi day quy ve phim 107 s.

### 4.1 V4a — **A, lam**

**0,32–0,54 s tuong** = **+0,3–0,5 %** cua 115 s. **1,7–2,0 giay CPU** tren may 20 loi.
Đo la muc gia re nhat trong ca ho: mot lan mo video, 16 khung, moi thu con lai chay o
be rong 360 px.

**Đo dan hoi theo so khung** (phim1, `N_FRAMES` = 8/16/32/48, 3 luot moi muc):

```
n =  8  ->  2,22 s CPU · 0,64 s tuong
n = 16  ->  3,39 s CPU · 0,81 s tuong     (mac dinh cua Viral)
n = 32  ->  6,80 s CPU · 1,46 s tuong
n = 48  ->  9,39 s CPU · 1,94 s tuong
```

⇒ **tuyen tinh: 0,179 giay CPU va 0,033 s tuong MOI KHUNG**, cong ~0,8 s phi co dinh.
Đay la cau tra loi cho Đ1-② ve phia GIA: bai hoc `_han_tren_hinh` cua Viral (nang
`n_frames` 6 → 20 sau ca khach treo 34 phut) **gia chi 0,7 giay CPU / 0,13 s tuong**.
Ke ca 48 khung van chi **1,9 s tuong = 1,7 %** cua 115 s. ⇒ Khi lan `asv-vung2` do ti le
do dung (V4-①), **dung tiec khung**: mua do chinh xac o day gan nhu mien phi.

### 4.2 V4b — **A, lam**

**0,57–0,92 s tuong** = **+0,5–0,8 %**. Đat gap **~1,9×** V4a vi no doc 18 khung o be
rong 480 **cong** 12 khung nua o **be rong GOC** trong `_om_sat_vien` (`g>190` &
`dilate(g<70)` chay tren khung day du).

⇒ V4a + V4b chay ca hai: **~0,9–1,5 s tuong (0,8–1,3 %)** va **5–6 giay CPU**. Mot doi
thuong.

### 4.3 V4c — ⛔ **C, khong lay** — hai ly do doc lap

**① Gia.** So voi V4a: **5–7× ve giay CPU** (25,19/3,47 = 7,3× phim1 · 21,53/4,25 =
5,1× phim2) va **8–10× ve dong ho tuong** (7,91/0,96 = 8,2× · 7,78/0,81 = 9,6×).
Quy ve phim 107 s: **3,0–4,5 s tuong = 2,6–3,9 %** cua phan viec cuc bo. Tien di dau:
`bam()` **khong mo video mot lan** — no goi **MOT `ffmpeg` rieng cho TUNG mau**
(`_doc_khung:34`), 55 lan cho hai phim nay, moi lan tu tim va tu dung. Cong voi
`_net` (CLAHE + 2 Sobel + normalize) va `matchTemplate` tren **khung DAY DU**, khong ha
do phan giai nhu V4a/V4b.

**② Va ly do nay quan trong hon gia: `bam()` KHONG PHAI mot bo tu do.** No doi
**khach khoanh mot o** (`x,y,w,h` + `t_mau`) roi may di bam o do. Ban tu do cua chinh
Viral — `tu_do():332` — **da thu va BI LOAI**, co so do ghi ngay trong nguon
(`bam_watermark.py:520-540`):

```
o 290x44 tai t=150     diem khop qua 4 canh khac        min
watermark THAT         0,20 · 0,16 · 0,16 · 0,16        0,16
dai phu de             0,69 · 0,60 · 0,64 · 0,55        0,55   <- tool chon CAI NAY
```

*"Khong nguong nao tach duoc, vi cai ĐUNG nam DUOI cai SAI."* ⇒ **khong co ban tham
chieu nao cho "tu do logo di chuyen" de ma chep.** Ta co the chep `bam()`, nhung the la
mot tinh nang **khach khoanh tay**, khong phai `V4c` nhu plan mo ta.

⇒ **Đe nghi C.** Va theo dung yeu cau nghiem thu cua V4c trong plan: neu sau nay ai mo
lai, phai **khai thang la KHONG HO TRO** — ⛔ tuyet doi khong im lang tra mot hop TINH
cho mot logo dong.

### 4.4 V5 — **A, lam** (`che_keo`), va no **KHONG lam khach cho lau hon**

Đay la ket qua bat ngo nhat cua ca luot. Đoi `lam_mo` (hanh vi hien tai) sang
`che_keo` mot ben:

| | giay CPU | dong ho tuong |
|---|---|---|
| phim1 (190 s) | **+3,09 s** (10,08 → 13,17) | **−0,90 s** (3,23 → 2,33) |
| phim2 (275 s) | **+9,35 s** (25,03 → 34,38) | **−1,25 s** (5,63 → 4,38) |
| **quy ve 107 s** | **+1,7–3,6 s** | **−0,5 s (ca hai phim)** |

Vi sao: `boxblur` cua ta chay **mot luong** (`lam_mo` gan nhu khong them giay CPU nao —
+0,16 s tren phim1 — ma them **+1,57 s tuong**: dung chan dung mot nut nghen mot luong).
`che_keo` thi la `crop` + `vflip` + hai `scale` — `swscale` chay SIMD/nhieu luong, nen no
**an nhieu chu ky hon nhung ket thuc som hon**. Đung ho voi so do 12/08/2026 cua Viral
(`xu_ly_video.loc_mo_ngang`: bo `gblur`, thay bang thu-nho-roi-phong-lai, 5,31 s → 1,97 s).

Chi phi **rong** cua `dien_nen` so voi "khong che gi" (chi giai ma), quy ve 107 s:
`che_keo_1ben` **+1,8–3,5 giay CPU / +0,4–0,6 s tuong**.

Xep hang ba bien the (giay CPU, phim2): `che_patch` 33,1 < `che_keo_1ben` 34,4 <
`che_keo_2ben` 41,3. ⇒ `che_keo_2ben` dat hon mot ben **~20 %** giay CPU va
**~43 %** tuong (6,27 vs 4,38 s) — khop voi chinh chu thich cua Viral (*"1 chieu … re hon
(2 node filter thay vi 4)"*) va voi so do chat luong cua ho (hai ban **gan nhu bang
nhau** tren render that). ⇒ **Lay mot ben lam mac dinh**, dung cong nhau ky khac.

⚠️ Mot ca `che_patch` cua ban do nay chay voi dai nguon **bi ffmpeg tu kep** vao trong
khung (dai y 79–93 % thi phia duoi chi con 42 px < chieu cao dai 80 px). So do van dung
ve **cau truc node** va **so diem anh**, nhung khi lam that thi phai kep **co y** —
chinh la `_pdt`/`_pdd` cua Viral (`localize.py:8035+`), va la bat bien §3.4 cua plan
(*"chua cho cho dai nguon, va chi o ben that su lay nguon"*).

## 5. V5 theo do phan giai — hai phim thu deu 576p

Nguon `lavfi testsrc2` 20 s (sinh khung, khong giai ma) ⇒ hieu so la **chi phi chuoi loc
thuan**. Giay CPU doc tu `ffmpeg -benchmark` (`utime+stime`). 3 luot, trung vi.

| chuoi loc | 864×576 (0,50 Mpx) | 1080×1920 (2,07 Mpx) | he so |
|---|---|---|---|
| chi sinh khung | 0,19 s | 0,73 s | — |
| `lam_mo` (them) | +0,37 s | +1,80 s | **4,9×** |
| `che_keo_1ben` (them) | +0,79 s | +4,00 s | **5,1×** |
| `che_keo_2ben` (them) | +0,67 s | +4,54 s | **6,8×** |
| `che_patch` (them) | +0,39 s | +3,47 s | **8,9×** |

⇒ Chi phi loc ti le xap xi **so diem anh** (4,17× khi len 1080×1920), khong te hon.
⚠️ Cac so nay **chi doc theo TI LE trong chinh bang nay** — nguon tong hop nen tri so
tuyet doi khong so sanh duoc voi §3. Ket luan an toan: **tren 1080p, chi phi V5 nhan
~4–5 lan so voi §3**, tuc `che_keo_1ben` ≈ **+8–17 giay CPU / +2–3 s tuong** cho phim
107 s — van duoi 3 % cua 115 s, va van **re hon `lam_mo` ve dong ho tuong**.

## 6. `big-lama` — ⛔ **C, giay phep chan**, xac nhan

Theo thang `OPEN_SOURCE_METRIC_AUDIT.md` (EasyOCR tung bi loai vi *"weights chua xac
minh"*). Nguon **thuong nguon**, khong trich model card ban port:

| Bang chung | Noi |
|---|---|
| Ma nguon LaMa = **Apache-2.0**, "Copyright [2021] Samsung Research" | `advimman/lama/LICENSE` (doc qua GitHub MCP, blob `786f5936`) |
| README tro trong so ve **mot kho HF cua NGUOI THU BA**: `huggingface.co/smartywu/big-lama/resolve/main/big-lama.zip` — `smartywu` khong phai tac gia, khong phai Samsung | `advimman/lama/README.md:113` |
| Kho HF do khai `license: apache-2.0` **chi trong cardData**, khong kem van ban giay phep cho trong so | `api/models/smartywu/big-lama` → `"tags":["license:apache-2.0"]` |
| Thuong nguon **chua bao gio** khai giay phep cho trong so — **BA issue dang mo, khong ai tra loi** | `advimman/lama#365` (26/08/2026) · `#366` (01/09/2026) · `#368` (08/09/2026) |
| `#368` noi thang: *"`LICENSE-MODELS.md` la referenced but missing"* | tieu de issue |
| `#366`: hai nguoi hoi thang ve **dung thuong mai** (private cloud, app macOS co phi) va hoi ca **dieu khoan du lieu Places** — **khong co maintainer tra loi** | 2 comment, ca hai `author_association: NONE` |
| Trong so `big-lama` huan luyen tren **Places365-Challenge** (476 GB) — dieu khoan tap du lieu la mot cau hoi RIENG, cung chua ai tra loi | `advimman/lama/README.md:261-267` |

⇒ **Apache-2.0 cua kho chi phu MA. Giay phep TRONG SO: KHONG XAC ĐINH.** Mot ban port
(`Carve/LaMa-ONNX`, `smartywu/big-lama`) **khong rua duoc** giay phep trong so thuong
nguon. ⇒ **LaMa = loai C** cho tới khi thuong nguon khai ra.
⭐ Va ta **khong can** no: `che_keo` (ffmpeg, 0 trong so) da do xong o §4.4 va du cho
video; con anh thumbnail thi `cv2.inpaint` (Telea, OpenCV Apache-2.0, 0 trong so).

## 7. ⭐ Phep do ta KHONG can chay — va da khong chay

⛔ Đo thua khong mien phi (`N-54`: hom nay mot phep do khong-can-chay lam lo mat khau CSDL).

| Phep | Vi sao khong chay |
|---|---|
| **VRAM** cua ca bon muc | Tra loi bang **doc ma** (§1), khong phai bang do. Khong tep nao trong duong di nap `torch`/`onnxruntime`; do VRAM cua mot chuong trinh khong mo CUDA la do **con so 0 da biet truoc** |
| **RAM cong don + "ta can khoa toan cuc khong"** (Đ1-③) | Cau hoi **tu tieu**: `bam()` khong nap OCR (§1), nen khong co model dung chung de tranh. RAM dinh do that 88–142 MB/luot la du de tra loi |
| **106 MB / 0,8 s cua RapidOCR** | Khong nam tren duong ta lay. Va `rapidocr_onnxruntime` khong co trong venv — do duoc no doi **cai goi moi**, ma brief cam |
| **Ti le do dung / bao dong gia cua V4a-V4b** | Đo la **V4-①** cua lan `asv-vung2` (can ≥ 4 clip + san may rui), khong phai Đ1. Đ1 chi hoi GIA |
| **Đo co NVENC** | Sai phuong phap tu goc: NVENC che toi 95 % chi phi filter (§2.2). Chay no chi de sinh mot bang so trong co tham quyen |

## 8. Lam lai the nao

```powershell
# bo do nam o scratchpad cua phien asv-do-vung: phep.py (chep thuat toan) + do.py (bam gio)
$env:PYTHONUTF8=1
python do.py v4a  "<phim>" --lap 3        # v4a | v4b | v4c
python do.py v5_che_keo_1ben "<phim>" --lap 3
python do_pixel.py                        # he so theo do phan giai
```

Hang so chep nguyen tu Viral (⛔ dung go lai bang tay o cho khac):
`CHE_KEO_HS_MAX=4` (`localize.py:6106`) · `CHE_KEO_FEATHER=0.30` ·
`CHE_KEO_FEATHER_X=0.04` · `CHE_PATCH_GAP=0.10` · `CHE_PATCH_FEATHER=0.30` ·
`nguong_khop=0.55`, `o_luoi=24` (`bam_watermark`) · `std<8.0`, `Laplacian>26`,
dien tich `0.0009..0.06` (`dai_watermark`) · `peak≥0.22`, `0.03≤cao≤0.20`,
`CHE_OPENCV_BU=0.015` (`dai_sub`).
Nen `lam_mo` cua ta: `che_do_render._loc_lam_mo:252` (`boxblur`, `_MAU_BAN_KINH=20`).

## 9. Đ1-④ — co dung lai duoc khung `canh.py` da trich khong?

**Duoc ve ky thuat, nhung khong nen — va tien tiet kiem qua nho de danh doi.**
`canh.rut_khung` dua ra JPEG (`CHAT_LUONG_JPEG=4`) **da ha xuong canh dai 512**
(`CANH_DAI_KHUNG`), lay tai **giua moi canh** (`moc_khung_mau`, `KHUNG_MOI_CANH=2`),
tran `KHUNG_TOI_DA=60` va **ha DEU** khi vuot tran.

- V4a can **khung CACH DEU theo thoi gian** — no do `std` theo truc thoi gian. Mau theo
  **giua canh** khong cach deu, va mot canh dai se do sang mot canh ngan.
- Ca V4a va V4b dat nguong tren **Laplacian** (`>26`) va tren `g>190 & g<70`. JPEG
  chat luong 4 + ha ve 512 px **them/bot net** dung o cai dai luong ma nguong do.
- Tien tiet kiem: toan bo V4a + V4b la **0,9–1,5 s tuong / 5–6 giay CPU** cho phim
  107 s. Buoc giai ma chi la mot phan trong do.

⇒ **Giu doc khung RIENG.** Đoi lay 1 giay la buoc mot bo do sang mot kenh **loi mat
mat** va mot luoi lay mau **khac ban chat** — dung ho `doc-thu-dai-dien-thay-vi-doc-thu-that`.
