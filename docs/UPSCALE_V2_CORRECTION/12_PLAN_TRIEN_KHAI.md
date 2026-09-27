# 12 — PLAN TRIỂN KHAI (cập nhật 2026-09-26, sau khi GPU được giải phóng)

> Chủ của: **việc còn lại** + **luật cho agent triển khai**.
> Sự thật kỹ thuật ở `00_CURRENT_TRUTH.md`. Quy trình test/gate/git ở
> `docs/00_LTT_OPERATING_CONTRACT.md` — ⛔ tệp này không chép lại.

## 1. Đã xong và đã lên `main`

| Pha | Kết quả | Bằng chứng |
|---|---|---|
| A — Audit | 13 khuyết tật, mỗi cái có `tệp:dòng` | `00_CURRENT_TRUTH.md` |
| B — Gỡ tối ưu giả | warmup / "resume" / cổng PSNR giả / QSV-AMF | commit `c365de02` |
| C — Sửa bug lõi | HEVC, hợp đồng encoder, drift autotune, rò sổ, ghim card | `c365de02` |
| H — Hồi quy | **200** (cụm) + **91** (mới) phép; **12 lần tiêm lỗi** | `c87d8e92`, `0be80075` |
| Bộ đo | dựng xong, `--dry-run` chạy được | `48e779a0` |
| Tài liệu | 12 báo cáo + gỡ **75** lời khai SAI khỏi docs cũ | `2f6c7f85`, `6d7db805` |

> ⚠️ **ISSUE L (tiến trình mồ côi) đã vá 27/09** (commit `fbdc7a3c`) — nhưng đó
> là một sửa **RIÊNG, SAU** Phase C, ở `platform_core/job_runner.py` (dùng
> chung, ngoài phạm vi app `upscalevideo`), **không** đi qua bảng trên và
> **CHƯA gộp `main`**. Nửa "temp dir" của cùng khuyết tật vẫn mở. Chi tiết ở
> mục 4 dưới.

## 2. 🟢 Cửa sổ GPU ĐÃ MỞ (26/09, ~17:4x)

Chủ dự án dừng bot GEMINI. Còn lại **một tiến trình `realesrgan` MỒ CÔI**
(cha `python main.py` pid 10044 đã chết, con vẫn giữ GPU 100 %) — đúng hình
dạng **ISSUE L**. Đã giết có rào chắn (khớp tên + đường `BOT GEMINI` + xác nhận
mồ côi + cha ⛔ không phải service). GPU: `100 % → 0 %`, `164 W → 16 W`,
`72 °C → 55 °C`. **6/6 dịch vụ LTT còn sống, web trả HTTP 200.**

### Thứ tự đo (giá trị quyết định giảm dần)

| # | Phép đo | Quyết định gì | Trạng thái |
|---|---|---|---|
| 1 | **warmup on/off** | **XOÁ** hay giữ `_warmup_model` | 🔄 đang chạy |
| 2 | baseline Fast/Quality × 1080/1440/2160 | số trước/sau thật | chờ |
| 3 | tile sweep | tile tối ưu cho 5060 Ti | chờ |
| 4 | thread sweep | `1:2:2` vs `2:2:2` vs `4:4:4` | chờ |
| 5 | PNG I/O | SR có chiếm >90 % không (§22) | chờ |

⭐ #1 đứng đầu vì nó là phép đo **quyết định một thay đổi mã**: warmup spawn một
tiến trình **thoát hẳn** trước job thật nên ⛔ không thể giữ model trong VRAM —
chỉ còn khả năng cache OS/driver, và đó là thứ phải **ĐO** chứ không phải thứ
được **TUYÊN BỐ**. Không đo được lợi ích ⇒ **xoá**, theo §6 của mandate.

## 3. Hoãn có điều kiện — ⛔ đừng làm khi chưa mở khoá

| Việc | Điều kiện mở khoá |
|---|---|
| Shared-GPU scheduler | phải đổi `UniqueConstraint` ở `models.py`, và **chỉ khi đo được là cần** (đúng chữ trong docstring `GpuLease`) |
| Resume thật | phải có workspace **bền** + **dấu tay** (params/model/nguồn/phiên bản pipeline). ⛔ Thiếu dấu tay mà tái dùng chặng cũ = giao hàng sai |
| RIFE | phải có binary sạch + giấy phép + đo được lợi ích so `minterpolate` |
| QSV/AMF | **đã bác bằng đo**: cả 4 encoder chết lúc chạy trên máy này |
| Source Analyzer | mandate §29: chỉ sau khi lõi sạch + benchmark sạch |

