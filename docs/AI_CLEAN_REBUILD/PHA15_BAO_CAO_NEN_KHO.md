# Pha 15 — báo cáo nén kho, và những gì KHÔNG được nén vào một con số

**Ngày:** 2026-09-10 · chiến dịch **LTT AI CLEAN REBUILD V2**
**Trunk khi đóng:** `admin-mvp-v3` · **Production:** `84661047c2ae`

---

## 1. Cái đã gỡ — đo có phạm vi

```
21 tep xoa han      2.978 dong
```

⛔ **Con số ấy KHÔNG phải `git diff --shortstat` của cả nhánh.** Nhánh
`phien/aiclean` mang **51 commit** kể từ nền `0d1ffe5a`, trong đó chỉ khoảng
mười lăm là của chiến dịch này — số còn lại là LTT VOICE, WORKFLOW V2, VPS V2.
Lấy `328 files changed, +29.153/−5.524` rồi gán cho chiến dịch là **nhận công
của bốn phiên khác**, và tôi đã suýt làm đúng điều đó ở pha 12 khi một nền so
sánh quá rộng biến `frontend/agent-canvas/src/workflowApi.ts` của WORKFLOW V2
thành "một lỗ hổng của pha 08".

| Đã gỡ | |
|---|---|
| `apps/chataistudio/` | 9 tệp — bản chất là chat gọi ra pool Codex bên ngoài |
| `codex_sidecar/` + `codex_sidecar_main.py` | sidecar Codex |
| `platform_core/image_gen/dich_gemini.py` | lớp dịch prompt qua Gemini |
| `tools/doi_chung_gemini.py` · `tools/import_api_keys_from_botgemini.py` | công cụ đối chứng + nhập khoá |
| 6 tệp test của các đường đã gỡ | `test_83` · `118` · `119` · `162` · `251` · `255_doi_chung` |
| **4 nhà cung cấp** trong `providers.py` | `gemini` · `apiai` · `cheapkeyai` · `plenx` |
| **1 dịch vụ Windows** trên máy chủ | `LTTStudioCodex` |
| **3 khoá chết** trong `secrets\app.env` | `LTT_CODEX_SIDECAR_TOKEN` · `LTT_CODEX_SIDECAR_PORT` · `CODEX_SERVER_HOME` · và `GEMINI_API_KEY` |
| **4 khoá API đang SỐNG** trong CSDL production | `apiai` ×1 · `cheapkeyai` ×2 · `gemini` ×1 |

---

## 2. Thứ CỐ Ý giữ, và lý do là **cơ học** chứ không phải tình cảm

Bốn nhà cung cấp trên còn đúng ba dòng: `id`, `display_name`, `is_active=False`.
Không `base_url`, không `auth_style`, không `list_models_path`, không một
`ModelInfo` nào — tức **không còn mẩu công thức nào để dựng lại một lượt gọi**,
kể cả khi ai đó có sẵn khoá API.

Vì sao không xoá nốt ba dòng ấy:

```python
def da_ngung(provider_id):
    p = REGISTRY.get(provider_id)
    return p is not None and not p.is_active     # VANG MAT => False
```

⇒ Xoá hẳn dòng đăng ký thì `chan_neu_da_ngung("gemini")` **thôi ném**, tức cổng
fail-closed của pha 04 **im lặng mở ra**. Ở đây, xoá nốt dòng cuối không làm hệ
thống sạch hơn — nó gỡ mất **lời từ chối**. Cái còn lại không phải một đường
chạy; nó là một tấm biển *"đường này đã đóng"* mà cổng đọc được.

⚠️ **Cái mất, nói thẳng để đảo lại được bằng một commit:** `kling-3.0` và
`seedance-2.0-pro` rời khỏi catalog video khi PLENX nghỉ. BytePlus vẫn phục vụ
`seedance-2.0`, `-fast`, `-mini`, nên nhóm video không chết.

---

