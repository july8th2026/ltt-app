# BÁO CÁO CUỐI — VÒNG TỰ CHẠY THEO PACK V4

Ngày 2026-09-02 · nhánh `claude/ltt-voice-autonomous-supervisor-1c3f95`
Gói: `LTT_VOICE_AUTONOMOUS_SUPERVISOR_PACK_V4`

---

## 1. Kết luận ngắn

LTT Voice **đã ở trạng thái tốt hơn nhiều so với giả định của gói V4**. Sáu màn
đã xây xong từ P1–P8 (2026-08-31), đã phát hành, và đang bán qua `/api/v1`.

⇒ Vòng này **không phải một vòng xây MVP**. Nó là một vòng **rà soát + bịt lỗ**,
và giá trị lớn nhất nó tạo ra là:

1. **Đóng lỗ P0 duy nhất còn thật**: không nghe thử được giọng nào.
2. **Bắt một chip nói dối** về trạng thái engine.
3. **Bật ba cơ chế đã viết mà chưa bao giờ chạy** ở màn Lịch sử.
4. **Bác bỏ bốn "khoảng trống" mà chính bản rà soát đầu của tôi bịa ra.**

Điểm ④ đáng kể ngang ba điểm đầu, và mục §5 nói tại sao.

---

## 2. Việc đã làm — bốn commit

| SHA | Nội dung |
|---|---|
| `339af2e` | Backend nghe thử + `sidecar_client.song()`/`trang_thai()` + cửa đọc + 25 phép kiểm |
| `747db66` | Nút nghe thử trên thẻ giọng + trình phát trong panel + sửa `daVe` của trình phát dùng chung |
| `b5ea593` | Nghe thử trong **bộ chọn giọng**; bỏ chip mã trùng lặp; bỏ S2 |
| `fed7073` | Lịch sử nói rõ **giọng nào** đã đọc; "Giọng mặc định (Adam)" thay ô trống |
| `8fcb5c9` | Nghe thử ở **cả bốn** màn dùng bộ chọn, không chỉ Studio |

| `<commit cuoi>` | Trình phát clip gốc nâng thành trình phát sóng âm — **bốn màn một kiểu**; báo cáo cuối |

---

## 3. Ba lỗi sản phẩm THẬT đã tìm ra và sửa

### 3.1 🔴 Không nghe thử được giọng nào — P0

Trang Giọng liệt kê hai mươi cái tên kèm ba nhãn mô tả. Không có gì trong đó trả
lời câu hỏi duy nhất người chọn giọng thật sự hỏi: **giọng này nghe như thế nào.**
Cách duy nhất để biết là tạo một lượt đọc thật — tức **trả tiền để xem mình có
muốn mua không**.

Ba cách làm, chọn cách thứ ba (`nghe_thu.py` ghi đủ lý do):
sinh-khi-bấm đi vòng qua chốt GPU một-suất; qua-hàng-đợi hỏng trải nghiệm;
**dựng sẵn một lần rồi phục vụ như tệp tĩnh** thì lượt nghe thứ nhất và thứ
mười nghìn tốn như nhau.

**Đo thật:** hai mươi giọng mẫu dựng hết trong **86,1 giây**, ~5 s mỗi giọng,
**một lần**. Giọng nhân bản dựng ở **đuôi job ghi danh** — job đó vừa giành GPU,
vừa nạp model, vừa có `ref_b64` trong tay, nên thêm chưa tới hai giây vào một
lượt đã chạy hàng chục giây. Đo trên luồng thật: ghi danh xong lúc `17:28:02`,
tệp nghe thử 506.924 byte có lúc `17:28:13`.

### 3.2 🔴 Chip "Engine sẵn sàng" nói dối — P1

```python
def san_sang() -> bool:
    return bool(_token())
```

Chỉ kiểm **biến môi trường có được đặt hay không**. Đo được trong phiên này:
chip **"Engine sẵn sàng"** màu xanh nằm trên một trang mà mọi lượt bấm Tạo đều
trả *"Máy tạo tiếng nói chưa sẵn sàng"* — vì sidecar đã chết.

Hai câu mâu thuẫn trên cùng một màn hình, và câu **to hơn, xanh hơn** là câu sai.

