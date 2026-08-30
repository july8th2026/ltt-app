# API Expansion V2 — kế hoạch triển khai

**Lập 2026-08-30.** Nguồn yêu cầu: `LTT_API_EXPANSION_V2_PROMPT_PACK` (18 tệp,
9 phase). Gói đó tự cấm coi nó là nguồn chân lý, nên mọi dòng dưới đây **đo từ
code đang chạy**, và chỗ nào chưa đo thì nói rõ là chưa đo.

> Đây là **kế hoạch**, chưa phải thi hành. Phase 01 của gói (discovery) đã làm
> đủ để lập kế hoạch; các tệp `01_CURRENT_TRUTH.md` / `02_OPTIONS…` sẽ viết đầy
> đủ khi bắt đầu thi hành.

---

## 1. Current truth — đo được, không phỏng đoán

### 1.1 Bốn tool đang mở (hỏi `GET /api/v1/tools`, 30/08)

```
image.ltt        ASYNC_JOB
text.chat        ASYNC_JOB
video.subtitle   ASYNC_JOB   (mo 29/08)
video.upscale    ASYNC_JOB   (mo 29/08)
```

### 1.2 Hai mục tiêu của gói, trạng thái thật

| | `video.generate` (Seedance) | Codex bridge |
|---|---|---|
| Mã có chưa | ✅ `apps/taovideo/` — manifest, `modelark.py`, submit→poll, `cost.py`, `quotes.py`, `refs.py` | ✅ `codex_sidecar/` (server+runtime) + `apps/chataistudio/` |
| ToolSpec | ✅ `video.generate`, `job_type="taovideo.generate"` | ❌ `job_types=()` — chat chạy trong tiến trình web |
| Đã mở API | ❌ **ĐÓNG** | ❌ chưa có ToolSpec công khai |
| Lý do chặn *(theo `APP_API_COVERAGE_FINAL.md`)* | *"Tập tuỳ chọn hợp lệ đổi theo model, chưa publish được một hợp đồng đúng."* | *"Cần một hợp đồng chạy mới, không phải một tool mới."* |

### 1.3 🔴 Phát hiện làm đổi hình dạng kế hoạch

**Lý do chặn của `chataistudio` đã LỖI THỜI.** Nó viết trước H38.

`platform_core/public_api/protocol.py` nay có `STREAM` trong `MODES_IN_USE`, và
`server/api/streaming.py:486` gác luồng bằng **chính ba cổng của tool**:

```python
tool = require_tool(build_catalog(config), TOOL_CHAT, principal)
```

Nghĩa là **hợp đồng chạy streaming đã tồn tại và đã sống** — nó dựng cho
`ltt_llm`, nhưng nó khoá theo một ToolSpec chứ không hardcode cho `ltt_llm`. Đo
thật qua Cloudflare 30/08: `/v1/messages` và `/v1/responses` trả
`text/event-stream`, 66 và 63 khối SSE.

⇒ **Rào cản còn lại của Codex bridge là CHÍNH SÁCH, không phải kiến trúc.** Đó
là kết luận quan trọng nhất của phase discovery này, và nó ngược với hồ sơ cũ.

### 1.4 Giá của Chat AI Studio — đã đúng khuôn gói yêu cầu

`apps/chataistudio/cost.py` ghi rõ: nhà cung cấp **không** đưa chi phí token
(tính theo quota tuần của tài khoản), nên credit ở đây là **giá bán ta đặt**,
phẳng. Gói V2 §4 Prompt 04 cấm *"giả token count để thu tiền"* — mô hình hiện
tại **đã** tuân thủ. Không phải xây lại.

---

## 2. Rủi ro phải nói trước, vì nó quyết định có nên đầu tư hay không

⚠️ **Hạng mục Codex bridge có thể xong hoàn hảo về kỹ thuật mà vẫn không bán
được.**

Mô hình đích là: một tài khoản ChatGPT/Codex cá nhân đăng nhập bằng Auth, rồi
LTT bán quyền gọi runtime đó cho **khách bên ngoài** bằng khoá LTT. Điều khoản
của OpenAI hạn chế việc chia sẻ/bán lại quyền truy cập tài khoản và việc lách
giới hạn sử dụng — `EXTERNAL_POLICY_NOTE.md` của chính gói đã nêu.