## 3. Cái đã CHỨNG MINH, và cái chỉ mới *tin*

| Mệnh đề | Bằng chứng | Hạng |
|---|---|---|
| Không còn lối ra tới 5 host đã gỡ | `test_1007` — bẫy ở tầng **socket** (3 cửa), kèm `test_BAY_that_su_no` | **đo được** |
| 0 occurrence executable trong 787 tệp mã | **hai bộ dò độc lập** (AST và tokenize), không dùng chung một dòng mã | **đo được** |
| `HISTORY_ONLY` không gọi được | `test_1005` — 150 phép kiểm, 5 điều kiện, đọc thẳng ma trận CSV | **đo được** |
| Rào kiến trúc | `test_1006` — 18 phép kiểm, **12 là tự kiểm** (mẫu dương + mẫu âm) | **đo được** |
| LTT_IMAGE sinh thật | job qua Public API → **ảnh 5.519.918 byte**, `held:3 charged:3`, `mode:"live"` | **đo được** |
| LTT_LLM Text | ba cửa `/chat/completions` · `/messages` · `/responses` đều 200 với token thật | **đo được** |
| Seedance/BytePlus | **lời xác nhận của chủ sản phẩm** rằng nó đang chạy thật | ⚠️ **không phải phép đo của chiến dịch** |
| **VLM** | `model=ltt_llm_vision`→`qwen38-vision`; ảnh **sinh bằng mã**, model trả `{"so_hinh_tron": 3, "chu": "K7QX"}` — khớp đáp án | **đo được** |
| **Voice** | job `7a0ea335` qua hàng đợi production → **8,48 giây tiếng, 814.124 byte RIFF/WAVE**; báo giá 2 = thu 2 | **đo được** |

⭐ **Hai dòng cuối đóng ngày 10/09**, và cách đóng đáng ghi lại: kế hoạch cũ định dùng
   `tools/danh_gia_vision.py` chạy **trên máy B**. Đọc kỹ thì công cụ ấy trả lời một câu
   **khác**: nó chấm **chất lượng** model. Câu chiến dịch cần là *“đường VLM có đi tới
   LTT_LLM và trả về thật không”* — một câu **không phụ thuộc** vào việc model trả lời
   đúng hay sai, và trả lời được từ **máy A** bằng một lượt gọi thật qua Public API.

⚠️ Và một lỗi của chính bộ kiểm VLM, ghi ra thay vì giấu: bước đầu của nó in *“không
   thấy `ltt_llm_vision` trong catalog”*. Đó là **bộ đọc của tôi sai hình dạng phản hồi**,
   không phải catalog thiếu — vì ngay sau đó lượt gọi với đúng model ấy trả 200 kèm
   usage thật. Một phát hiện giả, và nó chỉ lộ ra vì đọc tiếp thay vì dừng ở dòng đầu.

⛔ **Seedance vẫn KHÔNG được cộng điểm.** Nó rời khỏi phạm vi bằng lời xác nhận
của chủ sản phẩm, không bằng một lượt đo của chiến dịch — và bỏ bớt một dòng
chưa đo không biến những dòng còn lại thành đã đo. Một nghiệm thu tự nâng điểm
bằng cách **thu hẹp mẫu số** là một nghiệm thu đã hỏng.

⇒ Nên trục E2E là **9/10**, không phải 10/10: bốn đường đo được thì đã đo, còn
  đường thứ năm thì ta *tin*, và hai thứ đó không được viết cùng một chữ.

---

## 4. 🔴 Một lỗ THẬT mà chiến dịch chỉ tìm ra ở phút cuối

Sau khi mọi phép kiểm đã xanh và báo cáo đã viết, việc dọn **dữ liệu** lôi ra
thứ việc dọn **mã** không thấy:

```
apiai      ...KYJs   455 luot   dung cuoi 09/09 15:05:59
cheapkeyai ...3qUP   456 luot   dung cuoi 09/09 23:35:41   <-- dung giay mot job anh
cheapkeyai ...9Dbf   455 luot   dung cuoi 09/09 15:08:57
gemini     ...B3sk   455 luot   dung cuoi 09/09 15:10:54
```

`public_api/capacity.py::_providers_healthy` gọi `api_pool.chon_key()` **không
truyền `thu_tu_provider`**, nên nó quét mọi nhà cung cấp và chọn trúng một khoá
`cheapkeyai` — hàng khoá tự khai `categories` có `image`, **độc lập với Provider
Registry**.

Hậu quả không phải hiệu năng: `_providers_healthy` trả lời câu *"nền tảng còn
phục vụ nhóm này không"*, và câu ấy đi thẳng ra `/api/v1/capacity`. Nền tảng
**chào bán một năng lực không tồn tại**.

⭐ **Bài học của cả chiến dịch nằm ở đây:** mọi phép kiểm đều soi **mã**. Không
   phép kiểm nào soi **hàng trong bảng `api_keys`**. Một chiến dịch xoá provider
   mà chỉ đọc mã sẽ tuyên bố thành công trong khi bốn khoá của chính những
   provider ấy vẫn đang được cấp phát mỗi ngày.

Đã vá ở mã (`tests/test_1008`, 6 phép kiểm, một là đối chứng chạy lại **nguyên
văn thân hàm cũ** trên cùng dữ liệu), và xoá 4 hàng khỏi CSDL (có sao lưu).

---

## 5. NĂM việc NGOÀI PHẠM VI — báo cáo, không tự sửa

Gói chiến dịch dặn: *vấn đề ngoài phạm vi thì viết báo cáo, đừng mở rộng chiến
dịch*. Năm thứ dưới đây đều thật, đều không phải việc của chiến dịch này:

1. **`tools/i18n.py thieu` so `mtime`.** Sau bất kỳ lượt `ff`/`merge` nào nó có
   thể báo *"`.mo` cũ hơn `.po`"* thuần tuý vì **thứ tự git ghi hai tệp** —
   chênh lệch đo được là **2,7 mili giây**, trong khi nội dung khớp tuyệt đối
   (3404 msgid, thiếu 0 / thừa 0 / khác 0). Nó **không** phải bước gate
   `dich thieu ban EN` (bước ấy chạy `check_dich_thieu.py`, không đọc mtime).

2. **`tools/nghiem_thu_chat_l1.py` in một mệnh đề SAI.** Nó kết bằng
   *"mỗi cửa phải thu > 0 và khớp với usage báo cáo"* — nhưng chế độ tính tiền
   **mặc định là C3** (tích luỹ phần lẻ, chỉ thu phần nguyên), nên một lượt 67
   token **đúng ra phải thu 0**. Nó không `assert`, nên không đỏ giả; nó chỉ đẩy
   người đọc tới một kết luận sai. Tôi là người đọc ấy, và suýt báo một P0
   doanh thu không tồn tại.

3. **Hai docstring nói ngược nhau về chế độ mặc định.**
   `gia_token._san_moi_luot()` viết *"C1 là mặc định"*; `thanh_toan._san_moi_luot()`
   viết *"Mặc định KHÔNG"*. Hành vi thì nhất quán (cái trước uỷ quyền cho cái
   sau) — chỉ chú thích mâu thuẫn, và nó nằm trong tệp tự nhận là *"chỗ duy nhất
   được phép đại diện cho giá"*.

