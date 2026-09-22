# Lane `fix-toc-do` — R-04 (giai doan GIONG chiem 79% lan chay) va R-05 (VLM doc canh hong)

Nhanh `phien/asv-final-fix-toc-do`, tu `29aaacd8`. Moi con so duoi day **do tren
duong that**: LTT Voice sidecar :8120, model nha may B, phim khach that
`深度解析…#和平精英夏日探险.mp4` (106,833 s, tieng Trung) — cung phim cua
`bang_chung/NEN_V3.md`.

Cong cu do: **`tools/do_toc_do_giong.py`** (moi, commit trong lane nay). Nam che do:

```
--che-do tts        doc 6 doan tieng Viet THAT -> giay tuong, giay am, RTF, am tiet/giay
--che-do llm        goi `rut_ngan_cho_vua` THAT -> giay, token vao/ra, khoi suy nghi
--che-do vong-dau   `chuyen_loi_thoai` THAT -> `doc_mot_doan` THAT -> co vua khe khong
--che-do wer        bo do `giong` (whisper large-v3 + jiwer) tren chinh tieng vua sinh
--muc-nghi low|medium|xhigh   ep muc suy nghi de A/B
```

⛔ Cong cu khong doc `app.env`; nguoi goi nap bien vao env tien trinh con. Phan
TTS giu khoa `may_tao_tieng`; phep do WER chay qua `chay_nang.py`.

Ket qua tho cua moi phep do o **`bang_chung/fix_toc_do/`** (8 tep JSON: TTS van
ban cu · LLM nan `medium` va `low` · ba vong `vong-dau` · WER truoc/sau · 18 canh
`doc_canh` truoc va sau). Chung mang **nguyen van phan hoi model**, khong mang
mot gia tri bi mat nao.

---

# R-04 — `voice_synthesis` 937-943 giay cho mot phim 107 giay

## 1. Thoi gian di dau: **80% la LLM viet lai, khong phai may sinh tieng**

Bao cao nen v3 chi biet TONG. Do tach ra:

| cua | so luot cua nen v3 | giay/luot (do 23/09) | tong |
|---|---|---|---|
| TTS `doc_mot_doan` | 17 | **14,18** (RTF 0,68) | ~241 s |
| LLM `rut_ngan_cho_vua` | 11 | **68,32** | ~751 s |
| | | | **992 s** (nen v3 do 942,7 s) |

Phep quy chieu khop voi so do that trong ~5%. ⇒ **Khong phai may sinh tieng cham.**

Mot luot `rut_ngan_cho_vua` — viet lai MOT cau cho ngan hon — tieu:

```
token vao  ~430      token ra 4.209      khoi suy nghi 11.783 ky tu      68,3 giay
```

Tuc **>95% ngan sach token ra di vao khoi suy nghi**, cho mot thao tac khong doc
anh, khong dung ho so, khong sap lo.

## 2. Vi sao co 11 luot viet lai: **hang so nhip doc sai 34%**

`ngon_ngu.CUM[vi]["nhip"]` noi voi model *"khoang 4,5 am tiet/giay"*. Con so do
chua tung duoc do. Do that, sau doan tieng Viet cua luot nen v3, giong
`Minh Đức`, hai vong:

```
seg_0001 3,04 · seg_0002 3,33 · seg_0003 3,37 · seg_0004 3,42 · seg_0005 3,44 · seg_0006 3,51
vong 1 trung binh 3,349   vong 2 trung binh 3,324   do lech chuan 0,15   bien 3,04-3,51
```

`4,5 / 3,35 = 1,34`. Nen **moi cau cua luot viet dau dai hon khe ~34% theo dung
thiet ke**. Do lech that cua sau doan (van ban luot viet dau vs khe goc):

```
+27,8%  +31,1%  +39,7%  +44,1%  +47,4%  +50,8%      ->  6/6 ngoai dung sai (+8%)
```

⇒ Bac thang `nan_cho_vua` khong phai mot luoi an toan hiem khi cham — no chay o
**moi** doan, va chay het so vong (11/12 vong toi da) ma van con 2 doan `can_sua`.

