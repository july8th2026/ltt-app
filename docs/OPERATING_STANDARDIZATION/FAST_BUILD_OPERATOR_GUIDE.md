# FAST BUILD — sổ tay thao tác

> Luật ở `docs/00_LTT_OPERATING_CONTRACT.md` §4.10. Đây chỉ là các lệnh.
> Thiết kế và bằng chứng: `FAST_BUILD_WORKTREE_DESIGN.md` cùng thư mục.

## Hỏi cây bạn đang đứng

```powershell
python tools\ho_so_cay.py trang-thai
```

Không chạy test, không đụng cây. Trả lời: nhánh · HEAD · thiếu bao nhiêu commit
của trunk · hồ sơ và trạng thái · tệp governance nào lệch trunk.

Governance lệch ⇒ `git merge admin-mvp-v3` **trước**, rồi mới tin một luật hay
một lượt gate ở cây này.

## Một chiến dịch dài, từ đầu đến cuối

```powershell
# 1. cây riêng, sinh từ trunk mới nhất
python tools\cay_rieng.py tao <ten>
cd D:\LTTSTUDIOSAPP-<ten>

# 2. opt-in — ghi baseline = HEAD lúc này
python tools\ho_so_cay.py bat --pham-vi "<mo ta ngan>"
python tools\ho_so_cay.py chuyen BUILDING

# 3. xây. Commit checkpoint thoải mái, KHÔNG kèm gate.
#    Microcheck rẻ khi cần: ast.parse, json.loads, render một template.

# 4. đóng băng tập tính năng
python tools\ho_so_cay.py chuyen FEATURE_COMPLETE

# 5. vào chứng nhận — lệnh này in luôn kế hoạch
python tools\ho_so_cay.py chuyen CERTIFYING

# 6. chạy theo đúng thứ tự kế hoạch in ra, rẻ trước
python tools\gate.py --quick
python tools\gate.py --doi --tu <baseline_sha>
#   … tích hợp / parity / E2E / trình duyệt …
python tools\gate.py

# 7. sẵn sàng hoà
python tools\ho_so_cay.py chuyen READY_TO_MERGE
```

Xem nợ kiểm bất cứ lúc nào:

```powershell
python tools\ho_so_cay.py no-kiem
```

Trở về `NORMAL`:

```powershell
python tools\ho_so_cay.py tat
```

## Ba câu hỏi hay gặp

**Đang `CERTIFYING` mà phát hiện thiếu một tính năng?**
`chuyen BUILDING`. Công cụ cho phép và **ghi lại** lần hạ cấp đó. Đừng lách bằng
cách `tat` rồi `bat` lại — làm thế là đặt một `baseline_sha` mới, và mọi thứ
trước đó biến mất khỏi phép đo.

**Bị chặn bởi một khiếm khuyết của lõi?**
Tách một changeset lõi riêng và chứng nhận riêng nó theo `NORMAL` (§4.10, mục
*Ngoại lệ lõi*). Không dùng nó làm cớ quay về chạy gate sau mỗi lần sửa.

**Bật được ở cây chính không?**
Không. Công cụ từ chối ở cây chính, ở `master`, ở trunk và ở nhánh phát hành.
Đó là chốt cơ học, không phải lời khuyên.