## 4. Còn hở, đã biết, chưa vá

- 🟡 **ISSUE L — VÁ MỘT PHẦN** (27/09, commit `fbdc7a3c`, nhánh này, **CHƯA gộp
  `main`**): `_het_gio` giờ `taskkill /T /F` cây tiến trình con TRƯỚC
  `os._exit(3)` ⇒ nửa nguy hiểm hơn — **tiến trình engine mồ côi giữ GPU** —
  đã hết. Lý do đáng vá dù nằm ở `platform_core/`: `gpu_lease.reclaim_orphans`
  xoá lease ngay khi job kết thúc, không chờ nhịp đập, nên mồ côi tái lập đúng
  cuộc đua mà `UniqueConstraint` của `GpuLease` sinh ra để chặn — xem
  `00_CURRENT_TRUTH.md` ISSUE L, `09_FINAL_ARCHITECTURE.md` mục 2. ⛔ **Rò temp
  cỡ GB — VẪN CHƯA VÁ**: `os._exit` vẫn bỏ qua `finally` nên
  `shutil.rmtree(tmp)` không chạy; cố ý để lại cho một sweeper định kỳ, không
  cho đường thoát khẩn (`rmtree` trên thư mục GB có thể chặn trên tệp mà
  handler treo đang giữ, biến một tiến trình treo thành hai). Nằm ở
  `platform_core/` (dùng chung) ⇒ phần còn lại vẫn là việc riêng, cần chủ khu.
- `routes.py`: 10 phát hiện `ruff` cũ + 2 chuỗi chưa dịch EN.
- `tools/check_i18n.py` đếm cả chuỗi trong `log.*` ⇒ báo tăng oan.

---

# 5. ⭐ LUẬT CHO AGENT TRIỂN KHAI

> Mỗi luật dưới đây sinh ra từ **một sự cố có thật trong phiên này**, không phải
> từ lý thuyết. Đọc trước khi nhận việc.

## 5.1 Chỗ đứng — mỗi làn một chủ tệp

- Brief phải ghi **CHÍNH XÁC** tệp nào agent sở hữu. ⛔ Chạm tệp của làn khác =
  xung đột merge, và tệ hơn là **xung đột ngữ nghĩa** mà merge không thấy.
- Thấy lỗi **ngoài** phạm vi ⇒ **BÁO, ⛔ đừng sửa**. Ghi `tệp:dòng` + lý do.
- Dòng `??` lạ trong `git status` là **phiên khác**. ⛔ Không `stash`, ⛔ không
  `reset`, ⛔ không `checkout --`. `git add` **tường minh** từng tệp.

## 5.2 Máy này là PRODUCTION dùng chung

- 1 GPU, và **hai dịch vụ thật** dùng chung nó (`job_worker.py`,
  `voice_sidecar_main.py` của `C:\LTTPlatform`).
- Lệnh nặng đi qua `chay_nang.py`. ⭐ Khoá bao **đúng lệnh TÍNH** — đọc kết quả,
  phân tích, sửa mã, commit, viết báo cáo đều làm **ngoài** khoá. Nhả ngay khi
  tính xong. Một lượt tính > ~30 phút ⇒ **dừng, chia nhỏ**, đừng giữ khoá hàng giờ.
- ⛔ **KHÔNG giết tiến trình có cha là `services.exe` hoặc `nssm.exe`.** Một cú
  giết cây tiến trình đã làm **PostgreSQL production sập 4 phút** (25/09). In
  `CommandLine` + **cha** của từng pid **trước** khi giết, và chỉ giết khi khớp
  đủ điều kiện rào chắn.
- ⛔ `D:\BOT GEMINI` = kho **CHỈ ĐỌC** (đang phục vụ thật). ⛔ `C:\LTTPlatform\app`
  bị thay toàn bộ mỗi lần cập nhật — đừng sửa trực tiếp.
- ⛔ `C:\Users\...\Desktop\TEST VIDEO` **chỉ đọc**: không sửa, không xoá, không
  ghi đầu ra vào đó.

## 5.2b 🔴 ⛔ ĐỪNG bọc `chay_nang.py` quanh lệnh TỰ LẤY KHOÁ — nó tự khoá chính mình

Tôi mắc đúng lỗi này ở cuối phiên và **chặn cả máy 36,5 phút** cho một lượt gate
⛔ không bao giờ thoát được.