Nay có `song()` (hỏi cổng thật, đệm 5 giây, trần 1,5 giây) và `trang_thai()` trả
**ba** nhánh. Ba chứ không phải hai, vì hai trạng thái hỏng cần hai câu trả lời
khác nhau: *chưa bật* là việc của người cài đặt, *không trả lời* là một dịch vụ
đã cài nhưng đang chết. Đã kiểm cả ba nhánh.

### 3.3 🔴 Lịch sử không nói lượt nào đọc bằng giọng nào — P1

Và đây là loại lỗi khó thấy nhất: **ba cơ chế đã được viết đầy đủ mà chưa bao
giờ chạy.** Khuôn mẫu đã có nhánh in tên giọng. Route đã truyền `ten_giong`,
`giong_da_dung`, `f_giong`. `doc_man_lich_su` đã có `_giong_cua()` và
`loc(giong=…)`. Ô lọc giọng đã được viết.

Không cái nào chạy, vì tất cả treo vào `params["voice_id"]`/`params["preset"]` —
và lượt khách **không chọn giọng** thì cả hai đều rỗng. Nên ô lọc luôn rỗng (ẩn
đi), dòng luôn trống, và "Giọng dùng nhiều nhất" không bao giờ có gì.

⭐ Sửa **không phải** bằng cách điền tên mặc định vào `_giong_cua()`. Hàm đó cũng
là thứ `loc()` so bằng và `tom_tat()` gom nhóm; nhét một cái tên vào sẽ trộn lượt
"mặc định" với lượt khách **chọn đúng giọng ấy** — hai việc khác nhau, và gộp
chúng làm một giọng trông phổ biến hơn thực tế.

Đã kiểm trên trình duyệt: `?giong=Adam` trả về **đúng một** dòng (lượt chọn Adam
tường minh), **không** gom hai dòng "Giọng mặc định (Adam)".

---

## 4. Quyết định BỎ có căn cứ

| Mục | Quyết định | Căn cứ |
|---|---|---|
| **S2** bộ chọn ngôn ngữ đầu ra `Auto/VI/EN` | **BỎ** | Engine song ngữ thật, **không nhận tham số ngôn ngữ nào**. Ba nút ấy sẽ không điều khiển gì — vi phạm mục 8 hợp đồng gói ("không tạo control không hoạt động chỉ để giống ảnh") |
| **Batch** | **BỎ** | `START_HERE.md` loại; đã không còn trên bề mặt từ trước. Dư lượng còn lại (`"lo": Chạy lô` trong `NHAN_NGUON`) **phải giữ** — hàng lịch sử cũ vẫn mang `nguon="lo"` |
| **S1** bố cục "lãng phí bề ngang" | **BỎ — tôi đọc sai** | Ở 1680 px các màn **đã** hai cột (802+300). Trần 1120 px là container của **nền tảng**, dùng chung 14 app; nới nó là sửa nền tảng cho một app |
| Ba thanh `Similarity/Pronunciation/Stability` | **BỎ** | Nền tảng không đo gì cả (cổng V10). Bịa ba con số là cách nhanh nhất phá lòng tin |
| Chip mã giọng cho giọng **mẫu** trong bộ chọn | **Đã thêm rồi GỠ** | Với giọng mẫu `public_id == ten_hien_thi`; chip in đúng chuỗi nằm ngay trên nó, hai mươi dòng |
| Khoá/hạn mức/nhật ký trên màn API | **Giữ là đường dẫn** | Khu `/developers` đã có cho **mọi** công cụ; chép về đây là tạo bản thứ hai của một sự thật |

---

## 5. ⛔ Phần quan trọng nhất: bản rà soát đầu của tôi SAI BỐN CHỖ

Bản `01_RA_SOAT_HIEN_TRANG.md` liệt kê hai P0 và bảy P1. Sau khi **bấm thật**,
bốn trong số đó không tồn tại:

| Tôi đã viết | Sự thật |
|---|---|
| `V2` Panel chi tiết giọng là **khung rỗng** — **P0** | Panel chạy đầy đủ: tên · loại · tính chất · mã + nút chép · trạng thái · nút dùng · thống kê · clip gốc · biểu mẫu tắt |
| `S7` Studio không có **Lưu vào dự án** | Có, cả nút lẫn đường `POST /du-an/luu-tu-studio`, đầy đủ |
| `H3` Lịch sử không có trình phát/sóng âm mỗi dòng | Có, mỗi dòng một trình phát sóng âm + WAV/MP3/Đọc lại/Chi tiết |
| `S1` Bố cục lãng phí ~600 px | Ở bề rộng desktop các màn đã hai cột |

