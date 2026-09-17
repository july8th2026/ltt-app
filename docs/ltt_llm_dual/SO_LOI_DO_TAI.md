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
| L-06 | cua DONG BO khong huy duoc: khach cat ket noi ma slot van bi giu toi khi sinh XONG | DOC LAP | HAI goc: thieu `ma_luot`, va `is_disconnected()` chet sau `BaseHTTPMiddleware` | loopback 16,54 -> **1,43 s**; qua Cloudflare van 16,8 s | **DONG o tang ma; con phan BIEN** |
| L-07 | **MOT job anh la ha `ltt-3.8` VINH VIEN**: trong tai nha LLM roi ket o `nha_llm` | DOC LAP | cong render may B thieu `/v1/nha_comfy` (404) + `nha_llm` khong co duong lui | chu trinh di tron 182 s; huy giua chung lui trong 30 s | **DONG 13/09** |
| L-08 | cua STREAM giu suat **>=643 s** sau khi khach cat: may B ranh ma suat van bi chiem | DOC LAP | **KHONG phai mot khuyet tat — la BA lop don cung hong.** Starlette khong bao gio `aclose()` than phan hoi (`responses.py:250`); `BackgroundTask` khong duoc `shield` (`Kludex/starlette#1438`, ta co 4 tang `BaseHTTPMiddleware`); va nhip tim dap VO DIEU KIEN nen `reclaim_expired` khong bao gio khai hoa | truoc va >=643 s; sau ban va 1 van ~225 s; lease van dap nhip trong khi may B `requests_processing=0` | 🟡 **BA LOP DA DUNG 13/09 — cho nghiem thu may that** |
| L-09 | **nam anh hong la TAT MODEL NHA**: yeu cau sai cua khach bi dem la loi cua KHOA | 🔴 **CHAN** | `CongVlmError` khong mang ma; `dieu_phoi` khong truyen `http_status` | may B tra 400 dung chuan, may A tra 503 va phat khoa | **DONG 13/09** |
| L-10 | **ban va L-07 tu sinh ngo cut moi**: 3 lan ComfyUI hong la phia anh khoa ngoai VINH VIEN | DOC LAP | bo dem chi xoa sau `chay_comfy()` thanh cong — thu nam sau chinh cai phanh dang chan | ComfyUI da LANH, ca 4 dich vu may B song: residency dung im o `llm` **120 s**, job `queued` | **DONG 13/09** |

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

### NGHIEM THU sau deploy -- va mot cho toi da ket luan SAI

| duong | truoc | sau |
|---|---:|---:|
| **loopback** (thang may A) | 16,54 s | **1,43 s** -- DAT (nguong 2 s) |
| **qua Cloudflare** | 18,67 s | 16,82 s -- van vuot |

Ban sua o tang ung dung **chay dung**: 1,43 s tren duong truc tiep.

⛔ **Va day la cho toi ket luan sai.** Truoc do toi do ca hai duong, thay ca hai
   deu ~17 s, roi ket luan *"Cloudflare khong phai nguyen nhan"*. Sai: luc ay
   **loi tang ung dung dang hong ca hai duong**, va no CHE MAT khac biet mang.

   Mot phep do phan biet chi phan biet duoc khi cac nguyen nhan kia DA BI LOAI.
   Dung no de **loai** mot nguyen nhan khi con nguyen nhan khac dang tron la
   dung sai chieu — no chi chung minh "co mot loi khac", khong chung minh
   "nguyen nhan nay vo can".

### Phan con lai: bien Cloudflare, khong sua duoc o tang ma

`cloudflared` dang chay **2026.7.3** (build 22/07/2026) -- moi, da qua TUN-6427
tu lau, nen khong phai chuyen phien ban. Voi mot request KHONG stream, bien
Cloudflare khong bao cho origin biet khach da di; origin chay toi het.

⚠️ **Chua ket luan duoc cho cua STREAM.** Khach that (Codex, Claude Code) dung
   `/api/v1/messages` va `/api/v1/responses`, va o do byte chay lien tuc nen mot
   luot ghi hong LA tin hieu origin thay duoc. Toi da thu do nhung bo do cua toi
   sai o vong dem thoi gian (bao "sau 120 s lease chua ve" trong khi doc lai
   CSDL thay lease = 0 va so sach da quyet toan). **Chua co so** -- va mot con
   so tu mot bo do da lo ra sai thi khong duoc ghi vao day.

## L-09 -- DONG 13/09/2026, CHAN: nam anh hong la tat model nha

Tim ra khi chay cong N, tinh huong *"Tep anh hong"* (§22).

### Do duoc

Gui bon kieu anh hong qua `/api/v1/chat/completions`:

| kieu hong | may A tra | spec §22 doi |
|---|---:|---|
| base64 rac | 503 | 4xx |
| PNG cut dau | 503 | 4xx |
| rong | 503 | 4xx |
| base64 sai cu phap | 503 | 4xx |

Ve THU HAI cua §22 -- *"khong lan sang slot khac"* -- **DAT**: 3/3 luot lanh
manh chay song song van 200 kem noi dung.

Va may B tra **dung chuan**:

```
400 {"error": {"code": 400, "type": "invalid_request_error",
               "message": "Failed to load image or audio file"}}
```

### Goc, va no nang hon mot ma trang thai sai

`cong_vlm.chat()` co bang phan loai rieng cho 429, 499, 413, 404, 504 — **400
roi vao nhanh catch-all** `CongVlmError`. Va `CongVlmError` **khong mang ma**,
nen `dieu_phoi` goi:

```python
api_pool.danh_dau_loi(db, key)      # khong co http_status
```

`danh_dau_loi` doc `http_status=None` thanh *"5xx hoac loi mang"*:

```python
else:
    moi["error_count"] = int(key.error_count or 0) + 1
    if moi["error_count"] >= ERROR_TO_STATUS_THRESHOLD:   # = 5
        moi["status"] = APIKEY_ERROR
```

Va `APIKEY_ERROR` **khong tu hoi** (`_ung_vien` bo moi khoa `status != ACTIVE`;
chi `COOLDOWN` tu ve).

🔴 **Tuc mot khach gui nam anh hong la tat model nha cho toi khi co nguoi
   sua tay.** Bat ky ai co khoa API deu lam duoc, ke ca vo tinh.

⭐ Va chinh `danh_dau_loi` DA co nhanh dung: *"400 <= s < 500: Bad request CUA
   TA — KHONG phat"*. Loi khong nam o luat. No nam o mot **tham so khong duoc
   truyen** — va do la ly do no song sot qua moi lan doc ma.

### Day la CUA THU BA cua cung mot tham hoa D-005

```
luat 1 (dau cong_vlm.py)   bit cua 429
ban va 09/09               bit cua 504
cua 400                    dung mo toi 13/09
```

### Ban sua

- `CongVlmError` mang `ma` (ma HTTP thuong nguon).
- Them `YeuCauSaiError(CongVlmError)` cho 400/422: **khong phat khoa**, va
  **khong cascade** — gui lai y het mot yeu cau sai thi no sai y het (cung khuon
  `ProviderOomError`).
- `dieu_phoi` truyen `http_status=e.ma` xuong `danh_dau_loi`.
- Cua dong bo tra **4xx** kem thong diep cua thuong nguon: *"Failed to load image
  or audio file"* la thu khach sua duoc, con *"The model could not serve this
  request"* thi khong noi cho ho biet gi ca.