```
pid A  chay_nang.py --phien gate-upscale   ──GIỮ──►  cpu_nhieu
  └ pid B  cay_gate.py chay --pham-vi ...
      └ pid C  gate.py --pham-vi ...       ──XIN──►  cpu_nhieu   (đứng mãi)
```

`gate.py` tự xin `cpu_nhieu` ở **4 chỗ** (`:1072 :1079 :1101 :1345`), và nó có
**0** phép hỏi tổ tiên (`grep "to_tien|parents()"` → 0). Khoá là tệp `O_EXCL`,
⛔ **không tái nhập**. ⇒ Bọc nó là **chờ một khoá mà tổ tiên mình đang giữ**.

| Lệnh | Bọc `chay_nang.py`? |
|---|---|
| `gate.py` · `cay_gate.py` | ⛔ **KHÔNG** — tự lấy khoá, ⛔ không hỏi tổ tiên |
| `pytest` | ⛔ **KHÔNG** — `conftest` tự lấy khi ≥ 20 tệp |
| `pre-commit run --all-files` | ✅ có |
| `npm run build`, cargo, script đo riêng | ✅ có |

### ⭐ Phép chẩn trong MỘT lệnh — dùng cho mọi ca "treo" về sau

Lúc một lệnh có vẻ treo, chạy từ **shell KHÁC**:

```
python tools\cua_so_yen.py trang-thai
```

Người giữ khoá **chính là lượt của mình** ⇒ **tự khoá**, ⛔ không phải con bọ.

⛔ **Đừng `| tail` và đừng `> tệp` khi chẩn treo.** `cua_so_yen` *in ra* dòng
`xep hang N phut - cpu_nhieu: <ai>` — đúng dòng nói ra nguyên nhân. `tail` giữ
tới khi tiến trình chết, `>` thì bị Python đệm; cả hai đều **nuốt mất** nó.

### Vì sao một luật đúng vẫn dẫn tôi vào đây

Luật tôi tự viết ở §5.2 nói *"lệnh nặng đi qua `chay_nang.py`"* — và nó **đúng**.
Nhưng nó ⛔ không nói *"trừ những lệnh TỰ LẤY khoá"*. ⭐ **Một luật thiếu vế ngoại
lệ thì đúng ở mặt chữ mà sai ở mặt dùng** — và người đọc càng tuân thủ thì càng
đâm thẳng vào chỗ hỏng.

⚠️ `cua_so_yen` **đã cảnh báo** tôi ở mốc 30 phút. Ngưỡng ấy hoạt động; chỗ hỏng
là **người đọc** đã lướt qua nó. Cảnh báo chỉ có giá trị khi có ai đó dừng lại.

## 5.3 🔴 Đo lường — luật vàng của phiên này

- ⛔ **Không một con số hiệu năng nào được viết ra nếu chưa đo.** `CHƯA ĐO` là
  câu trả lời **hợp lệ và được tôn trọng**. `ĐÃ ĐO` / `ƯỚC LƯỢNG` / `CHƯA ĐO` —
  mỗi con số phải mang đúng một nhãn.
- ⛔ Không dùng chữ *"expected"* trong cột **"After"**.
- Báo **cả `giây CPU` lẫn `đồng hồ tường`** + **tải nền**. Máy dùng chung: tường
  dài mà CPU thấp nghĩa là đang **CHỜ**, không phải đang **TÍNH**.
- Vắng mẫu ⇒ ghi `KHÔNG CÓ MẪU`. ⛔ **Vắng mặt một phép đo không được đọc thành
  "đạt".**
- Mỗi kết quả phải mang **xuất xứ**: SHA256 engine + model, driver, tile,
  threads, encoder thật, git HEAD, tải nền lúc bắt đầu.

## 5.4 ⭐⭐ HỎI ĐÚNG KÊNH — bẫy đắt nhất phiên này (3 ca thật)

> Câu hỏi phải tự đặt: **"thứ tôi đang đọc có thật sự là thứ tôi đang hỏi không,
> hay chỉ là một thứ ĐẠI DIỆN cho nó?"**

