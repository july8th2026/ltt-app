# FINAL REPORT — OPERATING STANDARDIZATION

**2026-09-08** · cây `D:\LTTSTUDIOSAPP` · nhánh `admin-mvp-v3` · phiên `lttstudiosapp-32`

---

## Rules

| | |
|---|---|
| Tệp `.md` **được git theo dõi** đã quét | **822** (`git ls-files`, trừ `docs/_luutru/`) |
| Nguồn có mệnh lệnh cadence toàn cục / kế hoạch | **30** |
| Rule ghi vào inventory | **44** |
| **Rule xoá khỏi HEAD** | **11** |
| Rule hợp nhất vào canonical | **11** |
| Rule giữ + trỏ về canonical | **11** |
| Tách ra thành "sự thật kỹ thuật, không phải chính sách" | **6** |
| **Chính sách vận hành cạnh tranh còn lại** | **0** *(đóng nốt 15:55 — xem dưới)* |

### Cadence mâu thuẫn tìm thấy — **5 bản khác nhau** cùng sống trong HEAD

| Bản | Nguồn |
|---|---|
| `--vong-lap` sau **mỗi** lần sửa | `CLAUDE.md` §4 · `AGENTS.md` §4b · CHATLTT_V3 · KE_HOACH_NOI_TIEP · admin_mvp_v3 · VOICE_UI · MOBILE |
| `--doi` trong vòng lặp | `DEVELOPMENT_WORKFLOW.md` §2 · CHATLTT |
| `test_nhanh.py --lf` sau mỗi lần sửa | VPS/UI_MVP_V2 |
| một tập bất biến riêng sau mỗi edit | auto_scan_video/STATE · STATE_V4 |
| `test_nhanh.py` **rồi** `gate.py` | MOBILE · auto_scan_video/BASELINE_COMMANDS |

⭐ **Bản đúng nhất lại là bản ít được nhắc nhất.** `DEVELOPMENT_WORKFLOW.md` §2 —
nguồn duy nhất đặt `--doi` làm mặc định — bị hai tệp mà mọi phiên đọc đầu tiên
(`CLAUDE.md`, `AGENTS.md`) nói ngược lại. Hợp đồng canonical giữ lựa chọn của
`DEVELOPMENT_WORKFLOW.md`.

### Ba mục hoãn ban đầu — nay **đóng cả ba**

Lúc 12:00 tôi hoãn ba tệp vì worktree của chúng **đang sống**, và sửa một tệp
phiên khác đang mở là tạo xung đột merge cho họ.

| Tệp | Cách đóng |
|---|---|
| `docs/LTT_VOICE/VOICE_UI_EXECUTION_PLAN.md` | **phiên chủ tự sửa** sau migration note |
| `docs/CHATLTT_V3/00_KE_HOACH_V3.md:253` | tôi sửa lúc 15:55 — xem dưới |
| `docs/auto_scan_video_v4/STATE_V4.md:400` | tôi sửa lúc 15:55 — xem dưới |

⭐ **Lý do hoãn hết hiệu lực, và tôi ĐO điều đó chứ không đoán:**

```
$ git rev-parse admin-mvp-v3:<tep>  vs  <nhanh-kia>:<tep>
  GIONG NHAU  docs/CHATLTT_V3/00_KE_HOACH_V3.md      (chatltt-v3-agentic)
  GIONG NHAU  docs/auto_scan_video_v4/STATE_V4.md    (phien/asv-v4)
```

Cùng một băm trên mọi nhánh ⇒ **không ai đang sửa chúng**, và cả hai phiên đều
không chạy (`list_sessions`). Rủi ro tôi hoãn vì nó không còn tồn tại.

⚠️ Một worktree **tồn tại** không có nghĩa là một phiên **đang sửa**. Tôi đã lẫn
hai thứ đó lúc 12:00 — thận trọng đúng lúc ấy, nhưng đáng lẽ phải đo lại thay vì
để nó thành nợ vĩnh viễn.

⇒ Bảng `NO_CU` của bánh cóc nay **rỗng**, và bộ dò đỏ nếu ai để lại một mục đã
được dọn — nên trạng thái này không trôi ngược được.

---

## Gate

