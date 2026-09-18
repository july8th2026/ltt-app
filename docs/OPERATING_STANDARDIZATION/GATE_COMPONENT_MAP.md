# GATE COMPONENT MAP — từng bước, giá của nó, và nó thuộc cấp nào

> ⚠️ **Ảnh chụp ngày 08/09/2026.** Danh sách bước và chi phí hiện hành: nguồn chân lý
> là `tools/gate.py::_steps` (và bản ghi `test-results/gates/*.json`), không phải bảng dưới.

> Số liệu **đo được**, không ước lượng: trung vị trên **59 bản ghi thật** trong
> `test-results/gates/*.json` (43 lượt `day-du`, 16 lượt `vong-lap`).
> Bước lấy bằng cách **gọi `_steps()`**, không bằng đọc tài liệu và cũng không bằng
> đếm `Step(` trong mã — xem cảnh báo ở §1.

## 0. Ba con số phải biết trước

| | Tài liệu **nói** | Đo được (trung vị) | Chênh |
|---|---|---|---|
| Gate đầy đủ | "~5 phút" (`CLAUDE.md` §4, `AGENTS.md` §4b) | **682,8 s ≈ 11,4 phút** | **2,3×** |
| `--vong-lap` | "~15 giây" | **21,4 s** — nhưng **max 543,7 s** | tới **36×** |
| Lượt đầy đủ ĐỎ | — | **20/43 = 47 %** | — |

⛔ Con số "~5 phút" trong `CLAUDE.md` và `AGENTS.md` **sai hơn gấp đôi**. Nó là
lý do người ta né gate: một người tin "5 phút" rồi mất 11 phút sẽ không chạy lại.

## 1. Bảng bước

`nhom`: `cong` = cổng vào · `tinh` = kiểm tĩnh (mặc định) · `nang` = nặng ·
`frontend` = vitest · `sau_test` = chạy sau bộ test.

| Bước | Lệnh | Giá (trung vị) | Tài nguyên | Cấp | Song song? | Trùng? |
|---|---|---:|---|---|---|---|
| `bo test (song song)` | `test_nhanh.py -n <ngân sách>` | **550,8 s** | `cpu_nhieu`, `postgres_test` | **L3** | nội bộ xdist | ⛔ **có** — xem §3 |
| `bat bien da tien trinh` | `check_multiproc.py` | **138,0 s** | `postgres_test` | **L2/L3** | 2 lõi | — |
| `secret scan` | `scan_source_secrets.py` | 16,6 s | — | **L0** | ✅ | — |
| `frontend agent-canvas` | `npm test --run` | 15,1 s | — | L2 | ✅ | — |
| `frontend chatltt` | `npm test --run` | 9,0 s | — | L2 | ✅ | — |
| `frontend prompt-ai-ommi` | `npm test --run` | 5,1 s | — | L2 | ✅ | — |
| `frontend autosub-studio` | `npm test --run` | 4,7 s | — | L2 | ✅ | — |
| `bien dich duoc` | `check_bien_dich.py` | 3,7 s | — | **L0** (cổng) | ✅ | — |
| `ten chua dinh nghia` | `check_undefined_names.py` | 3,5 s | — | **L0** | ✅ | — |
| `mypy` | `check_mypy.py` | 2,7 s | — | **L0** | ✅ | — |
| `dich thieu ban EN` | `check_dich_thieu.py` | 2,5 s | — | L0 (`sau_test`) | ✅ | — |
| `bo qua im lang` | `check_bo_qua.py` | 2,4 s | — | **L0** | ✅ | — |
| `postman` | `build_postman.py --check` | 2,4 s | — | L0 (`sau_test`) | ✅ | — |
| `chuoi chua dich` | `check_i18n.py` | 2,1 s | — | **L0** | ✅ | — |
| `ruff` · `ranh gioi import` · `nuot loi lang le` · `app contract lint` · `kieu xuong dong` · `kich thuoc route server` · `chuong chua treo` · `bien .ps1 trung tham so` · `trung so test` · `ky tu dieu khien` · `hop dong API` · `anh chup hop dong` · `tai lieu sinh ra` · `SDK khop hop dong` · `tai san GUI` | — | mỗi bước **< 2 s** | — | **L0** | ✅ | — |

**Tổng: 30 bước** ở hồ sơ đầy đủ trên cây này — `1 cổng · 18 tĩnh · 5 sau_test ·
4 frontend · 2 nặng`. `--vong-lap` còn **25**.