4. **`tools/check_ps_bien_trung_tham_so.py` — docstring và mã nói ngược nhau.**
   *(phát hiện của phiên `ltt-llm-api-http-guide-a3e123`, họ chủ động không tự sửa)*

   Docstring nói luật chỉ cấm gán tham số **trong thân vòng lặp** (nguyên văn:
   *"gan tham so ngoai vong lap = duoc"*), nhưng `kiem()` báo lỗi cho **mọi**
   phép gán trùng tên tham số ngoài mẫu miễn trừ `if (-not $X) { $X = ... }`.
   Nó chỉ đổi **nhãn vị trí** (`"than vong lap"` / `"cap ngoai"`), không đổi
   phán quyết.

   ⭐ Hai dữ kiện làm mục này **tự chứng minh**:
   - **ca dính thật**: `tools/quet_mtp.ps1:82-84` — ba phép gán ở **cấp ngoài
     cùng**, không vòng lặp nào. Docstring nói được, mã nói không.
   - và docstring **có lý do tốt** cho luật hẹp: nó kể lần chạy đầu báo nhầm
     `setup/cai_dich_vu_giong.ps1:42` (`if (-not $VenvRoot) { $VenvRoot = ... }`)
     rồi kết luận *"mot phep kiem bao dong o do se bi tat di trong mot tuan"*.

   ⇒ Tức **bản hẹp là bản đã được cân nhắc**, và phần thi hành mới là bản đi
     lệch. Đây là một **quyết định**, không phải một lỗi chính tả: nới mã cho
     khớp docstring là **hạ** một bánh cóc đang bảo vệ thật; sửa docstring cho
     khớp mã thì giữ nguyên mức bảo vệ. Hai hướng đi hai nơi khác hẳn nhau.

## 5c. 🔴 MỘT CẢNH BÁO TÔI ĐÃ ĐƯA RA, VÀ NÓ SAI

Chiến dịch đã hạ mốc `check_ruff` (09/09): `B904` 24→21, `F401` 416→415,
`F841` 25→23 — mức giảm đến từ 21 tệp chiến dịch xoá.

Tôi tự khai điều này như một **tác dụng phụ**, với lập luận: *"một cây chưa hoà
trunk vẫn mang đủ 21 tệp, nên số đếm vượt mốc mới và gate của nó đỏ ở một bước
nó không gây ra"*.

⛔ **Lập luận ấy sai**, và phiên `ltt-llm-api-http-guide` bắt được. Đo lại:

```
tools/check_ruff.moc la mot TEP DUOC GIT THEO DOI, moi nhanh giu ban rieng:
  admin-mvp-v3                          B904=21  F401=415  F841=23
  claude/ltt-llm-master-upgrade-ddcfc9  B904=26  F401=416  F841=25
```

⇒ Cây chưa hoà chạy **mốc của chính nó** với **mã của chính nó** — xanh. Khi hoà,
  nó nhận **cả hai cùng lúc**: mốc thấp hơn *và* 21 tệp đã xoá. Số đếm tụt cùng
  nhịp với mốc. **Không có cửa sổ nào để ai đỏ oan.**

⭐ **Vì sao tôi sai** mới đáng giữ: tôi **khớp mẫu** vào một bài học có thật —
   *"bản vá MỘT PHÍA phạt người sửa đúng"* — mà **không kiểm cơ chế này có cùng
   hình dạng không**. Bài học ấy đúng cho trạng thái **toàn cục** (một khoá, một
   bảng, một biến môi trường). Mốc ở đây không toàn cục — nó đi theo nhánh, tức
   đi **cùng** mã biện minh cho nó.

⇒ Luật đúng, hẹp hơn bản tôi viết lần đầu: **hạ mốc chỉ nguy hiểm khi mốc sống
  NGOÀI cây.** Thấy một bánh cóc đỏ ở cây chưa hoà thì **so mốc của hai nhánh
  trước, đừng chẩn đoán mã.**

## 5d. MỘT PHÉP KIỂM KHÔNG BAO GIỜ ĐỎ ĐƯỢC

*(ví dụ của phiên `ltt-llm-api-http-guide`, họ đề nghị ghi kèm tên)*

Họ dựng một "phép phân định" cho việc model trả về rỗng:

```
reasoning / predicted_n = 34.210 / 12.000 = 2,851
                           8.458 /  3.000 = 2,819     -> "ti le giu nguyen"
```

