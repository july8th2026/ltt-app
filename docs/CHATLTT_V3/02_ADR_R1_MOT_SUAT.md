= P02 · ADR-R1 — MỘT SUẤT LLM VÀ VÒNG LẶP NHIỀU BƯỚC
(bản nháp; đóng khi P01 ra phán quyết đầy đủ)

# ADR-R1 — Vòng lặp tool sống thế nào trên một nền tảng chỉ có MỘT suất LLM

*H44 · nháp 2026-09-04 · trạng thái: **ĐỀ XUẤT**, chờ P01 đóng.*

## 1. Bối cảnh, bằng chứng

```
apps/ltt_llm/manifest.py:197      admission_resource="llm_remote", admission_slots=1
llm_gateway/deploy/llama-swap.yaml  --parallel 1
```

Một suất, toàn nền tảng, dùng chung bởi **ba** cửa: `runtime_noi_bo` (ChatLTT),
`/api/v1` job, và cửa đồng bộ OpenAI.

`platform_core/llm/admission.py` — đọc hết 201 dòng, và ba tính chất định hình
mọi phương án:

| Tính chất | Dòng | Hệ quả |
|---|---|---|
| `acquire` **không có hàng đợi** — thử slot 0..n-1, hết thì trả `None` | 74-104 | không có thứ tự chờ, không có công bằng. Ai gọi đúng lúc thì được |
| `ORPHAN_TIMEOUT = 20 phút`, nhịp tim 60 s | 23-24 | lease treo khoá GPU tối đa 20 phút |
| `hold_persisted` + `keep_alive` **đã tồn tại** | 168-201 | primitive giữ lease xuyên một khối **đã có sẵn**, không phải xây |
| `release` idempotent | 116-127 | nhả hai lần vô hại |

## 2. 🔴 Phát hiện quyết định: phương án A **tự khoá chính nó**

Phương án A ("giữ lease suốt cả run") nghe hiển nhiên vì `hold_persisted` đã có.
Nhưng ghép nó vào đường hiện tại thì hỏng, và hỏng theo kiểu buồn cười nhất:

```
ChatLTT giu lease slot 0  (holder_id = run_id)
  -> goi mo_luong() vong 1
       -> chuan_bi() luong.py:202  admission.acquire(slots=1)
            -> slot 0 DA BI CHIEM ... boi chinh ChatLTT
            -> tra None
            -> raise DangBan("het suat thuc thi")
```

⛔ **Run chết vì lease của chính nó.** `chuan_bi` không có tham số "tôi đã cầm
lease rồi", và `acquire` không phân biệt chủ sở hữu — nó chỉ đếm slot đã chiếm.

⇒ Phương án A **bắt buộc** phải sửa `platform_core/runtime_noi_bo/luong.py`.
Đó là module có **20 tệp test ghim** và nằm trong danh sách KHÔNG-VIẾT-LẠI §2.
Không phải cấm tuyệt đối — nhưng cái giá đã rõ, không còn là ẩn số.

## 3. Ba phương án, và cái giá thật của từng cái

| | **A** giữ lease cả run | **B** ưu tiên trong `admission` | **C** giành lại mỗi vòng |
|---|---|---|---|
| Sửa lõi | **có** — `luong.py` nhận `lease_id` sẵn | **có** — `admission.py` thêm hàng đợi/ưu tiên | **không** |
| Run chết giữa chừng | không | hiếm | **có thể**, khi tải cao |
| Khoá GPU của người khác | **cả run**, tối đa `ORPHAN_TIMEOUT` | không | không |
| Công bằng | **tệ nhất** — một run 8 vòng chặn mọi người | tốt nhất | tuỳ may |
| Rủi ro hồi quy | 20 tệp test ghim `luong.py` | `admission` dùng bởi **mọi** đường | thấp |
| Làm được ngay | phải sửa lõi trước | phải thiết kế hàng đợi | **có** |

### Vì sao C **không** phải lựa chọn hèn

Ba dữ kiện làm C rẻ hơn nó trông:

1. **Đo được, không đoán:** một vòng model của lô chính mất **2,0–3,9 giây**.
   Khoảng hở giữa hai vòng — thời gian ChatLTT thi hành tool rồi gọi lại — là
   phần dễ mất suất. Với tool nội bộ (calculator, đọc dữ liệu) khoảng hở ấy tính
   bằng **mili-giây**.