| Cấp | Lệnh | Ghi chú |
|---|---|---|
| **FAST (L0)** | `python tools\gate.py --quick` · `--vong-lap` | đã có sẵn |
| **AFFECTED (L1)** | `python tools\gate.py --doi` | đã có sẵn — **nhưng chưa từng thu hẹp gì; đã sửa** |
| **SUBSYSTEM (L2)** | `python tools\gate.py --pham-vi <tp>` | đã có sẵn |
| **FULL (L3)** | `python tools\gate.py` | đã có sẵn |

**Gate có chứa pytest không? — CÓ.** Bước `bo test` *chính là* `tools/test_nhanh.py`
(`tools/gate.py:844`). Nên "`test_nhanh.py` rồi `gate.py`" là trả ~9,2 phút hai
lần; hai tài liệu dạy đúng việc đó, cả hai đã gỡ.

### ⛔ KHÔNG thêm bí danh `--fast/--affected/--subsystem/--full`

Điều lệ §13 cho phép giữ quy ước sẵn có nếu nó tốt hơn. Ở đây nó tốt hơn, và
`gate.py:900` **tự cấm** việc thêm: *"MOT BANG CHE DO DUY NHAT — `HO_SO`. Khong
co 'gate cu' va 'gate moi'."* Bảy hồ sơ hiện có, mỗi cái kèm **hợp đồng viết
thành chữ** (`chung_minh` / `khong_chung_minh`) in ra ở dòng `RESULT`. Thêm tên
thứ hai cho cùng một hồ sơ là **nhân đôi đúng thứ chiến dịch này đang xoá**.

⇒ Bốn cấp ngữ nghĩa **đạt bằng tài liệu trỏ vào cơ chế sẵn có**, không bằng cờ mới.

### 🔴 Phát hiện lớn nhất: `--doi` là một CỬA GIẢ

```
day-du  43 luot   vong-lap  16 luot   doi  0 luot   pham-vi  0 luot
```

Không ai dùng `--doi` — vì nó **không bao giờ thu hẹp**. `bi_anh_huong()` hạ cấp
xuống đầy đủ khi gặp đường dẫn không ai sở hữu, và `thanh_phan.toml` **không khai
`tests/`**. Mà gần như mọi thay đổi thật đều kèm một tệp test.

**Sửa:** một tệp test **không có người tiêu thụ** — không ai `import` một module
test — nên nó chỉ ảnh hưởng chính nó, và được nộp thẳng vào danh sách chạy.

| Thay đổi điển hình | Trước | Sau |
|---|---:|---:|
| chỉ một tệp test | 532/532 | **1/532** |
| app + test của nó | 532/532 | **118/532** |
| `thumbnail/routes.py` + `test_104` | 532/532 | **48/532** |

⛔ **Một hướng đã thử và BỎ.** Bản đầu suy chủ của tệp test từ `import` của chính
nó. Đo ra **456/532 (86 %)** — một phạm vi *trông hẹp mà không hề hẹp*, đúng cái
bẫy `HO_SO` cảnh báo. Phép đo giết giả thuyết, không phải trực giác.

**Fail-open giữ nguyên**, đã kiểm từng cái: `tests/conftest.py`, `tools/gate.py`
(cả hai `DUNG_CHUNG`), `tests/fixtures/*.py` (mã hỗ trợ), đường dẫn không tồn tại
— tất cả vẫn hạ cấp xuống đầy đủ. Đó là bốn phép chốt của `test_394`.

---

## Performance

| | Tài liệu cũ | **Đo được** |
|---|---|---|
| Gate đầy đủ | "~5 phút" | **682,8 s ≈ 11,4 phút** (trung vị/43 lượt) |
| `--vong-lap` | "~15 giây" | **21,4 s**, max **543,7 s** |
| `bo test` chiếm | — | **81 %** thời gian gate |
| nhóm kiểm tĩnh + frontend chiếm | — | **9 %** |
| Bước mới `luat van hanh` | — | **1,6 s** (0,23 %) |

⭐ Con số "~5 phút" sống ở **6 tệp**, sai hơn gấp đôi ở cả sáu — vì cả sáu đều
chép tay từ nhau. Và cái giá không chỉ là thời gian: một người tin "5 phút" rồi
mất 11 phút sẽ **không chạy lại lượt sau**.

**Lần chạy trùng đã gỡ:** 2 nguồn × ~9,2 phút mỗi lượt.

---

## Sessions

Câu để re-anchor một phiên đang chạy: **`SESSION_MIGRATION_NOTE.md`** (bốn dòng).