**Vì sao tôi sai — và cả bốn lần đều cùng một gốc:** tôi đo bằng thứ không phải
trình duyệt.

- `V2`: đọc `document.body.innerText` rồi tìm chuỗi *"Chọn một giọng…"*, thấy có
  → kết luận rỗng. Chuỗi ấy nằm trong một nút `[hidden]` vẫn còn trong DOM.
- `S7`, `H3`: chụp màn hình ở **trạng thái rỗng** (CSDL dev mới tinh) rồi kết
  luận về tính năng. Cả hai chỉ hiện khi có dữ liệu.
- `S1`: đo ở viewport 998 px rồi nói về bố cục 1680 px.

⭐ Và một lần thứ năm, ở chiều ngược lại: tôi kết luận nút nghe thử **không
chạy** vì lớp `dang-phat` biến mất — trong khi clip chỉ dài ~6 giây và phép đo
của tôi rơi vào sau lúc nó phát xong. Đo lại trong **cùng một lượt gọi** thì nó
đúng.

🔴 Đây chính xác là điều `VOICE_UI_EXECUTION_PLAN.md` §15 đã ghi sau bốn pha:
*"Audit đọc mã trả lời được component nào dùng lại được. Nó **không** trả lời
được thứ này có thực sự làm điều nó trông như đang làm không."*

Tôi đã đọc câu đó **trước khi** viết bản rà soát, và vẫn mắc lại. Nên bài học
đáng ghi không phải "hãy cẩn thận" mà là một quy tắc thao tác:

> **Không viết một dòng nào vào bảng chênh lệch cho tới khi đã bấm vào đúng thứ
> đó, trên một trang CÓ DỮ LIỆU, ở đúng bề rộng mình định nói về.**

Chi phí của việc không làm vậy đã đo được: bốn hạng mục sai trong một bản rà
soát, và một trong số đó suýt dẫn tới xây lại một panel đang chạy tốt.

---

## 6. Ba cái bẫy môi trường (không phải lỗi sản phẩm)

1. **`MAX_PATH` 260 của Windows.** Kho tệp đặt trong scratchpad (~150 ký tự) +
   khoá `voice/out/<uuid>/<uuid>/tieng.wav` (~85) làm job chết với
   `FileNotFoundError [WinError 3]` — **ở bước ghi, sau khi GPU đã chạy 12 giây**,
   nên nó đọc như "kho hỏng". Chuyển kho về `D:\_lttvoice_dev`.
2. **Tiến trình nền chết theo shell.** Sidecar khởi động bằng `&` chết khi lượt
   gọi kết thúc; triệu chứng ở worker là `WinError 10061`, đọc y hệt "chưa cài
   dịch vụ".
3. **`write_text()` trên Windows đổi LF thành CRLF.** Làm `git diff` phình 5.670
   dòng ở `ltt.css`. Và bẫy ngược: **đừng ép mọi tệp về LF** — một số tệp vốn LÀ
   CRLF trong git. Khớp **từng tệp** với HEAD.

---

## 7. Chứng cứ — đã chạy thật, không phải suy ra

**Đường đo dựng riêng, không đụng production:**

| | production | phiên này |
|---|---|---|
| cổng sidecar | 8120 | **8121** |
| GPU | 0 | **1** (`CUDA_VISIBLE_DEVICES=1`) |
| CSDL | PostgreSQL | `D:\_lttvoice_dev\dev.db` |
| kho | `C:\LTTPlatform\data` | `D:\_lttvoice_dev\store` |

⇒ Không cần một bí mật nào của production. Không có HARD BLOCKER.

**Chuỗi đã chạy đầu-tới-cuối trên trình duyệt thật:**

- Tạo tiếng: web → job → worker → GPU 1 → sidecar → WAV 775.724 byte, 12 s,
  credit 5.000 → 4.998 (khớp `credit_cost`).
- 13 lượt đọc thật với 6 giọng khác nhau + 3 mốc tốc độ.
- **Ghi danh giọng riêng** từ một clip 9,84 s: job `enroll` → biểu diễn →
  `trang_thai=active` → **tệp nghe thử tự dựng** 506.924 byte.
