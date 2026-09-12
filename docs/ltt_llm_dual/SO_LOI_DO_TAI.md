# SO_LOI_DO_TAI — bo do hai model tren duong that

> Co che chong bo sot. Cau hoi "con loi nao chua xu" tra loi o **day**, khong
> tra loi bang tri nho hay bang cach cuon lai transcript.
>
> **CHAN** = cac tinh huong sau no khong con tin duoc ⇒ sua ngay.
> **DOC LAP** = ghi so, chay tiep, sua theo lo.

| ma | trieu chung ĐO ĐƯỢC | loai | sua o | doi chung | trang thai |
|---|---|---|---|---|---|
| L-01 | qua may A: mot model bi nen lam model KIA cham **2,1-8,1x** | **CHAN** | `platform_core/api_pool.py` | 4 vong sau deploy: **0,99x · 1,08x · 1,15x · 1,10x**; `pg_locks` **0/369** mau | ✅ **DONG 13/09** |
| L-02 | `ltt-3.5` voi `max_tokens <= **200**` tra **RONG** va van bi tinh tien (`mcredit_du` **+4**) | DOC LAP | ban khai may A (cua vao) | 200->rong+4mc; 300->dung; san chan o cua vao | ✅ **DONG 13/09** |
| L-03 | `ltt-3.8` khai *"Text only"* du engine DA nap `mmproj` | DOC LAP | ban khai (may A) | `catalog.HO_SO` co_vision=True ca hai | cho |
| L-04 | bo cham `bia-01` do **su vang mat** -> cau bia dat VA cau lac de deu duoc cham dung | DOC LAP | `tools/do_tai_hai_model.py` | ban cu: 3/3 cau sai -> "dung"; ban moi: 1/3 | ✅ **DONG 13/09** |
| L-05 | **108/131 job loi 14 ngay** deu la `AmbiguousProviderError: mat ket noi sau khi bat dau gui` | DOC LAP | he qua cua L-01 | 48/48 done, 0 loi (p=0,3%) | ✅ **DONG 13/09** |

## L-05 — mot MUC CAN DO, khong phai mot ket luan

Do 13/09 tren `jobs` (14 ngay): `ltt_llm.chat` co **1423 done / 118 error** o cua
so 7 ngay; mo rong 14 ngay thi 131 loi, trong do **108 cung MOT kieu**:

```
AmbiguousProviderError: mat ket noi sau khi bat dau gui
```

Tap trung 08/09 (**64**) va 09/09 (**34**) = 75% tong so. Tu 11/09 khong con job
`ltt_llm.chat` nao.

⚠️ **Gia thuyet — CHUA do:** L-01 lam cac luot xep hang, ma `timeout_s` truyen
   xuong `_goi_openai` la `_con_lai_s(bat_dau_cua, SYNC_BILLED_MAX_SECONDS)` —
   tinh tu luc request **vao cua**, khong phai luc goi. Cho khoa lau ⇒ ngan sach
   con lai ngan ⇒ httpx dut giua chung ⇒ dung lop loi nay.

⛔ **Dung sua theo gia thuyet nay.** No khop qua vua, va phien 12/09 da mat mot
   vong vi dung mot gia thuyet khop qua vua ("khoa advisory theo tai khoan").
   Phep do dung: sau khi deploy ban sua L-01, lop loi nay phai **bien mat** —
   khong phai giam. Neu no chi giam, nguyen nhan la thu khac.

## L-01 — nhung gi da LOAI TRU duoc

| Phep do | Ket qua | Loai tru |
|---|---|---|
| qua may A (Cloudflare) | 1,93x / 6,20x | — |
| qua may A (**loopback** 8100) | 2,09x / 8,11x | khong phai Cloudflare |
| **thang may B** (bo may A) | **0,85x / 1,05x** | **hai GPU DOC LAP — kien truc DUNG** |
| nen bang **tai khoan khac** | 7,15x / 2,36x | khong phai khoa advisory theo tai khoan |
| may B `/health` | `phuc_vu 170 / tu_choi 0`, moi bo dem chan = 0 | may B khong xep hang, khong tu choi |
| may B GPU | dung card sang (5060Ti 82%), VRAM on dinh, CPU-B 9-27% | khong nghen CPU/VRAM may B |
| may A, tien trinh nghe 8100 (pid that, **nang quyen**) | cpu 6-14%, luong 8->15, ket noi 8->12 | **khong CPU-bound**; cac luong dang CHO |