## 3. Da sua gi

| # | Cho | Viec |
|---|---|---|
| A | `ngon_ngu.py` | `NHIP = {vi: 3.35, en: 2.6}` + `DON_VI_DO_DAI` + `HE_SO_MUC_TIEU = 0.92`; `CUM[*]["nhip"]` **tinh ra** tu chung. Them `ngan_sach_do_dai(giay, dich) -> int`. |
| B | `long_tieng.loi_nhac` | Moi doan mang `do_dai_toi_da` — mot TRAN **dem duoc**; loi nhac doi model dem lai truoc khi tra ve. `PHIEN_BAN_LONG_TIENG` 1→2. |
| C | `nan_cho_vua.loi_nhac_nan` | Cung tran do; `muc_tieu_giay` lay `ngon_ngu.HE_SO_MUC_TIEU` thay cho `0.92` go tay. `PHIEN_BAN_NAN` 1→2. |
| D | `ai.py` | `ThaoTac.muc_nghi`; `RUT_NGAN_CHO_VUA.muc_nghi = "low"`; `ai.goi` truyen `reasoning_effort` xuong `dieu_phoi`. |
| E | `giai_doan_giong.chay` | Hai dong ho: `tom_tat.giay_tts` va `tom_tat.giay_llm_nan`. |

**Vi sao `HE_SO_MUC_TIEU = 0.92` chu khong 1,0** — va no kiem duoc bang test:
mot cau viet dung ngan sach (`3,35 × 0,92 = 3,082` am tiet/giay) doc o hai dau
bien do that (3,04 / 3,51) ra `+1,4%` / `−12%` so voi khe — ca hai nam trong dung
sai `nan_cho_vua` (`+8%` / `−35%`). Voi he so 1,0 thi dau bien cham 3,04 se tran.

**`en` = 2,6 tu/giay CHUA DO** tren may sinh tieng nay — giu nguyen so cu va ghi
ro la chua do. Do bang cung cong cu khi duong `en` co mot luot chay that.

**Muc suy nghi**: A/B tren cung 6 doan, mot vong moi muc:

```
medium : 68,3 giay/luot · 4.209 token ra · 11.783 ky tu suy nghi
low    : 47,7 giay/luot · 3.337 token ra ·  8.652 ky tu suy nghi     (-30%)
```

Ca hai: 6/6 luot `finish_reason=stop`, 6/6 cau viet lai NGAN HON ban vao
(89→66, 73→55, 65→53, 75→61, 115→102, 23→18 am tiet). `none` khong phai lua chon
— `ltt_llm` tu choi no tu 14/09.

## 4. Truoc / sau, do tren duong that

`--che-do vong-dau` chay CA HAI cua cua luot dau (`chuyen_loi_thoai` that →
`doc_mot_doan` that), 3 vong × 6 doan = 18 luot:

| | truoc (loi nhac cu) | sau |
|---|---|---|
| doan phai nan | **6/6 = 100%** | **5/18 = 28%** |
| lech so voi khe | +27,8% … +50,8% | −22,2% … +24,8% |
| luot LLM cho 1 phim 6 doan | 11 | ~1,7 |
| luot TTS cho 1 phim 6 doan | 17 | ~7,7 |
| **uoc `voice_synthesis`** | **943 s** (do that) | **~190 s** |

Phep uoc "sau" = `6 × 14,2` (TTS luot dau) `+ 1,7 × (47,7 + 14,2)` (moi luot nan
= 1 LLM `low` + 1 lan doc lai) ≈ **190 giay** ⇒ **~5×**.

⚠️ Model **khong tuan thu tran tuyet doi**: 3/6 doan (seg_0004, seg_0005,
seg_0006 — cac doan ngan) van viet qua tran 14-36%. Do la ly do bac thang nan
VAN o nguyen cho, chu khong phai ly do de bo tran: tran keo trung binh tu +40%
xuong +5%, va do la khac biet giua "nan moi doan" voi "nan mot doan tren sau".

## 5. Chat luong KHONG bi doi lay toc do