⭐ Gói đã dựng sẵn khuôn đúng để xử việc này, và tôi theo nguyên văn: tách
`TECHNICALLY_READY` khỏi `COMMERCIAL_RELEASE_ALLOWED`, và nếu chính sách chưa
rõ thì ghi `BLOCKED_POLICY` chứ **không** tự đổi kiến trúc Auth, **không** làm
xoay tài khoản.

⇒ **Hệ quả cho thứ tự làm:** đây là lý do Codex xuống sau cùng trong kế hoạch
dưới — không phải vì nó khó hơn, mà vì **giá trị thương mại của nó chưa chắc
tồn tại**, trong khi Seedance thì chắc chắn có.

*(Đây là ý kiến kỹ thuật, không phải tư vấn pháp lý. Chủ sản phẩm quyết.)*

---

## 3. Kế hoạch — ba đợt, xếp theo **giá trị chắc chắn trên rủi ro**

### Đợt A — `video.generate` (Seedance) ra công khai

**Vì sao trước:** mã đã có đủ (submit→poll, giá, refs, artifact), rào cản đã
được chẩn đoán chính xác và **repo đã tự đề xuất cách sửa** ở
`APP_API_COVERAGE_FINAL.md` dòng 210: *"Cho `models` khai luôn tập giá trị hợp
lệ riêng, thay vì publish hợp nhất."* Trùng khớp với Prompt 03 §1. Không vướng
chính sách nào.