⭐ Ket luan chac chan: **kien truc dual-model khong hong**. Toan bo can thiep cheo
   do **ung dung may A** sinh ra.

## L-01 — GOC, do duoc 12/09 cuoi phien

🔴 **Moi luot chat qua may A giu mot khoa hang PostgreSQL DOC QUYEN tren DUNG
   MOT hang `api_keys` suot ca luot goi model.**

Chuoi su kien, doc thang tu ma:

```
dieu_phoi.goi(db, ...)
  api_pool.chon_key(db, ...)      api_pool.py:195-199
      chon.last_used_at = now
      chon.total_requests += 1
      chon.window_requests += 1
      db.flush()                  <-- UPDATE hang, CHI flush, KHONG commit
  _goi_openai(...)                dieu_phoi.py:296   <-- 3-20 giay goi may B
  api_pool.danh_dau_thanh_cong()  dieu_phoi.py:347   <-- UPDATE hang lan hai
... commit mai o server/api/chat.py::_finish_chat, SAU khi model tra loi
```

PostgreSQL giu khoa hang cua mot UPDATE **toi khi giao dich commit**. Giao dich
o day trum len ca luot goi model. => luot thu hai dung o `chon_key` cho luot
thu nhat xong han.

### Ba su that lam no thanh loi CHEO GIUA HAI MODEL

| | |
|---|---|
| Production co **dung 1 hang** `api_keys` provider `ltt_llm` | do 12/09, `status=active`, `total_requests=923` |
| **Ca hai model** di qua provider ay | `features.chay` -> `model_theo_provider={"ltt_llm": ...}` |
| Hang khoa **khong mang user_id** | nen doi tai khoan khong go duoc — dung nhu da do (7,15x/2,36x) |

### Doi chung (khong phai doc ma — do duoc)

`scratchpad/do_khoa_hang_khoa.py`, PostgreSQL **that** (`lttplatform_test`),
mot hang khoa, hai luong, moi luong `chon_key -> ngu 2s -> commit`:

```
luot1: chon_key mat  0.011s | ca luot  2.014s
luot2: chon_key mat  2.015s | ca luot  4.016s     <-- cho DUNG bang luot1
TONG: 4.017s     song song => ~2.0s | TUAN TU => ~4.0s
PHAN QUYET: TUAN TU HOA
```

### Vi sao no khop voi TAT CA phep do cu

| Phep do cu | Giai thich |
|---|---|
| thang may B: 0,85x/1,05x | khong di qua `api_pool` — khong co hang nao de khoa |
| loopback 8100 van 2,09x/8,11x | khoa nam o may A, khong lien quan Cloudflare |
| tai khoan khac van 7,15x | hang khoa la cua **provider**, khong cua user |
| may B `/health`: tu choi 0 | may B khong he xep hang — luot thu hai chua toi noi |
| pid 8100: cpu 6-14%, luong CHO | luong bi chan tren khoa hang, khong phai CPU |

⚠️ Duong **streaming** (`/api/v1/messages`, `/api/v1/responses` — Claude Code va
   Codex di loi nay) con nang hon: `luong_vlm.mo` goi `chon_key` roi giu giao
   dich suot **ca luong**, khong chi luot goi.

⚠️ `ltt_image` cung co dung 1 hang (`total_requests=2340`) nen job anh tuan tu
   hoa theo dung co che ay — chua do, ghi de khong quen.

## L-01 — BAN SUA (13/09/2026)

`platform_core/api_pool.py`. Mot nguyen tac: **so cua pool khoa khong ky sinh
vao giao dich nghiep vu** — no co giao dich cua chinh no, mo/ghi/commit ngay,
nen khoa hang song vai mili giay thay vi vai chuc giay.