**Worktree được bảo vệ — không cái nào bị chạm:**

```
phien/asv-v4 · claude/chatltt-v3-agentic · phien/video-v2-wangp
ltt-llm-api-http-guide (detached) · h42-release-clean
```

⛔ **Việc dở của phiên khác trong CHÍNH cây này được giữ nguyên.** 16 tệp LTT
VOICE (12 `M` + 4 `??`) không bị `stash`, `checkout`, hay commit gộp. Chiến dịch
chỉ liệt kê **đúng tệp của nó** khi commit.

### ⚠️ Hai thứ bắt được ở khu người khác — báo, không sửa

1. **Việc dở của phiên VOICE đang làm đỏ BA bánh cóc** ⇒ gate đầy đủ của **bất kỳ
   ai** trên cây này cũng đỏ:

   | Bánh cóc | Mốc → nay | Vị trí | Test đỏ |
   |---|---|---|---|
   | ruff `F401` | 416 → **417** | `apps/ltt_voice/routes/_p_tao.py:5` (`File`) | `test_306` |
   | mypy `var-annotated` | 44 → **45** | `tools/do_ho_so_giong.py:110` | `test_306` |
   | mypy `arg-type` | 124 → **126** | `tools/do_ho_so_giong.py:114` (×2) | `test_306` |
   | nuốt lỗi lặng lẽ | 62 → **63** | `tools/do_ho_so_giong.py:94` | `test_145` |

   **Đã đối chứng, không suy đoán:** `ruff --select F,B` trên ba tệp của chiến
   dịch cho **0** phát hiện mới; mypy cho **0**; `check_silent_except --list`
   không nêu tệp nào của chiến dịch. Không phải lỗi của chiến dịch.

   ⚠️ **Và một bài học về cách đọc.** `check_ruff.py` in `[ruff] dat moc: 943 phat
   hien` rồi vẫn **thoát mã 1** — lượt đọc đầu của chiến dịch này đã đọc dòng đó
   thành "xanh". Đọc `returncode`, đừng khớp mẫu stdout.
2. **`docs/auto_scan_video_v4/STATE_V4.md:756`** viết *"There is no `pytest.ini`
   … in the repo at all"* — **sai**, `pytest.ini` có trong HEAD và khai marker
   `nang`. Kết luận rút ra từ câu đó nên được đọc lại.

---

## Remaining

### P0

| | |
|---|---|
| Đo thời gian **đầu-cuối** thật cho `--doi` | Cây đang bẩn bởi phiên khác, và `gate.py`+`thanh_phan.py` vừa sửa đều `DUNG_CHUNG` ⇒ lượt `--doi` kế tiếp **tự hạ cấp**. Phải đo ở lượt sạch sau. Số hiện có là **số tệp test**, không phải giây — đừng suy tuyến tính. |
| ⭐ **Không có công cụ nào trả lời "cây có đứng yên không" TRƯỚC khi chạy** | `cua_so_yen` đo **máy bận**, không đo **cây đổi**. Lượt 15:32 hỏng vì đúng khe này. Cần một phép chụp-và-so trước khi bấm, hoặc một khoá ghi theo cây |

### P1

| | |
|---|---|
| `docs/**` vẫn hạ cấp xuống đầy đủ | **70 tệp test đọc `docs/`** — đã `grep`, không đoán. Luật "docs thì trơ" sẽ bỏ qua 70 phép kiểm **im lặng**. Cần bản khai chủ sở hữu cho `docs/`, không phải luật miễn trừ. |
| `@pytest.mark.slow` dùng 1 lần mà **không khai** trong `pytest.ini` | chưa gãy vì `--strict-markers` chưa bật |
| ~~3 phiên còn cadence riêng~~ | ✅ **đóng cả ba** lúc 15:55 |
| 11 tệp trích `OPERATING_CONTRACT §5/§10/§13` **không tồn tại trong HEAD** | Nay đã có hợp đồng thật; các trích dẫn cũ trỏ vào một prompt của phiên đã đóng, không kiểm chứng được |

### Hoãn có chủ ý

`pytest-xdist` mở rộng — **đã tối ưu xong 26/08** (2 giờ → 4 phút). Không còn
phần dễ ăn.

---

## Trung thực về việc chưa làm

## ✅ CẬP NHẬT 15:45 — đã chạy L3, chủ sản phẩm cho phép