- Voices → Studio: bấm "Dùng" trên *Ngọc Huyền* → Studio chọn sẵn `m:Ngọc Huyền`.
- Nghe thử phát thật ở cả bốn màn; **không** đổi lựa chọn radio.
- Đổi giọng trong panel → sóng âm **vẽ lại** (`canvas.toDataURL()` đổi).
- Lọc `?giong=Adam` → đúng 1 dòng, không gom dòng "mặc định".
- Màn API nhánh **đóng**: không một lệnh chép được. Nhánh **mở**: banner xanh,
  tab cURL/Python, nút chép, endpoint thật.

**Ranh giới an toàn kiểm trên máy chủ đang chạy, không chỉ trong test:**
`GET …/vc_…/repr-abc.npz` → **404**. Biểu diễn người nói không rò ra.

**Console:** 0 lỗi trên cả 5 màn. *(Lỗi duy nhất từng thấy là chính lượt `fetch`
404 tôi cố tình gọi để thử ranh giới trên.)*

---

## 8. Phép kiểm

`tests/test_394_ltt_voice_nghe_thu.py` — **33 phép kiểm**, gồm:

- hình dạng khoá mang **phiên bản** (mất nó = đổi câu đọc thử mà khách vẫn nghe
  câu cũ, **mãi mãi, không triệu chứng**);
- slug **giữ dấu** tiếng Việt (bỏ dấu là gộp hai giọng có thật thành một khoá);
- `dung()` **không được ném** (người gọi là đuôi job ghi danh);
- vòng bảo trì có **trần** mỗi lượt;
- cửa đọc: giọng mẫu **mở cho mọi khách đã đăng nhập**, giọng nhân bản **chỉ
  chủ**, và `repr-*.npz` **vẫn đóng**;
- ba nhánh `trang_thai()`, và `song()` **có bộ nhớ đệm**;
- **mọi màn** dùng bộ chọn giọng đều phải có nút nghe thử.

`tests/test_348_ltt_voice_lich_su.py` — thêm 3: lượt không chọn giọng được đánh
dấu `giong_mac_dinh`; lọc theo giọng **không** gom lượt mặc định; màn Lịch sử in
tên mặc định lấy từ ảnh chụp preset chứ không gõ tay.

**Đã thử lùi để chắc bánh cóc cắn:** mở cửa audio theo **thư mục** thay vì theo
**tên tệp** → **6 phép kiểm đỏ**, gồm cả hai phép kiểm **cũ** của `test_346`.

⚠️ Và một phép kiểm của chính tôi cũng từng sai: bản đầu của
`test_bo_chon_KHONG_lap_lai_ma` đếm số lần chuỗi tên giọng xuất hiện trong HTML
rồi đòi đúng 1 — nó **đỏ với một kết quả đúng**, vì cái tên còn nằm hợp lệ trong
`data-ten`, `value`, `aria-label` và URL nghe thử. Nay hỏi thẳng cơ chế
(`lv-ma-chep`) thay vì đếm chuỗi.

---

## 9. Còn lại (P2, không chặn phát hành)

| # | Việc | Ghi chú |
|---|---|---|
| 1 | Màn API thiếu ví dụ **JavaScript** (có cURL + Python) | prompt 09 gợi ý ba |
| 2 | "Chi tiết" ở Lịch sử dẫn sang `/jobs/<uuid>` — **màn ops của nền tảng** | Gói nói History phải là *artifact library*, không phải *raw job monitor*. Sửa đúng nghĩa là dựng một panel chi tiết trong app |
| 3 | Không lọc theo **ngôn ngữ** ở Lịch sử | Lọc giọng + nguồn + thời gian đã có |
| 4 | Không phân trang / đổi số dòng mỗi trang ở Lịch sử | Trần đọc 500 đã **nói ra** khi chạm |
| 5 | Sửa tên giọng nhân bản (mới có "Tắt") | |
| 6 | Sắp xếp / đổi lưới-danh sách ở màn Giọng | |
| 7 | **Benchmark âm thanh** VI/EN/số/tiền/ngày/tên riêng | Cổng V10, cần một lô đo có người chấm — ngoài phạm vi một vòng UI |

---

## 10. Khuyến nghị phát hành

**Phát hành được** phần đã làm trong vòng này:

