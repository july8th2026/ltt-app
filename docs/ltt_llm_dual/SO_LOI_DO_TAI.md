# SO_LOI_DO_TAI — bo do hai model tren duong that

> Co che chong bo sot. Cau hoi "con loi nao chua xu" tra loi o **day**, khong
> tra loi bang tri nho hay bang cach cuon lai transcript.
>
> **CHAN** = cac tinh huong sau no khong con tin duoc ⇒ sua ngay.
> **DOC LAP** = ghi so, chay tiep, sua theo lo.

| ma | trieu chung ĐO ĐƯỢC | loai | sua o | doi chung | trang thai |
|---|---|---|---|---|---|
| L-01 | qua may A: mot model bi nen lam model KIA cham **2,1-8,1x** | **CHAN** | `platform_core/api_pool.py` | 4 vong sau deploy: **0,99x · 1,08x · 1,15x · 1,10x**; `pg_locks` **0/369** mau | ✅ **DONG 13/09** |
| L-02 | `ltt-3.5` voi `max_tokens <= 300` tra **RONG** va van bi tinh tien | DOC LAP | may B / ban khai | 300->rong, 600->"391" | cho |
| L-03 | `ltt-3.8` khai *"Text only"* du engine DA nap `mmproj` | DOC LAP | ban khai (may A) | `catalog.HO_SO` co_vision=True ca hai | cho |
| L-04 | bo cham `bia-01` cam chuoi tieng Viet, model tra loi tieng Anh -> **diem dung gia** | DOC LAP | bo do | — | cho |
| L-05 | **108/131 job loi 14 ngay** deu la `AmbiguousProviderError: mat ket noi sau khi bat dau gui` | CAN DO | chua ro | chua co | **chua phai phat hien** |

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