### Chot, va mot dot bien DA LOT o lan dau

`test_1244` (8 phep) + hai phep moi trong `test_255`. Tiem ba dot bien:

| dot bien | bat duoc? |
|---|---|
| bo nhanh 400/422 khoi `cong_vlm` | CO |
| bo `YeuCauSaiError` khoi nhanh `raise` | CO |
| **bo `http_status=` khoi `dieu_phoi`** | **ban dau KHONG** |

Ban chot dau chi do `danh_dau_loi` truc tiep voi ma truyen tay, nen no khong
canh duoc **ben goi**. Them `test_255::test_ma_thuong_nguon_di_toi_danh_dau_loi`
— dung mot loi 404 that di qua `dieu_phoi.goi` — thi dot bien ay bi bat.

⛔ Bai hoc: mot phep kiem cho `danh_dau_loi` khong the canh duoc loi cua NGUOI
   GOI no. Loi o day chua bao gio nam trong `danh_dau_loi`.

## L-12b -- DONG (ma) 17/09/2026: tran TOKEN cua phong cho CHONG len luat ngan sach

Chu du an chot 17/09: LTTCODE phai chay phien ~150K token, *"chap nhan cham de lay
chat luong"*. Ban va 13/09 duoi day chi noi cho MOT mon lon; tran 57.000 van la
luat THU HAI cho cung cau hoi *"co vua khong"*.

### Do / kiem duoc tren ma `main` (c80876a3), khong phai suy

| phong cho dang co | luot moi | ket qua cu |
|---|---|---|
| mot whale 68K dang cho | **10 token** | **429** `phong_day_token_prefill` |
| mot whale 68K dang cho | 70K | **429** `phong_day_mot_mon_lon` |

Va hai ca o luat nhan (`luat_nhan.xet`):

- **Khong co backfill**: luot dung truoc chua vua pool KV thi `XEP_SAU` chan MOI
  luot sau, ke ca luot vua pool (vi du chu du an: 15K+100K dang chay, 110K cho,
  55K toi sau -> cu: 55K cung cho).
- **Whale ket sau whale** cho >30 s thi `WHALE_CHAN` MOI luot khac suot luot whale
  dang chay (~4,5 phut cho 150K) — chan khong mua duoc gi.

### Ban do cac luat (truoc -> sau)

| cau hoi | noi | truoc | sau |
|---|---|---|---|
| vua cua so model? | `luong.tien_kiem` (413) | `input_cap` 171.458 | giu nguyen |
| hang co vo han? | `phong_cho.kiem_phong` (429 truoc 200) | so nguoi 32 **+ Σ token MOI dang cho ≤ 57.000** | so nguoi 32 + **so whale cho ≤ 2** |
| vua pool KV (`-kvu`)? | `luat_nhan` luat 2 | Σ `token_dat_truoc` dang chay + luot ≤ pool | giu nguyen — **luat nhan chinh** |
| so chuoi dong thoi | `luat_nhan` luat 1 | 3 (= `-np`) | 3, **env ha duoc** `LTT_ADMISSION_SO_SUAT__<resource>` |
| cong bang prefill | `luat_nhan` luat 5 + cong may B | ≤1 whale chay | giu nguyen; whale ket sau whale khong chan ai |
| thu tu | `luat_nhan` luat 6 | FCFS chat | FCFS + **backfill co chan** 120 s (`LTT_LLM_CHO_BACKFILL_S`), qua thi `NHUONG_LUOT_LON` |
| cho toi da cua stream | `luong_co_cho` | 300 s moi luot | 300 s thuong / **900 s whale** (`LTT_LLM_CHO_STREAM_WHALE_S`) |

⭐ `token_dat_truoc` = token vao uoc (uoc CAO: 2,5 ky tu/token) + `max_tokens` da
   kep + 2.048 dem + anh. `max_tokens` bao ca token suy nghi (`--reasoning-budget`
   chi cat BEN TRONG `n_predict`: `server-context.cpp` `has_budget()` dem `n_gen`),
   nen khong cong them budget suy nghi lan nua. Pool = `-c` cua engine; bien an
   toan nam o tung luot (dem + uoc cao), va ha pool duoc bang
   `LTT_ADMISSION_POOL__<resource>` khong can deploy ma.
⭐ `-kvu` that su cho mot chuoi dung toi ca `-c`: `llama-context.cpp`
   `if (cparams.kv_unified) n_ctx_seq = n_ctx` (ggml-org/llama.cpp master).

### Chot bang phep kiem, co doi chung

`test_1203`: vi du chu du an; doi chung 110K sau khong backfill; chong bo doi
(ca bo chan backfill ⇒ luot lon CHET DOI, co chan ⇒ nhan trong 120 + 100 s);
khong bao gio nhan vuot pool/so suat tren 3 mo phong. 4 ca DO tren luat cu.
`test_1250`: phong cho khong con tran token; tran so whale; hai num cau hinh doc lap.

### Con mo — KHONG nam trong ma nay

1. 🔴 **Adapter LTTCODE (`D:\LTTCODEAPP\plugins\llm-ltt\src\adapter.ts:285`)
   khong thay nhip tim.** `withIdleTimeout` dem SU KIEN tu `EventSourceParserStream`
   (eventsource-parser 3.1.1), ma dong chu thich SSE (`: ltt-cho`, `: keep-alive`)
   di vao `onComment`, KHONG duoc `enqueue`. Cho hang + prefill 150K (~230 s) de
   vuot 300 s ⇒ adapter tu cat. Sua ben LTTCODE: truyen `onComment` de dat lai
   dong ho (hoac do dong ho tren byte tho).
2. Tai su dung cache prompt: llama.cpp da tu chon slot theo LCP
   (`--slot-prompt-similarity` mac dinh 0,1) va co cache RAM (`--cache-ram` mac
   dinh 8.192 MiB, PR #16391). **Khong** ghim `id_slot`: ggml-org/llama.cpp#28139
   (ghim vao slot rong bo qua cache), #27148 (cache RAM khoi phuc noi dung hoi
   thoai KHAC duoi tai dong thoi — can doi chieu ban b10883 dang chay).
3. `uoc_moi` (ai la whale) nho trong tien trinh; slot bi thay thi prefill that
   150K ma may A tuong nho — chi lech THU TU, khong lech an toan KV.

## L-12 -- MO 13/09/2026: request PREFILL LON bi DUOI khi co nguoi khac cho

Tim ra o kich ban J10 cua ma tran test job dai.

### Do duoc — co DOI CHUNG

Cung MOT request (prefill ~67.989 token, duoi tran vao 171.458 cua ltt-3.8):

| phong cho | ket qua |
|---|---|
| co nguoi dang cho | **429** `concurrency_limited` sau 0,48 s |
| **trong** | **200**, chay tron, TTFB 71,3 s |

⇒ Request ay HOAN TOAN hop le voi model. No bi duoi **chi vi co nguoi khac
  dang cho**. Day la BO DOI request lon, khong phai gioi han suc chua.

### Co che

`phong_cho.kiem_phong`:

```python
if song and sum(w.token_prefill_moi for w in song) + token_prefill_moi > token_prefill_toi_da:
    raise PhongDay("phong_day_token_prefill")
```

