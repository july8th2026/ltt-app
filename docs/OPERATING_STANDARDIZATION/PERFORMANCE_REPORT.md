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
| Đo thời gian đầu-cuối thật cho `--doi` | Vẫn treo. Xem §9 — cây chưa đứng yên được một lượt nào. **P0** |
| Bật `pytest-xdist` rộng hơn | **Đã tối ưu xong từ 26/08**: 2 giờ → 4 phút bằng `--dist loadfile` + bỏ `fsync` SQLite tạm. Không còn phần dễ ăn. |

## 8. Cách đo lại

```powershell
python tools\thanh_phan.py --doi          # pham vi cua cay hien tai
python tools\check_luat_van_hanh.py       # banh coc luat van hanh
```

Số gate lấy từ `test-results/gates/*.json` — **bằng chứng máy sinh**, có `sha` và
`cay`, nên đối chiếu được với commit. ⚠️ Trường `cho_khoa_giay` tách riêng thời
gian **chờ khoá** khỏi thời gian **chạy**; đừng cộng nhầm hai cái.


---

## 9. Lượt L3 thật, 15:32–15:45 — **12,4 phút**, và nó tự nói KHÔNG phải bằng chứng

Chủ sản phẩm cho phép chạy, và máy **đúng là yên**: `[tai may] 0.9/20 loi dang ban -> RANH`.

```
28 buoc PASS · 1 BOQUA · 1 FAIL = 30 buoc
pha 1 song song   606 giay
pha 2 noi tiep    138 giay
TONG              744 giay (12,4 phut)
RESULT: FAIL (1/30) [1 BUOC TU BO QUA...] [CAY DA DOI GIUA CHUNG - KHONG DUNG LAM BANG CHUNG]
```

⭐ **744 s xác nhận con số 682,8 s** (trung vị 43 lượt) và bác dứt điểm "~5 phút".
Bước mới `luat van hanh` chạy **1,9 s** — khớp phép đo trước.

### ⛔ Nhưng lượt này KHÔNG dùng làm bằng chứng được, và gate tự nói ra

```
CAY DA DOI TRONG LUC CHAY:
    M alembic/versions/20260908_1200_workflow_v2_thi_hanh.py   (6218 -> 6221 byte)
    + alembic/versions/20260908_1600_voice_license_va_curate.py
    M apps/ltt_voice/nghe_thu.py                               (16285 -> 18351 byte)
    M apps/ltt_voice/tables.py                                 (18234 -> 23515 byte)
    + apps/ltt_voice/muc_dung.py
    ... va 4 tep nua                            (tong 16+ tep, hai phien khac)
```

🔴 **Đây là bài học đắt nhất của cả chiến dịch, và nó là một PHÂN BIỆT:**

> Chủ sản phẩm đã bảo các phiên khác **không dùng CPU**, và họ giữ lời — máy chỉ
> 0,9/20 lõi bận. Nhưng họ **vẫn ghi tệp**. "Không dùng CPU" và "cây đứng yên" là
> **hai điều kiện khác nhau**, và một lượt gate cần **cả hai**.

`cua_so_yen` trả lời *"máy có bận không"*. Không công cụ nào ở đây trả lời *"cây
có đứng yên không"* **trước** khi chạy — chỉ có ảnh chụp trước/sau, tức nó nói
cho bạn biết **sau khi đã mất 12,4 phút**.

### Một lỗi duy nhất, và nó cũng không phải của chiến dịch

`test_306::test_bo_qua_hien_tai_dat_moc` — hai phép kiểm mới bị bỏ qua:

```
CHO BO QUA MOI (2):
  test_507_muc_dung_thu_tu_giong.py::_cung_tang  <- khong co tang nao co hai giong
  test_507_muc_dung_thu_tu_giong.py::test_muc_dung_KHONG_keo_duoc_mot_giong_qua_TANG
```

`tests/test_507_muc_dung_thu_tu_giong.py` là tệp **untracked**, tạo lúc **15:37**
— tức **giữa** lượt gate bắt đầu lúc 15:32, bởi phiên LTT VOICE.

⇒ Đúng cơ chế `Bẫy 37` (`docs/BAY_TRONG_CONG_CHAT_LUONG.md`), ở **dạng thứ hai**:
lần trước một tệp untracked của phiên A cộng vào bánh cóc `ruff` của phiên B;
lần này nó cộng vào bánh cóc **bỏ qua**. Cùng một lỗ, hai bánh cóc khác nhau.

### Bước tự bỏ qua

`bat bien da tien trinh` ra `[BOQUA]` sau **0,7 s** (bình thường 138 s) — nó cần
PostgreSQL và tự khai là không chạy được. Gate in điều đó **ở dòng `RESULT`**,
đúng như thiết kế: một bước không chạy mà trông như đã chạy thì không ai đi tìm nó.

### Kết luận cho hạng mục P0

Con số **12,4 phút cho L3 là dùng được** (thời lượng không phụ thuộc cây có đổi
hay không). Nhưng **phán quyết PASS/FAIL thì không**, và số giây cho `--doi` vẫn
chưa đo được — cả ngày 08/09 **chưa có một cửa sổ nào cây đứng yên đủ 12 phút**.
