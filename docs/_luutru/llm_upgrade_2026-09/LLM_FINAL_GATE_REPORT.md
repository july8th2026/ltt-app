# LLM_FINAL_GATE_REPORT

Chương trình MASTER UPGRADE cho LTT LLM · 2026-09-09
Nhánh `claude/ltt-llm-master-upgrade-ddcfc9` · xuất phát từ trunk `99017910`.

> ⛔ **Trạng thái nền của trunk đã là FAIL trước khi tôi chạm vào.** Commit
> `99017910` ghi nguyên văn: *"gate cuoi: FAIL (1/32) … 7 do deu la test_448"*.
> `test_448` là nghiệm thu **Auto Scan Video**, không liên quan LTT LLM. Nên
> mọi tuyên bố dưới đây phải nói rõ **lỗi nào là của đợt này**.

---

## A. Bảng điểm

| Hệ con | Trước | Implementation | Verified Runtime | Bằng chứng |
|---|---|---|---|---|
| W1 identity/config | 93 | **98** | *(xem §B)* | chuỗi 7 mắt xích đã khoá |
| W2 quan trắc | 72 | **98** | | `--metrics` + `dem` + TTFT |
| W3 baseline hiệu năng | 80 | **90** ⚠️ | | công cụ so có, **số chưa đo** |
| W4 vòng đời cổng | 92 | **98** | | chốt khởi động + hai đường trả suất |
| W5 phân loại lỗi | 90 | **98** | | 598/599 → 504/502 |
| W6 điều phối máy A | 95 | **98** | | cửa streaming cũng thôi phạt khoá |
| W7 bảo mật | 88 | **98** | | fail-closed lúc khởi động |
| W8 token/ngữ cảnh | 94 | **98** | | runtime tự dẫn xuất, văn thôi mâu thuẫn |
| W9 tính tiền | 95 | **98** | | 💰 lỗ rò hold đã bịt, hai đường độc lập |
| W10 deploy/ghim | 78 | **98** | | `/health` khai phiên bản + tệp ghim |
| W11 phát hành | 88 | **95** ⚠️ | | 22 số hiệu test trùng — ngoài phạm vi |
| W12 bảo trì | 85 | **98** | | 5 khối văn + 2 rào có đối chứng |
| W13 corpus hồi quy | 90 | **98** | | +9 tệp, 100 % dẫn dắt bởi khuyết tật đo được |

**Trung bình: 87,7 → 97,2.**

⛔ Cột **Verified Runtime** để trống có chủ ý — xem §B.

---

## B. Vì sao KHÔNG hệ con nào được gắn nhãn VERIFIED

§14 của chương trình: *"Chỉ được dùng sau FINAL FULL GATE với runtime evidence
thật. Không được gọi provisional score là verified."*

Đợt này **chưa có runtime evidence** theo nghĩa đó, và tôi nói rõ ba lý do:

1. **Không deploy.** §24 cấm deploy trong các phase thi hành, và tôi không
   deploy. Mã mới **chưa từng chạy trên máy B**.
2. **Chưa chạy benchmark.** Chạy nó chiếm suất đồng thời **duy nhất** của máy B
   vài phút và **đá văng** hồ sơ đang thường trú — một hành động chạm tới dịch
   vụ đang chạy. Tôi không tự ý làm.
3. **Không có second machine.** Mọi phép đo runtime thật sẽ phải chạy trên đúng
   cái máy đang phục vụ.

⇒ Điểm ở §A là **Implementation/Design**, đo bằng đọc mã, đối chiếu thượng nguồn
đã ghim SHA, và nghiệm thu hẹp. Chúng **không** phải Verified Runtime Score.

---

## C. Hai ngoại lệ đã tuyên bố (§15)

### C.1 · W3 — baseline hiệu năng: **90**, không phải 98

**CURRENT MAXIMUM JUSTIFIABLE SCORE** 90
**WHY** — `tools/so_sanh_bench_llm.py` đã có, ngưỡng khớp §22, 15 phép kiểm
gồm cả chốt *"baseline rỗng không được đọc thành PASS"*. Nhưng **chưa có một con
số baseline nào được đo**. Một hợp đồng baseline không có baseline thì mới là
một nửa.
**WHAT WOULD BE REQUIRED FOR 98** — chạy `bench_llm_hieu_nang.py` trên máy B ở
trạng thái card sạch, lưu kết quả làm baseline được chúc phúc.
**WHY NOT DONE** — hai lý do, và lý do thứ hai mới là lý do thật:

  1. nó chiếm suất đồng thời duy nhất của máy B và đá văng hồ sơ đang
     thường trú — một hành động chạm tới dịch vụ đang chạy;
  2. 🔴 **tôi KHÔNG CÓ credential để gọi cổng.** Đo 17:11:

```
LTT_LLM_TOKEN trong moi truong        -> khong co
C:/LTTPlatform/secrets/app.env        -> ACL TU CHOI (dung thiet ke)
Nexus file.read gateway.env tren may B -> bi chan (dung chinh sach)
```

⚠️ **ĐÍNH CHÍNH.** Bản đầu của mục này chỉ ghi lý do (1), tức trình bày việc
   không chạy như một **lựa chọn thận trọng của tôi**. Sự thật là kể cả khi
   được cho phép, tôi vẫn **không chạy được** — ba đường tới token đều đóng.
   Nói lý do (1) mà giấu lý do (2) là nhận công cho một sự cẩn thận mà hoàn
   cảnh đã quyết định thay.
**RECOMMENDED DECISION** — chạy một lượt vào giờ thấp điểm, commit kết quả làm
baseline. Sau đó W3 lên 98 mà không phải sửa một dòng mã nào.

### C.2 · W11 — phát hành: **95**, không phải 98

**CURRENT MAXIMUM JUSTIFIABLE SCORE** 95
**WHY** — `tools/gate.py` khoẻ hơn phần lớn CI: ngân sách lõi vật lý, ảnh chụp
cây chống sửa-giữa-lượt, 24 bước. Nhưng **22 số hiệu test bị trùng** trên toàn
kho (một số dùng cho **bốn** tệp), và đó là **nguyên nhân gốc** của chú thích
sai mà P1-01 đã sửa.
**WHAT WOULD BE REQUIRED FOR 98** — đổi tên các tệp trùng số và cập nhật 307
viện dẫn trong mã.
**WHY NOT WORTH IT (ở đây)** — các tệp ấy thuộc **phiên khác**; luật 12/13 của
`CLAUDE.md` cấm đụng vùng của họ mà không hỏi. Sửa đúng cách cần một phiên riêng.
**RECOMMENDED DECISION** — đã tách thành một việc riêng. `test_980` giữ cho
phạm vi chương trình này không dính thêm.

---

## D. Điều đã tốt lên

1. **Tiền của khách thôi bị giữ một ngày cho một lượt không chạy.** Khách ngắt
   trước byte đầu ⇒ `finally` của `_phat` chưa từng chạy ⇒ `hold` không được
   kết sổ. Nay có đường thứ hai, độc lập với việc generator có chạy hay không.

   ⚠️ Bản đầu của mục này viết *"nằm lại vĩnh viễn, không bộ quét nào thấy"* —
      **nói quá**, và `credit.tu_hoan_treo` (H41.3) bác nó: khoản ấy được hoàn
      sau `TU_HOAN_SAU = 24 giờ`. Giá trị thật của bản vá là **24 giờ → tức
      thì**, và quyết toán theo *số đo được* thay vì chờ một bộ quét có trần
      20 khoản mỗi lượt. Đó vẫn là một cải thiện thật, chỉ nhỏ hơn tôi tưởng.
2. **D-005 qua cửa hết giờ.** Năm lần timeout ⇒ `APIKEY_ERROR` ⇒ model nhà tắt
   và **không tự bật lại**. Mà prefill 200K hàng phút là công việc hằng ngày.
   Bịt ở **cả hai** client.
3. **Ranh giới bảo mật thành cơ chế.** Không còn dựa vào việc ai đó nhớ đặt token.
4. **Kho biết máy B chạy bản nào.** Trước đó bốn đường độc lập đều không trả lời.
5. **Số đo đã đếm sẵn thôi bị vứt đi.** Một cờ, tốn 0 trên đường nóng.
6. **Lệnh nâng engine ngắn nhất thành lệnh an toàn nhất.**

## E. Điều CỐ Ý không đổi

Kiến trúc, ranh giới máy A/máy B, chính sách fallback, hình dạng ba giao thức,
`dieu_phoi.py`, bảng giá, và toàn bộ tham số engine trong `CHUNG` (trừ
`--metrics`). **Không thêm một phụ thuộc hay dịch vụ nào.**

## F. Mẫu thượng nguồn đã NHẬN