| cho | truoc | sau |
|---|---|---|
| `_ung_vien` | gan len ORM MOI ung vien (tu hoi cooldown, cuon cua so) ⇒ autoflush ⇒ UPDATE ⇒ khoa hang | chi TINH, khong ghi |
| `chon_key` | `+= 1` roi `flush()` | MOT cau UPDATE o ket noi rieng, commit ngay; cuon cua so + tu hoi cooldown **trong chinh cau lenh** (nguyen tu) |
| `danh_dau_thanh_cong` · `danh_dau_loi` | nhu tren | nhu tren |

⛔ Chi ap cho **PostgreSQL**, cung khuon `admission._khoa_resource`. SQLite va
   `db` gia trong test giu duong cu **tung byte** — do la ly do 428 test cua cum
   `api_pool` xanh ma khong phai sua mot dong test nao.

⚠️ Khong sua `danh_dau_thanh_cong`/`danh_dau_loi` thi la **doi cho** nghen chu
   khong go: luot ke tiep se dung o do thay vi o `chon_key`.

### Doi chung

| | ma cu | ma moi |
|---|---|---|
| `tests/test_1234_khoa_hang_api_key.py` | **2 FAILED** (luot 2 cho **8,0s**) | **3 passed** |
| thoi luong ca tep | 18,87s | **3,15s** |

Ca thu ba (`test_bo_dem_van_tang_that`) la **doi chung nguoc**: mot ban sua go
khoa bang cach bo luon phep dem se lam hai ca kia xanh ngay, va lam
`rpm_limit`/`tpm_limit` thanh do trang tri.

### ✅ NGHIEM THU TREN DUONG THAT — 13/09/2026, sau deploy `edfcdd9f`

Deploy may A: `nghiem_thu_deploy.py` bao **lech 0 / thieu 0 / thua 0** doi chieu
`edfcdd9f8a99`; `/health/version` tra dung commit do (`commit_nguon="marker"`).
Ban sua la tep `.py` **duy nhat** khac giua cay va production truoc luc deploy —
bien so co lap.

Do qua `https://app.lttstudios.com`, khoa that, tai khoan `canary.api`:

| vong | nen 3.8 -> do 3.5 | nen 3.5 -> do 3.8 | te nhat |
|---|---|---|---|
| 1 | 0,95x | 0,99x | **0,99x** |
| 2 | 0,94x | 1,08x | **1,08x** |
| 3 | 1,15x | 1,15x | **1,15x** |
| 4 | 1,05x | 1,10x | **1,10x** |

**Truoc ban sua: 2,1x - 8,1x.** Dieu kien dung cua chu san pham (*hai vong lien
tiep trung khop*) dat o vong 1-2, va vong 3-4 xac nhan lai.

🔑 **Bang chung CO HOC, khong chi con so thoi gian.** Sample `pg_locks` +
`pg_stat_activity` 75 giay **trong luc co tai** (369 mau, dinh 2 phien `active`):

```
khoa CHUA duoc cap (granted = false) : khong co mau nao
phien dang CHO tren mot khoa         : khong co mau nao
mau thay chan tren `api_keys`        : 0/369
```

### ⭐ He qua phu KHONG luong truoc: moi luot nhanh gan GAP DOI

Khoa hang khong chi gay can thiep cheo — no lam cham **ca nhung luot don le**,
vi vong tham `/health` cua worker (`job_runner.py:1239`) cung goi `chon_key` tren
dung hang ay vai giay mot lan.

| trung vi luc RANH | truoc (12/09) | sau (13/09) | thang may B |
|---|---:|---:|---:|
| `ltt-3.8` | 3,2 s | **1,85 s** | 1,47 s |
| `ltt-3.5` | 7,2 s | **4,55 s** | 4,12 s |

⇒ Overhead cua may A tut tu **+1,7s / +3,1s** xuong **+0,38s / +0,43s**. Qua may
  A nay gan **bang** goi thang may B — tuc may A khong con them can thiep nao.

### ⛔ Va day la doi chung cho vong 2 cua "kien truc DUNG"

Do thang may B lai 13/09: **0,95x / 0,95x** (vong 1 ngay 12/09: 0,85x / 1,05x).
Hai vong trung khop ⇒ ket luan "hai GPU doc lap" nay co **hai** phep do doc lap.