```
28 buoc PASS · 1 BOQUA · 1 FAIL = 30 buoc      TONG 744 giay (12,4 phut)
RESULT: FAIL (1/30) [1 BUOC TU BO QUA] [CAY DA DOI GIUA CHUNG - KHONG DUNG LAM BANG CHUNG]
```

| | |
|---|---|
| **28 bước PASS** | gồm bước mới `luat van hanh` (**1,9 s**) và cả 23 bước tĩnh |
| `bat bien da tien trinh` | `[BOQUA]` sau 0,7 s — **tự khai** là không chạy. ⚠️ Nguyên nhân **không** phải "thiếu PostgreSQL", cũng **không** phải thiếu `CREATEDB` — xem đính chính 08/09 bên dưới |
| `bo test` FAIL | **1 phép kiểm**: `test_306::test_bo_qua_hien_tai_dat_moc` |

Phép kiểm đỏ duy nhất: hai `skip` mới trong
`tests/test_507_muc_dung_thu_tu_giong.py` — tệp **untracked**, tạo lúc **15:37**,
tức **giữa** lượt gate bắt đầu lúc 15:32, bởi phiên LTT VOICE. Không phải của
chiến dịch này. *(Đúng cơ chế `Bẫy 37`, dạng thứ hai — xem `PERFORMANCE_REPORT` §9.)*

⭐ **744 s xác nhận 682,8 s** và bác dứt điểm "~5 phút".

### ⚠️ Và tôi chẩn đoán SAI bước `[BOQUA]` ấy — phiên LTT VOICE bắt được

Tôi viết *"cần PostgreSQL"*, người đọc hiểu thành *"máy này thiếu PostgreSQL"*.
Đo lại trên chính máy này:

```
cong 5432                MO            <- PostgreSQL DANG CHAY
LTT_TEST_DATABASE_URL    (chua dat)
check_multiproc._tim_url()
  -> ('', 'khong tao duoc CSDL test: ProgrammingError
           (khong noi duoc truoc do: OperationalError)')
```

⇒ PostgreSQL **có**.

### ⛔ ĐÍNH CHÍNH 08/09/2026 (phiên LTT VOICE) — CHẨN ĐOÁN TRÊN CŨNG SAI

Đoạn gốc ở đây viết *"gần như chắc là tài khoản ứng dụng thiếu quyền
`CREATEDB`"*. Đo tiếp thì **không phải**:

```
_doc_env doc theo thu tu:
  1) C:\LTTPlatform\secrets\app.env   -> Access to the path is denied   (ACL)
  2) D:\LTTSTUDIOSAPP\secrets\app.env -> DOC DUOC                       (dung cai nay)

ket noi bang URL lay tu (2):
  FATAL: password authentication failed for user "ltt_app"

production /health/ready -> 200
```

Xác thực **trượt trước** khi tới bước dựng CSDL nháp, nên `CREATEDB` chưa bao
giờ được hỏi tới. Nguyên nhân thật: gate chạy dưới tài khoản **không đọc được
bí mật production**, nên `_doc_env` rơi xuống `app.env` **trong cây nguồn**, và
mật khẩu ở đó không khớp Postgres đang chạy. Production khoẻ (200) — bí mật
thật hoàn toàn đúng, chỉ là gate không đọc được nó.

### 🔴 Và bản vá "hiển nhiên" là bản vá SAI

