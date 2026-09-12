# LLM_CHANGELOG_UPGRADE

Nhật ký thay đổi của chương trình MASTER UPGRADE. Mỗi mục nói **đã đổi gì** và
**bằng chứng nào chứng minh nó đúng** — không nói ý định.

Dải test cấp cho chương trình này: **980–989**.
(600–699 H43 · 700–799 VIDEO AI V3 · 800–899 CHATLTT V3 · ≤970 đã dùng.)

---

## PHASE 1 — identity / config / chú thích đã hết đúng · 2026-09-09

### Không thay đổi mã chạy. Không thay đổi một giá trị nào.

⭐ Kết luận lớn nhất của Phase 1 là một **phát hiện âm tính**: chuỗi dẫn xuất
ngân sách **đã được khoá đầy đủ** từ trước, ở bảy mắt xích:

```
apps/ltt_llm/ngan_sach.py  (CUA_SO_MODEL · CUA_SO_MODEL_VISION)
  ├─ llama-swap.yaml  `-c`         test_334::test_llama_swap_yaml_khop_cua_so_cua_TUNG_ho_so
  ├─ catalog.py  max_context       test_334::test_catalog_may_B_khop_cua_so_model
  ├─ config.py   max_input/output  test_334::test_tran_{vao,ra}_khop_mac_dinh_trong_ma_may_B
  │                                + test_250_llm_gateway.py:45
  ├─ deploy.ps1  (BA chỗ)          test_334::test_deploy_ps1_KHONG_lui_tran_cua_may_B
  ├─ manifest.CUA_SO_NGU_CANH      test_334 (dòng 147)
  ├─ public_api/examples.py        test_334::TestBanSaoConLai
  └─ server/api/tools.py           test_334::TestBanSaoConLai
```

⇒ Mục P1-03 của kế hoạch (*"ba bản sao gõ tay trong `deploy.ps1`"*) đóng lại với
**NO CHANGE REQUIRED**. Baseline đã đánh dấu nó `[?]` chứ không `[X]`, và việc
đọc trước khi thiết kế đã tiết kiệm đúng một bản vá không cần thiết.

### P1-01 — chú thích trỏ sai phép kiểm · ĐÃ SỬA

`llm_gateway/config.py` và `platform_core/public_api/config.py` đều nói
`tests/test_312` giữ hằng số của chúng. `tests/test_312_vps_khoa_dich_vu.py` là
**khoá dịch vụ VPS**. Phép kiểm thật là `test_334_ngan_sach_ltt_llm.py` (và
thêm `test_250_llm_gateway.py` cho cái đầu).

**Hằng số vẫn luôn được bảo vệ** — thứ hỏng là *lời hứa*, không phải *hàng rào*.

Nguyên nhân gốc đo được: **22 số hiệu test bị trùng** trong `tests/`, nặng nhất
`test_251` (BỐN tệp), `test_250`/`test_252`/`test_156` (BA tệp). Viết `test_250`
trong một chú thích là không nói được điều gì cả.

* sửa: hai chú thích nay viện dẫn **tên tệp đầy đủ**.
* rào: `tests/test_980_vien_dan_phep_kiem.py` — viện dẫn có tên phải tồn tại;
  viện dẫn bằng số trần phải **xác định** (một số trỏ tới nhiều tệp ⇒ đỏ).

⚠️ **Nói đúng phạm vi, không nói quá:** chốt này **không** bắt được ca gốc.
`test_312` trỏ tới đúng một tệp — xác định, nhưng sai. Thứ bắt ca ấy là người
đọc lại. Cái test_980 ngăn là ca **kế tiếp**, vốn nguy hiểm hơn vì người đọc
không có cách nào tự kiểm chứng.

**Một phép kiểm mạnh hơn đã bị từ chối, và lý do được đo trước khi từ chối:**
bản "đối chiếu ngược" (A nói test X giữ nó ⇒ X phải nhắc lại A) **bắt được** ca
gốc, nhưng cũng **báo động nhầm** `apps/ltt_llm/features.py → test_212`. Viện
dẫn ấy đúng: `test_212` chứng nhận mọi alias bằng cách duyệt registry nên nó
không bao giờ gõ chữ `ltt_llm` — nó tổng quát, và đó là giá trị của nó. Một hàng
rào phạt những phép kiểm viết tốt nhất sẽ được "sửa" bằng danh sách miễn trừ.