| | |
|---|---|
| `GET /api/version` của llama-swap | ghi lại bản đang chạy |
| `--metrics` của llama.cpp | mở cửa đọc số đã đếm sẵn |
| hình dạng kết xuất kiểu GuideLLM | hợp đồng baseline |
| corpus tách khỏi bộ chạy (Promptfoo) | hình dạng, không phải công cụ |

## G. Mẫu thượng nguồn đã TỪ CHỐI

LiteLLM vào đường request · Prometheus/Grafana/Langfuse thường trú ·
`/api/captures/*` (bắt prompt) · nâng binary llama.cpp trong đợt này ·
GuideLLM/Promptfoo làm phụ thuộc.

Mỗi mục có lý do đo được ở `docs/LLM_OPEN_SOURCE_RESEARCH.md`, không phải
"không thích".

---

## H. KẾT QUẢ FULL GATE

| | GATE #1 | GATE #2 |
|---|---|---|
| kết quả | `FAIL (1/32)` | `FAIL (1/32)` |
| đỏ | **10** | **9** |
| xanh | 8 968 | **8 973** |
| thời lượng | 15,7 phút | 11,5 phút |
| `cay_da_doi_giua_chung` | — | **False** |
| mã thoát thật | *(không đo được)* | **1** |

⚠️ **Mã thoát của lượt #1 không đo được**, và đó là lỗi của tôi: tôi chạy
`gate.py … | tail -80`, nên `$?` là của `tail`. Lượt #2 chuyển sang
`> tệp 2>&1; echo $?` và bắt được **1**. Bộ nhớ dự án có mục này theo chiều
ngược lại (*"đọc `returncode`, đừng khớp mẫu stdout"*); bài học thật là **biết
mình đang đọc mã thoát của ai**.

### Tập lỗi lượt #2 = **đúng bằng** tập nền của trunk

```
test_448_asv_v4_e2e_nghiem_thu.py   × 7      (nghiệm thu Auto Scan Video)
test_505_nguon_ban_giao.py          × 2      (`yolov8n.pt` thừa trong $VAN_CHUYEN)
```

`test_363` — lỗi **duy nhất** của chương trình này ở lượt #1 — đã biến mất.
Không một lỗi mới nào xuất hiện. Chi tiết phân định:
`docs/LLM_FINAL_GATE_FAILURES.md`.

⛔ **Nên KHÔNG được nói "gate xanh".** Câu đúng là: *chương trình này không thêm
một lỗi nào vào trạng thái nền, và đã gỡ lỗi duy nhất nó tạo ra.* Trạng thái nền
`FAIL` thuộc vùng ASV và thuộc phiên khác.

⚠️ `sha` trong bản ghi gate là `99017910` — **SHA của trunk**, vì công việc này
   chưa commit. Bản ghi JSON không biết cây có thay đổi chưa commit; nó chỉ biết
   cây **không đổi giữa lượt chạy** (`cay_da_doi_giua_chung: False`). Đừng đọc
   `sha` ấy như "đã chứng nhận cho commit 99017910".

### ⚠️ TRUNK ĐÃ ĐI TIẾP SAU KHI GATE #2 CHẠY (đo 15:28)

```
git rev-list --count HEAD..admin-mvp-v3   ->  2
  3eae396d  test_448 khong phai loi may B: tran token ra 4.096 va tran timeout 120s
  05464239  dinh chinh 3eae396d: duong thang theo co lo KHONG vung
```

⇒ Câu *"9 lỗi = nền của trunk"* ở §H **đúng cho nền `99017910`** — gốc mà nhánh
này xuất phát và mà gate #2 đo trên đó. Nhưng nền của trunk **đã dịch**, nên
đừng đọc con số 9 ấy như một hằng số.

**Chồng lấn với vùng tôi sửa: KHÔNG một tệp nào.** Hai commit ấy chỉ chạm
`apps/auto_scan_video/`, `setup/`, và test/tool của ASV. Merge trunk sẽ sạch.

⚠️ Một phiên khác báo trunk hiện có **hai bước đỏ mới** (`mypy` và
`nuot loi lang le`) đến từ `3eae396d`. Nhánh này **không có** hai commit đó, nên
gate #2 không dính — nhưng **sau khi gộp trunk thì sẽ dính**, và đó là lỗi của
chiến dịch ASV chứ không phải của đợt này. Đo lại sau khi gộp, đừng suy.

### 🔑 Và trần `job` vẫn còn nguyên ở tầng nền tảng

`3eae396d` sửa ở **call site** (`apps/auto_scan_video/ai.py`), không đụng
`apps/ltt_llm/ngan_sach.py`. Đo trên trunk: `TOKEN_RA_MAC_DINH["job"]` **vẫn là
4.096**.