Bo do `giong` (`apps/asv_gpu/do_luong/giong.py` — faster-whisper `large-v3`
ghim commit + `jiwer`), cham tren **chinh tieng vua sinh**, nguong
`sua_chua.NGUONG_DOC_SAI["vi"]` = `{wer: 0,30, cer: 0,23}` (lane `giong` hieu
chinh tren 50 doan that):

| ve | n | WER tb | WER max | CER tb | CER max | bi cham `doc_sai` |
|---|---|---|---|---|---|---|
| van ban **cu** | 6 | 0,0175 | 0,0435 | 0,0080 | 0,0220 | **0** |
| van ban **moi** | 12 | 0,0136 | 0,0500 | 0,0060 | 0,0199 | **0** |

⇒ Khong lui. Ca hai ve deu cach nguong mot bac lon.

Ngoai le tinh: van ban moi **khong con sot chu Han** (ban cu co `"趁 địch"`,
`"千万别 học"`, `"công楼"` — xem `ban_long_tieng.chu` cua luot nen v3).

---

# R-05 — VLM doc canh hong 4/12 ⇒ `smart_localize` khong cat gi

## 1. Tai hien, va nguyen nhan

Nhat ky san pham chi ghi TEN LOP (`(LuocDoSai)` / `(HieuCanhError)`), nen khong
tra loi duoc *vi sao*. Goi lai 18 canh cua chinh phim do bang model that va giu
nguyen van phan hoi: **8/18 hong**.