Gia tri that dang chay:

```
nguong_whale             = 16.384
token_prefill_cho_toi_da = 57.000     <- tran CUA CA PHONG
tran vao ltt-3.8         = 171.458    <- thu nen tang QUANG CAO
```

🔴 **Mot request lon hon tran CUA CA PHONG thi khong bao gio vao duoc**, bat ke
   cho bao lau — vi `sum(...) + token_prefill_moi` luon vuot ngay khi `song`
   khong rong. Menh de `if song and` chi hoan lai toi luc co nguoi thu hai.

⛔ Va cau chu tra ve noi sai ban chat: *"The requested execution resource is
   busy. Retry later"*. Retry KHONG giup neu luon co nguoi cho. Khach doc "ban,
   thu lai" roi thu mai, trong khi thu that su chan ho la MOT TRAN HO KHONG
   DUOC BIET (57.000, trong khi tai lieu noi 171.458).

### Vi sao dang ke voi san pham

Codex / Claude Code gui hoi thoai dai; 57.000 token la muc RAT de cham. Nghia la
dung luc he dong khach nhat (co nguoi cho) thi khach dung nhieu ngu canh nhat
lai bi duoi dau tien — nguoc voi thu ta muon ban.

### Huong sua — CHUA CHOT, can tra cong dong truoc

Luat chung cua admission control: **mot tran TONG khong duoc phep loai tru vinh
vien mot muc don le von hop le**; neu khong thi muc lon bi bo doi. Vai huong:

1. Tran hieu luc = `max(token_prefill_cho_toi_da, token_prefill_moi)` — mot
   nguoi cho lon van vao duoc, nhung chi MOT.
2. Hang rieng cho whale, phuc vu xen ke theo tuoi cho.
3. Giu nguyen tran nhung doi 429 thanh 413 + `limit_value` THAT, de khach biet
   con so that ma nen ngu canh xuong.

⚠️ Chua chon. Bay 13/09: ban va dau cua L-11 cung la do toi tu suy, va tra
   Kubernetes Lease API xong moi thay huong khac tot hon.

## L-11 -- MO 13/09/2026: deploy giet stream => MAT TOI 20 PHUT SUC CHUA

Tim ra khi chay ma tran test job dai (kich ban J4, bao hoa 6 job). Mot deploy
chay giua luc sau luot stream dang chay, va sau do:

```
tong lease: 6          <- TOAN BO suc chua (3 moi card)
lay   20:20:20         nhip cuoi 20:20:20   im 516 s
```

### Co che

Lease `mode=stream` duoc giu boi mot GENERATOR TRONG TIEN TRINH web, va nhip tim
cua no la mot luong trong chinh tien trinh ay. Deploy dung dich vu => tien trinh
chet => luong nhip chet theo => **dong lease nam lai**. `reclaim_expired` chi
chay khi co ai do `acquire`, va chi don khi nhip da cu hon `ORPHAN_TIMEOUT = 20
phut`.

⇒ **Deploy giua luc co stream dang chay = mat toi 20 phut suc chua LLM.** Khach
  that goi vao trong cua so ay bi xep hang sau nhung cai xac.

⚠️ Khong lien quan L-08 va khong phai hoi quy cua no: L-08 la khach CAT, o day
   la MAY CHU chet. Ban va ba lop cua L-08 khong cham toi ca nay, vi ca ba lop
   deu chay TRONG tien trinh da chet.

### Ban va — va vi sao no don gian den the

Mot lease `mode=stream` **khong the song qua mot lan khoi dong lai tien trinh**,
khong co ngoai le nao can xet. Nen:

⇒ **Luc ung dung KHOI DONG, xoa sach moi lease `mode='stream'`.**

Dieu kien da KIEM (khong phai gia dinh):

| | |
|---|---|
| `setup/2-cai-dat.ps1:950` | `-m uvicorn server.run:app` — **khong** `--workers` |
| `netstat` cong 8100 | **1** tien trinh LISTENING |
| don lease luc khoi dong | **chua co** |

⛔ Neu mot ngay nao do nen tang chay NHIEU tien trinh web, luat nay phai hep lai
   theo `holder_id` — mot tien trinh khoi dong lai khong duoc xoa lease cua tien
   trinh khac. Phep kiem cua ban va phai chot dieu kien nay, khong chi chot hanh vi.

## L-08 -- MO 13/09/2026: cua STREAM giu suat >= 643 giay sau khi khach di

> ### ⭐ CAP NHAT 13/09 — loi giai, va mot loi thu nhan
>
> **Ba ban va dau deu hong vi cung mot ly do**: ca ba treo viec nha mot suat GPU
> vao mot cho ma Starlette **khong he bao dam**. Doc mot lan roi dung doc lai:
>
> | nguon (tra duoc) | no noi gi |
> |---|---|
> | `starlette/responses.py:250` (1.3.1) | than phan hoi chi `async for`, **khong bao gio `aclose()`** ⇒ `finally` cua async generator chay khi Python THU GOM. Do that: **~225 s** |
> | `starlette/background.py` (1.3.1) | `BackgroundTask.__call__` **khong** `CancelScope(shield=True)` |
> | `Kludex/starlette#1438` | background bi huy khi khach cat — tac gia chot: **chi khi co it nhat mot `BaseHTTPMiddleware`**. Ta co **bon** tang |
> | `Kludex/starlette#3458` (dong 06/09/2026) | thoi diem chay background duoi middleware VAN lech hop dong tai lieu; **5 PR, khong PR nao duoc gop** |
>
> ⛔ **THU NHAN.** Ban truoc cua muc nay va cua docstring `bat_dong_bo_hoa` trich
>    `fastapi/fastapi#7572` va `Kludex/starlette#2866` nhu "doi chieu cong dong".
>    **Ca hai deu 404** (kiem 13/09/2026 bang API da xac thuc, trong khi
>    `#3538`/`#3000` cung kho tra ve binh thuong). Chung duoc bia ra trong luc
>    tin rang minh dang tuan thu dung luat doi chieu cong dong. Do moi la ly do
>    that khien ba luot vap: **khong phai va sai cho, ma tuong minh da tra cuu
>    trong khi khong.**
>    (`ggml-org/llama.cpp#27572` o cac tep khac thi CO THAT — dung go nham.)
>
> ### Co che thay the — BA LOP, moi lop mot chan tren
>
> | lop | co che | chan tren | ma |
> |---|---|---|---|
> | **1 — chinh** | `khi_dut` trong `finally` cua `bat_dong_bo_hoa` nha suat THANG | **~0,05 s** | `runtime_noi_bo/luong.py`, `server/api/streaming.py:_nha_suat` |
> | **2 — luoi** | nhip tim chi dap khi **co byte di qua**; im qua `TRAN_IM_LANG_S` thi luong nhip **tu nha** | tran im lang | `llm/admission.py:keep_alive(con_song=...)` |
> | **3 — chan cuoi** | `reclaim_expired` | 20 phut | `llm/admission.py` |
>
> 🔑 **Lop 2 moi la loi giai that cho cau "vi sao BAT TU chu khong chi cham".**
>    Nhip tim cu dap vo dieu kien — no chung minh **luong con song**, khong chung
>    minh **cong viec con tien trien**. Mot generator treo cung trong khoe manh
>    mai mai, nen lop 3 KHONG BAO GIO khai hoa.
>
> ⚠️ `TRAN_IM_LANG_S = 900` lay tu NGUON, khong phai so chon cho tron:
>    `luong_vlm.mo(timeout_s=900.0)` dung `httpx.Client(timeout=900)`, va o httpx
>    mot so vo huong dat **read timeout** — tuc khoang lang HOP LE dai nhat giua
>    hai byte tu may B. Thap hon la tu giet mot luot prefill dai dang chay dung.
>    `test_1247::test_tran_im_lang_lay_tu_NGUON` chot rang buoc nay.
>
> ### Bai hoc ve PHEP DO — bo test cu XANH trong khi production NGHEN
>
> Nguon gia cua `test_1246` **tu mo troi cho chinh no** (`_dong()` goi
> `cho_nha.set()`). May B khong lam the. Ban gia khac vat that **dung o chieu
> dang do** — lan thu NAM cua cung mot khuon trong mot phien.
> Ban tai hien trung thuc (uvicorn that + 4 tang `BaseHTTPMiddleware` + nguon
> khong the tu tinh day) cho: `dong_nguon` +0,05 s, `BackgroundTask` chay tron,
> con `with keeper` thi **khong bao gio** thoat.
>

