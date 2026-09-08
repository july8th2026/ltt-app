# PERFORMANCE REPORT — trước và sau

> Nguồn số **trước**: 59 bản ghi thật trong `test-results/gates/*.json`
> (43 lượt `day-du`, 16 lượt `vong-lap`), không phải ước lượng.
> Nguồn số **sau**: đo trực tiếp ngày 2026-09-08 trên cây `admin-mvp-v3`.

## 1. Tài liệu nói vs. đồng hồ nói

| | Tài liệu cũ | **Đo được (trung vị)** | Chênh |
|---|---|---|---|
| Gate đầy đủ | "~5 phút" | **682,8 s ≈ 11,4 phút** | **2,3×** |
| `--vong-lap` | "~15 giây" | **21,4 s**, max **543,7 s** | tới **36×** |
| Bộ test đầy đủ (`test_nhanh.py`) | "~4 phút" | **550,8 s ≈ 9,2 phút** *(bước `bo test` trong gate)* | 2,3× |

⛔ Con số "~5 phút" xuất hiện ở **`CLAUDE.md`, `AGENTS.md`, và 4 tệp kế hoạch**.
Nó sai hơn gấp đôi ở **mọi** chỗ, vì cả sáu chỗ đều **chép tay** từ nhau.

⭐ Và cái giá không chỉ là thời gian. Một người tin "5 phút" rồi mất 11 phút sẽ
**không chạy lại lượt sau** — tức một con số sai trong tài liệu biến thành một
cổng chất lượng ít được chạy hơn.

## 2. Gate tiêu thời gian ở đâu

```
bo test (song song)      550,8 s  ████████████████████████████  81 %
bat bien da tien trinh   138,0 s  ███████                       20 %
23 buoc tinh + frontend   ~60 s   ███                            9 %
```

⇒ Nhóm tĩnh — thứ bắt phần lớn lỗi thật — chỉ tốn **9 %**. Đó là lý do một cấp
L0 có ý nghĩa: bỏ **2** bước nặng là bỏ **91 %** chi phí mà vẫn giữ **28/30** bước.

⚠️ Số bước phải lấy bằng cách **gọi `_steps()`**, không bằng đếm `Step(` trong mã:
ba lời gọi `frontend` nằm trong một vòng lặp có điều kiện. Bản nháp đầu của các
tệp này ghi *26* vì đếm bằng AST — sai, số đúng là **30**.

## 3. 🔴 `--doi` tồn tại nhưng CHƯA TỪNG thu hẹp gì

```
day-du     43 luot
vong-lap   16 luot
doi         0 luot   <--
pham-vi     0 luot   <--
```

Không phải vì không ai biết. Vì `bi_anh_huong()` trả `None` (⇒ hạ cấp xuống đầy
đủ) khi gặp đường dẫn **không thành phần nào sở hữu**, và `thanh_phan.toml`
**không khai `tests/`**. Nên **mọi thay đổi chạm một tệp test đều hạ cấp xuống
gate đầy đủ** — mà gần như mọi thay đổi thật đều kèm một tệp test.

Đo trên cây bẩn lúc bắt đầu:

```
$ python tools/thanh_phan.py --doi
18 duong dan doi
=> cham tep DUNG CHUNG hoac duong khong ai so huu -> phai chay TAT CA
```

### Sau khi sửa — số tệp test phải chạy

| Thay đổi điển hình | Trước | Sau | Bớt |
|---|---:|---:|---:|
| chỉ một tệp test | 532 (100 %) | **1** (0 %) | **99,8 %** |
| `apps/ltt_voice/vo.py` + test của nó | 532 (100 %) | **118** (22 %) | **78 %** |
| `apps/thumbnail/routes.py` + `test_104` | 532 (100 %) | **48** (9 %) | **91 %** |

⚠️ **Đây là số TỆP TEST, không phải giây.** Thời gian thật chưa đo được trên cây
này vì cây đang bẩn bởi một phiên khác, và `tools/gate.py` + `tools/thanh_phan.py`
đều nằm trong `DUNG_CHUNG` ⇒ chính lượt `--doi` đầu tiên sau chiến dịch này sẽ tự
hạ cấp xuống đầy đủ. Đó là hành vi **đúng**, và nó có nghĩa là **phép đo thời
gian đầu-cuối cho `--doi` là việc của lượt sau**, không phải của lượt này.