## Hai lan quy trinh nay SUA TOI

1. Phep do dau ket luan *"hai card can thiep nhau => kien truc hong"*. Goi thang
   may B lat nguoc han.
2. Gia thuyet "khoa advisory theo tai khoan" khop rat vua — co ca dong ma dung
   hinh dang. Doi chung bang tai khoan thu hai **bac bo** no.

Lam theo loi cu — thay 6,2x, doc ma, tim ra khoa, sua, deploy — la sua **nham
cho** va tin la xong.

## L-02 — da khoanh 13/09/2026, va SO CU SAI O BA CHO

Do qua `https://app.lttstudios.com`, khoa that, quet `max_tokens` 100..800:

| model | max_tokens | noi dung | token_ra | finish | mcredit |
|---|---:|---|---:|---|---:|
| `ltt-3.5` | 100 | **RONG** | 100 | `length` | — |
| `ltt-3.5` | 200 | **RONG** | 200 | `length` | **+4** |
| `ltt-3.5` | 300 | dung | 294 | `stop` | — |
| `ltt-3.5` | 600 | dung | 337 | `stop` | +6 |
| `ltt-3.8` | 100..800 | dung | 63 | `stop` | +25 |

### Ba dinh chinh voi ban ghi cu

| so cu ghi | do duoc |
|---|---|
| rong khi `max_tokens <= 300` | rong khi **<= 200**; o 300 tra loi **DUNG** |
| "model tra rong" | `token_ra` = **dung bang** `max_tokens`, `finish_reason=length` ⇒ model **sinh du**, nhung la SUY NGHI, bi cat truoc khi toi cau tra loi |
| loi o "may B / ban khai" | may B lam **dung**: sinh het tran roi dung. Cho sua nam o **cua vao may A** |

### 🔴 "Van bi tinh tien" — DUNG, va phep do dau tien cua toi suyt bac bo no

Doc `credit` (so nguyen) truoc/sau: **0**. Ket luan "khong bi thu" la **SAI**.
`thanh_toan._cong_du` (C3) **chi thu phan NGUYEN** va don phan le vao
`users.mcredit_du`. Do lai dung tang:

```
luot RONG (3.5, 200 tok):  credit_charged=0  MA  mcredit_du +4
```

⇒ Khach tra 4 mcredit va nhan mot chuoi **rong**.

⛔ Bai hoc: **san lam tron la mot tang khac voi bang gia**. Doc sai tang thi ca
   hai chieu ket luan deu sai duoc — o day no suyt bien mot loi tien THAT thanh
   "khong co gi".

### Vi sao no KHONG phai "may B hong", va ban sua phai o dau

Hanh vi hien tai **dung chuan OpenAI**: `finish_reason=length` + content rong la
cach chuan bao "het tran truoc khi xong". Cai sai la nen tang **biet truoc** model
nay co `--reasoning-budget` (L-15/L-16) ma van nhan mot `max_tokens` khong the
nao du, dot GPU, thu tien, roi tra rong.

⇒ Sua **o cua vao**, cung khuon 413 cua input qua dai: `max_tokens` duoi nguong
  kha thi cua model ⇒ tu choi NGAY, khong dot GPU. Nguong phai **do nhieu lan**
  chu khong lay tu mot luot — `token_ra` cua 3.5 do duoc 294/298/345/284/288 o
  cac muc khac nhau, tuc no **ngau nhien**; mot nguong dat theo mot luot se sai.

### Nguong do that: 5 luot moi o, 0 luot rong

| model | `none` | `low` | `medium` | `xhigh` |
|---|---:|---:|---:|---:|
| `ltt-3.5` token_ra max | 4 | 350 | 517 | 476 |
| `ltt-3.5` SAN chot | 64 | 512 | 1024 | 1024 |
| `ltt-3.8` token_ra max | 4 | 63 | 63 | 55 |
| `ltt-3.8` SAN chot | 64 | 64 | 64 | 64 |