Tim ra khi di do cau hoi khac: *"cua stream co nha nhanh qua Cloudflare khong?"*.
Cau tra loi hoa ra khong phai "nhanh" hay "cham" — la **khong bao gio**.

### Do duoc

Khach doc 21.625 byte roi CAT o giay 3. Sau do:

```
giay   lease  mayB_dang_sinh
  0.0      1          0
 ...
180.1      1          0        <- may B ranh tu lau, lease van giu
```

Theo doi tiep bang CSDL: lease `mode=stream`, `lop=tuong_tac` song toi **643
giay** va van con do — voi `heartbeat_at` duoc cap nhat moi ~60 giay.

### ⛔ MOT DINH CHINH CUA CHINH TOI, trong cung mot lan do

Toi da viet vao day chu **"VINH VIEN"**, dua tren hai su that DUNG: lease van dap
nhip, va `admission.py:49` thu hoi theo `heartbeat_at < cutoff` — nen bo thu don
**khong the** bat duoc no.

Suy luan dung, ket luan SAI. Doc lai sau do: lease **da tu nha**, dau do giua
643 s va ~700 s. Co mot co che khac ket thuc no (nhieu kha nang la han cua chinh
luot stream), va toi khong biet no vi toi CHUA DO.

⭐ Bai hoc ve hinh dang: *"bo thu don khong bat duoc"* chi chung minh **MOT**
   duong ket thuc khong hoat dong. No khong chung minh **KHONG CON duong nao**.
   Mot ket luan pho quat ("vinh vien") doi mot phep do pho quat, khong doi mot
   suy luan tu mot co che.

⇒ Loi khai dung: suat bi chiem **>= 643 giay** sau khi khach di. Nguong cong M
  la **2 giay** — du de goi la mot loi ma khong can phong dai.


### Co che

```python
def _ket_thuc() -> None:
    try:
        cua_luong.dam_bao_quyet_toan(luot)
    finally:
        if cb.lease_id:
            admission.release_by_id(cb.lease_id)

nen = BackgroundTask(_ket_thuc)
return StreamingResponse(luot.luong, ..., background=nen)
```

Starlette chay `background` **sau khi phan hoi ket thuc**. Khach di giua chung
thi vong doi ay khong ket thuc som — va voi `BaseHTTPMiddleware` o giua,
`send_no_error` **nuot** `BrokenResourceError`, nen ngay ca luot ghi hong cung
khong lam no dung.

⭐ Chinh chu thich o cho ay da ghi mot bai hoc gan y het, tu 09/09:

> *"Truoc 09/09 chi co ve suat. Ve tien nam trong `finally` cua generator
> `_phat`, va mot `finally` chi ton tai SAU khi generator chay dong dau tien.
> Khach ngat truoc byte dau => khoan `hold` nam lai VINH VIEN."*

Ho da sua cho *"khach ngat TRUOC byte dau"*. Cho nay la *"khach ngat GIUA
chung"* — cung mot lop loi, mot buoc muon hon, va van con nguyen.

### Chua sua

Ban sua cham vao vong doi cua `StreamingResponse` va cua bo sinh, tuc cham vao
moi luot stream cua nen tang. Ghi day voi so do san: **>= 643 s**, so voi nguong cong M la 2 s. Va mot cau
hoi con no: **cai gi** ket thuc no o quanh giay 700 — biet duoc no la biet ban
sua phai dat o dau.

## L-07 -- DONG 13/09/2026, chung minh tren duong that

Ba phan, va ca ba deu co phep do dung sau.

### Phan 1 -- goc: cong render may B chay ban 04/09

`render_gateway/deploy/deploy.ps1`: 33 tep, hash khop hai ben, kem
`gpu_may_b.json` (RUNBOOK: thieu tep nay la **dung han** viec sinh anh, khong
phai giam chat luong). Khoi dong lai `LTTRenderGateway`.

Do duoc sau do: buoc tung gay -- `nha_llm -> anh`, tuc luot `chay_comfy()` --
nay mat **9,3 s** va di qua.

### Phan 2 -- hinh dang: `nha_llm` gio co duong lui

`CHUYEN_HOP_LE[NHA_LLM]` tu `{ANH}` thanh `{ANH, NAP_LLM}`, kem mot PHANH o
`LLM` de duong lui khong thanh vong lap.

### Phan 3 -- bit cho no lot qua

L-07 khong phai "ComfyUI hong". No la **may B troi ban bon ngay ma khong ai
biet**. Gate may A CO Y khong hoi may B, nen be mat that cua may B chua bao gio
duoc doi chieu voi cay. `tools/soi_troi_may_b.py` hoi thang `/openapi.json` roi
so voi tuyen cay khai (doc bang AST). Chay that: render 8/8, llm 11/11 khop.

### Nghiem thu -- HAI phep, va phep thu hai moi la phep quan trong

**Phep 1 -- chu trinh binh thuong:**

```
 0,6s  llm
 4,1s  xa_llm
 7,0s  nha_llm
16,3s  anh            <- buoc tung gay, nay di qua trong 9,3 s
148,8s job anh -> succeeded
151,7s tra_anh
159,9s nap_llm
182,1s llm            <- ltt-3.8 tra 200 trong 2,0 s
```

**Phep 2 -- HUY giua chung, dung kich ban da hong:**

```
 0,8s  xa_llm
 3,5s  nha_llm
 4,9s  HUY job anh -> HTTP 200
11,4s  nap_llm        <- DUONG LUI, no khong ton tai truoc 13/09
29,9s  llm            <- ltt-3.8 tra 200 trong 1,7 s
```

Chuoi bo qua `anh` hoan toan, dung nhu thiet ke: duong lui 1 no khi
`job_anh_cho == 0`.

⛔ **Vi sao phep 1 mot minh la chua du.** No di qua `anh`, tuc no chi chung minh
   PHAN 1. Duong lui khong bao gio duoc cham toi trong mot luot chay suon se.
   Dung o do la bao "da sua" cho mot nua chua ai thu -- va nua ay chinh la nua
   ma hom 13/09 phai ghi tay vao CSDL moi go duoc.