⛔ Tử số là **KÝ TỰ**, mẫu số là **TOKEN**. Đó là *ký tự trên một token* — một
   **hằng số của bộ tách token**, quanh 2,8 dù model làm gì. Một phép kiểm **không
   bao giờ đỏ được**, và màu xanh của nó được đọc thành bằng chứng.

⭐ Bằng chứng **đúng** nằm ngay trong cùng hai dòng và không cần chia gì:
   `predicted_n` chạm **đúng trần** ở cả hai mức (model bị cắt, không tự dừng), và
   `ky_tu_content = 0` ở **cả hai** — nhân ngân sách bốn lần, khách vẫn nhận 0 ký tự.

Họ tự rút ở `4b89bf94` sau khi phiên `ltt-voice-98-upgrade` bắt được.

### ⭐ Bốn biến thể, một gốc

| Ai | Sai ở đâu |
|---|---|
| họ | `git log -- <tệp>` **quá hẹp** → *"không có commit sửa"* đọc thành *"chưa sửa"* |
| tôi | `git diff 0d1ffe5a..HEAD` **quá rộng** → suýt báo một lỗ hổng của pha 08 |
| họ | ký tự / token — **đúng đơn vị, sai đại lượng** |
| tôi | §5c — **khớp mẫu vào một bài học đúng, cho một cơ chế khác hình dạng** |

Gốc chung: **hỏi một câu gần đúng rồi nhận câu trả lời như thể nó là câu mình
muốn hỏi.**

5. **Bước `ky tu dieu khien` chỉ nằm trong gate đầy đủ, không trong `pre-commit`.**

   Ca thật, và cái giá chia không đều: **một byte của tôi** (`0x07`, §5e) đi
   qua `pre-commit` — bốn bánh cóc chạy lúc commit **không** có bước ấy — rồi
   nổ ở **lượt gate của phiên khác**, sau khi họ ff trunk. Họ mất thời gian
   tìm trong thay đổi của **chính họ** trước khi thấy nó không phải của mình.

   ⭐ Cách đặt vấn đề hay nhất đến từ phiên `auto-scan-video-analysis-plan`,
      tức chính người trả giá: *“đó là một **tính chất của hàng rào**, không
      phải một lần bất cẩn của bạn. Người ff sau luôn là người trả giá cho
      khoảng cách ấy — đó là thứ đáng sửa ở hàng rào, không phải ở người.”*

   ⛔ **Cả hai phiên đều không tự sửa, và cùng một lý do:**
      `.pre-commit-config.yaml` là tệp **dùng chung**, và thêm một bước vào đó
      làm chậm **mọi lượt commit của mọi phiên**. Đó là một **đánh đổi** thuộc
      về chủ dự án, không phải một **lỗi** thuộc về phiên nào phát hiện ra nó.

### Và một phép đo đóng lại nghi vấn "thu 0"

```
mcredit_du = 61        (>0 => phan le DA vao so)
hold -1 / settle +1  x3  => giu 1 credit, hoan 1, rong 0
```

Không có lỗ doanh thu. Kết luận này đến từ **sổ sách production**, không từ một
lần đọc mã.

---

## 5b. Bước gate TỰ BỎ QUA — biến một dấu hỏi thành một phép đo

Lượt gate cuối còn **1 bước tự bỏ qua**: `bat bien da tien trinh`.

Lý do là **cấu trúc, không phải thiếu sót**: `check_multiproc.py` đọc
`LTT_DATABASE_URL` từ `C:\LTTPlatform\secrets\app.env`, mà thư mục đó đã siết về
SYSTEM+Administrators từ 27/08. Gate chạy không quyền nâng ⇒ không đọc được ⇒ bỏ
qua. Chính công cụ in ra: *"Đó **KHÔNG** phải lỗi."*