`icacls` mở `C:\LTTPlatform\secrets\` cho gate đọc được là **gỡ hạng mục
W1.5** của `AUDIT_MVP_2026-07-31` — *"thư mục bí mật chỉ SYSTEM/Admin đọc"*.
`CLAUDE.md` ghi thẳng rằng ACL ở đó là **cố ý**.

⭐ Nên bước này bỏ qua **vì một bản vá bảo mật đang làm đúng việc của nó**. Đó
không phải một khiếm khuyết cần vá — nó là một **đánh đổi** cần một đường thứ
ba: một CSDL test **riêng**, tài khoản **riêng**, đặt qua
`LTT_TEST_DATABASE_URL`. Không bao giờ cho cổng chất lượng chạm bí mật
production.

### ⭐ Ba vòng, và mỗi vòng đều "đúng" ở tầng của nó

```
vong 1  "thieu PostgreSQL"       -> sai. Postgres dang chay.
vong 2  "thieu quyen CREATEDB"   -> sai. Xac thuc da truot truoc do.
vong 3  doc nham TEP app.env, vi tep dung bi ACL chan
```

Cùng hình dạng với `Bẫy 8`: **thông điệp đúng về sự việc, sai về nguyên nhân** —
và ở đây nó lặp **ba** vòng, vì mỗi thông điệp lỗi đều đúng về sự việc của tầng
nó. *Loại trừ một nguyên nhân không phải là xác định nguyên nhân còn lại.*

⚠️ Thứ cắt được vòng lặp không phải sự cẩn thận — là in `user=` và `host=` ra
thay vì chỉ in `type(ex).__name__`. Hai vòng đầu chỉ đọc **tên lớp ngoại lệ**,
và một tên lớp thì tương thích với mọi giả thuyết.

🔴 **Hệ quả thật, và nó không nhỏ:** bước ấy là bước **duy nhất** chạy migration
trên PostgreSQL. Nó `[BOQUA]` ⇒ **chưa migration nào trong kho từng được thi hành
trên một PostgreSQL sống, ở bất kỳ lượt gate nào.** Phiên Workflow V2 vừa tìm ra
một lỗi mà **chỉ** Postgres bắt được (`BOOLEAN DEFAULT 1` — SQLite nhận, Postgres
từ chối), tức lớp lỗi ấy có thật và đang không có ai canh.

⇒ **FOLLOW_UP P0 mới**: dựng một CSDL test **riêng** với tài khoản **riêng**,
rồi đặt `LTT_TEST_DATABASE_URL`. Không tự làm — đổi trạng thái một máy đang chạy
thật là quyết định của chủ sản phẩm.

⛔ **Đừng ghi sẵn một lệnh sửa vào P0 này.** Bản đầu ghi `GRANT CREATEDB`, và
lệnh ấy **không sửa gì** — sẽ có người chạy nó, thấy bước vẫn `[BOQUA]`, rồi kết
luận sai lần thứ tư. Thứ đáng ghi là **lệnh ĐO**:

```
python -c "import sys; sys.path.insert(0,'.'); from tools import check_multiproc as M; print(M._tim_url())"
```

rồi phân biệt ba nguyên nhân ở trên bằng chính thông điệp trả về.

### 🔴 Bài học đắt nhất — một PHÂN BIỆT, không phải một lời nhắc

> Chủ sản phẩm đã bảo các phiên khác **không dùng CPU**, và họ **giữ lời**: máy chỉ
> 0,9/20 lõi bận suốt lượt chạy. Nhưng họ **vẫn ghi tệp** — 16 tệp.
>
> **"Không dùng CPU" ≠ "cây đứng yên".** Một lượt gate cần **cả hai**, và
> `cua_so_yen` chỉ trả lời được vế thứ nhất.

Vế thứ hai hiện **không có công cụ nào trả lời trước khi chạy** — chỉ có ảnh chụp
trước/sau, tức nó báo cho bạn sau khi đã mất 12,4 phút. **FOLLOW_UP P0 mới.**

---

⛔ **Vì sao trước 15:45 chưa chạy L3.** Ba lý do, và lý do thứ ba mới là lý do thật:

1. Cây mang **16 tệp dở của phiên VOICE**, và **một tệp trong đó đang làm đỏ hai
   bánh cóc** (`test_306`, `test_145` — bảng ở mục Sessions). Tức một lượt L3
   **chắc chắn đỏ**, và đỏ vì lý do không thuộc chiến dịch này. Chạy nó chỉ tạo
   ra một dòng `FAIL` mà người đọc sau sẽ gán nhầm cho chiến dịch.
2. Điều lệ §21 cấm biến chiến dịch tăng tốc thành chiến dịch chạy 20 lượt gate.
3. Một lượt L3 trên cây bẩn **không phải bằng chứng** — luật của chính kho này.
   Và cây này **không đứng yên**: lúc 15:06–15:22, giữa lượt kiểm của chiến dịch,
   một phiên thứ hai ghi 8 tệp Workflow V2 vào đây. Một lượt 11,4 phút cần cây
   đứng yên 11,4 phút; điều đó đã không xảy ra lần nào hôm nay.

**Đã chạy thay vào đó:**

| Phép kiểm | Kết quả |
|---|---|
| `check_luat_van_hanh.py --tu-kiem` | ✅ 3 mẫu xấu + 9 mẫu tốt, 0 sai |
| `check_luat_van_hanh.py` toàn kho | ✅ `RESULT: PASS` (1 nợ cũ có chủ) |
| **Đối chứng**: tiêm một luật xấu vào tệp tracked | ✅ **`RESULT: FAIL`, rc=1**, rồi khôi phục **byte-exact**, rc=0 |
| `check_ruff.py` | ✅ đạt mốc (943/12) |
| `check_mypy.py` trên 2 tệp đã sửa | ✅ 0 lỗi mới *(mốc chung tăng vì tệp phiên khác)* |
| `ast.parse` sau **mỗi** lần ghi tệp `.py` | ✅ |
| `test_394` (chốt `bi_anh_huong`, 4 ca fail-open) | ✅ pass |
| `test_145` · `test_332` · `test_394` — **247 phép kiểm** | **243 pass, 4 fail** |

Bốn lượt đỏ, **không lượt nào của chiến dịch này** — đã truy từng cái tới nguồn:

| Đỏ | Nguồn thật |
|---|---|
| `test_306::test_ruff_hien_tai_dat_moc` | phiên VOICE — `F401` 416→417 ở `_p_tao.py:5` |
| `test_306::test_mypy_hien_tai_dat_moc` | phiên VOICE — mypy +3 ở `do_ho_so_giong.py` |
| `test_145::test_banh_coc_nuot_loi_...` | phiên VOICE — nuốt lỗi 62→63 ở `do_ho_so_giong.py:94` |
| `test_145::test_ba_tep_..._CA_DAU_THOI_GIAN` | ⭐ **một phiên THỨ HAI ghi Workflow V2 vào cây GIỮA lượt chạy** (15:06→15:22) |

⭐ Cái thứ tư đáng chú ý: phép kiểm chụp cây trước/sau và thấy
`platform_core/workflow/he_kieu.py` + `tests/test_958_wf_he_kieu_cong.py` xuất
hiện giữa chừng. Câu báo lỗi đổ cho "ba tệp pha 2" — một **nghi phạm vô tội**
(Bẫy 8). ⚠️ Và `ListAgents` **không** phát hiện được: nó vẫn báo đúng 4 phiên
như lúc 09:00, vì phiên ấy chỉ **đổi việc**. Thứ trả lời "ai đang ghi vào đâu"
là `mtime`, không phải bảng phiên.

**Quan trọng: `test_145` và `test_332` — hai tệp chốt chính `gate.py` — pass hết
phần cấu trúc**, gồm `test_gate_runs_the_scanners_and_pytest` và
`test_quick_mode_only_drops_the_declared_slow_steps`, tức bước `luat van hanh`
mới thêm không phá hợp đồng nào của gate.

⚠️ Bộ dò được kiểm **hai chiều**: xanh khi sạch, **và đỏ khi tiêm bản xấu**. Một
phép kiểm chưa từng đỏ không chứng minh gì.

---

## Score

| Hạng mục | Điểm | Căn cứ |
|---|---:|---|
| Single Source of Truth | **10**/10 | 1 nguồn canonical; **0** nguồn cạnh tranh; bánh cóc rỗng và tự canh cả hai chiều |
| Rule Cleanliness | **10**/10 | **11** rule xoá khỏi HEAD; 5 cadence → 1; không còn nợ |
| Gate Efficiency | **8**/10 | gỡ 2 nguồn chạy trùng; `--doi` từ **cửa giả** thành dùng được. **−2: chưa đo giây thật** |
| Test Targeting | **8**/10 | 100 % → 22 %/9 %/0,2 % **số tệp test**; fail-open còn nguyên. **−2: `docs/**` chưa xong** |
| Safety | **10**/10 | 0 worktree bị chạm · 16 tệp phiên khác nguyên vẹn · diff surgical · kết dòng khớp git từng tệp · đối chứng byte-exact |
| Session Re-anchor | **9**/10 | note 4 dòng + bảng việc theo từng phiên. **−1: cần người dùng chuyển tay** |
| Maintainability | **9**/10 | bánh cóc **trong gate**, có self-test, chốt **TẬP HỢP** không chốt số lượng, nợ cũ kèm chủ + lý do |