## L-06 -- GOC THAT, sau khi HAI gia thuyet cua toi bi bac bo

Ban ghi dau cua toi noi: *"`chat.py` khong goi `huy_luot.phien`"*. Dung mot nua,
va nua ay khong phai nguyen nhan.

### Ba gia thuyet, hai cai dau SAI

| # | gia thuyet | phep do phan biet | ket |
|---|---|---|---|
| 1 | Cloudflare giu ket noi nguoc dong nen may A khong thay `http.disconnect` | do CA HAI duong: qua CF **18,67 s**, loopback **16,54 s** | **SAI** |
| 2 | `Request.is_disconnected()` khong bao gio tra True o hinh dang cua ta | thi nghiem uvicorn toi gian, dung phien ban thu vien that, endpoint `def` nhu that | **SAI** -- thay o giay **2,02** |
| 3 | Phat hien duoc, nhung **khong cat duoc** | doc `dieu_phoi._dong()` | DUNG |

* Gia thuyet 1 chet vi mot phep do **mot dong lenh**: them mot duong loopback
  vao chinh bo do da co. Neu bo qua buoc ay, toi da di sua mot thu khong hong
  (cau hinh Cloudflare) va de nguyen thu dang hong.

### Goc

`dieu_phoi._dong()` -- duong huy **day du** -- lam ba viec, va HAI trong ba phu
thuoc `ma_luot`:

```
1. huy_luot.danh_dau(ma_luot)      chi khi CO ma
2. client.close()                   luon luon
3. _bao_may_b_huy(..., ma_luot)     chi khi CO ma   <- "bao may B thoi sinh chu"
```

`apps/ltt_llm/executor.run()` **khong nhan** `ma_luot`, nen cua dong bo goi
`features.chay` voi mac dinh rong => chi lam viec 2. Ma `httpx.Client.close()`
**khong cat** mot request dang bay o luong khac: may B sinh chu toi het, luong
goi cho toi het, `chay_canh_ngat` cho luong ay truoc khi nem `KhachNgat`.

Va chinh docstring cua `_bao_may_b_huy` da noi truoc dieu nay:

> *"neu may A chi dong ket noi cua minh, luot B->llama van chay toi het cho mot
> nguoi da di: dung cai GPU ta dang co tra lai. `POST /v1/huy` la cach noi
> **bang loi** dieu ma mot socket dong khong noi duoc."*

Mot loi canh bao viet dung cho, va van bi vuot qua -- vi no canh bao ve mot
tham so ma tang tren **quen truyen**, khong ve mot dong ma ai do se doc.

### Ban sua THU NHAT -- can, nhung KHONG DU

`executor.run(..., ma_luot="")` truyen xuong; `chat.py` truyen `ma_luot=request_id`.

Deploy roi do lai: **van 24-36 s**. Nen do tiep thay vi tin.

### Goc THU HAI: `is_disconnected()` chet sau `BaseHTTPMiddleware`

Phep do tach khong gian con lai -- trong luc lease bi giu, may B con sinh chu
khong? Doc `llamacpp:requests_processing` moi giay:

```
giay  lease  mayB_sinh
 0.0      1          1
...                        <- giu nguyen 1 suot 27,8 giay
27.8      0          0     <- ca hai cung ve 0
```

May B **sinh toi het** => lenh huy khong bao gio duoc phat => `ngat_chua()`
khong bao gio tra True.

Thi nghiem MOT BIEN SO, cung phien ban thu vien, cung hinh dang endpoint `def`:

| | thay khach ngat |
|---|---|
| khong middleware | giay **2,02** |
| co `BaseHTTPMiddleware` | **khong bao gio** |

`server/app.py` co `AccessControlMiddleware` va `PublicApiGuardMiddleware`, ca
hai ke thua `BaseHTTPMiddleware`.

**Co che, doc tu chinh ma Starlette:** `is_disconnected()` doc `receive` trong
mot `CancelScope` **da huy san**. Khong middleware thi uvicorn tra ngay tu hang
doi nen kip; con `receive_or_disconnect` cua middleware **mo mot task group** --
tuc co diem kiem tra -- nen scope da huy cat truoc khi gia tri ve.

=> Tinh nang huy-khi-khach-ngat da chet lang le **tu luc hai middleware ay duoc
   them vao**, va no chi lo ra o hoa don.

### Ban sua THU HAI

Doc `receive` voi han gio 50 ms thay cho scope huy san. Do lai trong dung hinh
dang production: **thay ngat o giay 2,02**.

⛔ Kem mot RAO quan trong hon ca ban sua: than request chua doc xong thi **khong
   duoc cham `receive`** -- doc mot tin la LAY no khoi hang doi, va o mot cua
   stream do la nuot mat mot manh than. Rao kiem `hasattr(request, "_body")`,
   thu Starlette dat sau khi `body()` chay xong.

### Va mot loi cua chinh PHEP KIEM, giu lai vi no la mot bai hoc ve hinh dang

Ban chot dau tien quet **van ban nguon** tim chuoi `_body`. Tiem dot bien -- go
rao, quay ve `is_disconnected` -- **van xanh**, vi hai chuoi ay con nam trong
DOCSTRING giai thich. Phep kiem khop vao loi giai thich chu khong vao ma.

Viet lai theo HANH VI (mot `Request` gia, dem so lan `receive` bi cham, chay
trong dung luong cong nhan anyio): nay bat duoc ca hai dot bien.

Ky vong do duoc sau khi deploy: llama.cpp nha slot **<=1 s** sau khi client roi
(`server-context.cpp:39`), cong mot nhip tham ~1 s => tong **~3 s**. Nguong cong
M la 2 s -- neu con vuot, phan con lai la nhip tham, va do la mot con so chinh
duoc.

### Va mot he qua ve HINH DANG PHEP KIEM

Ban sua lam **19 phep kiem do cung luc**, khong phai vi ma sai ma vi cac ban gia
cua `run()` go tay dung ba tham so:

```python
def gia(db, params, *, timeout_s=300.0):        # ban cu
def gia(db, params, *, timeout_s=300.0, **_):   # ban moi
```

Mot ban gia **chat hon** thu no thay the la mot cai phanh dat sai cho: no khong
bao ve gi ca, no chi no khi hop dong that mo rong.

## L-07 — MO 13/09/2026, CHAN: mot job anh ha `ltt-3.8` vinh vien

🔴 **Day la su co THAT, khong phai mot phep do.** `ltt-3.8` tra 429 cho MOI
   yeu cau tu 04:57 toi 05:29 — **32 phut**. Toi la nguoi kich hoat no (nop mot
   job anh de do cong I), nhung khuyet tat co san va bat ky job anh nao cung
   kich hoat duoc.

### Chuoi su kien, doc tu CSDL va log

```
04:57:29  job anh vao hang, admission_resource = anh_3090
04:57:31  gpu_residency: llm -> xa_llm       (ngung nhan luot LLM moi)
04:57:34  gpu_residency: xa_llm -> nha_llm   (da drain, phat lenh nha)
04:57:37+ moi ~3 giay, lap lai vo tan:
          "khong bat lai duoc ComfyUI => KHONG vao anh
           (cu tru rtx3090 van o nha_llm); se thu lai luot sau"
05:14:15  job anh van `queued`, progress 0, heartbeat van dap
05:29:41  can thiep tay: dat lai trang_thai = llm
05:30      ltt-3.8 tra 200 sau 17,7 s (nap lanh, khop cong K: 17,37 s)
```