⭐ Nhưng *"bỏ qua có lý do"* vẫn là một **dấu hỏi**, không phải một phép đo. Và
   `gate.py` biết điều đó — chúnh nó giữ một **trạng thái thứ ba** riêng cho việc
   bỏ qua, sau khi đo được 31/08 rằng *"một bước bỏ qua và một bước đạt trông **Y
   HỆT nhau** trên dòng RESULT"*.

Đã chạy tay 10/09 03:5x, với một CSDL **vứt đi** tự tạo (tên chứa chữ `test` —
`tests/pg_scratch.py` từ chối mọi URL không chứng minh được nó vứt đi được, vì các
test này gọi `drop_all()`):

```
tools/check_multiproc.py  ->  7 passed in 139.55s   exit = 0
```

⇒ Bất biến mà bước ấy canh — *"nhiều worker chạy cùng lúc thì cảnh báo không
  nhân đôi và số credit khớp"* — **đứng vững trên PostgreSQL thật**.

## 5e. 🔴 ĐÍNH CHÍNH: tôi đã giải thích một triệu chứng bằng SAI nguyên nhân

Suốt đêm 09–10/09, `cua_so_yen trang-thai` trả `RANH` **ba lần** trong khi đang có
gate chạy. Tôi kết luận nó *"trả lời câu có ai XIN khoá, không trả lời câu có gì
đang CHẠY"*, rồi **gửi kết luận ấy cho ba phiên khác** như một lời khuyên.

⛔ Mệnh đề ấy đúng về cơ chế, nhưng **không phải nguyên nhân**. Phiên
   `ltt-4bot-workflow-app` đo ra nguyên nhân thật, và tôi **tái hiện độc lập** trên
   cây trunk: fixture `khoa_sach` (`tests/test_394_nen_da_phien.py`) gọi
   `dang_giu()` — liệt kê **mọi** khoá trên máy — rồi `nha(ep=True)` từng cái,
   không monkeypatch `TEP_KHOA`. Nó **xoá khoá thật của máy**, kể cả khoá của phiên
   khác đang chạy.

Đối chứng hai chiều, tôi tự chạy:

```
truoc va:  giu khoa True -> pytest 31 passed -> khoa con: False   BI THAO
sau  va:   giu khoa True -> pytest 32 passed -> khoa con: True    SONG SOT
```

⭐ `31 passed` là phần đáng sợ nhất: bộ test **XANH** trong khi nó xoá hàng rào
   đồng thời của cả máy. Họ đo được: khoá vắng **119 giây / lượt 756 giây = 84%**.

Đã vá trên trunk `5694f90c` (cherry-pick `56dfc811` + `598108be` của họ).

### 🔑 Bài học, và nó đắt hơn bản vá

Tôi giải thích một **triệu chứng** bằng một **tính chất có thật nhưng không liên
quan**, và vì lời giải thích ấy nghe rất đúng nên tôi **ngừng điều tra**.

⇒ Dấu hiệu đáng lẽ phải làm tôi đi tiếp: khoá không chỉ *"không thấy"* mà **TỆP
  BIẾN MẤT**. Một công cụ trả lời sai câu thì vẫn để lại tệp; tệp biến mất là một
  sự kiện **khác hạng** — và tôi đã không hỏi *"ai xoá nó"*.

⚠️ Ba phép đo tôi gửi đi đêm nay đều **đúng**; thứ sai là **lời giải thích** đi kèm.
   Một con số đúng với một nguyên nhân sai vẫn làm người đọc đi sai hướng — và nó
   đi xa hơn một con số sai, vì không ai kiểm lại một con số đúng.

## 5f. ⚠️ RANH GIỚI CỦA CÂU “ĐÃ GỠ GEMINI”