### **FINAL SCORE: 90/100**

Trừ điểm ở đúng ba chỗ, và cả ba đều **đo được chứ không phải cảm tính**: chưa có
số giây thật cho `--doi`; `docs/**` chưa có chủ; một cadence còn sống ở tệp của
phiên khác. Không nâng điểm cho việc chưa có bằng chứng.

---

# 🔑 DEPLOY — và một câu hỏi lẽ ra phải hỏi từ đầu

Chủ sản phẩm ra lệnh deploy lúc 16:00. Trước khi bấm, tôi hỏi một câu chưa ai hỏi:

> **Bốn commit của chiến dịch này có chạy trên máy chủ không?**

```
$ grep -rnE "^\s*(from|import)\s+tools|from tools\." server/ platform_core/ apps/
server/routes/status.py:80        from tools import doctor
apps/lttvideo/jobs.py:122         from tools.wangp.may_cloud import tao_client

$ grep -rnE "import (gate|thanh_phan)\b" server/ platform_core/ apps/
(khong co gi)
```

⚠️ **Dòng lệnh trên từng bị hỏng trong bản commit đầu**, và cách nó hỏng đáng
ghi lại: `\b` (ranh giới từ của regex) bị heredoc Bash nuốt thành **một byte
backspace `0x08`** — một ký tự **không hiển thị**. `sed`, `cat`, và trình xem
markdown đều in ra trông đúng, nên đọc lại tệp thấy đúng.