| # | Việc | Nghiệm thu |
|---|---|---|
| A1 | Hợp đồng **tuỳ chọn theo model**: mỗi model khai tập `resolution`/`duration`/`aspect_ratio`/audio/ref hợp lệ **của riêng nó**, dạng máy đọc được | `/api/v1/tools` trả ràng buộc theo model; tài liệu **sinh ra** từ đó, không parse văn xuôi |
| A2 | Thứ tự kiểm: tổ hợp sai bị từ chối **trước** quote/hold/dispatch | test tổ hợp hợp lệ và không hợp lệ; **không** bút toán nào phát sinh ở lượt sai |
| A3 | Media đầu vào: chỉ mở loại đã có ownership + vòng đời an toàn; loại chưa an toàn thì **hoãn có ghi**, không bỏ qua kiểm | test upload ownership; loại hoãn được liệt kê |
| A4 | Giá: dùng nguyên `apps/taovideo/cost.py`, **không** bảng giá thứ hai ở tầng API | quote = giá job thật; test trần giữ chỗ |
| A5 | Mở ba cổng Q92 + cập nhật `APP_API_COVERAGE_FINAL.md` (test_212 đọc nó hai chiều) | gate xanh; `contract_hash` mới đã ghi CHANGELOG + `--accept` |
| A6 | Canary bằng credential thật, **hoặc** ghi `BLOCKED_EXTERNAL** | không giả PASS |

⚠️ **Bẫy đã biết, đừng dẫm lại:** ba tool video trước đã dính Q84 — giá theo
`duration_s` **khách khai**, worker đo lại rồi nâng hold, tức báo giá đã ký vẫn
quyết toán cao hơn. H35.10a+b đóng nó bằng cách **máy chủ đo** thời lượng lúc
báo giá. `video.generate` phải theo cùng luật đó ngay từ đầu.

---

### Đợt B — Developer API Center

**Trạng thái: đã làm được ~60% trong ngày 30/08**, cần nói rõ để khỏi làm lại:

- ✅ Con số cửa sổ ngữ cảnh nay **sinh ra** từ `apps/ltt_llm/ngan_sach.py`; đã
  dẹp 6 chỗ gõ tay nói ba giá trị mâu thuẫn.
- ✅ `DEVELOPER_GUIDE.md` **sinh** từ manifest (`tools/build_public_api_docs.py`).
- ✅ Bảng **ba cửa** (`examples.BA_CUA`) đã ra trang công khai `/huong-dan`.
- ✅ `HUONG_DAN_CAM_CLI.md` có `model_catalog_json`, `CLAUDE_CODE_MAX_*`, và
  **§2.6 Gỡ ra** (mục trước đây không tồn tại).

Còn lại:

| # | Việc | Nghiệm thu |
|---|---|---|
| ~~B1~~ | 🔴 **RÚT — khuyến nghị này SAI.** Tôi đề xuất mở một trang danh mục công khai, nhưng chủ sản phẩm **đã chốt hai lần** rằng *toàn bộ `/developers/*` đứng sau đăng nhập* (`QUY_CHUAN_TRANG_TAI_LIEU_API.md` §1), và mã có bánh cóc hai chiều quanh chốt đó. Xem `02_OPTIONS` §5. | — |
| B2 | Mỗi tool/model/capability có: route, hình dạng request, ví dụ chạy được, giá, chế độ thi hành | ví dụ trong tài liệu **chạy được** ở test-mode |
| B3 | Không danh sách thứ hai — mọi thứ từ registry/contract | bánh cóc: gate đỏ nếu có danh sách gõ tay |

---

### Đợt C — Codex Auth bridge *(chỉ làm sau khi chủ sản phẩm quyết chính sách)*

**Kiến trúc rẻ hơn dự kiến** nhờ mục 1.3: không cần "hợp đồng chạy mới".

| # | Việc | Nghiệm thu |
|---|---|---|
| C1 | Khai một ToolSpec cho năng lực Codex, chế độ `STREAM`, đi qua `require_tool` như `text.chat` | ba cổng Q92 hoạt động; tắt cờ là biến mất |
| C2 | Máy trạng thái sức khoẻ Auth (chưa đăng nhập / sẵn sàng / hết hạn / bị giới hạn / hỏng) | test từng trạng thái |
| C3 | **Cô lập** thread theo principal LTT; có luật dọn/lưu giữ | test khách A không thấy ngữ cảnh khách B |
| C4 | Admission: dùng `rate-limits` của sidecar; hết capacity thì **fail trước khi chạm tiền** | test đồng thời |
| C5 | Không rò: token ChatGPT, `CODEX_HOME`, bearer sidecar, đường dẫn tệp | test redaction ở log và ở thân lỗi |
| C6 | Giá: dùng nguyên `chataistudio/cost.py` (phẳng, có căn cứ), **không** bịa token | test quyết toán |
| C7 | Ảnh: chỉ mở nếu promote sạch sang artifact; chưa sạch thì `CODEX_IMAGE_DEFERRED` | không có URL filesystem công khai |
| C8 | Báo cáo **hai trạng thái tách rời** | `TECHNICALLY_READY` ≠ `COMMERCIAL_RELEASE_ALLOWED` |

---

## 4. Bất biến áp cho cả ba đợt

Lấy từ `[INVARIANT]` của gói, đối chiếu với luật sẵn có của repo:

1. **Không hàng đợi / sổ tiền / storage thứ hai** — dùng `jobs`, `credit`,
   `upload_sessions`, `storage` đang có (đây cũng là luật của H35).
2. **Fail-closed** — `LTT_PUBLIC_API_TOOLS` rỗng thì không tool nào mở;
   `customer_visible` **không** phải cờ public (Q92).
3. **Không lộ bí mật** — kể cả trong thông điệp lỗi.
4. **Không thu tiền hai lần** — `Idempotency-Key`, giữ chỗ → quyết toán → hoàn.
5. **24 route đóng băng** ở `server/api/inventory.py`, so hai chiều.
6. **Đổi tool đang mở ⇒ cập nhật `APP_API_COVERAGE_FINAL.md`** — `test_212` đọc
   nó như dữ liệu.
7. `ho_so_he_thong.txt` sinh lại bằng generator chính thức sau khi xong.

---

## 5. Đề nghị

**Làm đợt A trước, một mình.** Nó là hạng mục duy nhất có giá trị thương mại
chắc chắn, rào cản đã chẩn đoán xong, và cách sửa đã được chính repo đề xuất.

**Đợt B chạy song song được** — nó không đụng tiền, và phần khó nhất (một nguồn
chân lý cho số công bố) đã xong hôm nay.

**Đợt C chờ một quyết định của chủ sản phẩm**, không chờ thêm code. Câu hỏi cần
trả lời trước khi viết dòng nào: *ta có được phép bán quyền gọi một tài khoản
ChatGPT cá nhân cho khách bên ngoài không?* Nếu câu trả lời là không, phần kỹ
thuật vẫn có thể làm cho **nội bộ** — nhưng đó là một sản phẩm khác, và nên
biết điều đó **trước** khi đầu tư.