### Goc: cong render may B chay BAN CU

```
POST http://192.168.2.66:8199/v1/nha_comfy   ->  404 {"detail":"Not Found"}
```

`residency.MayBResidency.chay_comfy()` goi dung duong ay va doi
`{"dang_chay": true}`. Cay co dinh tuyen do (`render_gateway/api.py:299`, dang
ky VO DIEU KIEN), ban dang chay tren may B thi khong:

```
duong may B 8199 dang co: /health · /live · /v1/exclusive
                          /v1/images/generations · /v1/jobs/{id}
                          /v1/jobs/{id}/cancel · /v1/models
```

### Vi sao mot 404 thanh mot su co toan phan

`CHUYEN_HOP_LE[NHA_LLM] = {ANH}` — tu `nha_llm` co DUNG MOT duong ra, va lenh
vao `ANH` chi phat khi `chay_comfy()` thanh cong. Khong co duong lui.

So sanh: `CHUYEN_HOP_LE[XA_LLM] = {NHA_LLM, LLM}` — o `xa_llm` co duong huy
("job anh rut khoi hang giua luc drain"). Duong ay **dung mot buoc truoc chO
can no**.

⇒ Ket cuc: LLM da roi card (3090 con 184 MiB), anh khong bao gio duoc ve, va
  khong trang thai nao mo cua cho ai. Card 24 GB nam khong, hai ben cung doi.

⛔ Va **huy job anh khong go duoc**: toi huy no luc 05:2x, trang thai van o
   `nha_llm`. Duong huy chi ton tai o `xa_llm`.

### Vi sao chua ai gap

Luu luong 7 ngay: **1** job `anhnoibo`. Viec sinh anh qua duong nay gan nhu
khong duoc dung, nen khuyet tat nam im. Mot ngay co khach dung anh la ngay
`ltt-3.8` tat theo.

### Ban sua — hai phan, va phan thu hai moi la phan quan trong

1. **Deploy lai cong render may B** de co `/v1/nha_comfy`. Day la phan de.
2. **May trang thai phai co duong lui tu `nha_llm`.** Sua (1) lam su co nay het,
   nhung no khong lam `nha_llm` het la mot ngo cut: lan sau ComfyUI hong that
   (o dia day, driver loi, dich vu khong bat duoc) thi ket qua VAN la 3090 nam
   khong vo han. Mot trang thai co the vao ma khong the ra la mot khuyet tat
   ve HINH DANG, khong phai ve cau hinh.

**PHAN 1 DA LAM 13/09.** `render_gateway/deploy/deploy.ps1`: 33 tep, hash khop
hai ben, kem `gpu_may_b.json` (RUNBOOK canh bao thieu tep nay la **dung han**
viec sinh anh). Khoi dong lai `LTTRenderGateway`, va `/v1/nha_comfy` nay **da co
mat** -- dung duong da 404.

**PHAN 2 DA LAM 13/09.** `CHUYEN_HOP_LE[NHA_LLM]` nay la `{ANH, NAP_LLM}`, kem
mot phanh o `LLM` de duong lui khong thanh vong lap. Chot o `test_1240` (15 phep
kiem) va bang 7x15 = 105 o cua `test_1216`.

### Can thiep tay da lam gi (de hoan lai duoc)

`UPDATE gpu_residency SET trang_thai='llm', tu_luc=now(), cua_so_bat_dau=NULL,
phien_ban=phien_ban+1 WHERE nhom='rtx3090' AND phien_ban=2` — mot dong, co
dieu kien khoa lac quan. Truoc khi ghi da kiem ba rao: trang thai DUNG la
`nha_llm`, hang doi ComfyUI rong (`queue_remaining` = 0), VRAM 3090 sach
(184 MiB). Thieu bat ky rao nao thi ban ghi la nap 16 GB len mot card dang ve.

## L-06 — MO 13/09/2026: cua dong bo khong cat duoc viec khi khach bo di

Cong M doi *"slot trong <= 2 s"*. Do duoc **15,4 s**.

### Phep do PHAN BIET — vi mot con so don khong noi duoc no la loi gi

Mot lan do ra 15 giay co the la ba thu khac han nhau: ro lease, mot han cho co
dinh, hoac "chay het roi moi tra". Ba ket luan ay khac nhau ve muc nghiem trong,
nen phai co phep do tach chung ra. Doi `max_tokens`:

| `max_tokens` | slot duoc tra sau |
|---:|---:|
| 900 | 15,37 s |
| 1024 | 17,17 s |
| 2000 | **31,90 s** |

`2000 / 1024 = 1,95x` · `31,90 / 17,17 = 1,86x`. Gan nhu ti le thuan.

⇒ Khong phai ro lease (lease CO ve 0), khong phai mot han cho co dinh. Nen
  tang **chay het** luot sinh tren may B roi moi tra slot.

### Goc — tim ra bang cach doc ma SAU KHI phep do chi huong

```
apps/ltt_llm/jobs.py:81     with huy_luot.phien(ma_luot):     <- cua JOB co
server/api/chat.py          (khong co dong nao)               <- cua SYNC khong
```

Cua job boc luot trong mot **phien huy**, nen `POST /jobs/<id>/cancel` cat duoc
lenh goi len may B — do duoc **0,33 s** (dang xep hang) va **0,36 s** (dang
chay). Cua dong bo sinh `request_id` cho so sach nhung khong ghi danh phien huy
nao, nen khi client dut thi khong co gi de cat.

### Hai hau qua, va cai thu hai la tien

1. **Slot bi giu vo ich** toi 32 giay. Voi 3 slot, ba client dut lien tiep la
   ca may B dung yen trong nua phut trong khi hang doi van xep.
2. **Khach van bi tinh tien cho token ho khong nhan duoc.** Do duoc: sau mot
   luot bi cat, `mcredit_du` toan he tang **+360**. Day khong phai thu hai lan
   — so sach can — nhung no la thu tien cho mot thu chua tung roi may chu.

⚠️ **Chua sua.** Ban sua cham vao vong doi cua cua dong bo (dang ky phien huy
   + phat hien client dut), va do khong phai thu nen lam ke ben mot lo do. Ghi
   day de no khong bi mat, va de ban sua co doi chung san: ba con so 15,4 /
   17,2 / 31,9 la thu phai doi thanh <= 2 s.

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

---

# L-10 — ban va cho L-07 tu dung mot ngo cut o phia ben kia

Tim ra khi chay cong N, tinh huong *"ComfyUI hong"*.

## Hinh dang

L-07: `nha_llm` co DUNG MOT duong ra, va loi ra ay doi `chay_comfy()` thanh
cong. Ban va 13/09 them duong lui (`tran_vao_anh_hong = 3`) va — dung — them
mot PHANH o `LLM`, vi mot duong lui khong kem phanh vao se thanh vong quay.

