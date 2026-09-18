# LLM_FINAL_GATE_FAILURES — gom theo NGUYÊN NHÂN GỐC

FULL GATE #1 · 2026-09-09 · `test-results/gates/20260909T080131Z-6264.json`

```
RESULT: FAIL (1/32)   [4 BƯỚC TỰ BỎ QUA, KHÔNG PHẢI BẰNG CHỨNG]
10 failed · 8968 passed · 61 skipped · 15,7 phút
```

⚠️ **`exit code 0` ở đây VÔ NGHĨA** — tôi chạy `gate.py … | tail -80`, nên mã
thoát là của `tail`. Phán quyết đọc ở dòng `RESULT`, không đọc mã thoát. (Bộ nhớ
dự án có đúng mục này theo chiều ngược lại: *"đọc `returncode`, đừng khớp mẫu
stdout"* — bài học thật là **biết mình đang đọc cái gì**.)

---

## Phân định: 1 lỗi của tôi, 9 lỗi có sẵn

Chứng minh bằng diff chứ không bằng suy đoán:

```
git diff --stat 99017910 -- setup/ apps/auto_scan_video/ tools/ frontend/ alembic/ locale/
  -> RỖNG
```

Tôi không chạm một tệp nào mà `test_448`/`test_505` đọc. Và trunk `99017910` tự
ghi trong commit của nó: *"gate cuoi: FAIL (1/32) … 7 do deu la test_448"*.

| Nhóm | Số lỗi | Của ai |
|---|---|---|
| RC-1 bánh cóc chuỗi ở `test_363` | 1 | **TÔI** |
| RC-2 `test_448` nghiệm thu ASV | 7 | có sẵn trên trunk |
| RC-3 `test_505` `yolov8n.pt` | 2 | có sẵn trên trunk |

---

## RC-1 · Bánh cóc khớp chuỗi vỡ vì mã được cải thiện — **ĐÃ SỬA**

**TRIỆU CHỨNG**
`test_363::test_moi_generator_giao_cho_StreamingResponse_deu_co_luoi`

```
AssertionError: ve admission khong con nha bang BackgroundTask
assert 'BackgroundTask(admission.release_by_id' in <streaming.py>
```

**NGUYÊN NHÂN GỐC THẬT** — không phải "tôi gỡ mất lưới". Tôi đổi

```python
nen = BackgroundTask(admission.release_by_id, cb.lease_id)      # cũ
```

thành

```python
def _ket_thuc():
    try:     cua_luong.dam_bao_quyet_toan(luot)      # lưới TIỀN (mới)
    finally:
        if cb.lease_id: admission.release_by_id(cb.lease_id)   # lưới VÉ (giữ)
nen = BackgroundTask(_ket_thuc)                                 # mới
```

Vé vẫn nhả, và nay nhả trong `finally` nên một ngoại lệ ở đường tiền **không**
làm kẹt vé. Hành vi **mạnh lên**; chuỗi thì biến mất.

⛔ Đây đúng *"bánh cóc chỉ bảo vệ thứ nó nhìn thấy"*: một phép khớp chuỗi không
   phân biệt được **"gỡ mất lưới"** với **"bọc lưới vào một hàm có tên"**.

**BẢN SỬA** — viết lại mệnh đề cho **bất biến với hình dạng mã**, và bản viết
lại **khó xanh hơn** bản cũ (đòi 3 điều thay vì 1 chuỗi):

1. `StreamingResponse` vẫn nhận `background=BackgroundTask(...)` — đọc AST;
2. `release_by_id` vẫn gọi được;
3. **và nó nằm trong `finally`** — vế bản cũ *không hề đòi*.

Cộng thêm một chốt cho lưới thứ hai (`dam_bao_quyet_toan`).

**RỦI RO** — thấp. Không đổi mã sản phẩm; chỉ thay một phép khớp chuỗi bằng một
phép đọc AST chặt hơn.

**NGHIỆM THU HẸP** `pytest test_363 test_987 test_292` → **29 passed**.

**TRẠNG THÁI** ✅ ĐÃ SỬA

---

## RC-1b · Và nó sửa lại CHÍNH TÔI

Docstring của `test_363` — phép kiểm mà bản vá của tôi làm đỏ — mang câu:

> `server.api.streaming._phat` → cùng phơi nhiễm, nhưng **có lưới**: vé nhả bằng
> `BackgroundTask`, **tiền treo được `credit.tu_hoan_treo` quét (H41.3)**

Tôi đi kiểm, và nó **đúng**:

```
giu_cho(db, user_id, amount, job_id)   <- stream truyền `request_id` làm job_id
giu_cho_treo()  điều kiện 3: quá `treo_sau` mà không `Job` nào ĐANG SỐNG mang khoá
tu_hoan_treo()  hoàn mọi khoản treo CÓ job_id · TU_HOAN_SAU = 24 giờ · trần 20/lượt
```

⇒ **Tuyên bố Phase 7 của tôi bị nói quá ở hai chỗ**, và tôi đã đính chính cả
bốn nơi đã ghi (`luong.py`, `test_987`, `test_292`, `LLM_FINAL_ARCHITECTURE.md`,
`LLM_CHANGELOG_UPGRADE.md`):

| Tôi đã viết | Thật ra |
|---|---|
| hold *"nằm lại **vĩnh viễn**"* | ≤ **24 giờ**, rồi `tu_hoan_treo` hoàn |
| *"không bộ quét nào thấy nó"* | `credit.tu_hoan_treo` (H41.3) **có** thấy |

**Bản vá vẫn đáng làm** — nhưng lý do đúng là: nó biến một **backstop 24 giờ có
trần 20 khoản/lượt** thành một **quyết toán tức thì theo số đo được**. Đó là
"24 giờ → tức thì", không phải "mất tiền → không mất tiền".

⭐ Đáng ghi vì đường tôi biết mình sai: **bánh cóc tôi phá cũng là thứ sửa tôi.**
   Nếu `test_363` chỉ khớp chuỗi và tôi "sửa" nó bằng cách nới lỏng, tôi đã
   không bao giờ đọc docstring ấy, và một lời nói quá về tiền của khách sẽ nằm
   lại trong tài liệu.

---

## RC-2 · `test_448` — nghiệm thu Auto Scan Video · **CÓ SẴN, KHÔNG PHẢI CỦA TÔI**

7 lỗi. Tệp này có hai nửa: nửa A chạy thật (nặng, mặc định KHÔNG chạy), nửa B
đối chiếu **báo cáo đã lưu** với **mã nguồn hôm nay**. Nửa B đỏ khi mã ASV đổi
mà chưa ai chạy lại nghiệm thu nặng.

Trunk tự ghi đúng trạng thái này. Tôi không chạm `apps/auto_scan_video/`.

⚠️ Bộ nhớ dự án còn ghi rằng **bốn phiên** từng kết luận sai về tệp này ("chờ
máy B rảnh rồi chạy lại" — chờ vô ích, vì nửa B đọc **tệp tĩnh**, không gọi máy
B). Tôi không lặp lại: tôi **không** chạy lại nó và **không** đụng vào nó.

**TRẠNG THÁI** ⏭️ NGOÀI PHẠM VI — thuộc phiên đang làm ASV.

---

## RC-3 · `test_505` — `yolov8n.pt` thừa trong `$VAN_CHUYEN` · **CÓ SẴN**

2 lỗi:

```
muc khai trong $VAN_CHUYEN nhung KHONG ma runtime nao nhac toi:
    yolov8n.pt
```

Phép kiểm đối chiếu hai chiều giữa `setup/2-cai-dat.ps1` và mã runtime. Một mục
khai mà không mã nào tham chiếu ⇒ nó đi theo **mọi** lượt deploy mãi mãi.

Tôi không chạm `setup/`. Đây là hệ quả của việc mã ASV thôi tham chiếu YOLO —
cùng gốc với RC-2.

**TRẠNG THÁI** ⏭️ NGOÀI PHẠM VI — cùng phiên với RC-2.

---

## Kết luận trước FULL GATE #2

Đúng **một** lỗi thuộc chương trình này, đã sửa, và bản sửa làm phép kiểm **chặt
hơn** chứ không nới ra. Chín lỗi còn lại là trạng thái nền của trunk, thuộc vùng
ASV, và tôi cố ý không chạm.

⛔ **Nên FULL GATE #2 sẽ vẫn `FAIL`**, và điều đó **không** có nghĩa chương trình
này chưa xong. Tiêu chí đúng để đọc lượt #2:

> `test_363` xanh, và tập lỗi còn lại **bằng đúng** tập lỗi nền của trunk
> (`test_448` ×7 + `test_505` ×2) — không thêm một lỗi nào.