🔴 **HAI MODEL TIEU KHAC NHAU 6 LAN** cho cung mot cau hoi mot dong. Nen san
   phai theo **model x muc**, khong phai mot bang chung: mot bang chung lay so
   cua model ton nhat va **phat oan** model kia -- `ltt-3.8` tra loi DUNG o
   `max_tokens=100`, va hang chuc phep kiem khap kho gui dung con so ay.

⛔ **Hai quy tac dat san, khac nhau co chu y.** Model DA THAY hong (`ltt-3.5`)
   lay do-duoc x ~2, vi cau do la cau MOT DONG con cau kho suy nghi nhieu hon.
   Model CHUA thay hong (`ltt-3.8`) lay dung so do duoc, KHONG nhan bien -- bien
   o day khong mien phi, no **tu choi luot hop le**, va chi duoc tra bang luot
   hop le khi ta DA thay thiet hai no ngan.

### Va mot khuyet tat thu hai, lo ra tu chinh ban sua

San dat dau tien trong `features.kiem_tham_so`, tuc trong `executor.validate` --
ma `validate` chay **TRUOC** khoi 413 o `server/api/chat.py`. Hau qua: mot hoi
thoai 65K token xin `max_tokens` thap bat dau nhan **400 thay vi 413**.

🔴 Do la mot buoc lui THAT. Codex va Claude Code dua dung vao ma **413** de TU
   NEN hoi thoai; doi no thanh 400 la lay mat duong tu chua cua client, doi lay
   mot loi khuyen ("nang max_tokens len") vo nghia voi mot hoi thoai du sao cung
   qua dai.

✅ San nay tach thanh `features.kiem_san_token_ra`, goi tu `chat.py` **sau**
   khoi 413. Chot o hai tang: `test_1239` (cau truc) va `test_259` (HTTP that,
   mot yeu cau vi pham CA HAI dieu cung luc phai nghe 413).

### ⚠️ Gioi han cua ban sua nay -- doc truoc khi tin no

San chan mot tran **hien nhien qua thap**. No **KHONG** bao dam khong con luot
rong: nguong do bang mot cau hoi MOT DONG, con cau kho tieu nhieu token suy nghi
hon, nen `max_tokens` ngay tren san van co the rong. Thu duoc dong hoan toan la
*"tran thap den muc chac chan hong"*; phan con lai (`finish_reason=length` +
rong) van can mot cau tra loi ro o tang phan hoi.


## L-04 — DONG 13/09/2026, va loi SAU HON mot lan quen dich

So cu ghi: *"bo cham cam chuoi tieng Viet, model tra loi tieng Anh -> diem dung
gia"*. Dung, nhung do moi la trieu chung.

`bia-01` cham kieu `khong_chua`: **sai** neu chua chuoi bia dat, **dung** neu
khong chua. Tuc no do **SU VANG MAT** — va kho nay da ghi bai hoc do
(`banh-coc-do-su-vang-mat-thi-xoa-cung-xanh`).

### Doi chung: ban CU vs ban MOI tren cung ba cau

| cau | ban CU | ban MOI |
|---|---|---|
| `The capital of Wakanda is Birnin Zana.` | **dung** | sai |
| `Toi khong biet.` | **dung** | sai |
| `Wakanda is a fictional country.` | dung | dung |

⇒ Ban cu cham **ca ba** la dung — ke ca cau bia dat VA cau lac de. Mot ban sua
  chi *them chuoi cam tieng Anh* se sua duoc dong dau va **van de lot dong hai**.

### Ban sua: doi sang menh de DUONG

Kieu cham moi `khong_bia` co HAI ve:

* **duong** — cau tra loi PHAI chua mot dau hieu noi rang Wakanda khong co that
  (`khong co that`, `hu cau`, `fictional`, `does not exist`, `marvel`, ...);
* **am** — va khong duoc khang dinh mot thu do nhu that (nay co ca tieng Anh).

Vang mat khong con la bang chung; phai co mat mot dau hieu.

### 🔑 Va mot khoang trong lon hon da lo ra

`tools/do_tai_hai_model.py` — thu ta dung de **phan xu hai model** — truoc hom
nay **khong co mot phep kiem nao**. Do la ly do L-04 lot duoc.

**Mot cong cu do ma khong ai do lai no thi khong phai mot cong cu do.**