Nhung phanh ay viet thang la `lan_vao_anh_hong < tran`, con bo dem thi chi duoc
xoa o **dung mot cho**: sau mot `chay_comfy()` thanh cong. Ma `chay_comfy()`
nam sau chinh cai phanh do.

    phanh chan  ->  khong vao `ANH`  ->  khong goi `chay_comfy()`
                ->  khong xoa bo dem ->  phanh chan  ->  ...

⇒ Doi mot ngo cut lay mot ngo cut khac. L-07 giet LLM; L-10 giet phia ANH.

## Do duoc (13/09, ca bon dich vu may B Running)

| vong | tiem | ket qua |
|---|---|---|
| 1 | `LTTComfyUI` -> Disabled | `llm -> nha_llm -> nap_llm -> llm` trong **46,7 s** — duong lui L-07 chay dung |
| 2 | `LTTComfyUI` -> Automatic (**da lanh**) | job anh moi: residency **khong he roi `llm`** suot 120 s, job `queued` |

Khong mot dong log, khong mot bao dong. Chi `Restart-Service LTTStudioWorker`
moi go duoc — tuc mot trang thai **doi ban tay nguoi**, dung lop khuyet tat ma
L-07 sinh ra de chan.

## ⛔ Hai lan toi ket luan sai truoc khi ket luan dung

1. **Lan dau toi bao "xac nhan" khi phep do dang nhiem.** Truoc do toi chay
   `Stop-Service LTTLlamaSwap -Force`; lenh ay keo theo dich vu PHU THUOC
   (`LTTLlmGateway`), va `Start-Service LTTLlamaSwap` **khong** bat lai chung.
   Cong 8299 tat ⇒ trong tai khong hoi duoc may B ⇒ fail-closed giu `llm`.
   Log noi thang: *"khong hoi duoc may B ve cu tru 'rtx3090' => giu nguyen
   'llm', khong phat lenh nao (fail-closed)"* — khong lien quan bo dem.
2. **Lan hai toi doc "van khoa" sau khi restart worker**, trong khi log cho thay
   tien trinh moi chi len sau do 2 phut. Toi da do tien trinh CU.

⭐ Bai hoc chung cua ca hai: mot phep do ve "he thong khong lam gi" rat de dung,
   vi *khong lam gi* la ket qua cua RAT NHIEU nguyen nhan. No chi tro thanh bang
   chung khi moi nguyen nhan khac da bi loai — o day la "ca bon dich vu Running"
   va "dung tien trinh dang song". Cung bai hoc da ghi o L-06 voi Cloudflare.

## Ban sua: mot vi tu, dung o HAI cho

`duoc_thu_anh(qs, ts, bay_gio)` = chua cham tran, **hoac** da lui du lau.

    `LLM`     -> `XA_LLM`   khi  duoc_thu_anh      (nha card de THU)
    `NHA_LLM` -> `NAP_LLM`  khi  KHONG             (duong lui 2, tra card)

🔴 Vi sao khong duoc noi rieng ve o `LLM` — cai bay that su cua ban va nay: o
   `NHA_LLM`, duong lui 2 duoc kiem **truoc** nhanh vao `ANH`. Noi mot minh ve
   `LLM` thi luot thu lai se nha card roi nap lai ngay ma **khong he goi
   `chay_comfy()`** — ton tron 47 s de khong hoi duoc cau duy nhat can hoi, va
   bo dem van khong bao gio duoc xoa. Hai cho phai doc cung mot su that.

Nhip lui: `lui_anh_hong_s = 300 s`, gap doi, **tran ×8** (40 phut). Thap hon
`lui_nap_s` (tran 480 s tren nen 30 s ⇒ cung 480 s) co chu dich: ben kia LLM da
chet han nen lui lau khong mat them gi, ben nay LLM van dang phuc vu va thu dang
cho la hang job anh. Gia moi lan thu la mot chu trinh nha/nap **do duoc 47 s**,
nen nhip 300 s giu gia ay o ~16 %.

## Phep kiem: `tests/test_1245_dem_anh_hong_tu_nhat.py`

⚠️ `test_1240` van XANH nguyen ven voi ma hong. No dung `bay_gio` trong khoang
   100–200 con nhip lui la 300 s, nen vi tu moi tra ve cung ket qua voi bieu
   thuc cu — no xanh nho mot **gia tri dong ho tinh co**. Mot bo kiem xanh ca
   truoc lan sau ban va thi khong bao ve ban va, va do la ly do bo 1245 ton tai
   rieng thay vi them vai ve vao 1240.

Doi chung da chay: tiem lai bieu thuc cu (`return qs.lan_vao_anh_hong <
ts.tran_vao_anh_hong`) lam **6/11 ve do**, gom ca hai ve `monkeypatch` chung
minh CA HAI cho deu doc vi tu.

---

# L-08 — cau hoi "cai gi ket thuc no quanh giay 700" da co loi dap

## Loai tru: khong mot han dinh nao khop

| han | gia tri | vi sao khong phai no |
|---|---|---|
| `admission.ORPHAN_TIMEOUT` | **20 phut** (1200 s) | khong bang 700 s |
| va no khong bao gio toi | — | `keep_alive` chay luong nhip tim rieng, moi **60 s** goi `heartbeat_by_id`, nen `heartbeat_at` khong bao gio cu di de `reclaim_expired` nhin thay |
| `jobs.ORPHAN_TIMEOUT` | 5 phut | khong phai duong nay |
| `gpu_lease.ORPHAN_TIMEOUT` | 10 phut | khong phai duong nay |

## ⛔ Gia thuyet dau cua toi — "GC thu don generator treo" — SAI

Toi da viet muc nay mot lan voi ket luan ay, dua tren mot bo mo phong generator
tu viet. Bo mo phong chay dung, nhung no mo phong **sai vat**: no gia dinh lease
duoc nha trong `finally` cua generator. Doc lai ma thi lease KHONG nha o do —
no nha trong `_ket_thuc()`, mot `BackgroundTask` (`server/api/streaming.py`).

⚠️ Bai hoc: mot bo mo phong chi tra loi ve **cai no dung lai**, khong tra loi ve
   he thong that. Toi da do mot khuon toi tu dung roi doc ket qua nhu mot su
   that ve production — cung lop loi voi "Idempotency-Key" hom qua (do chinh
   cong cu cua minh) va voi "Cloudflare khong phai nguyen nhan" (ket luan khi
   nguyen nhan khac chua bi loai).

## Co che THAT — doc ma thu vien DANG CAI, tung mat xich

| # | cau hoi | tra loi | nguon |
|---|---|---|---|
| 1 | uvicorn khai ASGI `spec_version` nao? | **"2.3"** (< 2.4) | `uvicorn/protocols/http/h11_impl.py` |
| 2 | ⇒ nhanh nao cua `StreamingResponse.__call__` chay? | nhanh **CO** `listen_for_disconnect` | starlette 1.3.1 |
| 3 | `background` co chay khi khach cat khong? | **CO** — `await self.background()` o thut le **NGOAI** `async with`, chay o ca hai nhanh | nt |
| 4 | vay tai sao lease van bi giu 643 s? | vi `luong: Iterator[bytes]` la **DONG BO** | `platform_core/llm/luong_vlm.py:64` |