### P1-02 — số đã trôi trong văn · ĐÃ SỬA, 5 khối

| tệp | nói | thật |
|---|---|---|
| `llm_gateway/config.py:55` | *"Engine 131.072; public giữ 65.000 theo Q116"* | 204.800 · số dẫn xuất · Q116 đã bị **Q120** thay |
| `llm_gateway/catalog.py:86` | *"CHỜ P5 xác nhận"* | P5 đo xong 03/09 |
| `apps/ltt_llm/ngan_sach.py:64` | vision *"nạp với `-c 65536`"* | `-c 131072` |
| `apps/ltt_llm/ngan_sach.py:183` | vision công bố 28.262 ⇒ `nen_cua` trả **0** | công bố **88.555** ⇒ trả **55.787** |
| `apps/ltt_llm/manifest.py:31-46,94` | bảng engine + 96.256 + 89K + 28K | tất cả đã đổi 03/09 |

🔴 **Khối `manifest.py` đã trôi HAI LẦN, và lần hai là bài học.** Nó mở đầu bằng
*"SỬA 01/09 — BA CON SỐ Ở ĐOẠN NÀY ĐỀU ĐÃ TRÔI"*. Bản vá ấy thay câu sai bằng
một **bảng số cụ thể**, và đợt nâng ngữ cảnh 03/09 làm cả bảng hết đúng. Bản vá
đi sửa số trôi đã tự trôi y hệt — vì nó sửa **giá trị**, còn khuyết tật là
**hình dạng**. Chính tệp đó đã đặt tên: *"Sửa giá trị không phải sửa hình dạng."*

⇒ Lần này văn **không chứa bảng số nào**; nó nêu tên nguồn và một bất biến không
đổi theo `-c`: `cửa sổ engine > trần vào > công bố cho client`.

* rào: `tests/test_981_van_khong_go_lai_so.py` — hai hình dạng đã thật sự trôi:
  `-c <số>` và `TÊN_HẰNG (<số>`. Có đường thoát tường minh cho văn lịch sử
  (khuôn lấy của `test_604`), vì bốn khối văn quý nhất trong hai gói này **là**
  chuyện về những con số đã chết.

⭐ **Đối chứng đã bác bản đầu của chính chốt này.** Luật đầu chỉ hỏi *"số này có
phải một cửa sổ đang sống không"*. Đối chứng tiêm nguyên văn bảng cũ và bắt được
**1/2**: `` `qwen38-api` `-c 131072` `` lọt, vì 131.072 hôm nay hợp lệ — cho
*vision*. Tức chốt xanh trên đúng nửa nói về model khách dùng nhiều nhất. Luật
đã siết thành **khớp theo hồ sơ** khi tên hồ sơ có mặt trên cùng dòng; đối chứng
nay bắt 2/2.

### Nghiệm thu hẹp

```
pytest test_980 test_981 test_334 test_250_llm_gateway test_256 test_604 test_212
  -> 201 passed, 3 skipped                                        (90,5 s)

check_bien_dich PASS · check_ruff PASS · check_silent_except PASS
check_undefined_names PASS · check_xuong_dong PASS · check_so_test PASS
check_luat_van_hanh PASS · check_ranh_gioi 3 kept/0 broken
lint_app_contract PASS · check_mypy dat moc (616/14)
```

Kiểm số đã khai trong văn mới bằng chính mã:

```
vision  tran_vao = 96256 · cong_bo = 88555 · nen_cua = 55787
api     nen_cua  = 123617
TOKEN_VAO_TRAN = 169984 · CONG_BO_CHO_CLIENT = 156385
```

### Điểm

| Hệ con | Trước | Implementation | Căn cứ |
|---|---|---|---|
| W1 identity/config | 93 | **98** | chuỗi 7 mắt xích đã khoá (đo, không giả định); hai viện dẫn sai đã sửa + có rào |
| W8 token/ngữ cảnh | 94 | **98** | runtime luôn đúng và tự dẫn xuất; văn đã thôi mâu thuẫn |
| W12 bảo trì | 85 | **98** | 5 khối văn sửa; 2 rào, cả hai có đối chứng ĐỎ được |

### Ngoài phạm vi — báo cáo, KHÔNG sửa

**22 số hiệu test bị trùng trên toàn kho.** Đây là **nguyên nhân gốc** của
P1-01, và nó nằm ngoài phạm vi chương trình:

* sửa nghĩa là đổi tên tệp test của **phiên khác** — trái luật 12/13 của
  `CLAUDE.md` (*"một dòng `??` lạ là một PHIÊN KHÁC đang làm việc"*);
* 307 viện dẫn `test_NNN` trong mã nguồn, phần lớn ở dạng số trần ⇒ một đợt
  đổi tên sẽ kéo theo một đợt sửa chú thích hàng trăm chỗ.

⇒ Ghi vào W11 (phát hành) như một khuyết tật quản trị đã đo được, và
`test_980` giữ cho **phạm vi của chương trình này** không dính thêm.

---

## PHASE 2 — cong fail-closed khi nghe ra LAN . 2026-09-09

### Do TRUOC khi sua (may A -> may B, chi doc)

```
GET http://192.168.2.66:8299/live    -> 200  {"ok":true,"version":"0.1.0"}
GET http://192.168.2.66:8299/health  -> 401  {"detail":"token khong dung"}
```

`/health` tra **401 khi khong kem bearer** => `LTT_LLM_TOKEN` **dang duoc dat**
tren production.

**Nen phai noi dung muc do: day KHONG phai mot lo hong dang mo.** Bao cao noi
qua len la mot cach lam sai khac, va phep do nay ngan dung dieu do.

### P2-01 - fail-closed luc khoi dong . DA SUA

`llm_gateway/main.py`: `host` khong thuoc `LOOPBACK` **va** `token` rong
=> `SystemExit(3)`, kem thong diep noi ro cach go.

* `LOOPBACK = {127.0.0.1, ::1, localhost}` - `0.0.0.0` va `::` **co y khong**
  nam trong do: chung bind MOI giao dien, tuc la dang phoi ra rong nhat.
* Chot dung **truoc** chot cong-bi-giu: kiem cau hinh thuan, khong ton I/O,
  trong khi chot kia mat toi ~21 giay (connect + netstat).
* `SystemExit(3)` phan biet duoc voi `SystemExit(2)` cua chot cong-bi-giu.
* Duong dev **khong vo**: loopback + khong token van chay.

**Phuong an da tu choi:** tra 401 cho moi yeu cau khi cau hinh sai. Dich vu van
"chay", `/live` van xanh, va nguoi van hanh nhin thay mot cong khoe manh khong
phuc vu duoc ai. Kho nay da tra gia cho dung lop trieu chung do ngay 01/09
(health xanh gia). Hong luc khoi dong thi to tieng va chi dung thu pham.

### Doi chung - ban CU co that su di qua chot khong?