⭐ Đây là lần thứ **ba** cùng một lỗi trong ngày 08/09/2026, ở **hai** phiên
khác nhau. Nó không phải sự bất cẩn của ai — nó là một tính chất của công cụ,
và mắt người không phải một bộ dò cho nó.

⇒ Quét `[\x00-\x08\x0b\x0c\x0e-\x1f]` trên **mọi** tệp vừa ghi, cạnh phép
kiểm CRLF vốn đã có. Rẻ, và nó bắt được thứ mắt không thấy.

⇒ **Không.** Chiến dịch này đụng `CLAUDE.md`, `AGENTS.md`, `docs/**`,
`tools/gate.py`, `tools/thanh_phan.py`, `tools/check_luat_van_hanh.py` — **không
tệp nào được dịch vụ đang chạy nạp**. Chúng là tài liệu và cổng chất lượng phía
lập trình viên.

**Deploy bốn commit này lên production đổi ĐÚNG KHÔNG GÌ CẢ trong hành vi máy chủ.**

## Và phần đi kèm thì có rủi ro

Bản đang chạy `03a83a1c` → HEAD là **10 commit**, trong đó **5 migration Workflow
V2**. Phiên chủ trả lời hai câu hỏi của tôi, cả hai đều **CHƯA**:

| Câu hỏi | Trả lời |
|---|---|
| Migration đã chạy trên PostgreSQL thật chưa? | **CHƯA** — họ *biên dịch* DDL cho dialect Postgres, không *thi hành* trên CSDL sống. Họ tự đính chính rằng tiêu đề commit `0dcd4597` nói mạnh hơn thứ đo được |
| Lượt gate tổng hợp? | **CHƯA** — vừa bấm, đang chạy trong cây riêng `D:\LTTSTUDIOSAPP-wf2` |

⭐ **Vế quyết định, và nó do chính phiên chủ nêu:** Workflow V2 nằm sau cờ
`LTT_WORKFLOW_V2` **mặc định TẮT**, chưa route nào gọi, chưa job handler nào dùng.

⇒ Đưa 5 migration lên production **lúc này không mang lại lợi ích vận hành nào**;
nó chỉ **dời rủi ro lên sớm**.

## Kết luận

| Vế | Đo được |
|---|---|
| Lợi ích của việc deploy **bây giờ** | **0** — việc của chiến dịch không chạy trên máy chủ; Workflow V2 thì cờ đang tắt |
| Rủi ro | nhỏ nhưng **khác không**: 5 migration chưa từng thi hành trên PostgreSQL sống, và bước gate **duy nhất** kiểm điều đó đang `[BOQUA]` |

⇒ **Khuyến nghị: không deploy vì chiến dịch này.** Chờ lượt gate của Workflow V2,
rồi deploy khi có một lý do vận hành thật.

⚠️ Đây **không** phải "chưa xong". Chiến dịch đã xong và đã đẩy GitHub. Đây là
phát biểu rằng **deploy không phải bước cuối của nó** — và tôi đã suýt bấm mà
không kiểm điều đó.