Starlette boc mot iterator dong bo bang `iterate_in_threadpool`. **Cancel scope
cua anyio khong cat duoc mot LUONG dang cho doc socket.** Nen day chuyen la:

    khach cat  -> `listen_for_disconnect` ve  -> task_group.cancel()  ✅
               -> nhung `stream_response` dang ket trong threadpool   ⛔
               -> task group KHONG sap duoc, phai cho luong ay xong
               -> `await self.background()` chua toi luot
               -> `_ket_thuc()` chua chay -> lease CHUA NHA

Moi thu cho may B tu dong ket noi. **643 s la thoi diem may B buong, khong phai
mot han dinh nao cua may A.**

⭐ VA DAY LA CUNG MOT HO VOI L-06. L-06: `BaseHTTPMiddleware` doc `receive`
   trong mot cancel scope da huy. L-08: generator dong bo trong threadpool. Hai
   trieu chung khac han, mot nguyen nhan chung — **mot cau noi DONG BO vo hieu
   hoa co che huy bat dong bo**. Su that ay dinh huong ban sua manh hon bat ky
   phep do nao ve thoi gian.

## Ba huong sua bi loai tru BOI chinh chuoi bang chung tren

1. **Ha `ORPHAN_TIMEOUT`** — vo ich: `keep_alive` dap nhip moi 60 s nen han ay
   khong bao gio toi, ha xuong 60 s cung khong doi gi.
2. **`gc.collect()` dinh ky** — GC khong phai co che (muc tren), nen no chua mot
   benh khong ton tai.
3. **Doi `BackgroundTask` chay som hon** — no **da** chay dung cho roi; nut that
   nam TRUOC no, o luong dong bo khong cat duoc.

⇒ Ban sua phai lam chinh luong ay **tu biet khach da cat** va thoat vong lap —
  tuc dung lai may moc `platform_core/llm/ngat.py` cua L-06 — hoac nha lease
  ngay tai luc phat hien ngat thay vi doi `background`.

## 🔴 BAN SUA 13/09 DA DUOC DEPLOY VA **KHONG CHAY**. Do tren may that.

`ngat.dung_khi_khach_cat` da len production (`6f1606267eaf`). Do ngay sau deploy:

| phep | ket qua |
|---|---|
| chay TRON luot, khong cat | **21,5 s** (849 manh) |
| cat o manh thu 5, qua Cloudflare | lease nha sau **99,0 s** |
| cat o manh thu 5, qua **loopback** | lease **CHUA nha sau 150 s** |
| log `"khach cat giua luong"` | **KHONG CO DONG NAO** |

Ve dau loai tru kha nang te nhat (luot tu xong o giay 99 — khong phai). Nhung ve
cuoi moi la ve quyet dinh: **vi tu `ngat_chua()` chua bao gio tra `True`**.

### Vi sao — va no bac chinh chu thich toi da viet

`request` CO duoc truyen (`streaming.py:181/192`), nen `do_ngat` nhan Request
that. Van de nam o cuoc dua:

    cua DONG BO  — khong ai tranh `receive` => `_doc_mot_tin` doc duoc => CHAY
                   (do L-06: 16,54 s -> 1,43 s)
    cua STREAM   — Starlette DA DO SAN tren `receive` qua `listen_for_disconnect`
                   tu luc phan hoi bat dau. `http.disconnect` chi toi tay MOT
                   ben, va ben do la Starlette.

⛔ Chu thich toi viet trong `dung_khi_khach_cat` noi cuoc dua nay *"an toan, ca
   hai duong deu dan toi dung"*. **SAI.** Khi Starlette thang, thu no lam la huy
   cancel scope — dung cai **khong cat duoc luong threadpool**. Ben thang cuoc
   dua la ben khong lam gi duoc. Hai nua cua bai toan khop nhau thanh mot vong
   kin, va toi da viet ra ca hai nua ma khong nhin thay chung dong lai.

### ⚠️ Va no dang lam production CHAM DI

Moi giay, generator chan toi `HAN_DOC_NGAT_S` = 0,05 s de hoi mot cau khong bao
gio co cau tra loi ⇒ ~5 % do tre them cho **moi** luot stream, doi lay **khong
gi ca**. Mot ban va khong chay ma van tinh phi.

### Hai duong di that, khong con duong thu ba

1. **Lam luong BAT DONG BO tu dau toi cuoi** (`luong_vlm._di` -> async, httpx
   `AsyncClient`). Day la ban sua DUNG GOC: no go bo chinh cau noi dong bo ma
   ca L-06 lan L-08 deu vap phai. Dat, nhung no ket thuc ca mot ho loi.
2. **Gianh `receive` TRUOC Starlette**: boc `receive` o tang ASGI (middleware
   hoac mot `Response` con) de ta thay `http.disconnect` roi CHUYEN TIEP no cho
   Starlette. Re hon, nhung them mot tang ASGI tu viet — va `BaseHTTPMiddleware`
   chinh la thu da gay ra L-06.

⛔ Truoc khi lam mot trong hai: **go ban va hien tai**. No khong chay, va no dang
   thu 5 % do tre cua moi khach dung stream.

## Ban sua: `ngat.dung_khi_khach_cat`, boc dung MOT cho

Mot ham boc dat o noi dung `StreamingResponse` (`server/api/streaming.py`), noi
`request` da co san. No tham `ngat_chua()` theo NHIP `NHIP_THAM_S` (1 s) giua
cac manh, va khi thay ngat thi thoat vong — luong tra ve ⇒ task group sap ⇒
`background()` chay ⇒ lease nha.

🔴 **Nua `close()` trong `finally` khong duoc quen.** Thoat vong ma khong dong
   `nguon` chi day cung mot loi xuong MOT TANG: generator ben trong nam treo,
   `finally` cua no (`ctx.__exit__` + `client.close()`) chua chay, ket noi httpx
   toi may B van mo. `close()` nem `GeneratorExit` vao dung cho ay nen `finally`
   chay NGAY — khac biet giua "nha lease" va "nha ca suat o may B".

⚠️ **Co mot cuoc dua, va no an toan** — nhung phai noi ra: `do_ngat` doc
   `request.receive()`, ma `listen_for_disconnect` cua Starlette **cung** doc.
   Mot `http.disconnect` chi toi tay MOT ben. Starlette thang ⇒ task group huy,
   ta khong thay; ta thang ⇒ ta thoat vong va dong nguon. Ca hai deu dan toi
   "dung", nen cuoc dua khong doi tinh dung — no chi doi AI dung truoc.

## ⛔ Va doi chung DAU TIEN cua toi TRUOT — bo kiem xanh ca khi da go ban va

Go han nua `close()` ma **6/6 ve van xanh**. Vi sao: trong phep kiem, KHONG AI
giu tham chieu toi generator nguon, nen khi ham boc ket thuc thi refcount ve 0
va CPython dong no ngay — `finally` chay nho REFCOUNT chu khong nho ban va.

San that khong nhu vay: generator nguon duoc `LuongMo.luong` giu, `LuongMo`
duoc khoi dung phan hoi giu. No song, va chi mot `close()` TUONG MINH moi chay
duoc `finally`.

⭐ Sua bang cach cho phep kiem GIU tham chieu (`_GIU`) dung nhu san that. Chay
   lai dot bien: **2/6 ve do**. Day la lan thu ba trong phien mot ban gia khac
   san that dung o chieu dang do — cung ho voi "bo mo phong GC" o tren va voi
   hai ban gia qua chat (`executor.run`, `danh_dau_loi`).