⚠️ Con số này **phải lấy từ `_steps()`, không đếm `Step(` trong mã.** Bản nháp
đầu của tệp này ghi *26* vì đếm lời gọi `Step(` bằng AST — nhưng ba lời gọi
`frontend` nằm trong một vòng lặp có điều kiện, nên số **lời gọi** không bằng số
**bước**. Đúng cái bẫy "đọc thứ đại diện thay vì đọc thứ thật".

### Phân bố giá — và nó nói gì

```
bo test (song song)      550,8 s  ████████████████████████████  81 %
bat bien da tien trinh   138,0 s  ███████                       20 %
23 buoc tinh + frontend   ~60 s   ███                            9 %
```

⇒ **Nhóm kiểm tĩnh — thứ bắt phần lớn lỗi thật — chỉ tốn 9 % thời gian
gate.** Đó chính là lý do một cấp L0 tồn tại được: bỏ hai bước nặng là bỏ 91 %
chi phí mà vẫn giữ 28/30 bước.

## 2. Bốn cấp — ĐÃ CÓ SẴN, không cần xây mới

`gate.py` đã có **bảng `HO_SO` 7 hồ sơ**, mỗi hồ sơ kèm **hợp đồng viết thành
chữ** (`chung_minh` / `khong_chung_minh`) in ra ở dòng `RESULT`.

| Cấp | Lệnh **đã có** | Bước chạy | Đo được | Xếp hàng |
|---|---|---|---|---|
| **L0** | `gate.py --quick` | **28** bước, bỏ 2 bước nặng | ~40–60 s | không |
| **L0+** | `gate.py --vong-lap` | **25** bước: tĩnh + `test_nhanh --lf` | 21,4 s *(max 543,7)* | không |
| **L1** | `gate.py --doi` | tĩnh + test của phần **đã đổi** | *(xem §4)* | ✅ |
| **L2** | `gate.py --pham-vi <tp>[,<tp>…]` | tĩnh (một lần) + HỢP test của các thành phần chọn tay | — | ✅ |
| **L3** | `gate.py` | tất cả **30** bước | **682,8 s** | ✅ |
| L3+ | `gate.py --noi-tiep` | L3, một bước một lúc, một tiến trình pytest | ~25–30 phút | ✅ |
| L3++ | `gate.py --ho-so phat-hanh` | L3 + cài/cập nhật/rollback + quét bí mật | — | ✅ |

⛔ **KHÔNG thêm bí danh `--fast`/`--affected`/`--subsystem`/`--full`.** Chính
`gate.py:900` cấm điều đó: *"MOT BANG CHE DO DUY NHAT — `HO_SO`. Khong co 'gate
cu' va 'gate moi'."* Thêm tên thứ hai cho cùng một hồ sơ là **nhân đôi đúng thứ
chiến dịch này đang xoá**. Bốn cấp đã đủ ngữ nghĩa; việc còn thiếu là **tài liệu
chỉ vào chúng**, không phải thêm cờ.

## 3. ⛔ Gate CÓ chạy pytest — nên "pytest rồi gate" là trả tiền hai lần

`tools/gate.py:844`:

```python
Step("bo test (song song)", [sys.executable, "tools/test_nhanh.py", "-n", str(loi_bo_test)], ...)
```

Bước `bo test` **chính là** `test_nhanh.py`. Vậy nên:

| Nguồn | Bảo làm gì | Giá thật |
|---|---|---|
| `docs/MOBILE/00_KE_HOACH.md:194-195` | `test_nhanh.py` (~4 phút) **rồi** `gate.py` | ~4 phút trả **hai lần** |
| `docs/auto_scan_video/BASELINE_COMMANDS.md:12,15` | y hệt | ~4 phút trả **hai lần** |
| `CLAUDE.md` §4 / `AGENTS.md` §4b | liệt kê cả hai trong **một** bảng ba lệnh | mời gọi đúng lỗi trên |

⇒ Luật canonical: **`test_nhanh.py` gõ tay chỉ dùng khi bạn KHÔNG định chạy gate
sau đó.** Chạy nó rồi chạy gate là mua cùng một câu trả lời hai lần.

## 4. 🔴 `--doi` tồn tại, được tài liệu hoá, và CHƯA TỪNG THU HẸP GÌ

Đếm trên **59 bản ghi** `test-results/gates/*.json`:

```
day-du     43 luot
vong-lap   16 luot
doi         0 luot      <-- 
pham-vi     0 luot      <--
noi-tiep    0 luot
```

Không phải vì không ai biết — `DEVELOPMENT_WORKFLOW.md` §2 đã đặt `--doi` làm
vòng lặp mặc định từ lâu. Lý do thật, đo được ngày 08/09:

`bi_anh_huong()` trả `None` (⇒ hạ cấp xuống **đầy đủ**) khi gặp một đường dẫn
**không thành phần nào sở hữu**. `thanh_phan.toml` khai đường cho mã **sản phẩm**
và **không khai `tests/`**. Nên:

> **Mọi thay đổi chạm một tệp test đều hạ cấp xuống gate đầy đủ.**
> Và gần như mọi thay đổi thật đều kèm một tệp test.

Đo trên cây bẩn lúc bắt đầu chiến dịch (18 đường dẫn đổi):

```
$ python tools/thanh_phan.py --doi
18 duong dan doi
=> cham tep DUNG CHUNG hoac duong khong ai so huu -> phai chay TAT CA
```

### Đã sửa — 08/09

Một tệp test **không có người tiêu thụ**: không ai `import` một module test, nên
không có cạnh nào để mở rộng. Sửa một tệp test chỉ ảnh hưởng **chính tệp đó**.

- `thanh_phan.bi_anh_huong` — `tests/test_*.py` **không đóng góp thành phần**
  (thay vì trả `None` làm hạ cấp cả lượt).
- `thanh_phan.tep_test_da_doi` — tệp test đã đổi nộp **thẳng** vào danh sách chạy.
- `gate._thu_hep` — hợp hai nguồn lại.

⛔ **Một hướng đã thử và ĐÃ BỎ.** Bản đầu suy chủ của tệp test từ `import` của
chính nó (đảo ngược `test_cua_thanh_phan`). Đo ra: `test_500` import một module
nền ⇒ **36 thành phần ⇒ 456/532 tệp test (86 %)**. Một phạm vi *trông như hẹp mà
không hề hẹp* — đúng cái bẫy `HO_SO` cảnh báo. Bỏ.

### Đo sau khi sửa

| Thay đổi | Trước | Sau |
|---|---|---|
| chỉ một tệp test | **532/532** (100 %) | **1/532** (0 %) |
| `apps/ltt_voice/vo.py` + test của nó | **532/532** | **118/532** (22 %) |
| `apps/thumbnail/routes.py` + `test_104` | **532/532** | **48/532** (9 %) |

### Fail-open giữ nguyên — đã kiểm từng cái

| Đường dẫn | Kết quả | Vì sao đúng |
|---|---|---|
| `tests/conftest.py` | `None` → đầy đủ | nằm trong `DUNG_CHUNG` |
| `tools/gate.py` | `None` → đầy đủ | nằm trong `DUNG_CHUNG` |
| `tests/fixtures/x.py` | `None` → đầy đủ | mã **hỗ trợ**, không phải module test |
| `mot/duong/khong/ton/tai.py` | `None` → đầy đủ | không ai sở hữu |
| `platform_core/credit.py` | 4 thành phần | mở rộng người tiêu thụ vẫn chạy |

Bốn dòng đầu chính là bốn phép chốt của `tests/test_394_nen_da_phien.py`.

## 5. Việc còn treo — `docs/**` vẫn hạ cấp xuống đầy đủ

`docs/**` cũng không thành phần nào sở hữu, nên một thay đổi **chỉ tài liệu** vẫn
chạy gate đầy đủ 11 phút.

⛔ **Và "tài liệu thì trơ" là SAI — đã kiểm.** `grep` thấy **70 tệp test** đọc
`docs/` (`test_104_design_system_contract`, `test_190_public_api_coverage`,
`test_212_coverage_certification`, …). Một luật "docs không đóng góp gì" sẽ bỏ
qua 70 phép kiểm một cách im lặng.

⇒ Cần một bản khai chủ sở hữu cho `docs/`, không phải một luật miễn trừ.
**FOLLOW_UP P1** — xem `docs/_luutru/OPERATING_STANDARDIZATION_2026-09-08/FINAL_REPORT.md`. Không làm trong chiến dịch này: rủi ro
bỏ sót phép kiểm cao hơn hẳn lợi ích, và §18 của điều lệ nói rõ chọn 80/20.
