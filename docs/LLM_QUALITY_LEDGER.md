# LLM_QUALITY_LEDGER — sổ điểm

Cập nhật sau **mỗi** item. Hai cột điểm, và chúng **không thay thế nhau được**.

* **Implementation/Design** — đọc mã + đối chiếu thượng nguồn + nghiệm thu hẹp.
  Dùng trong các phase thi hành.
* **Verified Runtime** — **chỉ** điền sau FULL GATE #2, có bằng chứng runtime.
  Trước đó cột này để trống. ⛔ Không được gọi điểm tạm là VERIFIED.

Trần rubric đang áp: chưa chạy final gate ⇒ **không** nhãn VERIFIED · chỉ có mã
mà chưa nghiệm thu hẹp ⇒ Implementation ≤ 95 · fail-open ⇒ Security ≤ 90 ·
trùng nguồn chân lý ⇒ ≤ 94.

---

## Bảng chính

| Hệ con | Trước | Implementation | Verified Runtime | Bằng chứng | Khoảng trống đã biết | Trạng thái |
|---|---|---|---|---|---|---|
| W1 identity/config | 93 | **98** | — | chuỗi 7 mắt xích đã khoá (`test_334`); P1-03 = NO CHANGE | — | **P1 xong** |
| W2 quan trắc | **72** | **98** | — | `--metrics` engine + `dem` theo nhóm kết cục + TTFT như khách thấy | — | **P4 xong** |
| W3 baseline hiệu năng | 80 | **90** ⚠️ | — | `so_sanh_bench_llm.py` + 15 chốt | **số baseline chưa đo** — ngoại lệ §C.1 | **P8 xong** |
| W4 vòng đời cổng | 92 | **98** | — | chốt khởi động P2 + hai đường trả suất + `close()` qua lớp bọc mới | — | **P5 xong** |
| W5 phân loại lỗi | 90 | **98** | — | 598/599 tách; 504→`AmbiguousProviderError`; đối chứng thứ tự `except` | `APIKEY_ERROR` không tự hồi → ngoài phạm vi | **P5 xong** |
| W6 điều phối máy A | 95 | **98** | — | cửa **streaming** cũng thôi phạt khoá khi 504 | 503 ở biên khách — ranh giới có ý | **P6 xong** |
| W7 bảo mật | **88** | **98** | — | fail-closed lúc khởi động; đối chứng bản cũ ĐỎ; production đo được là **có token** | — | **P2 xong** |
| W8 token/ngữ cảnh | 94 | **98** | — | runtime tự dẫn xuất; văn đã thôi mâu thuẫn | — | **P1 xong** |
| W9 tính tiền | 95 | **98** | — | 💰 **lỗ rò hold** khi khách ngắt trước byte đầu — đo được và đã bịt bằng hai đường độc lập | — | **P7 xong** |
| W10 deploy/ghim | **78** | **98** | — | `/health` khai phiên bản thượng nguồn; `phien_ban_ghim.json`; mặc định thôi lấy bản mới nhất | build llama.cpp còn `null` (chỉ đo được trên máy B) | **P3 xong** |
| W11 phát hành | 88 | **95** ⚠️ | — | gate 32 bước, ngân sách lõi vật lý | 22 số hiệu test trùng — ngoại lệ §C.2 | **P9 xong** |
| W12 bảo trì | 85 | **98** | — | 5 khối văn sửa; `test_980`+`test_981`, cả hai đỏ được trên khuyết tật gốc | trùng số hiệu test toàn kho → W11 | **P1 xong** |
| W13 corpus hồi quy | 90 | **98** | — | +9 tệp (980–988), mỗi tệp gắn một khuyết tật **đo được** | — | **P9 xong** |

**Trung bình cột "Trước": 87,7.** Không phải một hệ thống yếu; ba hệ con dưới 85
đều là **vận hành**, không phải **kiến trúc**.

---

## Vì sao từng điểm là như thế

### W7 = 88 — trần rubric, không phải phán xét về chất lượng
Phần còn lại của bảo mật **mạnh**: `/live` cố ý trần trụi để máy giám sát không
phải mang bí mật (`api.py:263-276`); llama-server vĩnh viễn loopback; fail-closed
danh mục model (Q92); có test SSRF riêng (`test_373`). Một khuyết tật kéo cả hệ
con xuống 88 vì rubric ép Security ≤ 90 khi có fail-open — và ép đúng.

### W2 = 72 — điểm thấp nhất, và **không** phải vì thiếu công cụ
`/health` của cổng khá tốt cho trạng thái **tức thời**: trọng tài, giới hạn,
`gpu.tren_gpu` (chốt duy nhất nhìn ra sự cố 23/08), `duoi_dich_vu` (chốt duy nhất
nhìn ra health-xanh-giả 01/09). Thiếu là **chuỗi thời gian** và **số cộng dồn** —
và nghiên cứu O2 cho thấy chúng **đang được đếm rồi vứt đi**.