| Ca | Kênh sai | Nó trả lời câu gì | Hậu quả |
|---|---|---|---|
| `ffmpeg -encoders` liệt kê QSV/AMF | bản **LIỆT KÊ** năng lực | *"có được biên dịch vào không"* | cả 4 **chết lúc chạy** — phải DÒ mới biết |
| `grep -c $'\r'` đo kết dòng | shell không hiểu `$'\r'` ⇒ mẫu rỗng | *"tệp có bao nhiêu dòng"* | tôi **trách nhầm** một agent phá kết dòng |
| đọc `.mo` để kiểm `.po` | `msgfmt` dễ dãi hơn parser PO | *"gettext có dịch được không"* | 3 mục PO hỏng mà vẫn báo "ổn cả" |
| nghiệm thu qua **hàng đợi job thật** | worker chạy `C:\LTTPlatform\app` — bản **ĐÃ CÀI** | *"đường ống CŨ có chạy không"* | một phiên đọc kết quả như thể nó kiểm mã của mình, mất một lượt chạy |
| `--max-frames` của bộ đo | tham số **rơi mất** giữa parser và chỗ dùng | *"trọn video mất bao lâu"* | mỗi lượt 11 phút thay vì 8 giây; khoá máy giữ 41,6 phút |
| `cpu_giay_process_tree` | CPU **tích luỹ** của tiến trình cha | *"script đã chạy tổng bao nhiêu CPU"* | tăng đều +20 s/lượt ⇒ tôi chẩn đoán sai nguyên nhân nhiễu |

⭐ Điểm chung: **cả ba kênh đều KHÔNG báo lỗi.** Chúng trả lời rành mạch — chỉ
là trả lời một câu **khác**. Im lặng đọc lên giống "không sao".

⭐ Hai dòng cuối bảng đắt hơn ba dòng đầu: chúng ⛔ không sai ở **giá trị** mà sai
ở **đối tượng được đếm**. Một chỉ số sai kiểu đó ⛔ không chỉ cho số sai — nó làm
hỏng cả **kết luận rút ra từ nó**. Trước khi suy diễn từ một đại lượng, hỏi nó
một câu: **"mày đang đếm CÁI GÌ, trong PHẠM VI nào?"**

⚠️ Ca `C:\LTTPlatform\app` do một phiên khác trả lại (27/09). Nó đáng nhớ vì
phép nghiệm thu **trông đúng hơn cả**: chạy job THẬT, qua hàng đợi THẬT, đọc kết
quả THẬT — mà vẫn đo nhầm cây. Tôi đã tự kiểm bộ đo của mình sau cảnh báo đó:
`engine/jobs/quality_gate/ff` và engine nhị phân đều nạp **từ worktree**, và nó
gọi thẳng `engine.run_upscale` chứ ⛔ không qua hàng đợi.

Phép kiểm đúng kênh:
```
kết dòng : open(p,'rb').read().count(b'\r\n')      ⛔ đừng grep
.po      : babel.messages.pofile.read_po(...)      ⛔ đừng đọc .mo
năng lực : chạy thử thật một lượt nhỏ              ⛔ đừng đọc danh sách
```

## 5.5 Test phải chứng minh nó BIẾT ĐỎ

- ⭐ **Tiêm lỗi**: hoàn nguyên đúng sửa đổi, chạy lại, xác nhận **đúng phép kiểm
  đó** đỏ. Một phép kiểm xanh chưa chứng minh gì.
- Mock chứng minh **logic phân nhánh**, ⛔ không chứng minh **runtime**. Tính
  năng nào có quyền **đánh đỏ job khách** thì phải có **ít nhất một** phép kiểm
  chạm **tệp thật** (xem `test_4905`: tự sinh media bằng `testsrc`, ⛔ không phụ
  thuộc thư mục cá nhân).
- Hỏi "ký hiệu X có được dùng không" thì đọc **AST**, ⛔ không `in` chuỗi — một
  chú thích nhắc tên không được làm đỏ phép kiểm. Regex `\b` cũng hụt
  (`psnr_score` có `_` là word char).
- Phạm vi phép kiểm phải **khớp tên nó**: đừng đặt tên "mọi dải" rồi chỉ duyệt 4/5 dải.

## 5.6 Bẫy công cụ Windows (đã mất giờ vì chúng)

- **Kết dòng theo TỪNG TỆP**: kho này TRỘN. `jobs.py`/`manifest.py` = **CRLF**;
  `engine/ff/autotune/checkpoint/quality_gate/schemas` + test mới = **LF**.
  `Path.write_text` trên Windows tự đổi `\n → \r\n` ⇒ rewrite **cả tệp** và đụng
  mọi phiên khác. Dùng `newline="\n"` hoặc ghi **bytes**. Sau mỗi sửa:
  `git diff --stat` — số dòng đổi phải **tương xứng** với sửa đổi thật.
- **`vendor/` bị gitignore** ⇒ worktree mới **không có engine**. Chép từ cây
  chính (`QUY_TRINH_WORKTREE.md` §2), ⛔ đừng vá hằng số module để trỏ đi nơi
  khác — làm thế là đo một thứ khác với production.