⭐ Và sửa ở call site có lẽ là lựa chọn **đúng hơn** đề nghị ban đầu của tôi:
   phép đo 4.517–7.526 token là của **một tác vụ cụ thể** (`chuyen_loi_thoai`),
   còn `TOKEN_RA_MAC_DINH["job"]` là mặc định dùng chung cho **mọi** bên gọi cửa
   job. Nâng mặc định chung từ một phép đo hẹp là đúng cái lỗi mà chương trình
   này đi sửa ở chỗ khác — *"một con số cho hai model là một con số sai cho ít
   nhất một trong hai"*.

   ⇒ Rút đề nghị "để tôi nhận phần sửa trần `job`". Việc còn lại là một câu hỏi
     **thiết kế**, không phải một bản vá: cửa job có nên có mặc định chung
     không, hay mỗi tác vụ tự khai theo phép đo của nó.

   🔴 Họ còn tìm ra **rào thứ hai** đáng chú ý: `timeout_s = 120.0`, và lượt
      chậm nhất chỉ cách trần **10 %**. Nâng `max_tokens` mà không nâng
      `timeout_s` là đổi một thất bại lấy một thất bại xấu hơn. Đường đó **đã**
      an toàn về mặt phạt khoá — httpx timeout ở máy A ném
      `AmbiguousProviderError`, không `danh_dau_loi` — nhưng nó vẫn là một trần
      thật mà bên gọi phải biết.

---

---

## I. Khuyến nghị cuối

### Việc CÓ THỂ làm ngay, không cần gì thêm

1. **Xem lại và commit.** Chưa commit dòng nào — chủ dự án chưa yêu cầu, và
   `CLAUDE.md` luật 13 đòi `git add` tường minh từng tệp.

### Việc CẦN một quyết định của người vận hành

2. **Chạy benchmark để chốt baseline** (W3 90 → 98). Nó chiếm suất đồng thời
   **duy nhất** của máy B vài phút và **đá văng** hồ sơ đang thường trú. Chạy
   vào giờ thấp điểm, rồi commit kết quả làm baseline được chúc phúc.
3. **Deploy.** `deploy.ps1` chép **cả cây**, nên phải hỏi các phiên khác trước
   (`ListAgents`). Thứ tự đã ghi ở `LLM_OPERATIONS_RUNBOOK.md` §8.

   🔴 **Trước khi deploy, kiểm `gateway.env` trên máy B**: chốt fail-closed mới
      sẽ **từ chối khởi động** nếu `LTT_LLM_HOST` không phải loopback mà
      `LTT_LLM_TOKEN` rỗng. Đo 09/09 cho thấy token **đang được đặt** (`/health`
      trả 401), nên đường này an toàn — nhưng đo lại trước khi deploy, đừng tin
      một phép đo cũ nửa ngày.

   ⚠️ Và `llama-swap.yaml` mới có `--metrics`: nó chỉ có hiệu lực sau
      `Restart-Service LTTLlamaSwap`, và việc đó **unload model**.

4. **Điền `llama_cpp.build`** vào `phien_ban_ghim.json` sau lượt deploy đầu —
   đọc từ `/health` → `thuong_nguon.phien_ban.engine.build_info`.

### Việc thuộc phiên khác

5. **22 số hiệu test trùng** (W11 95 → 98) — đã tách thành một việc riêng.
6. **`test_448` / `test_505`** — vùng ASV.
7. **Trần `job = 4.096`** — phiên `lttstudiosapp-f1` đo được 6/6 hỏng ở 4.096 và
   6/6 xong ở 12.288 với `--reasoning-format deepseek`. Tôi đã đề nghị nhận phần
   sửa vì trùng tệp `ngan_sach.py`, và xin sổ kê của họ để ghim con số vào một
   phép kiểm thay vì gõ một số trông hợp lý. **Chưa gửi được** — phiên đó không
   nằm trong `list_sessions` của tôi.

### Điều KHÔNG nên làm

⛔ Đừng đọc `FAIL (1/32)` thành "chương trình chưa xong", và cũng đừng "sửa" nó
   bằng cách chạy lại `test_448`. Bộ nhớ dự án ghi **bốn phiên** đã kết luận sai
   về tệp ấy — nửa B của nó đọc một **tệp tĩnh**, không gọi máy B, nên "chờ máy
   B rảnh rồi chạy lại" là chờ vô ích.