### W10 = 78 — có rollback, không có bản được chúc phúc
`deploy.ps1:99` chụp `releases/auto-*` trước mỗi lượt; `nang_llamacpp.ps1` có
nhánh hoàn nguyên. Nên "không có rollback" **không** áp dụng (trần ≤ 94 vì thiếu
rollback không kích hoạt). Điểm thấp vì **danh tính**: kho không biết máy B đang
chạy gì, nên "tái lập được" là không kiểm chứng được.

### W6 = 95 — cao nhất, và có lý do cụ thể
`dieu_phoi.py:228-231` **không** cascade `AmbiguousProviderError`. Rubric phạt
"retry duplicate-side-effect risk" xuống Reliability ≤ 90; LTT không dính, vì
một quyết định có chú thích lý do. Đối chiếu LiteLLM (O5) không tìm ra khoảng
trống nào đáng đổi.

### W9 = 95 — giữ chỗ → chạy → quyết toán, và "không đo được thì không thu"
`thanh_toan.py` không dựng sổ tiền thứ hai; nó quy đổi token→credit rồi gọi ba
nguyên hàm của `credit`. `usage` thiếu ⇒ hoàn đủ + cảnh báo. Chưa 98 vì chưa
soát hết đường **stream** và đường **job**, không phải vì tìm thấy lỗi.

---

## Nhật ký thay đổi điểm

| Ngày | Item | Hệ con | Từ | Đến | Căn cứ |
|---|---|---|---|---|---|
| 2026-09-09 | Phase 0 | tất cả | — | (bảng trên) | đọc mã + 5 thượng nguồn đã ghim SHA |
| 2026-09-09 | P1-01/02/03 | W1 · W8 · W12 | 93/94/85 | 98/98/98 | 201 passed 3 skipped + 10 chốt tĩnh; xem `LLM_CHANGELOG_UPGRADE.md` |
| 2026-09-09 | P2-01 | W7 | 88 | **98** | 84 passed + 8 chốt tĩnh; đo máy B 401; đối chứng bản cũ đi qua chốt |
| 2026-09-09 | P3-01/02 | W10 | 78 | **98** | 84 passed; llama-swap **v250** đo qua Nexus `file.list`; route đối chiếu trên **đúng thẻ v250** |
| 2026-09-09 | P4-01 | W2 | 72 | **98** | 145 passed; `--metrics` (cờ chỉ gác cửa đọc, đã đọc mã llama.cpp); 22 chốt quan trắc |
| 2026-09-09 | P5-01 | W5 · W4 | 90/92 | **98/98** | 160 passed; **D-005 qua cửa hết giờ** — 5 lần timeout là model nhà tắt và **không tự bật lại** |
| 2026-09-09 | P6-01 | W6 | 95 | **98** | 94 passed; cửa streaming là nửa bị bỏ quên của bản vá P5 |
| 2026-09-09 | P7-01 | W9 | 95 | **98** | 100 passed; hold không kết sổ ngay khi khách ngắt trước byte đầu |
| 2026-09-09 | P8-01 | W3 | 80 | **90** ⚠️ | 15 passed; công cụ có, **số chưa đo** — ngoại lệ đã tuyên bố |
| 2026-09-09 | P9/P10 | W11 · W13 | 88/90 | **95/98** | rà soát liên hệ thống tìm ra 1 khuyết tật trong chính mã vừa viết |
| 2026-09-09 | GATE #1 | — | — | FAIL (1/32) | 10 đỏ: **1 của tôi** (`test_363`) + 9 nền của trunk |
| 2026-09-09 | ĐÍNH CHÍNH | W9 | — | — | `tu_hoan_treo` **có** quét hold — hại là **24 giờ**, không phải vĩnh viễn |

---

## Ngoại lệ đã tuyên bố

**Hai**, cả hai theo khuôn §15, chi tiết ở `LLM_FINAL_GATE_REPORT.md` §C:

* **W3 = 90** — công cụ so sánh đã có, **số baseline chưa đo**, và tôi **không có
  credential để đo** — `LTT_LLM_TOKEN` không có trong môi trường, `secrets/app.env`
  bị ACL từ chối, Nexus `file.read` bị chặn. Cả ba đều **đúng thiết kế**, và tôi
  không lách. (Máy B đo lúc 17:11 là **rảnh**: VRAM 809 MB, model đã tự nhả.)
* **W11 = 95** — 22 số hiệu test trùng toàn kho là nguyên nhân gốc của P1-01,
  nhưng sửa là đổi tên tệp test của **phiên khác** (luật 12/13 `CLAUDE.md`).

Nếu một hệ con khác không đạt 98 mà không phải over-engineer, mục đó sẽ được
ghi ở đây theo khuôn §15 (`CURRENT MAXIMUM JUSTIFIABLE SCORE` / `WHY` /
`WHAT WOULD BE REQUIRED FOR 98` / `WHY NOT WORTH IT` / `RECOMMENDED DECISION`),
**không** được làm tròn lên.