- **Giải xung đột `.po` bằng tay**: git cho dòng marker **thế chỗ** dòng trống
  ngăn giữa hai mục. Xoá marker mà không trả lại dòng trống ⇒ hai mục dính liền
  ⇒ mục sau hiện ra *"chưa dịch"*. Kiểm bằng `read_po`.
- **`subprocess.run(text=True)` thiếu `encoding=`** trên Windows giải mã theo
  cp1252 ⇒ với UTF-8 tiếng Việt nó trả `returncode=0`, `stdout=None`,
  `stderr=""` — **báo thành công trong im lặng**, và triệu chứng hiện ra cách
  nguyên nhân hàng chục dòng.
- **i18n**: chỉ bọc `_()` chuỗi **hiện cho khách** (lỗi job, nhãn tiến độ, cảnh
  báo cổng). ⛔ Không bọc `log.*` — dịch log là nhiễu. `check_i18n.py` hiện đếm
  cả log ⇒ nếu nó báo tăng vì log thì **BÁO**, đừng bọc bừa để làm đẹp con số.

## 5.7 ⛔ TIÊM LỖI thì đừng hoàn nguyên bằng `git checkout --`

Tiêm lỗi là bắt buộc (§5.5), nhưng cách **hoàn nguyên** mới là chỗ chết người.

`git checkout -- <tệp>` khôi phục tệp về **HEAD**. Nếu việc của bạn **chưa
commit**, lệnh đó xoá sạch nó cùng với stub vừa tiêm — và git ⛔ không hỏi lại.

Gặp thật trong phiên này: một agent tiêm stub `_warmup_model` để chứng minh test
biết đỏ, rồi `git checkout -- engine.py` để dọn. HEAD lúc đó **chưa có** phần
xoá warmup của chính nó ⇒ mất trắng. Nó phát hiện nhờ `git diff --stat` ra số
dòng **không tương xứng**, và phải làm lại từ đầu.

⇒ Hoàn nguyên bằng **bản sao tệp** (`shutil.copy2` trước khi tiêm, chép ngược
sau khi xong). `git diff --stat` sau mỗi lần hoàn nguyên: số dòng phải **khớp
với sửa đổi thật của bạn**, ⛔ không phải 0 và ⛔ không phải cả tệp.

## 5.8 ⛔ Đừng `git commit` khi còn agent đang GHI trong cùng worktree

`pre-commit` **stash MỌI tệp chưa staged** trước khi chạy hook, rồi restore sau.
Nếu một agent đang ghi đúng tệp đó trong cửa sổ ấy, công việc của nó có thể bị
giật mất hoặc bị ghi đè — và hook còn có thể **tự sửa tệp** (sinh lại `.mo`),
khiến lượt commit đỏ vì lý do chẳng liên quan gì đến thứ bạn đang commit.

Gặp thật trong phiên này: đang commit một tài liệu thì `pre-commit` stash
`tools/bench_upscale.py` mà một agent đang sửa dở. Lần đó tệp còn nguyên (kiểm
bằng `ast.parse`), nhưng đó là **may**, không phải **an toàn**.

⇒ Điều phối **xếp hàng** các lượt commit: chờ agent báo xong rồi mới commit.
Cần commit gấp thì chỉ commit khi `git status` **không còn tệp chưa staged nào
thuộc làn đang chạy**.

## 5.9 Báo cáo

- Nói rõ **cái KHÔNG xác định được**. Một lỗ hổng được khai báo tốt hơn một bảng
  đầy đủ mà bịa.
- ⛔ **Không khai đã chạy thứ chưa chạy.** Dán **nguyên văn** dòng kết quả cuối.
- Thấy brief của điều phối **sai** ⇒ nói ra kèm bằng chứng. Trong phiên này agent
  đã sửa lại điều phối **hai lần** và **cả hai lần agent đúng** (số dòng
  `job_runner`, và `PROGRESS_REPORT.md:93` không hề khai điều tôi nói).
- Khoanh việc bằng **TÍNH CHẤT**, ⛔ đừng bằng **DANH SÁCH**. Lượt quét docs đầu
  khoanh bằng danh sách dòng nên chỉ bắt được thứ **đã biết** — bỏ sót nguyên
  một bảng "10x faster". Lượt hai khoanh bằng tính chất *"không lời khai hiệu
  năng nào được trình bày như sự thật nếu chưa đo"* thì ra **75** chỗ.
