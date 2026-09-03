# QUY TẮC CHẠY LỆNH NẶNG — viết sau hai lần treo máy trong một ngày

03/09/2026. Máy production bị reset **hai lần**, cả hai lần trong lúc tôi chạy lệnh.
Tài liệu này là ràng buộc tôi tự đặt cho mình, không phải một gợi ý.

## Lỗi thật không phải "chạy test" — mà là **chạy để dò lỗi**

Lần thứ hai, tôi chạy `gate --quick` **bốn lần liên tiếp** trong vài phút, mỗi lần 24 bước,
chỉ để tìm hai byte `0x0b` trong một tệp markdown.

Câu hỏi đó trả lời được bằng **một lệnh tức thì**:

```python
b = Path("docs/X.md").read_bytes(); b.count(b"\x0b")
```

Tôi có ba lượt gate để nhận ra điều đó và không nhận ra lượt nào. `CLAUDE.md` của kho đã ghi
đúng bài học này — *"gate là công cụ ra PHÁN QUYẾT, không phải công cụ CHẨN ĐOÁN"* — kèm số
đo: ngày 27/08 gate đầy đủ chạy **sáu lần** chỉ để dò lỗi, bốn lượt đỏ vì thứ một bước con lẻ
trả lời trong nửa giây.

⇒ **Quy tắc 0: dùng công cụ HẸP NHẤT trả lời được câu hỏi.** Một lượt gate để tìm một byte là
đổi 40 giây × 24 tiến trình lấy một thứ `read_bytes()` cho ngay.

## Phân loại lệnh

| Loại | Đặc điểm | Được chạy |
|---|---|---|
| **Nhẹ** | 1 tiến trình, < 5 s: `git`, `grep`, `python -c`, đọc tệp, `ast.parse` | tự do |
| **Vừa** | 1 tiến trình, 5–60 s: một tệp test, `lint_app_contract`, `check_*` | tự do, **một lần một** |
| **Nặng** | nhiều tiến trình / > 60 s: `gate.py` (mọi chế độ), `test_nhanh.py`, cụm ≥ 3 tệp test, `build_system_profile` | xem dưới |

⚠️ `gate --quick` **là nặng**. Nó bỏ bước `bo test` nhưng vẫn chạy 24 bước với nhiều tiến
trình con. Tôi đã xếp nhầm nó vào loại "vừa" và trả giá.

## Trước MỌI lệnh nặng — bốn bước, không bỏ bước nào

```bash
python tools/tai_may.py            # RẢNH / BẬN / QUÁ TẢI (theo RAM)
python tools/cua_so_yen.py trang-thai   # phiên khác có đang chạy không
```

1. **Đọc mã trước.** Câu hỏi này có trả lời được bằng đọc không? Nếu có, đọc.
2. **Đo tải.** `QUÁ TẢI` ⇒ không chạy. `BẬN` ⇒ hoãn hoặc chạy cụm nhỏ.
3. **Báo trước** cho các phiên khác nếu lượt kéo dài > 2 phút.
4. **Chạy qua nhật ký**, không chạy trần:

```bash
python tools/nhat_ky_chay.py -- python tools/gate.py --phien <ten>
```

## Sau một lần treo máy

```bash
python tools/nhat_ky_chay.py --xem 3
```

Nhật ký ghi từng dòng với `flush` + `fsync` **ngay**, nằm ngoài cây kho
(`%TEMP%\ltt_nhat_ky_chay`). Một lượt không có dòng `ket_thuc` là một lượt bị cắt giữa chừng —
và các mẫu CPU/RAM trước đó vẫn còn để đọc.

🔴 Đây chính là thứ thiếu ở cả hai lần treo hôm nay. Ba ứng viên cho lần đầu (gate / 45 tiến
trình ngoài gate / **chính phép đo của tôi**) không phân biệt được, vì mọi bằng chứng nằm
trong RAM của một tiến trình đã chết. Một lần reset không có nhật ký là một lần học được
**không gì cả**.

## Ba điều tuyệt đối không làm