| kieu hong | so luot | phan hoi that |
|---|---|---|
| `de_xuat` co **dau tieng Viet** | **5** | `"de_xuat": "giữ"` — JSON dung, khoa dung, kieu dung |
| tra ve mot **MANG** doi tuong | 1 | `[{...}, {...}, {...}, {...}]` trong ```` ```json ```` |
| boc them mot lop | 1 | `{"objects": [{...}, {...}]}` |
| gia tri la | 1 | `"de_xuat": "bu"` |
| `content` rong sau 120,3 s | 1 | `finish_reason` rong, khong khoi suy nghi |

⇒ **Khong luot nao la "model tu choi"**. Tat ca deu la phan hoi HTTP thanh cong
co hinh dang sai, va hai nguyen nhan lon deu la **loi nhac**, khong phai model:

1. `hieu_canh.DE_XUAT` la ASCII khong dau (`giu`/`bo`/`khong_chac`) vi moi loi
   nhac cua ASV viet ASCII. Model tra loi bang tieng Viet THAT. `"giữ"` va
   `"giu"` la cung mot gia tri viet hai cach — va `doc_hieu_canh` tu choi cau
   tra loi **dung**.
2. `loi_nhac_canh` la loi nhac **duy nhat** cua ASV ke ten khoa bang van xuoi
   thay vi dua mot khung JSON. Va no la loi nhac duy nhat bi tra ve sai hinh.

## 2. Da sua gi

| # | Cho | Viec |
|---|---|---|
| F | `hieu_canh.loi_nhac_canh` | Dua **khung JSON** (mot doi tuong, cam mang, cam boc lop); noi ro `de_xuat` la MA chep y nguyen, khong dich, khong dau. `PHIEN_BAN_HIEU_CANH` 3→4. |
| G | `hieu_canh.chuan_de_xuat` | Bo dau (NFD + `đ`→`d`) roi doi chieu. `"giữ"`→`giu`. ⛔ Van tu choi gia tri la: `"bu"`→`""`. |
| H | `giai_doan_ban_bien_tap._doc_cac_canh` | **Thu lai MOT lan** — va **chi** voi `LuocDoSai` / `HieuCanhError` (`SO_LAN_DOC_CANH = 2`); `item_key` khac de but toan lan hai khong bi `UNIQUE(run_id, ma_dispatch)` nuot. ⛔ `AiMoHo` (khong biet da chay chua) va `AiError` tran (may ban, provider tu choi) **khong** hoi lai. Log ghi **thong diep**, khong chi ten lop. Tra ve them danh sach canh hong. |
| I | `giai_doan_ban_bien_tap.chay` | `tom_tat` mang `so_canh_hong`, `canh_hong` (ma + loai + ly_do), `do_phu_bang_chung`. Canh bi bo o mot **luot lat cat truoc** cung duoc ghi (`loai: "luot_truoc"`), nen bat bien `so_canh_da_doc + so_canh_hong == so_canh` dung o moi luot. |
| J | `giai_doan_ban_bien_tap._chot_do_phu` | `smart_localize` doi bang chung cho **moi** canh (`PHU_BANG_CHUNG_TOI_THIEU = 1.0`); thieu ⇒ `ThieuBangChungCanh`. |

**Vi sao chi hoi lai loi HINH DANG.** `LuocDoSai` / `HieuCanhError` = model DA
tra loi, chi sai hinh dang — thu re-roll duoc, va 8/8 luot hong do duoc deu
thuoc loai nay. `AiError` tran la mot cau tra loi ve TINH TRANG (may ban,
provider tu choi), khong phai mot phan hoi rac; hoi lai ngay lap tuc chi ton
tien. Ranh gioi nay cung la ly do `test_2051` (lat cat) van xanh: stub cua no
nem `AiError`, va no chot rang mot canh hong khong duoc hoi lai.

**Va nen tang KHONG tu dong thu lai `ThieuBangChungCanh`.** No ke thua
`ThieuNguon` ⇒ `loi.phan_loai` tra `THIEU_THUONG_NGUON` ⇒ khong thu lai. Lan
hoi lai da xay ra roi, ngay trong giai doan; mot vong thu lai thu hai o tang job
la cung mot phep goi tren cung mot khung hinh, cong them mot hoa don. Nguoi
quyet dinh chay lai la KHACH, va thong diep noi ro ho co hai lua chon.

Do lai sau khi sua, cung 18 canh, cung model: **18/18 doc duoc** (0 hong).

## 3. Quyet dinh san pham — va vi sao

**Khi `smart_localize` khong doc duoc het cac canh thi giai doan TU CHOI, khong
giao mot ban "giu het".**

Hom nay mot canh khong bang chung **luon duoc GIU**
(`ban_bien_tap._quyet_dinh_mot_canh`) — va o cap CANH do la quyet dinh dung: cat
mu nguy hiem hon giu thua. Nhung o cap SAN PHAM thi khong: khach bam "cat thong
minh", tra tien cho duong cat thong minh, va nhan ve mot ban ma hoa lai cua chinh
video ho — giong het `localize_preserve_picture`, khong mot loi nao noi vi sao,
va giai doan bao `succeeded`. Do dung la dieu da xay ra o luot nen v3.

**Vi sao nguong la 1,0 chu khong phai mot con so hieu chinh.** Mot nguong 0,8 tra
loi cau *"bao nhieu phan tram la du"* — mot cau khong ai do duoc va khong ai do
cho, tuc dung loai hang so vua lam hong R-04. `1,0` tra loi mot cau khac han:
*"co lo hong im lang nao khong"*. Do la mot bat bien, khong phai mot tham so.

**Vi sao cho nay re.** `edit_plan` chay TRUOC `content_process` va
`voice_synthesis`. Mot lan tu choi o day tra lai cho khach ca doan dat nhat cua
chuoi (84 + 943 giay o luot nen v3), thay vi tieu het roi giao mot thu khong
phai cai ho mua.

---

# Phep kiem

| tep | so bai | noi dung |
|---|---|---|
| `tests/test_2018_asv_ngan_sach_do_dai.py` | 14 | NHIP mot nguon · tran dem duoc · bien do that nam trong dung sai · loi nhac ca hai pha · dong ho · muc suy nghi |
| `tests/test_2025_asv_doc_canh_hong.py` | 31 | `de_xuat` co dau · gia tri la van bi tu choi · khung JSON · thu lai · `AiMoHo` khong thu lai · do phu bang chung · `tom_tat` |

Bon tep cu phai doi theo — khong tep nao bi noi long menh de cua no:

* `tests/test_2000_asv_ngon_ngu.py::test_loi_nhac_vi_GIU_cum_da_nghiem_thu` —
  truoc chot chuoi `"khoang 4,5 am tiet/giay"` go tay. Nay chot rang cac cum
  **tinh ra tu `ngon_ngu.NHIP`** va `NHIP["vi"] == 3.35`. Doi con so la doi MOT
  cho, va phai co so do moi.
* `tests/test_452_asv_v4_pha27_va_blocker.py::test_EDIT_PLAN_THUC_SU_goi_VLM…` —
  phep doc AST chi nhan ve trai la MOT ten; `_doc_cac_canh` nay tra ve mot bo
  (`hieu, hong = …`). Sua phep doc, khong sua menh de.
* `tests/test_418_asv_phan_loai_loi.py` — `ThieuBangChungCanh` vao `NGOAI_LE`
  kem ly do, cung khuon voi `ThieuBanBienTap` / `ThieuTieng` (deu ke thua
  `ThieuNguon`, da co trong BANG).
* `tests/test_2051_asv_lat_cat_hang_doi.py` — kich ban cua no co chu y de
  `canh_0002` hong (de chung minh luot 3 KHONG hoi lai no), nen chinh sach do
  phu moi lam lan chay dung o `edit_plan` va moi menh de ve hang doi phia duoi
  khong bao gio duoc chay. Ha nguong **cho rieng phep kiem do** bang
  `monkeypatch`, khong ha o san pham; noi chot nguong la `test_2025`.

## Trang thai bo test cua thanh phan `app:auto_scan_video`

`python -m pytest <94 tep> -q -n 6` (qua `chay_nang.py`):
**1.803 xanh · 3 do · 16 bo qua · 1 xfail** (170 s).

Ba bai do **co truoc nhanh nay**, khong tep nao cua chung nam trong diff:

* `test_448…::test_moi_luot_di_HET_chuoi_giai_doan` va
  `…::test_phien_ban_ENGINE_trong_bao_cao_van_dung_HOM_NAY` — `chep_loi/1` vs
  `chep_loi/2`: dung **F-07** cua `LOI_TONG.md` ("luot that moi tai sinh bao
  cao", dang CHO).
* `test_432…::test_chi_MOT_cho_trong_app_goi_giu_cho` — `thi_hanh.py` goi
  `cache_chung.giu_cho`, den tu merge `5a3fa8d8` (lane `ky-thuat`).

---

# Con lai / can biet

* **Tran do dai khong duoc tuan thu tuyet doi** (3/6 doan ngan viet qua 14-36%).
  Bac thang nan van can. Neu muon di xa hon: do xem mot loi nhac dua **so am tiet
  hien tai cua ban nhap** vao co giup model tu dem khong — chua do.
* **`NHIP["en"] = 2,6` chua do** tren may sinh tieng nay. Cong cu da co che do
  `tts`; chi can 6 doan tieng Anh that.
* **Luot chay dau-cuoi tren phim that chua chay lai** sau ban sua nay — lane nay
  do tung cua that, khong chay lai ca chuoi (ca `edit_plan` moi lan tu choi lan
  `voice_synthesis` moi deu can mot luot nghiem thu). De nghi: lane `nghiem-thu`
  chay lai nen v3 tren nhanh nay va doi chieu `giay_tts` / `giay_llm_nan` /
  `so_canh_hong` / `do_phu_bang_chung` — bon truong nay nay co san trong bao cao.
* **`PHU_BANG_CHUNG_TOI_THIEU = 1.0` doi voi video nhieu canh**: phim nghiem thu
  co 18 canh; mot video 200 canh se nhay cam hon voi mot luot rac con lai sau lan
  thu lai. Neu so do sau nay cho thay ti le hong con ton tai, cho sua la **so lan
  thu lai**, khong phai ha nguong — ha nguong la quay lai chinh cai lo hong im
  lang vua bit.
* Phep do cham vao may B lam khoa pool bi danh `error` **trong CSDL tam cua phep
  do** (`_mo_db` chep khoa sang SQLite tam) — khoa production khong bi dung toi.
  Trong luc do, may B co mot khoang ~15 phut tra `502 upstream_unreachable`
  (`"model":"missing"`); phep do da cho va chay lai.