Ghim: `tests/test_1237_bo_cham_do_tai.py` (14 ca), trong do bon ca `cau LAC DE
van SAI` la thu phan biet ban sua that voi ban sua chi them chuoi.

## L-02 — GOC va BAN SUA (13/09/2026). Mot phan da dong, mot phan CON MO.

### Goc: template CHINH THUC hardcode `xhigh` — khong phai "khach dat tran thap"

Phep do PHAN BIET chi ra dich danh:

```
ltt-3.5  reasoning_effort = None / low / xhigh  ->  token_ra 250/250/250, RONG ca ba
ltt-3.8  cung ba gia tri                       ->  token_ra  63/ 63/ 62, dung ca ba
```

Tham so cua khach KHONG doi duoc gi o 3.5 => co thu khac ghi de no. Khac biet duy
nhat luc ay: 3.8 dung template froggeric, 3.5 dung template chinh thuc trong GGUF.

[nguon] `froggeric/Qwen-Fixed-Chat-Templates` mo ta dung loi nay tung chu:
*"Official `xhigh` default burns token budgets with zero content returned"*.
Model card Qwen: khuyen **32.768** token ra, va co **HAI nut rieng** —
`max_tokens` (do dai) vs `enable_thinking=False` (tat suy nghi).

⇒ Ha `max_tokens` KHONG phai cach tat suy nghi. Ban sua o cua vao (dat mot san
  `max_tokens`) la sua nham tang, va no con cuop mat cua khach mot tham so hop le.

### Da lam

1. `qwen35-api` dung `--chat-template-file chat_template_v22.5.jinja` (tep RIENG;
   3.8 giu v22.3 dang chay tot — mot bien so moi lan).
2. `reasoning_effort` mo them **`none`** o ca ba cho khai.

### Do sau khi sua — deploy ca hai may, nghiem thu 0/0/0

| model | effort | max_tokens | token_ra | ket qua |
|---|---|---|---|---|
| `ltt-3.5` | **none** | 100 · 200 | **4 · 4** | **dung** |
| `ltt-3.5` | low | 100 · 200 | 100 · 200 | **rong** |
| `ltt-3.8` | **none** | 100 · 200 | **4 · 4** | **dung** |
| `ltt-3.8` | low | 100 · 200 | 63 · 63 | dung |

`none` giam token ra **50 lan** (200 -> 4) va tra loi dung ngay o `max_tokens=100`.

### 🔴 CON MO — va toi da DOAN SAI mot lan o day

Toi doan ban va v22.5 se chua luon `low` tren 3.5. **Khong**. Voi `low`/`medium`,
`ltt-3.5` VAN tieu dung bang `max_tokens` va tra rong.

⇒ Phan con lai cua L-02: mot khach dung `low`/`medium` (hoac khong khai gi) voi
  `max_tokens` thap VAN nhan rong va VAN bi thu mcredit. Hai duong co the:

  * canh bao/tu choi o cua vao khi `max_tokens` thap VA thinking dang bat; hoac
  * tra loi RO khi `finish_reason=length` + content rong, thay vi 200 im lang.

⚠️ Chua chon duong nao — can do them va doi chieu nguon truoc (hop dong §1b).

## L-05 — do duoc lan dau tren cua job (13/09/2026)

### Vi sao truoc do khong do duoc

108/131 loi deu la dong trong bang `jobs`. Moi phep do cua phien nay di qua cua
**sync** (`/chat/completions`) nen khong sinh mot dong `jobs` nao — bang van dung
o 10/09, va *"khong co loi moi"* khong phai bang chung gi ca. Phai tao job THAT.

⛔ Cua job co **ba** buoc, khong phai mot: `POST /quotes` -> `POST /jobs` (kem
   truong **`quote`**, khong phai `quote_token`) -> `GET /jobs/{id}`.

### Ket qua

| | 08/09 (truoc sua L-01) | 13/09 (sau sua) |
|---|---|---|
| `ltt_llm.chat` | 490 done / **64 error** (11,6 %) | **6 done / 0 error**, `attempts=0` |

6 luot dong thoi — dung dieu kien tai tung sinh ra lop loi ay — va no **khong
xuat hien**.