1. **Không chạy lại một lệnh nặng để "xem đã sửa chưa"** trong cùng một vòng sửa. Sửa cho
   xong, kiểm bằng công cụ hẹp, rồi chạy nặng **một lần**.
2. **Không chạy nặng khi phiên khác đang chạy nặng.** Ngân sách lõi là per-máy từ 03/09, nhưng
   nó chỉ thấy ai *xin khoá* — bot, deploy và `pytest` gõ tay đều vô hình với nó.
3. **Không để phép đo thành nghi can.** Lấy mẫu thưa (≥ 8 s), chỉ đọc tổng máy. Quét
   `process_iter` qua trăm tiến trình mỗi 2 giây là tự thêm tải rồi đo chính mình.

## Hộp đen — bật MỘT LẦN, chạy nền suốt

```bash
python tools/giam_sat_may.py --chay        # ghi mỗi 15s vào %TEMP%\ltt_hop_den
```

Nó ghi **máy**, không ghi *lệnh của ta* — nên nó thấy cả bot, phiên khác, dịch vụ production,
deploy. Đó là điều `nhat_ky_chay.py` không làm được: hôm 03/09 cây gate có 13 tiến trình
trong khi toàn máy có 58, và 45 cái còn lại không đi qua bất cứ thứ gì ta bọc.

### Sau một lần treo / reset — lệnh đầu tiên phải gõ

```bash
python tools/giam_sat_may.py --kham
```

Nó tự tìm chỗ log **đứt** (khoảng trống > 3 nhịp = máy chết), lấy 6 mẫu cuối trước đó, xếp
hạng tiến trình theo CPU/RAM ở đúng những mẫu ấy, và so với **nền của chính máy này** (trung
vị 7 ngày) để chỉ ra cái gì bất thường.

⛔ Nó **không kết luận nguyên nhân**. Nó đưa ra ai đang chiếm chỗ và cái gì lệch khỏi thường
   lệ; phần kết luận là của người đọc. Một công cụ tự kết luận sẽ dẫn người đọc vào giả thuyết
   đầu tiên — và đó đúng là kiểu sai đã xảy ra **mười một lần trong một ngày** ở dự án này.

Đối chiếu thêm: `nhat_ky_chay.py --xem 3` (lệnh ta chạy) · `D:/FULL AUTO VIDEO/*/logs/` (bot)
· `ListAgents` (phiên khác).

### Ba lỗi tìm ra khi THỬ hai công cụ này, cả ba im lặng trên đường xanh

| Lỗi | Hậu quả nếu không thử |
|---|---|
| `cpu_percent(interval=None)` lần đầu trả `0.0` | ghi `0%` cho máy đang chạy 100% |
| cùng hàm gọi từ hai luồng → giẫm mốc | mẫu **giữa** cũng `0%` |
| `print` emoji vỡ trên cp1252 | `--xem` **chết đúng nhánh "bị cắt"** — tức đúng lúc cần đọc |
| `p.cpu_percent(None)` lần đầu mỗi tiến trình = 0 | `top: []` — máy bận trông y hệt máy trống |
| `System Idle Process` (pid 0/4) | báo cáo mở đầu bằng "1786%" của tiến trình *nhàn rỗi* |

⇒ **Một công cụ chống-treo chưa được thử là một công cụ chưa tồn tại.** Và thử nó ở đường
  **hỏng** quan trọng hơn thử ở đường xanh.

## Ngân sách hiện tại, để khỏi tra lại

```
lõi vật lý                 10
LOI_DE_DANH_VAT_LY          3   (OS + 4 dịch vụ production)
TRAN_WORKER_BO_TEST         6   (trần an toàn cứng — chủ dự án chọn 03/09)
ngan_sach_loi()             7   (= 10 − 3, đơn vị VẬT LÝ)
=> bo test  -n              6
   còn cho bước tĩnh        1
```

Đổi bất kỳ số nào ở trên: đọc `docs/KE_HOACH_NGAN_SACH_LOI.md` trước, nó ghi vì sao từng số
là số đó và những gì đã thử rồi hỏng.