Mo phong ban cu **khong sua tep nao trong cay** (bo nho du an: *"Chot khong
duoc ghi vao cay"* - mot test sua tam tep trong repo tu pha luot gate chua no):

```
LOOPBACK := {..., 0.0.0.0, ::}      # mo phong "khong co chot"
host=0.0.0.0, token=""              -> DI QUA CHOT, chi mot dong warning
```

=> Chot la thu chiu luc, khong phai trang tri.

### An toan deploy

Chot moi doi dung cai production **dang co**. Neu khong do truoc, ban va nay la
mot canh bac: token rong that thi lan deploy ke tiep se **khong khoi dong lai
duoc** va model nha tat giua gio chay.

### Nghiem thu hep

```
pytest test_982 test_250_llm_gateway test_269 test_363 -> 84 passed
check_bien_dich . check_ruff . check_silent_except . check_undefined_names
check_xuong_dong . check_so_test . check_ranh_gioi        -> PASS
check_mypy dat moc (616/14)
scan_source_secrets -> 0 findings   (**tung FAIL vi loi cua chinh toi**:
    `LLM_UPGRADE_BASELINE.md` cat doi mot SHA git thanh mot chuoi hex 32 ky tu
    va bo do doc no nhu mot bi mat. Da sua.)
```

### Quan trac ro ri bi mat (§27) - da soat

Cong **khong bao gio** ghi gia tri token hay noi dung prompt ra log. Thu no ghi:
duong, ten model, **so** token (`token_vao~%d`), so anh, ma trang thai. Dong
`main.py` moi ghi **ten bien** va **duong dan tep**, khong ghi gia tri.

### Diem

| He con | Truoc | Implementation | Can cu |
|---|---|---|---|
| W7 bao mat | 88 | **98** | tran rubric (fail-open => Security <= 90) da duoc go bang co che, khong bang giao uoc |

---

## PHASE 3 — ghim va ghi lai phien ban thuong nguon . 2026-09-09

### Do: BON duong doc lap, khong duong nao tra loi

Cau hoi "may B dang chay ban nao":

```
1. GET /health cua cong          -> thuong_nguon chi co {url, ma, song}
2. doc tep trong kho             -> khong tep nao ghi
3. Nexus command.run tren may B  -> BI CHAN (dung chinh sach, khong lach)
4. Nexus file.read log may B     -> BI CHAN (dung chinh sach, khong lach)
```

=> Thu DUY NHAT con lai la **cong tu khai**: no la tien trinh duy nhat noi
chuyen duoc voi llama-swap qua loopback. Do la ly do P3-01 ton tai, va viec bi
chan hai lan lam luan diem manh len chu khong yeu di.

### Do duoc GIAN TIEP bang Nexus `file.list` (liet ke ten, khong doc noi dung)

`H:/LTT_LLM/bin` chua `llama-swap_250_windows_amd64.zip` => **v250**
(phat hanh 2026-08-14; thuong nguon nay da o v255).

⭐ Roi doi chieu route tren **DUNG THE v250**, khong phai tren `main`:

```
git show v250:internal/server/server.go
  -> /api/version /metrics /api/hardware /api/metrics/activity /running  DEU CO
```

Neu doc `main` roi suy ra cho v250 thi do la "doc thu dai dien thay vi doc thu
that" — va ca thiet ke W2 se dung tren mot gia dinh.

### P3-01 — `/health` khai phien ban thuong nguon

* `thuong_nguon.phien_ban.swap` <- `GET /api/version` (RE: doc BuildInfo nhoi
  luc dung nhi phan, khong cham model, khong danh thuc GPU).
* `thuong_nguon.phien_ban.engine` <- `build_info` trong `/props`, **chi khi ho
  so DA NAP san**.

  ⛔ Bat bien dat nhat cua phase nay: `/upstream/<model>/props` di qua
     llama-swap, va llama-swap **se NAP model** de phuc vu duong `/upstream/...`.
     Hoi vo dieu kien thi mot luot `/health` vo hai se danh thuc GPU ~2,5 phut
     va **da vang** ho so dang phuc vu khach. Da chot bang test.

* Ban cu khong co `/api/version` => `null` + `ly_do`, **khong** lam `/health` do.
  Mot chot QUAN SAT khong bao gio duoc bien thanh chot vao cua (luat `_xem_gpu`).
* **Khong nho ket qua HONG**: llama-swap chua len ma nho luon thi `/health` noi
  doi toi het doi tien trinh — dung lop "health xanh gia" cua `to_tien.py`.

### P3-02 — `nang_llamacpp.ps1` thoi mac dinh lay ban moi nhat

Lenh NGAN NHAT phai la lenh AN TOAN NHAT. Truoc: khong truyen `-Ban` => hoi
GitHub, lay release moi nhat — tuc lenh mot nguoi met luc 1 gio sang se go lai
la lenh keo mot binary CHUA AI DO vao may dang phuc vu that.

Gio: mac dinh = ban ghim; `-Ban latest` phai go ra.

### `phien_ban_ghim.json` — va mot cho de TRONG co chu y

`llama_cpp.build = null`. Hai manh co that (`catalog.py` ghi `10689` cho lo do
03/09; `llamacpp.b10580` la thu muc SAO LUU tuc ban TRUOC) chi noi build dang
chay **moi hon b10580** — chung khong noi no la bao nhieu. Dien mot so trong
hop ly vao do la dung lai dung lop khuyet tat ca chuong trinh nay di sua.
Co chot rieng cam doan, va cam giu `vi_sao_null` sau khi da co so that.

### Nghiem thu hep
```
pytest test_983 test_250_llm_gateway test_257 test_270 -> 84 passed
10 chot tinh PASS
```

Diem: **W10 78 -> 98**

---

## PHASE 4 — quan trac . 2026-09-09

### Phat hien lon nhat: may B DEM ROI VUT DI

`/metrics` cua llama.cpp **tat theo mac dinh** (`server-context.cpp:4669`), va
macro `CHUNG` khong co `--metrics`. Nhung cac diem cong don chay **VO DIEU KIEN**
trong vong lap suy luan:

```
server-context.cpp:4066  metrics.add_prompt(...)
server-context.cpp:4072  metrics.n_decode++
server-context.cpp:3412  metrics.add_prompt_cached(n_past)
server-context.cpp:4129  metrics_on_prediction(slot)
```

=> Co `--metrics` chi gac **cua doc**. Bat len ton **0** tren duong nong. Va vi
`CHUNG` da bat `--spec-type draft-mtp`, no mo khoa luon
`llamacpp:spec_decode_num_accepted_tokens_per_pos_total` — ti le chap nhan suy
doan, mot trong nhung so W3 can, dang bi vut di cung.

### Cong tu dem: **chi** thu llama-server khong bao gio thay

Moi luot cong TU CHOI deu khong cham engine, nen khong co dong nao trong
`/metrics`. Su co 31/08 la vi du: **89/117** luot cua mot khach hong trong sau
gio, va `/metrics` cua engine hoan toan sach se suot sau gio do.

`/health` -> `dem`: tam nhom ket cuc, `phuc_vu`/`tu_choi`/`ti_le_tu_choi`, TTFT.

* **Ba loai 429 tach rieng.** Voi may A ca ba deu la `BanError` va do la DUNG.
  Nhung voi nguoi truc thi ba nhom doi ba hanh dong khac han: `ban_day` (suat
  chua tra / khach don), `ban_trong_tai` (ComfyUI-video giu card, cho la dung),
  `ban_card` (ComfyUI giu VRAM khong nha). Gop lam mot la vut di dung phan tra
  loi "toi phai lam gi bay gio".
* `ti_le_tu_choi` la **None** khi chua co luot nao, khong phai `0.0` — hai cau
  khac han nhau, va mot bang dieu khien hien `0%` cho cai thu hai la mot loi
  tran an khong co can cu.

### TTFT — hai cai bay, ca hai da chot bang test

1. **Boc TRONG `nhip_tim`, khong phai ngoai.** `nhip_tim` phat chu thich SSE moi
   15 giay **trong luc prefill**. Boc ngoai thi "khoi dau tien" la mot nhip tim
   va TTFT cua MOI luot dai deu ra ~15 giay — mot con so cuc ky on dinh va hoan
   toan vo nghia. Sai kieu nay **khong bao gio tu lo**: khong loi, khong hong,
   chi co mot phep do luon tra loi sai.
2. **Phai chuyen tiep `close()`.** `nhip_tim` goi `getattr(luong,"close")()`;
   mot generator chen vao giua ma khong chuyen tiep thi `LuongUpstream.close()`
   **khong bao gio chay** — dung hinh dang su co 31/08.

Va TTFT do tu luc **yeu cau vao cong**, khong phai luc mo luong: cho suat, don
card (toi 18 giay) va nap model (toi 2,5 phut) deu nam truoc do. Mot TTFT 150
giay ma engine bao "prefill 4 giay" thi so cua engine dung va **vo dung**.

### Rieng tu (§27)
Chi so, khong prompt, khong phan hoi, khong ten khach. llama-swap **co san**
`/api/captures/*` va ta co y khong dung. Co chot doi mot chuoi bi mat gui vao
khong duoc xuat hien o `/health`.

### KHONG lam
Khong Prometheus server, khong Grafana, khong Langfuse, khong kho ben thu hai
(llama-swap da co `/api/metrics/activity` ben). Ly le day du:
`docs/LLM_OPEN_SOURCE_RESEARCH.md` O6/O7/O8.

### Nghiem thu hep
```
cua_so_yen: RANH
pytest test_984 test_272 test_363 test_269 test_250 test_258 -> 145 passed
10 chot tinh PASS (ruff tung FAIL vi mot F401 cua chinh toi - da sua)
check_mypy dat moc
```

Diem: **W2 72 -> 98**

---

## PHASE 5 — phan loai loi . 2026-09-09

### D-005, di vao bang mot cua khong ai bit

Kho nay da bit rat ky cua **429**: `BanError` la lop ngoai le RIENG, khong ke
thua `CongVlmError`, vi neu lan thi `api_pool` phat khoa va "mot toi may B chay
video se tu tat vinh vien model nha".

Cua **het gio** thi chua ai bit. Duong di, do tren ma truoc 09/09:

```
httpx.TimeoutException  (CON cua HTTPError)
  -> upstream.json  bat `except httpx.HTTPError`   -> 599
  -> api.py         `if ma >= 500`                 -> **502**
  -> cong_vlm       `if ma != 200`                 -> **CongVlmError**
  -> dieu_phoi      `except CongVlmError`          -> **api_pool.danh_dau_loi()**
  -> api_pool       nhanh 5xx: error_count += 1
                    >= ERROR_TO_STATUS_THRESHOLD (5) -> status = APIKEY_ERROR
```

🔴 **Va `APIKEY_ERROR` KHONG TU HOI.** `api_pool._ung_vien()` bo moi khoa
`status != APIKEY_ACTIVE`, va cho tu hoi duy nhat la
`if k.status == APIKEY_COOLDOWN and cooldown_until <= now`. Khong nhanh nao dua
`APIKEY_ERROR` ve `ACTIVE`.

=> **Nam lan het gio la model nha tat, va no o lai tat** toi khi co nguoi sua tay.

⭐ Ma mot prompt 200K prefill hang phut la hanh vi **binh thuong** cua he nay:
   `catalog.py` do prefill 616-999 tok/s, tuc 180K token ~ 280 giay; cong nap
   model (toi 2,5 phut) va don card (toi 18 giay). Thu kich hoat tham hoa khong
   phai mot su co, ma la **cong viec hang ngay**.

⚠️ Toi da **dinh chinh mot gia dinh cua chinh minh** giua chung: ban dau toi viet
   "5 lan -> disable". Doc `api_pool` thi chi 401/403 moi `DISABLE`; 5xx dat
   `APIKEY_ERROR`. Nhe hon mot bac — nhung vi `APIKEY_ERROR` khong tu hoi, hau
   qua VAN la model nha tat cho toi khi co nguoi can thiep.

### Ban sua

```
upstream   tach MA_HET_GIO (598) khoi MA_KHONG_VOI_TOI (599)
api.py     598 -> 504 ; 599 va 5xx that -> van 502
cong_vlm   504 -> AmbiguousProviderError
dem.py     them nhom `het_gio`
```

⭐ **Dung lai `AmbiguousProviderError` chu khong de lop moi.** Ngu nghia da dung
   y het ("da gui di nhung khong biet ket qua"), va `dieu_phoi` san co nhanh
   `except (AmbiguousProviderError, ProviderOomError): raise` cho **hai** hanh vi
   can co: khong cascade (thuong nguon co the da bat dau sinh chu) va khong
   `danh_dau_loi`. Mot lop moi se phai chep lai ca hai, va ban chep se lech.

⛔ **Khong noi rong bang cach mien phat cho moi loi.** Khong voi toi hoac engine
   sap **la** hong that, va may A **nen** phat khoa o do — neu khong thi
   `api_pool` mat han kha nang nhan ra mot provider chet. Co chot rieng giu
   502 o lai `CongVlmError`.

### Doi chung
* `issubclass(httpx.TimeoutException, httpx.HTTPError)` — do that, vi ca ban sua
  dung tren menh de nay.
* Thu tu `except`: neu `HTTPError` dung TRUOC `TimeoutException` thi nhanh het
  gio **chet im lang** (lop cha nuot lop con) va khong phep kiem nao o tren do,
  vi chung tiem ma truc tiep. => co chot doc thu tu dong trong `upstream.py`.
* Nhanh `except AmbiguousProviderError` trong `dieu_phoi.goi` doc bang **AST**:
  khong `danh_dau_loi`, va phai re-raise.

### Ngoai pham vi — bao cao, KHONG sua
`APIKEY_ERROR` khong co duong tu hoi trong `api_pool`. Sua no la doi hanh vi
cua **toan nen tang** (moi provider, ke ca gemini) va cham ma sat tien. Ban sua
o tren da cat nguon sinh ra no tu phia LLM; con viec co nen cho `APIKEY_ERROR`
tu hoi sau mot khoang hay khong la mot quyet dinh rieng.

### Nghiem thu hep
```
cua_so_yen: RANH
pytest test_985 test_984 test_251_cong_vlm test_255 test_252 test_250 test_272
  -> 160 passed
10 chot tinh PASS (ruff tung FAIL vi `import json` thua cua chinh toi - da bo)
check_mypy dat moc
```

Diem: **W5 90 -> 98** · **W4 92 -> 98** (chot khoi dong P2 + hai duong tra suat
doc lap + `close()` nay co chot khi co lop boc moi + het gio da tach khoi hong)

---

## PHASE 6 — dieu phoi may A . 2026-09-09

### Ban va Phase 5 la MOT NUA, va nua bi bo quen la nua hay hong nhat

Phase 5 day **cua dong bo** (`cong_vlm.py`) doc 504 thanh
`AmbiguousProviderError`. Nhung `platform_core/llm/luong_vlm.py` la mot client
RIENG, va no co nhanh rieng:

```
if r.status_code >= 500:
    ...
    api_pool.danh_dau_loi(db, key, message=f"HTTP {r.status_code}")
```

`504 >= 500`. Nen sau Phase 5, cua dong bo duoc bao ve con cua streaming **van
phat khoa y nhu cu**.

🔴 Va **streaming la cua hay het gio nhat**: Codex/Claude Code chi noi SSE, va
   chung la thu gui prompt 100-200K. Cua dong bo bi Cloudflare cat ~100 giay nen
   khong ai gui viec dai qua do.

=> Ban va Phase 5, neu dung o `cong_vlm`, se **trong nhu da xong** trong khi no
   chua cham toi con duong ma khuyet tat that su di. Bo nho du an goi dung ten
   lop loi nay: *"pham vi phep do hep hon loi tuyen bo"*.

### Ban sua
`luong_vlm.KhongMoDuocLuong` co co `het_gio`; nhanh `== 504` dat **truoc** nhanh
`>= 500` (dat sau thi no chet im lang), khong `danh_dau_loi`, va **khong**
`ban=True` (ban hua "30 giay nua thu lai la duoc" — het gio khong hua duoc the).

### Mot ranh gioi CO Y khong vuot
Khach van nhan **503**, khong phai 504. Dua 504 ra toi khach doi mot **ma loi
moi trong hop dong Public API** (`CODE_*` + `_TITLES` + golden API + kiem tuong
thich + tai lieu) — mot thay doi be mat cong khai de doi lay mot sac thai ngu
nghia. Ba thu that su quan trong deu da dung o tang duoi: tien duoc hoan, khoa
khong bi phat, khong co vong thu lai. Ghi ra day thay vi lang le bo qua.

### Nghiem thu hep
`pytest test_986 test_985 test_272 test_600 test_259 -> 94 passed` · 7 chot tinh PASS

Diem: **W6 95 -> 98**

---

## PHASE 7 — tien o cua stream . 2026-09-09

### 💰 LO RO TIEN THAT, DO DUOC

`_phat` quyet toan trong `finally`. Nhung mot `finally` **chi ton tai sau khi
generator chay dong dau tien**. Do that 09/09:

```
g = _phat(mo, luot); g.close()   -> quyet_toan KHONG duoc goi
next(g); g.close()               -> quyet_toan DUOC goi
```

=> Khach ngat **truoc byte dau** thi khoan `hold` khong duoc ket so ngay.

⚠️ **DINH CHINH — ban dau toi viet "vinh vien", va do la NOI QUA.**
   `credit.tu_hoan_treo` (H41.3) CO quet khoan ay: cua stream truyen
   `request_id` lam `job_id`, va khong hang `Job` nao dang song mang khoa do,
   nen sau `TU_HOAN_SAU = 24 gio` no duoc hoan (tran 20 moi luot bao tri).
   => Hai that la **tien khach bi giu toi mot ngay cho mot luot khong chay**,
     khong phai mat tien. Ban va van dang lam: no bien 24 gio thanh TUC THI
     va quyet toan theo so DO DUOC thay vi cho mot bo quet.
   ⭐ Cach toi biet minh sai: chinh `test_363` — phep kiem ma ban va cua toi
     lam do — mang cau "tien treo duoc credit.tu_hoan_treo quet (H41.3)".

⭐ **Day la cung mot khuyet tat da duoc hoc mot lan, o mot tang khac.** Su co
   31/08 tren may B: `boc_luong` tra SUAT trong `finally`, generator khong khoi
   dong, suat bi giu vinh vien, cong tra 429 suot sau gio. Ban va o do la
   `BackgroundTask`. May A da hoc bai do cho **suat**
   (`admission.release_by_id` di qua `BackgroundTask`) nhung **khong** cho **tien**.

### Va `test_292` dang khang dinh dieu nguoc lai

Tep do viet: *"DOI CHIEU: cua streaming khong dinh, vi no quyet toan trong
`finally`."* Dung khi generator DA chay, sai khi no CHUA chay. Da dinh chinh
ngay trong tep, kem so do.

⚠️ Cau cu khong sai vi nguoi viet cau tha — no la mot **doi chieu khong duoc
   do**, dat canh mot phan da duoc do rat ky. Canh mot su that, mot loi tran an
   trong cung giong mot su that.

### Ban sua: HAI DUONG DOC LAP CHO CUNG MOT VIEC

```
duong 1  `finally` cua `_phat`                      — khi luong co chay
duong 2  `dam_bao_quyet_toan(luot)` tu BackgroundTask — ke ca khi than chua doc
```

`luot.da_quyet_toan` bao dam **chi mot** duong that su thu. Dung khuon may B da
dung (`Suat.tra()` + `dong()` idempotent, cong them chu khong thay the).

Va `_ket_thuc` la `try/finally`: nha suat nam trong `finally` de mot ngoai le o
duong TIEN khong lam ket SUAT — neu khong thi ban va nay de them dung su co 31/08.

### Ba ca da do
```
CA 1 generator chua tung chay -> finally khong thu; luoi thu  -> RO DA BIT
CA 2 generator da chay        -> finally thu; luoi im lang    -> KHONG THU 2 LAN
CA 3 goi luoi 4 lan           -> thu dung 1 lan               -> IDEMPOTENT
```

### Ba cua deu quyet toan theo so DO DUOC (da soat)
```
stream  quyet_toan(... dem.token_ra ...) trong finally + luoi an toan
dong bo thanh_toan.quyet_toan_hoac_hoan
job     features.gia_that_credit(); `do_duoc=False` -> tra 0
```
"Khong do duoc thi khong thu" duoc cuong che o ca ba.

### Nghiem thu hep
```
cua_so_yen: RANH
pytest test_987 test_292 test_600 test_272 test_253 test_313 -> 100 passed
10 chot tinh PASS · check_mypy dat moc
```

Diem: **W9 95 -> 98**

---

## PHASE 8 — hop dong baseline hieu nang . 2026-09-09

### Khoang trong that: co PHEP DO, khong co HOP DONG BASELINE

`tools/bench_llm_hieu_nang.py` **da** rat tot — chup `nvidia-smi` + `/health`
quanh moi luot, dung **trung vi** thay vi trung binh, tach nguoi khoi am, va
docstring cam chon luot dep. Khong sua gi o do.

Nhung no sinh ra mot **ket qua**, khong sinh ra mot **baseline**. Cau "ban nay
co cham hon ban truoc khong" chi tra loi duoc bang cach mo hai tep JSON doc bang
mat — dung cho nguoi ta vo tinh chon luot dep, tuc dung thu chinh cong cu ay cam.

### `tools/so_sanh_bench_llm.py`

Nguong lay dung §22: TTFT +15% · decode -10% · end-to-end +15%.

Ba tinh chat da chot, vi mot phep so **sai** van trong dung neu khong ai kiem:

* **Chieu tung chi so.** TTFT tang la xau, decode giam la xau. Nham chieu thi
  phep so se **an mung** dung luc he dang cham di.
* **Tu choi khi khong so duoc.** Khac model => DUNG LAI. §22: apple-to-apple.
  Va canh bao to khi so tien trinh GPU lech nhieu (do 31/08: **23 tien trinh**
  tren card) — khong chan, nhung phai noi ra, neu khong thi chenh lech do hang
  xom se bi doc thanh hoi quy cua ta.
* 🔴 **Baseline RONG khong duoc doc thanh KHONG HOI QUY.** Baseline rong cho 0
  dong so sanh va `hoi_quy = False`. In "PASS" o do la bien *"toi khong biet gi"*
  thanh *"moi thu on"*. `main()` tra **2** va khong in PASS.

### Khuon muon cua GuideLLM, cong cu thi khong

Muon **hinh dang ket xuat** (@ `f96d26b9`), khong muon phu thuoc: no la cong cu
Linux-truoc, may B la Windows, va thu ta thieu khong phai mot bo do ma la mot
hop dong baseline. §O3 cua bao cao nghien cuu.

### ⚠️ CHUA CHAY BENCHMARK THAT — va day la mot gioi han co y

Chay benchmark tren may B se chiem **suat dong thoi duy nhat** trong vai phut va
**da vang** ho so dang thuong tru. Do la mot hanh dong cham toi dich vu dang
chay, nen toi khong tu y lam. Cong cu da san sang; so baseline se duoc chup o
buoc final gate, khi co nguoi dong y cho phep.

⛔ Vi vay **W3 KHONG duoc cham 98**. Xem muc "Ngoai le da tuyen bo" o
   `LLM_QUALITY_LEDGER.md`.

### Nghiem thu hep
`pytest test_988 -> 15 passed`