Phiên `ltt-4bot-workflow-app` báo (10/09): trong cấu hình **đang chạy** của
bot dựng video ở `D:\FULL AUTO VIDEO\DUNGVIDEO-FULL\`, khoá `evaluation.gemini_api_key` nằm dưới
dạng **văn bản thuần**, giá trị đầy đủ. Họ không chép giá trị đi đâu, không
đụng cây ấy, và đã báo chủ dự án.

⛔ **Đây KHÔNG thuộc phạm vi chiến dịch, và tôi cố ý không đưa nó vào danh
   mục ở §1.** Đó là một **hệ thống khác**, không phải `D:\LTTSTUDIOSAPP`.
   Đưa nó vào sẽ khiến báo cáo **tuyên bố một phạm vi nó không có** — đúng
   kiểu lỗi mà chính báo cáo này đang đi đếm ở những mục khác.

⭐ Nhưng ghi con trỏ này vì một lý do cụ thể: người đọc sau rất dễ rút gọn cả
   chiến dịch thành câu *“đã gỡ Gemini”*, rồi hiểu nó thành *“máy này không
   còn khoá Gemini nào”*. Hai câu ấy **khác nhau**, và câu thứ hai **sai**.

⇒ Thứ chiến dịch thực sự chứng minh, đúng phạm vi của nó: **nền tảng LTT**
  không còn đường gọi, không còn khoá trong `secrets\app.env` (4→0), và
  không còn khoá trong bảng `api_keys` (4 khoá **đang sống** → 0). Xoay khoá
  của một hệ thống khác là quyết định của chủ dự án.

## 5g. ⭐ HAI LOẠI CHỐT, HAI CÁCH ĐẶT NGƯỠNG

Khi thêm `test_BA_TAP_NEN_khong_duoc_rong` (đặt `DA_XOA >= 4` trên mức thật 5),
phiên `auto-scan-video-analysis-plan` nêu ra một phân biệt đáng giữ:

| | Bánh cóc | Đối chứng chống-xanh-rỗng |
|---|---|---|
| Chốt cái gì | **TẬP HỢP** | **sự tồn tại** của tập |
| Khi tập đổi | phải sửa, và **bản sửa hiện trong diff** | không được phải sửa |
| Ai review | người đọc diff thấy ngay | **không ai** — `assert len(...) >= N` trông vô hại |
| Nên canh | sự **thay đổi** | sự **sụp đổ** |

⇒ Đó là lý do ngưỡng đặt **thấp hơn nhiều** mức thật. Một `>= 4` trên mức 5
  không bắt ai sửa khi danh sách thêm một mục, nhưng vẫn nổ khi tập sụp xuống
  rỗng. Ngược lại, một `>= 5` sát mức thật sẽ bắt sửa thường xuyên — và **một
  phép kiểm phải sửa thường xuyên là một phép kiểm sắp bị ai đó vô hiệu hoá.**

### ⚠️ Và luật ấy quay lại cắn chính người viết ra nó

Họ viết luật *“phải có mệnh đề dương”* trong một tin nhắn gửi tôi, rồi đi soát
lại và thấy **chính họ** vừa vi phạm nó hai giờ trước ở `test_466`: hai `not in`
đứng một mình, không kèm khẳng định nào rằng chuỗi lọc **có tồn tại**.

⭐ Và thứ bắt được nó không phải họ tự nhìn, mà là việc tôi đi soát **năm phép
   kiểm của mình** theo luật của họ rồi **kể lại kết quả** — cả phần tôi thiếu.
   Một luật được phát biểu thì dễ đồng ý; nó chỉ bắt đầu bắt được lỗi khi có
   người **áp nó vào một danh sách cụ thể và công bố số đếm**.

## 6. Nén kho

| | Trước | Sau |
|---|---|---|
| Nhánh remote | 25 | **10** |
| Nhà cung cấp ngoài còn gọi được | 5 | **1** (BytePlus) |
| Khoá API legacy trong CSDL | 4 | **0** |
| Khoá legacy trong `app.env` | 4 | **0** |
| Dịch vụ Windows của đường đã gỡ | 1 | **0** |

Chi tiết pha 14 và sổ khôi phục từng nhánh: `PHA14_DON_NHANH_REMOTE.md`.