⛔ Không suy tuyến tính từ 22 % tệp test ra 22 % thời gian. Các tệp test không
bằng nhau, và bước `bat bien da tien trinh` (138 s) vẫn chạy trong mọi hồ sơ.

## 4. Lần chạy pytest bị trùng — đã gỡ

| Nguồn | Bảo làm gì | Giá | Trạng thái |
|---|---|---|---|
| `docs/MOBILE/00_KE_HOACH.md:194` | `test_nhanh.py` **rồi** `gate.py` | ~9,2 phút trả **hai lần** | ✅ đã gỡ |
| `docs/auto_scan_video/BASELINE_COMMANDS.md:12` | y hệt | ~9,2 phút trả **hai lần** | ✅ đã gỡ |
| `CLAUDE.md` §4 · `AGENTS.md` §4b | liệt kê cả hai trong **một** bảng ba lệnh | mời gọi đúng lỗi trên | ✅ `CLAUDE.md` đã viết lại |

⇒ **Tiết kiệm khi lỗi này xảy ra: ~9,2 phút mỗi lượt.**

## 5. Bước mới thêm vào gate

| Bước | Giá đo được | Cấp |
|---|---:|---|
| `luat van hanh` (`check_luat_van_hanh.py`) | **1,6 s** *(2 lượt, cùng số)* | L0 |

Quét 822 tệp `.md` được git theo dõi. 1,6 s trên tổng 682,8 s = **0,23 %**.

## 6. Checkpoint bắt buộc chạy L3 — trước và sau

| | Trước | Sau |
|---|---|---|
| Số nơi định nghĩa cadence | **10 tệp, 5 bản KHÁC NHAU** | **1** (`docs/00_LTT_OPERATING_CONTRACT.md`) |
| Cadence mặc định của vòng lặp | `--vong-lap` (3 nguồn) / `--doi` (2) / `test_nhanh --lf` (1) / tập bất biến riêng (2) | **`--doi`** |
| L3 bắt buộc khi nào | mơ hồ; 4 kế hoạch bảo chạy "trước mỗi bước" | **6 checkpoint có tên** (§7 hợp đồng) |
| Bánh cóc chống mọc lại | không có | `check_luat_van_hanh.py` trong gate |

## 7. Đã hoãn có chủ ý

| Việc | Vì sao hoãn |
|---|---|
| **`docs/**` vẫn hạ cấp xuống đầy đủ** | **70 tệp test đọc `docs/`** — đã `grep`, không đoán. Một luật "docs thì trơ" sẽ bỏ qua 70 phép kiểm **im lặng**. Cần bản khai chủ sở hữu cho `docs/`, không phải một luật miễn trừ. **P1** |
| Chuẩn hoá marker pytest (`unit`/`integration`/`slow`/…) | `pytest.ini` mới khai `nang`; `@pytest.mark.slow` dùng **1 lần** mà chưa khai. ROI thấp, và `--strict-markers` chưa bật nên chưa gãy. **P1** |
| Đo thời gian đầu-cuối thật cho `--doi` | Cây đang bẩn bởi phiên khác + hai tệp `DUNG_CHUNG` vừa sửa ⇒ lượt tới tự hạ cấp. Đo ở lượt sạch kế tiếp. **P0** |
| Bật `pytest-xdist` rộng hơn | **Đã tối ưu xong từ 26/08**: 2 giờ → 4 phút bằng `--dist loadfile` + bỏ `fsync` SQLite tạm. Không còn phần dễ ăn. |

## 8. Cách đo lại

```powershell
python tools\thanh_phan.py --doi          # pham vi cua cay hien tai
python tools\check_luat_van_hanh.py       # banh coc luat van hanh
```

Số gate lấy từ `test-results/gates/*.json` — **bằng chứng máy sinh**, có `sha` và
`cay`, nên đối chiếu được với commit. ⚠️ Trường `cho_khoa_giay` tách riêng thời
gian **chờ khoá** khỏi thời gian **chạy**; đừng cộng nhầm hai cái.