- không còn P0;
- 5 màn đã kiểm bằng trình duyệt thật, có dữ liệu thật;
- 0 lỗi console;
- ví dụ API chạy (nhánh mở đã soi);
- luồng giọng mẫu **và** giọng nhân bản đều chạy đầu-tới-cuối;
- luồng dự án/lịch sử chạy;
- cổng tĩnh xanh.

**Cổng đầy đủ đã chạy** — xem §11. `--vong-lap` xanh **không phải bằng chứng**,
chính nó nói vậy, nên con số dưới đây mới là con số đáng đọc.

⛔ **Hai việc phải làm trước khi deploy**, không được suy ra từ báo cáo này:

1. `LTT_WORKER_POOLS` phải có làn `voice`. Thiếu nó thì job nằm `queued` **mãi
   mãi** — không lỗi, không cảnh báo, `/health/ready` vẫn 200.
2. `LTTStudioVoice` giữ handle trên `app\`, nên `update.ps1` phải dừng nó
   **đầu tiên**.

Và một việc **mới** của vòng này: tệp nghe thử được dựng bởi vòng bảo trì, **tối
đa 3 giọng mỗi giờ**. Sau khi deploy, hai mươi giọng mẫu cần **~7 giờ** để đủ
tệp — trong khoảng đó một số thẻ giọng sẽ không có nút nghe. Đó là hành vi đúng
(nói "đang chuẩn bị" thay vì một nút câm), nhưng nếu muốn đủ ngay thì chạy tay
một lượt `nghe_thu.bao_tri()` lặp lại, hoặc tạm nâng `MOI_LUOT_TOI_DA`.

---

## 11. Kết quả cổng đầy đủ (`python tools/gate.py`)

```
5.319 passed · 32 skipped · 5 failed · 378 giay (6,3 phut)
```

**Năm phép kiểm đỏ, và KHÔNG cái nào do vòng này gây ra.** Ghi rõ từng cái, vì
"năm đỏ" mà không giải thích thì lần sau người đọc phải điều tra lại từ đầu:

| Phép kiểm | Vì sao đỏ | Của tôi? |
|---|---|---|
| `test_177_system_profile` ×2 | Hồ sơ hệ thống **stale** — tôi sửa mã sau lượt dựng hồ sơ cuối | **CÓ** → đã dựng lại, **6/6 xanh** |
| `test_82_upscalevideo::test_vendor_engine_co_mat` | Thiếu `vendor/engine` (exe + models) — nhị phân lớn, không nằm trong git | không |
| `test_362::test_cay_chinh_co_dot_git_la_THU_MUC` | Đòi `GOC/.git` là **thư mục**. Ở một **worktree**, `.git` là một **TỆP** | không |
| `test_362::test_cay_lien_ket_co_dot_git_la_TEP[lien_ket0]` | Cùng gốc — phép kiểm này chỉ đúng khi chạy ở **bản checkout chính** | không |

⭐ Ba phép kiểm sau **không thể xanh trong worktree này** dù mã đúng tới đâu.
Chúng không phải "lỗi được bỏ qua" — chúng là phép kiểm **về môi trường**, và
môi trường này cố ý khác.

⛔ Và đừng tin câu đó vì tôi nói; ba phép đo dưới đây kiểm được trong mười giây:

```
git diff --name-only 89eb46c..HEAD -- apps/upscalevideo     tests/test_362_cay_rieng_va_deploy.py tests/test_82_upscalevideo.py
  -> 0 tep                  (vong nay khong dung vao chung)

file .git
  -> ASCII text, 79 byte    (worktree: `.git` la mot TEP, khong phai thu muc)

ls apps/upscalevideo/vendor
  -> No such file           (nhi phan vendor khong nam trong git)