⚠️ **6 la it.** Day la mot dau hieu, chua phai mot ket luan. Muon chot thi can
   mot lot lon hon, hoac cho luu luong that quay lai.

### Va mot loi cua chinh BO DO, giu lai vi no suyt doc nham

Bo do bao **"6/6 het gio"** sau 240 s, trong khi CSDL cho thay ca sau `done` luc
03:03:48 — tuc chung xong trong vai giay. Bo do doc sai ten truong trang thai
trong phan hoi `GET /jobs/{id}` nen khong bao gio thay `done`.

⇒ Neu tin bo do, ket luan se la *"cua job treo"* — mot su co nghiem trong khong
  he ton tai. **Doc CSDL truoc khi tin mot bo do minh vua viet.**


## L-05 — DONG 13/09/2026 o co mau du de bac bo

### Vi sao 6 luot khong noi duoc gi, va con so chung minh dieu do

Moc: 08/09 co **64 loi / 490 done = 11,6 %**. Neu lop loi ay VAN con nguyen ti
le ay thi xac suat quan sat duoc 0 loi tren N luot la `0,884 ** N`:

| N | xac suat thay 0 loi neu KHONG co gi thay doi |
|---:|---:|
| 6 | **47 %** |
| 20 | 8,2 % |
| 30 | 2,4 % |
| 48 | **0,3 %** |

⇒ "0 loi tren 6 luot" **hoan toan phu hop** voi gia thuyet *khong co gi thay
  doi*. No khong phai bang chung yeu — no khong phai bang chung.

### Ket qua o N = 48

| | 08/09 (truoc sua L-01) | 13/09 (sau sua, N=48) |
|---|---|---|
| `ltt_llm.chat` | 490 done / **64 error** (11,6 %) | **48 done / 0 error** |
| hai nguon doc lap | — | mat client **va** bang `jobs` deu cho 0 |
| thoi gian moi job | — | chay 1,6–2,8 s; cho hang doi 1,3–12,8 s |

8 dot x 6 job dong thoi, 156 s. Xac suat thay ket qua nay neu ti le cu con
nguyen: **0,3 %** ⇒ bac bo o muc y nghia 5 %.

⚠ **Pham vi cua ket luan.** No noi *lop loi ay khong con xuat hien o tai 6
   luong dong thoi*. No **khong** noi he thong khong bao gio loi nua, va cung
   khong chung minh L-01 la nguyen nhan DUY NHAT — chi rang sau khi sua L-01,
   dieu kien tung sinh ra 64 loi/ngay khong con sinh ra loi nao.

### Va lop bo do noi doi ve production — LAN THU BA

| lan | bo do bao | su that |
|---|---|---|
| 1 | "6/6 het gio" | CSDL: ca 6 `done` trong vai giay |
| 2 | "30/30 loi 400 Missing required field" | hinh dang `/quotes` toi tu doan sai |
| 3 | "2/2 het gio" | CSDL: ca 2 `done` luc 04:08:07 |

**GOC CHUNG, va lan nay tim ra no:** API cong khai va CSDL dung **hai bo tu vung
khac nhau** cho cung mot trang thai.

```
API   GET /api/v1/jobs/<id>   ->  "queued" -> "succeeded"
CSDL  bang `jobs`.status      ->  "queued" -> "done"
```

Bo do cho chu `done` **tren API**. Chu ay khong bao gio den.

⛔ Ban sua khong phai "them `succeeded` vao danh sach". Liet ke tap **da xong**
   la cach cu, va no im lang truot moi trang thai moi: mot `failed` chua tung
   gap se bi doc thanh "van dang chay" cho toi khi het gio — dung cai bay tren.
   Nay dinh nghia tap **CHUA XONG** (`queued`, `running`, …) va coi MOI thu
   khac la ket cuc.

⭐ Va bang `jobs` khai bang `app_slug` + `job_type`, **khong** co cot `tool`;
   `job_type` mang gia tri day du `ltt_llm.chat`, khong phai `chat`. Toi doan ca
   hai va truy van vo hai lan lien tiep. **Hoi luoc do truoc khi truy van** la
   mot buoc, dung bo qua no.