2. **Hiện chưa có tranh chấp:** một hồ sơ text, `--parallel 1`, **chưa có khách
   thật**. Xác suất mất suất hôm nay ≈ 0. Nó chỉ thành thật khi có khách — và
   lúc đó ta đã có số liệu thật để chọn lại.
3. **`WAITING_SLOT` không phải trạng thái chết:** run đã có `chatltt_run` bền,
   nên mất suất giữa chừng là **tạm dừng rồi nối lại**, không phải hỏng. Đó
   chính là thứ máy trạng thái của P02 sinh ra để làm.

⛔ Cái giá thật của C, nói thẳng: **đuôi trễ p95 của lượt agentic phụ thuộc tải
của cả nền tảng**, và ta không kiểm soát được nó bằng mã của ChatLTT.

## 4. Quyết định đề xuất

> **Chọn C làm mặc định.** Giành lại suất mỗi vòng; mất suất ⇒ `WAITING_SLOT`,
> lưu bền, nối lại theo lịch lùi dần.
>
> **Nâng lên A chỉ cho run đã tiêu tiền thật** — tức đã có ít nhất một
> `tool.result` từ một tool **có phí**. Một run đã trừ credit của khách không
> được phép chết vì mất suất.

Ranh giới ấy chọn theo **tiền**, không theo độ ưu tiên cảm tính: nó tự thu hẹp
(rất ít run chạm tool có phí), tự giải thích được với khách, và nó khớp đúng
với bất biến *"không thu tiền cho thứ không giao"*.

**Khi và chỉ khi nâng lên A** thì mới sửa lõi, và bản sửa là **nhỏ nhất có thể**:

```python
# platform_core/runtime_noi_bo/luong.py — chuan_bi()
def chuan_bi(..., lease_co_san: str = ""):
    ...
    if tai_nguyen and so_suat > 0 and not lease_co_san:
        ticket = admission.acquire(...)
        ...
    lease_id = lease_co_san or (ticket.id if ticket else "")
```

⭐ Và `_phat().finally` **không được nhả** một lease nó không tự giành. Đó là
chỗ dễ sai nhất của bản vá này: nhả nhầm lease của người gọi thì vòng sau mất
suất, và triệu chứng sẽ là "thỉnh thoảng run chết ở vòng 3" — một lỗi không tái
hiện được theo yêu cầu.

⇒ Kèm điều kiện: bản vá phải có test cho **cả hai** chiều (tự giành thì tự nhả;
được trao thì không nhả), và test phải **đỏ** khi cố ý đảo điều kiện.

## 5. Trần cứng, để A không thành cái cớ khoá GPU

| Trần | Giá trị | Vì sao |
|---|---|---|
| Thời gian giữ lease của một run | **≤ 5 phút** | dưới xa `ORPHAN_TIMEOUT` 20 phút; hết trần thì hạ xuống C |
| Số vòng model mỗi lượt | **8** | §B9 ma trận khoảng trống |
| Số lời gọi tool mỗi lượt | **12** | như trên |
| Credit tích luỹ mỗi lượt | chờ §6b-4 | phụ thuộc quyết định làm tròn |

## 6. Điều còn nợ

| Nợ | Đóng bằng |
|---|---|
| Chưa đo mất suất **thật** khi có tranh chấp | dựng hai phiên gọi song song, đo tần suất `DangBan` giữa vòng |
| Chưa biết khoảng hở giữa hai vòng dài bao nhiêu ở tool **có job** (ảnh/tiếng) | job ảnh mất hàng chục giây ⇒ với chúng, C gần như **chắc chắn** mất suất ⇒ đây mới là ca thật cần A |
| `mode` trên `ExecutionLease` chưa dùng | có thể mang nhãn ưu tiên khi cần B, không phải thêm cột |

⭐ Dòng thứ hai là dòng quan trọng nhất và nó **đổi trọng tâm của ADR này**:
với tool chạy bằng **job** (ảnh, tiếng), khoảng hở giữa hai vòng model là hàng
chục giây, không phải mili-giây. Ở đó C gần như chắc chắn mất suất. Nên ranh
giới "nâng lên A" có lẽ không phải *"đã tiêu tiền"* mà là ***"vòng kế tiếp phải
chờ một job"*** — và hai điều kiện đó trùng nhau phần lớn nhưng không hoàn toàn.

⇒ Chốt lại sau khi P05 đo được thời gian thật của một vòng ảnh/tiếng.