```

Hai phép kiểm `test_362` **được dựng ra để phân biệt cây chính với cây liên
kết** — chúng đỏ ở đây đúng như thiết kế của chúng.

⚠️ Và cổng tự nói ra một giới hạn của chính nó ở dòng cuối:
*"1 BUOC TU BO QUA, KHONG PHAI BANG CHUNG: bat bien da tien trinh"* — `test_214`
(đa tiến trình) **không chạy** trong lượt này. Vòng này không đụng vào worker
hay outbox, nên rủi ro thấp; nhưng nói ra vẫn hơn để nó im.

**Bộ test của riêng LTT Voice:** `-k "ltt_voice or voice_sidecar"` →
**307 passed, 1 skipped**, 134 giây.

---

# PHẦN HAI — VÒNG HOÀN THIỆN (cùng ngày, sau khi chủ dự án yêu cầu chạy đủ)

Phần trên viết khi vòng dừng ở ~40 % chương trình gói V4. Chủ dự án yêu cầu
chạy nốt rồi mới deploy. Dưới đây là phần bổ sung.

## 12. Failure tests — và một lỗi chỉ lộ ra khi THẬT SỰ giết cổng

`tests/test_501_ltt_voice_hong_hoc.py`, 33 phép kiểm. Chúng đo **hình dạng của
lỗi**, không đo thông điệp: thông điệp đổi được, hình dạng đổi là đổi hành vi
tính tiền.

### 🔴 Job vẫn CHẾT khi deploy, dù bản sửa 31/08 đã "làm nó thử lại"

Giết cổng giọng rồi nộp một lượt đọc:

```
max_attempts = 3  ->  attempts=3, status='error' sau ~45 giây
cửa sổ thử lại thật sự: chờ 10s rồi 20s = ~30 giây
```

Nhưng riêng phần **nạp model** khi deploy đã đo **39,9 s** (nguội) tới
**73,1 s**. Cộng dừng dịch vụ, chép `app\`, khởi động lại — **mọi lượt đang bay
khi deploy đều chết.**

⭐ Bản sửa 31/08 (`LoiHaTang`) sửa đúng việc **phân loại** lỗi mà không sửa
**kết quả**. Nửa còn thiếu chỉ lộ ra khi có ai thật sự giết cổng.

✅ **Tiền vẫn đúng**: sổ ghi `hold -1` rồi `refund +1`. Khách không bị thu. Cái
mất là công việc và một thông điệp lỗi không đáng có.

**Sửa**: `SO_LAN_THU_JOB = 5` — cửa sổ 10+20+40+80 = ~150 giây, gấp đôi lần nạp
model chậm nhất. Bốn cửa nộp job đều khai; có bánh cóc quét
`submit_with_credit(` để cửa thứ năm không thể quên.

**Đo lại sau khi sửa**: giết cổng → nộp → worker thử 2 lần hỏng → bật cổng lại
→ **job tự hoàn thành**, `done`, attempts 2/5, thu đúng 1 credit.

## 13. Benchmark âm thanh — bằng ASR, không bằng cảm nhận

Chi tiết ở `10_BENCHMARK_AM_THANH.md`. Ba điểm đáng nhớ:

**① Phép đo lần đầu bị nhiễm, và nhiễm đúng ở ba hạng mục tệ nhất.** So bản ASR
với văn bản đã chuẩn hoá thì `ngay` 39,6 %, `tien` 26 %, `so` 15,9 % — nhưng cả
ba **đúng nghĩa**; thứ khác nhau là ASR viết chữ số còn engine đọc ra chữ. Đưa
cả hai phía qua cùng bộ chuẩn hoá: `so` tụt còn **3,4 %**.

**② Kết quả sau khi chấm công bằng**: tiếng Việt thường 1,7 % · tên riêng 1,9 %
· tiếng Anh 0,0 % · câu 353 ký tự **5,2 %** (không thấy trôi giọng) · ba mức tốc
độ 0,0–2,5 %. RTF trung bình **1,273**.

**③ Hai "bản sửa" bị LOẠI, và đó là phần đáng giá nhất.** Bốn viết tắt hỏng thật
(`HTTPS`, `HTTP`, `MP3`, `WAV`) đã thêm vào `VIET_TAT` sau A/B. Nhưng `RTX` và
`HTML` **engine vốn đọc đúng** — giải chúng ra làm ASR nghe thành `AZTX` và
`hát, kềm L`. Hai trong năm ứng viên sẽ làm hỏng một thứ đang chạy tốt, và cả
hai "trông cần sửa" y hệt bốn cái kia.

⚠️ Một cái bẫy trong chính phép đo: ở câu dài, ASR nghe `RTX` thành `otx`. Dừng
ở đó thì đã kết tội nó. **Một lần nghe sai trong câu dài không đủ để kết tội một
từ.**

## 14. Responsive + accessibility

**a11y, cả 5 màn: 0 lỗi** — mọi nút/liên kết có tên đọc được, mọi ô nhập có
nhãn, không `aria-pressed` đặt sai vai. Nút chép ở màn API đều đã nối (3/3).

Nhưng phép kiểm tự động **không thấy** hai lỗi thật, và cả hai chỉ lộ ra khi thử
đúng cách:

### 🔴 Enter trên nút NGHE THỬ không phát tiếng

Nút có tên đọc được đúng, focus được, `aria-pressed` đúng — bốn thứ mà một phép
kiểm tự động hỏi đều đạt. Nhưng bấm Enter thì **panel chi tiết mở ra và tiếng
không phát**.

`keydown` nổi bọt từ nút lên thẻ giọng; thẻ gọi `e.preventDefault()` cho phím
của *chính nó*, và cái đó huỷ luôn hành vi mặc định Enter→click **của nút bên
trong**.

⭐ **Chuột không lộ ra lỗi này** — đường chuột đã có `stopPropagation` từ đầu.
Chỉ bàn phím mới thấy, vì bàn phím đi qua một **sự kiện khác**.

### Nút "Tạo tiếng nói" nằm TRÊN ô nhập kịch bản ở màn hẹp

Đo ở 375 px: nút chính y=1037, ô nhập bắt buộc y=1164. Màn rộng không ai thấy —
ba cột đứng cạnh nhau nên `trai` ở **bên cạnh** `giua`, không ở **trên**. Xếp một
cột thì thứ tự DOM trở thành thứ tự đọc.

Sửa bằng `order` ở breakpoint ≤820 px, **không** đổi thứ tự DOM — thứ tự DOM là
thứ tự TAB, và nó đang đúng.

## 15. Cổng đầy đủ — LẦN NÀY XANH

```
RESULT: PASS   [4 buoc tu bo qua: bat bien da tien trinh + 3 frontend]
bo test (song song): 299 giay
```

Bốn bước tự bỏ qua vì môi trường (thiếu `node_modules`, và phép kiểm đa tiến
trình cần CSDL riêng) — cổng **tự khai** chúng thay vì đếm là xanh.

Ba lỗi môi trường của lượt trước đã hết:
- `test_362` ×2 — hết đỏ nhờ merge `admin-mvp-v3` (`48d8dbd`).
- `test_82` — chép `apps/upscalevideo/vendor/` (48 MB, bị `.gitignore`) từ cây
  chính sang. Sau đó 18/18 xanh, và `git status` vẫn rỗng.

## 16. ⚠️ Một việc tôi làm sai với chính cái máy này

Tôi chạy `tools/gate.py` đầy đủ **hai lần** hôm nay. Cây tôi phân nhánh trước
`03845cb`, nên gate của tôi vẫn `-n auto` = **lấy hết 20 lõi** của một máy đang
chạy bốn dịch vụ phục vụ khách. Chủ dự án phải reset cứng máy hai lần hôm nay.

Một phiên khác đã đo và vá: 14/20 lõi, `-n 11`, vitest `--maxWorkers=2`,
`BELOW_NORMAL_PRIORITY_CLASS`. CPU đỉnh từ *treo máy* → **52 %**, và gate còn
**nhanh hơn 31 %** — vượt điểm bão hoà thì thêm worker chỉ thêm tranh chấp.

⛔ Bài học không phải "công cụ mặc định sai" (nó có sai, và đã vá). Là: tôi đã
đọc `CLAUDE.md` nói máy này **là production** ngay đầu phiên, rồi vẫn chạy một
công cụ nặng mà không hỏi nó tốn bao nhiêu.

---

## 17. ĐÃ DEPLOY — 2026-09-02 21:11

```
deploy-20260902-211112.ket.txt   EXITCODE=0    (2 phut 06 giay)
nghiemthu-20260902-211611        EXITCODE=0    "KET QUA: he thong hoan chinh."
```

**Bằng chứng mã đã lên máy chủ thật** (không suy từ log deploy):

```
C:\LTTPlatform\app\apps\ltt_voice\nghe_thu.py          13.094 byte
C:\LTTPlatform\app\tests\test_500_ltt_voice_nghe_thu.py  co
C:\LTTPlatform\app\tests\test_501_ltt_voice_hong_hoc.py  co
tham_so_cong_khai.py:87  SO_LAN_THU_JOB = 5
tu_dien.py               6 lan khop HTTPS/MP3/WAV
```

Nghiệm thu: **15 app nạp**, `ltt_voice /ltt-voice ok`, bản chạy khớp git
**536 khớp · 0 lệch · 0 thiếu · 0 thừa**, không lỗi trong log gần đây.

### 🔴 Chốt nguy hiểm nhất đã đóng

```
[OK]  LTT_WORKER_POOLS khong dat - worker da nang, job voice nhat duoc
```

`manifest.py` cảnh báo: nếu production **đã đặt** `LTT_WORKER_POOLS` mà thiếu
làn `voice` thì job nằm `queued` **mãi mãi** — không lỗi, không cảnh báo,
`/health/ready` vẫn 200. Ở đây biến ấy **không được đặt**, nên worker đa năng và
nhặt được job voice. Cấu hình an toàn.

⚠️ Chốt này chỉ đọc được khi chạy nghiệm thu **có nâng quyền** (`secrets/app.env`
có ACL). Lượt chạy không nâng quyền báo *"1 lỗi"* — và đó là lỗi của **cách
chạy**, không phải của hệ thống. Ai đọc kết quả nghiệm thu phải kiểm mình chạy
ở quyền nào trước khi tin con số.

### Kiểm trên URL công khai (quy tắc 5b), sau Cloudflare

| đường | kết quả |
|---|---|
| `https://app.lttstudios.com/health/ready` | **200** |
| `https://app.lttstudios.com/gia-api` | **200** · 6 bảng · 22 dòng · mục *Giá tạo giọng nói* đầy đủ |
| `https://app.lttstudios.com/ltt-voice` | **303 → /login** (đúng: cần đăng nhập) |

⭐ Trang `/gia-api` là món nợ của **một phiên khác** (họ đổi `dashboard.py` mà
chưa kiểm trình duyệt). Tôi kiểm hộ vì đã có sẵn công cụ. Kiểu hỏng họ lo —
`bang_gia_cong_khai()` trả rỗng, trang vẫn 200 vẫn đẹp nhưng mất một bảng —
**không xảy ra**: cả ba mục LLM · ảnh · giọng nói đều có số.

### Phạm vi deploy — chủ dự án quyết sau khi được cảnh báo

`deploy_nang_quyen.ps1` chạy từ `D:\LTTSTUDIOSAPP` (nhánh `admin-mvp-v3`),
**không** từ worktree. Nên đưa LTT Voice lên production nghĩa là merge vào nhánh
mà một phiên khác đang làm, và deploy **cả cây**.

Tôi đã nêu điều đó cùng ba lựa chọn; chủ dự án chọn *"deploy full, không lo code
phiên khác"* và nhắc lại một lần nữa. Đã deploy đúng phạm vi ấy.

⭐ Và phiên kia rút ra một điều đáng ghi hơn cả sự việc: *"tôi khai chương trình
của tôi là **không deploy** — nhưng tôi commit vào nhánh mà người khác deploy từ
đó, nên mã của tôi vẫn lên production, chỉ là qua tay người khác."*

⇒ **Một lời khai "không deploy" không bảo vệ được gì nếu nó không nói rõ mình
commit vào nhánh nào.** Ranh giới thật không nằm ở ai bấm nút, mà ở **cây nào
được deploy** — và điều đó chỉ lộ ra khi có người đi đọc `deploy_nang_quyen.ps1`
thay vì tin vào lời khai.

### Còn nợ sau deploy

⚠️ **Chưa tạo một lượt tiếng nói THẬT trên production trong phiên này.** Tài
khoản khách không phải của tôi để dùng. Bằng chứng gián tiếp: dịch vụ
`LTTStudioVoice` Running, app nạp ok, làn worker an toàn, bản chạy khớp git —
nhưng đó vẫn là *gián tiếp*, và tài liệu này không nên nói to hơn thứ nó đo.

Việc đầu tiên nên làm khi có người đăng nhập được: mở `/ltt-voice`, bấm một nút
nghe thử (hai mươi tệp mẫu sẽ dựng dần, **tối đa 3 giọng mỗi giờ**, nên trong
~7 giờ đầu một số thẻ sẽ nói *"đang chuẩn bị"* — đúng hành vi, không phải lỗi),
rồi tạo một lượt đọc và đối chiếu credit.

