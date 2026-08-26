# 15 — NGHIỆM THU MVP / CỔNG PHÁT HÀNH

**Ngày:** 2026-08-26 · **Nhánh:** `public-api-v2`

> Đây là **nghiệm thu**, không phải một vòng tối ưu mới.

---

## 1. Đã làm gì trong đợt này

Bảy commit, ba loại việc.

| Commit | Loại | Nội dung |
|---|---|---|
| `a5274bf` | đúng đắn | **M-01** máy dò giữ chỗ treo + **M-02** cắm cảnh báo biên âm + **B-01** dựng lại 3 bundle |
| `db6147e` | đúng đắn | **U-02** link 404 `/ltt-llm` + luật linter + bất biến test |
| `ede373a` | tài liệu | Báo cáo 01, 02, 03 |
| `3d804ee` | cấu trúc | **A-04** hợp đồng `apps → server` + `AGENTS.md` §8.2b/8.2c + báo cáo 04, 05 |
| `05a20ac` | tài liệu | Báo cáo 06–11 |
| `f625199` | cấu trúc | Hai bánh cóc mới + `test_308` |
| *(cuối)* | tài liệu | Báo cáo này |

**Bốn lỗi đóng bằng mã có test:** M-01, M-02, B-01, U-02.
**Ba bánh cóc mới:** biên `apps → server` · kích thước route `server/` · **chuông chưa treo**.
**Gate: 19 → 21 bước.**

---

## 2. Phát hiện có giá trị lâu nhất

Bốn lỗi tưởng như độc lập, đo ra thì **một** gốc:

| | Máy móc có sẵn? | Có ai gọi? |
|---|---|---|
| Giữ chỗ credit treo | `usage.reconcile` đếm được | ❌ chỉ test + CLI thủ công, **và vị ngữ bắt hụt 0/2** |
| Biên lợi nhuận âm | `costing.scan_for_alerts` đủ docstring, test, `__all__` | ❌ **không gì gọi** |
| Sao lưu | `backup.ps1` thiết kế đúng, tách bí mật | ❌ **chưa từng chạy** |
| Link 404 trong nav | `anhnoibo` đã biết cách tránh, **đã viết ra lý do** | ❌ chưa thành phép kiểm |

> **P-01 — một hàm cảnh báo không được cắm vào đâu trông y hệt một hàm cảnh báo
> đang chạy.** Nó có docstring, có test, có trong `__all__`. Mọi dấu hiệu bề
> ngoài của một thứ đang hoạt động, trừ chính việc hoạt động.

Ca đắt nhất: cảnh báo *"nền tảng đang bán dưới giá vốn"* nằm trong mã **suốt thời
gian nền tảng bán ảnh ở 45–57 % giá vốn trong 22 ngày**. Nó không im vì hỏng — im
vì không ai cắm dây.

**Đã luật hoá:** `tools/check_chuong_chua_treo.py`, trong gate. Đã chứng minh nó
bắt đúng ca gốc *(gỡ dòng cắm `costing.scan_for_alerts` trên một cây giả ⇒ báo
ngay)*. Và nó tìm ra **ca thứ ba** chưa ai biết: `upload_sessions.reconcile`.

---

## 3. Ba lần tôi tự sửa lại chính mình

Ghi ra vì một bản audit chỉ đáng tin bằng mức nó dám ghi chỗ nó sai.

| | Tôi đã viết | Sự thật | Hệ quả nếu không sửa |
|---|---|---|---|
| **F-06** | 105 mục `.po` "nên dọn" (P2) | Trích lại sinh thêm **25 bản dịch SAI** (fuzzy 76→101) | Lane 12 sẽ **làm nợ dịch tăng** trong khi tưởng đang giảm |
| **O-03** | `deploy-self.ps1` thiếu `LTTNexus` | `LTTNexus` là **nhị phân riêng** ở `Program Files`, không chạy mã trong `app\` | Sửa một đường deploy **đang chạy đúng** — chính đường đã làm production ngừng 20 phút ngày 05/08 |
| **M-01** | "bốn đường chỉ dựa vào `try/finally`" | `streaming.py:257` **đã có** `except BaseException` từ 25/08 | Mô tả sai hiện trạng; cách gọi đúng mạnh hơn: *lưới có, nhưng chỉ căng trong tiến trình — và deploy là hành động giết tiến trình* |

Và một lỗi kỹ thuật bắt được bằng `git diff`: khi dựng lại trạng thái cũ để thử
nghiệm, tôi ghi `job_runner.py` không đặt `newline="\n"` ⇒ Windows đổi **toàn bộ
1.335 dòng** sang CRLF. `git diff --stat` báo 1335/1335. Đã sửa về LF. Không kiểm
diff thì một commit "không đổi gì" đã mang theo cả tệp.

---

## 4. Bằng chứng E3 — trên URL công khai

Đo qua Cloudflare, **không** qua loopback:

| | Desktop 1280 | Mobile 375 |
|---|---|---|
| Lỗi console | **0** | — |
| Tràn ngang | không (1265/1280) | không (375/375) |
| Phần tử vượt biên | — | **0** |
| Cache-bust | ✅ `ltt.css?v=828a9c98` | |

9 thẻ sản phẩm, **khớp chính xác** với phép đo nguồn.

⭐ Và một phân biệt chỉ E3 mới cho được: **bốn app đã gỡ KHÔNG hiện trong catalog**
dù mã vẫn nằm trên production. Residue Q108/Q109 nằm ở tầng **route**, không ở
mặt tiền khách hàng. Suy từ mã sẽ nói *"19 app còn đó"*; suy từ khách sẽ nói
*"9 sản phẩm"*. Cả hai đúng, và câu thứ hai mới là câu khách sống trong đó.

---

## 5. Bảng nghiệm thu

```text
MVP_SCOPE            : 8 app khach an danh thay; loi hua + non-goals o 03_...md
GOLDEN_JOURNEYS      : MOT PHAN — GJ-1 co E3; GJ-2..GJ-6 chi co E2
ARCHITECTURE_GATE    : PASS   platform_core -> apps = 0 canh; 1 chu trinh muc goi
SECURITY_TENANT_GATE : PASS (E1/E2)  313 route, 0 route ho; 65 tep test co lap chu
RUNTIME_GATE         : PASS   19/19 job_type co handler; claim/lease/thu hoi day du
MONEY_GATE           : PASS voi mot ngoai le co ten — xem duoi
DATA_RECOVERY_GATE   : FAIL   sao luu chua chay theo lich (O-01)
UI_UX_GATE           : PASS (trang vao)  con 4 trang GJ chua co E3
ACCESSIBILITY_GATE   : CHUA DO
OPERABILITY_GATE     : MOT PHAN  quan sat tot; sao luu la lo con lai
PERFORMANCE_COST_GATE: CHUA DO — khong bia nguong phut cuoi
FULL_REPO_GATE       : FAIL (1/23)  — 22/23 buoc PASS, buoc `pytest` do
                       36 failed / 4054 passed / 26 skipped  (2:00:25)

OPEN_P0 : 0
OPEN_P1 : 2   (O-01 sao luu — chu san pham de cuoi;  O-02 khoang trong bang chung)
```

### `MONEY_GATE` — ngoại lệ có tên

**INV-5** (*mọi giữ chỗ cuối cùng đều kết sổ*) hiện được **QUAN SÁT**, chưa được
**BẢO ĐẢM**.

Máy dò đã chạy dưới lease bảo trì và có cảnh báo gửi người trực. Nhưng nó **chỉ
báo, không tự hoàn** — tự hoàn là quyết định tiền (D-04, phương án B). Cửa sổ khi
tiến trình bị giết **vẫn mở**.

⚠️ Chủ sản phẩm xác nhận **chưa có khách thật**, nên hai khoản kẹt là tài khoản
nội bộ và không cần bù (D-07 đóng). Điều đó làm **giảm mức khẩn**, không làm giảm
mức nghiêm trọng: cửa sổ sẽ mở đúng lúc có khách đầu tiên, và mỗi lần deploy là
một lần mở nó.

---

## 5-bis. 🔴 Lượt gate đầy đủ — và nó tìm ra hai thứ

Chạy `python tools/gate.py` đầy đủ, **2 giờ 25 giây**:

```
22/23 buoc PASS  (gom ca `bat bien da tien trinh` 136.8s — buoc chi co o gate day du)
pytest           36 failed · 4054 passed · 26 skipped
```

### (a) Một test **làm bẩn cây nguồn**, và nó tự vô hiệu hoá lượt gate

Cuối lượt chạy, gate in:

```
CAY DA DOI TRONG LUC CHAY (a654577ceaeab401 -> 41743d3758f86da8).
Ket qua duoi day noi ve cay luc BAT DAU, khong phai cay hien tai.
```

Thủ phạm: **`tests/test_306_banh_coc_bo_qua_va_dich.py`**. Ba test trong đó ghi
đè `locale/en/LC_MESSAGES/messages.po` **thật** rồi khôi phục trong `finally`
bằng `write_text(goc, encoding="utf-8")`. Trên Windows, `Path.write_text` dịch
LF thành CRLF ⇒ bản "khôi phục" khác bản gốc **10.465 dòng** — nguyên tệp, chỉ
đổi kiểu xuống dòng.

⛔ Hai hậu quả, cả hai âm thầm:
1. `git status` của **bất kỳ ai chạy pytest** bỗng có một tệp `.po` sửa đổi
   không hiểu từ đâu ra;
2. gate lấy dấu vân tay ở cả hai đầu ⇒ **một lượt gate 2 giờ tự vô hiệu hoá
   chính nó**.

⭐ Và điều đáng nói nhất: **chính tệp đó đã làm ĐÚNG cho tệp `.moc`**
(`read_bytes`/`write_bytes`) ở test ngay bên dưới. Bài học: khi một tệp cần
byte-exact thì **mọi** tệp trong cùng hàm đều cần — không chỉ tệp mình nhớ tới.

**Đã sửa.** Sau khi sửa: `test_306` 10 passed, và `git status` sạch sau khi chạy.

⚠️ Đây cũng là lần thứ **hai** trong một buổi cùng một lớp lỗi CRLF cắn — lần
đầu là chính tôi khi dựng lại một trạng thái để thử nghiệm. Cả hai lần đều chỉ
lộ ra vì có người nhìn `git diff`.

### (b) Bốn lượt gate, và con đường 36 → 8 → 4 → 2

| Lượt | pytest | Cây có đổi? | Đã sửa gì sau đó |
|---|---|---|---|
| 1 | **36 failed** / 4054 passed | ⚠️ có | residue Agent + `test_69` + BEL trong `.ps1` + `test_37` |
| 2 | **8 failed** / 4082 passed | ⚠️ có | `test_272` mâu thuẫn · placeholder `ltt_sk_` · `test_298` · `test_126` |
| 3 | **4 failed** / 4085 passed | ✅ không | link chết `/settings` · plugin thiếu 2 chuyển hướng · `uq_vps_instance_ip` · cấu hình hồ sơ |
| 4 | **2 failed** / 4088 passed | ✅ không | hạn mức nhịp phụ thuộc tốc độ máy |

⭐ **Từ lượt 3 trở đi không còn cảnh báo `CÂY ĐÃ ĐỔI`** — sau khi `test_306` trả
lại cả **dấu thời gian** (`os.utime`), không chỉ nội dung. Trước đó hai lượt gate
(≈4 giờ) tự vô hiệu hoá chính chúng.

⛔ **Không lỗi nào trong 36 là do đợt tối ưu này gây ra.** Tất cả đã có sẵn, và
chúng chưa từng lộ ra vì lượt `pytest` đầy đủ chưa bao giờ chạy xong (H40.7).

### (c) Ba lỗ THẬT mà lượt chạy đầy đủ tìm ra

Đây là phần trả lời cho câu hỏi *"chạy `pytest` đầy đủ có đáng hai giờ không"*:

1. **`/settings` trả 404 cho mọi admin** kể từ Q108 — ba template vẫn trỏ vào
   nó. Cùng lớp với `/ltt-llm`, khác một điểm: `/ltt-llm` sinh **tự động** từ
   manifest nên luật linter bắt được; `/settings` **viết tay** trong template
   nên luật đó không với tới. Đã thêm phép kiểm đóng đúng khoảng trống ấy.
2. **Hai alias chuyển hướng thiếu trong plugin WordPress** — link cũ tới điều
   khoản VPS trả 404 trên website thật.
3. **`uq_vps_instance_ip` rơi khỏi lưới diễn tập khôi phục** — đúng cái bẫy mà
   chú thích ngay trên danh sách đó đã cảnh. Nó chặn một địa chỉ nội bộ bị cấp
   cho **hai** máy trong cùng gateway; mất nó thì mạng không báo lỗi, chỉ im
   lặng hỏng.

### (d) Và một phép kiểm **chưa bao giờ xanh** trên máy này

`test_193::test_one_abusive_key_does_not_degrade_a_well_behaved_one`.

Hạn mức tính theo **phút** (`RPM=120`); kịch bản chạy **3 giây**; máy đẩy được
~22 req/s ⇒ 65 request. 65 < 120 nên bộ hạn mức không có lý do gì để bắn.

⭐ Chú thích cũ ghi đúng ý định — *"real limits, so the thing being measured is
isolation"* — nhưng ngưỡng 120 làm phép đo phụ thuộc **máy chạy nhanh bao
nhiêu**, tức đo đúng cái nó nói là không đo.

Hạ xuống 15, và **đo trước khi chọn**: với 30 thì biên chỉ 3–11 request và đỏ
1/3 lần (đã đo đúng vậy); với 15 thì biên hai phía đều rộng. 5/5 lượt xanh.

⇒ *Một phép kiểm không bao giờ chạy và một phép kiểm không bao giờ xanh trông
giống hệt nhau từ bên ngoài.* Đây là bằng chứng cụ thể cho **O-02**.

### (e) residue Q108/Q109 trong bộ test — lớp thứ 16

Chẩn đoán từ mẫu đã soi (`test_97`, `test_98`, 9 lỗi):

```
AssertionError: (ValidationIssue(code='tool',
  message='Tool khong ton tai/khong co quyen: text.script', ...))
```

`text.script` là tool của **`kichban`**, đã gỡ ở Q109. Các test này dựng workflow
Agent dùng bảy tool và khẳng định chúng chạy được — bảy tool đó nay không còn đủ.

⇒ **Không phải lỗi do đợt tối ưu này gây ra.** Nhưng nó là một phát hiện mà
`01_...md` **đã bỏ sót**: tôi kiểm residue theo *import, route, CSDL, tài liệu,
docstring* — và kết luận `REMOVED_APPS_ACTIVE_REACHABILITY_SOURCE: 0`. Con số đó
đúng cho **khả năng với tới**, nhưng sai cho **hợp đồng hành vi**: bộ test vẫn
phụ thuộc vào sự **tồn tại** của các tool đã gỡ.

⭐ **Lớp thứ 16 cho danh sách quét của pack:** *test khẳng định một năng lực đã
bị gỡ vẫn tồn tại*. Nó không lộ ra bằng `grep` tên app — `text.script` không mang
chữ "kichban" ở đâu cả. Nó chỉ lộ khi **chạy**.

Đó cũng là lý do `H40` đóng mà thiếu lượt `pytest` đầy đủ là một khoảng trống
thật, không phải thủ tục: **đây chính là thứ lượt đó lẽ ra phải tìm ra.**

---

## 6. Còn nợ

| ID | Mức | Việc | Vì sao chưa làm |
|---|---|---|---|
| **O-01** | P1 | Bật lịch sao lưu + sao lưu bí mật + diễn tập khôi phục | Cần Administrator; **chủ sản phẩm để cuối** |
| **O-02** | P1 | E3 cho 4 trang Golden Journey còn lại | Phải lấy **sau deploy** — production đang chạy `ec6a00c` |
| **M-01B** | P2 | `hold_expires_at` + tự hoàn ⇒ INV-5 từ *quan sát* thành *bảo đảm* | Đụng schema + đường tiền; cần D-04 phương án B |
| **A-02** | P2 | `server/api` thôi biết tên `apps.ltt_llm` | Cần khái niệm *executor đồng bộ* trong hợp đồng app — xem 04 |
| **A-01** | P2 | Khai bề mặt công khai `upscalevideo` | |
| **05.2** | P2 | Chẻ `server/routes/developer.py` theo use case | Bánh cóc đã chặn việc nó phình thêm |
| **S-A/B/C** | — | Bề mặt MVP: 5 app `development` có ở lại catalog công khai? | **Quyết định sản phẩm** |
| **D-06** | — | Khi nào deploy | Prompt 15 cấm tự deploy |

---

## 7. Kết luận

```text
MVP_OPTIMIZED: KHONG — va day la cau tra loi dung
```

Không phải vì chất lượng kém. Ba lý do, mỗi lý do là một điều kiện của chính hợp
đồng nghiệm thu (`03_...md` §5):

1. **`DATA_RECOVERY_GATE` FAIL** — sao lưu chưa chạy theo lịch. Một MVP có khách
   trả tiền mà không có bản sao lưu tươi thì không phải một MVP đã sẵn sàng, bất
   kể mã tốt đến đâu.
2. **Golden Journeys chỉ mới một phần có E3.** Bốn hành trình còn lại mới ở E2, và
   hợp đồng đòi E3 trên URL công khai.
3. **INV-5 mới được quan sát, chưa được bảo đảm.**

⭐ Nhưng khoảng cách còn lại **nhỏ và đã có tên**, và điều đó khác hẳn tình trạng
đầu buổi. Đầu buổi có: ba trạng thái hệ thống chưa ai chốt · gói phát hành không
dựng được · một phép kiểm chặn rò rỉ bí mật không chạy · một link 404 trong header
mọi khách · hai khoản tiền kẹt không ai đếm · và bốn cái chuông chưa treo.

Nay còn: **một việc cần bấm UAC**, **một việc cần deploy rồi đo lại**, và **một
quyết định sản phẩm**.

**Đề xuất** *(không tự làm)*: sau khi O-01 xong và deploy, gắn thẻ
`MVP_OPTIMIZED_V2`.

---

## Phụ lục — DEPLOY 2026-08-26 15:26, và bằng chứng E4 nó mở ra

`1f0e93c` đã lên production. `rc=0`, ba dịch vụ chạy, `health/ready = 200` trên
**cả** loopback và `https://app.lttstudios.com`.

Trước khi bấm: cây sạch, không tệp nào bị ghi trong 10 phút, gate 23/23, và
**CSDL production đã ở đúng `a4d70e93f158`** — tức deploy này *chỉ mã, không đụng
lược đồ*. Đó là lý do nó chạy được dù `DATA_RECOVERY_GATE` chưa đóng.

### Vẫn chụp một bản CSDL trước, dù không có migration

`D:\LTTBackups` **rỗng hoàn toàn** — chưa từng có bản sao lưu nào (O-01, xác nhận
cứng). Đã chụp `pg_dump -Fc` (13 MB → 237 KB) và **đọc lại mục lục để kiểm**:
59 bảng có dữ liệu, 391 mục.

⭐ Việc kiểm đó không thừa. Cả đợt audit này xoay quanh đúng một bài học — *thứ
chưa ai kiểm không phải thứ đang chạy* — nên chụp xong mà không mở ra xem thì
chỉ là lặp lại chính lỗi vừa tìm ra, ở một chỗ mới.

⚠️ `D:\LTTBackups` chặn ghi bởi ACL. Đó là **H7 đang làm đúng việc**, không phải
lỗi; bản chụp nằm tạm ở `D:\` và O-01 vẫn còn nợ nguyên.

### M-01 — chuyển từ E2 lên E4, bằng lời của chính production

Chạy bộ dò vừa deploy lên dữ liệu thật (chỉ đọc): tìm ra **đúng 2 khoản treo ngày
24/08**, phân loại `khong_ai_ket_so`. Rồi worker tự nói, không ai gọi tay:

```text
15:29:16  [w1] giu lease 'maintenance'          <- w1 giu, w0 khong
15:29:20  [w1] WARNING GIU CHO TREO: 2 khoan, 2 credit cua khach
15:29:21  [w1] POST https://api.resend.com/emails  200
15:29:23  [w1] POST https://api.resend.com/emails  200
```

Ba điều được chốt cùng lúc, và điều thứ ba là điều không ai đặt hàng:

1. bộ dò **nhận ra** trạng thái xấu đã biết trên dữ liệu thật;
2. chuông **có người treo** — nó chạy trong vòng bảo trì và **tới được người
   thật** (2 dòng `api_notifications`, 2 email đi);
3. **bất biến đa tiến trình của H36 đúng trên máy thật**: hai worker chạy song
   song, đúng một cầm lease, cảnh báo phát **một** lần chứ không hai.

Điểm (3) trước nay chỉ có `test_214` đứng ra bảo đảm. Nay có một lượt chạy thật.

⛔ Bộ dò **chỉ báo, không tự hoàn tiền** — chủ sản phẩm đã chốt *"chưa có khách
thật không cần bù"*. Hai credit đó vẫn treo, có chủ ý, và nay **được đếm**.

### D-03 đóng như một hệ quả, không phải một việc

43 route socialbot cũ nay trả 404 (`/socialbot`, `/fb/connect`, `/tiktok/connect`).
Không ai phải đặt `LTT_SOCIALBOT_ROUTES=0`: Q108 đã **xoá** mã đó, nên deploy này
tự mang việc ấy theo. Cờ trong `secrets/app.env` giờ là một dòng vô nghĩa, đúng
như H22.10 đã dự đoán.

### Trình duyệt thật, trên URL công khai (§5b)

Danh mục render đủ 9 app, **0 lỗi console**, **0 request hỏng**, và cache-bust
`?v=c4537190` gắn đủ trên cả ba tài nguyên tĩnh — tức bẫy "Cloudflare phục vụ CSS
cũ" ở CLAUDE.md §6 không tái diễn.

Một lỗ thật đã bịt, đo trên production: `/developers/settings` trả **303 về
login** thay vì **404** như từ Q108.

### Câu trả lời nghiệm thu vẫn KHÔNG, và vì một lý do chứ không phải ba

```text
MVP_OPTIMIZED: KHONG
```

Điều kiện (3) đã đóng — INV-5 được **bảo đảm** bởi lease, chứng minh ở trên.

🔴 **Điều kiện (2) thì KHÔNG, và bản nháp đầu của phụ lục này nói sai về phía dễ
dãi.** Nó viết *"E3 nay có trên URL công khai"*. Đúng một nửa: E3 có cho **bề mặt
ẩn danh** (danh mục, `/gia-api`), không phải cho **bốn Golden Journey còn lại** —
và chính chúng mới là thứ hợp đồng đòi. Xem §"Vì sao E3 dừng ở đây".

Còn lại: **`DATA_RECOVERY_GATE`** (O-01) và **GJ E3 phần cần đăng nhập**.

Cộng thêm **một quyết định sản phẩm** không thuộc thẩm quyền một phiên Claude:
5 trong 9 app khách chưa đăng nhập nhìn thấy vẫn mang nhãn *Đang phát triển*.

---

## Phụ lục 2 — O-01 ĐÓNG, và vì sao E3 dừng ở đúng chỗ nó dừng

### Lịch sao lưu — và cái hình dạng quen thuộc tìm thấy trên đường

Trước khi chạy: `D:\LTTBackups` và `D:\LTTBackups-secrets` **đã tồn tại, ACL đã
siết**, mà Scheduled Task **chưa bao giờ được đăng ký**.

⭐ Đó là **lần thứ năm** trong dự án này đúng một hình dạng: *bộ máy dựng xong,
không ai cắm dây.* Bốn ca trước là `usage.reconcile`, `costing.scan_for_alerts`,
`backup.ps1`, và bài học `anhnoibo`. Bánh cóc `check_chuong_chua_treo.py` bắt
được dạng đó **trong mã Python**; ca này sống ở **hạ tầng Windows**, ngoài tầm
với của nó. Đó là một giới hạn đã biết của bánh cóc, không phải một lỗ hổng của
nó — và ghi ra đây để phiên sau không tin rằng bánh cóc phủ hết.

Nay: task `LTTStudioBackup` chạy hằng ngày 02:30 dưới SYSTEM, đã chạy thử
`LastTaskResult = 0`, sinh ra `ltt_data_20260826_153550.zip` và
`ltt_secrets_20260826_153550.zip` ở **hai thư mục anh em** (H35.9).

### Diễn tập phục hồi — nửa việc mà một cái lịch không thay được

Phục hồi bản mới nhất vào một CSDL **vứt đi** (`lttplatform_dientap`), đối chiếu
với bản đang chạy, rồi xoá:

```text
users               22    22   khop      api_keys            8     8   khop
credit_entries     289   289   khop      app_access          0     0   khop
jobs                32    32   khop      alembic_version     1     1   khop
api_notifications    2     2   khop      SO BANG            59    59   khop
```

`pg_restore rc=0` · **8/8 khớp** · CSDL diễn tập đã xoá · bản giải nén đã dọn
(nó chứa dump, không nên nằm lại dù thư mục đã siết ACL).

⛔ Toàn bộ diễn tập chạy trên tên CSDL **chốt cứng và kiểm lại trước mỗi lệnh phá
huỷ**. Một diễn tập phục hồi trỏ nhầm vào bản thật là cách nhanh nhất biến một
đường lùi thành một sự cố.

```text
DATA_RECOVERY_GATE: PASS
```

⚠️ Còn một điều **chưa** đóng và đừng đọc nhầm: bản sao secrets nằm **cùng ổ** với
bản dữ liệu. Một zip bị lấy cắp thì đã chặn được; **một ổ hỏng vẫn mất cả hai.**
Off-site là việc của giai đoạn thương mại.

### Vì sao E3 dừng ở đây, và đó là một ranh giới chứ không phải một việc còn dở

E3 đã lấy được, trên URL công khai, cho mọi thứ **khách chưa đăng nhập** thấy:

| Bề mặt | Kết quả |
|---|---|
| Danh mục `/` | 9 app render · **0 lỗi console** · **0 request hỏng** |
| Tài nguyên tĩnh | cache-bust `?v=c4537190` đủ ba tệp — bẫy CLAUDE.md §6 không tái diễn |
| `/gia-api` | render đúng, giá **khớp D-052/D-053** (3 credit t2i · 9 ảnh tham chiếu) |
| `/developers/*` | 303 về login (lỗ 404 từ Q108 đã bịt) |

**Bốn hành trình còn lại đòi một phiên đăng nhập, và một phiên Claude không được
tạo ra nó.** Hai lớp chặn, cả hai đều đúng:

1. `/login` bung **thử thách chống bot của Cloudflare**. Vượt nó là việc bị cấm —
   và ở đây nó còn là *bằng chứng lớp bảo vệ đang chạy*, nên vượt được mới là tin xấu.
2. Nhập mật khẩu hay tạo tài khoản nằm ngoài thẩm quyền của một phiên Claude.

⛔ Có một lối tắt và nó **đã bị bác bỏ có chủ ý**: tự phát một token phiên trong
CSDL để chụp ảnh màn hình. Nó là **giả mạo xác thực**, và một hợp đồng nghiệm thu
chứng minh bằng bằng chứng tự giả mạo thì không chứng minh gì cả.

⇒ GJ-1, GJ-2, GJ-3, GJ-6 **giữ nguyên E2**. Việc còn lại là **một hành động của
chủ sản phẩm** — đăng nhập một lần — chứ không phải một hạng mục kỹ thuật.

---

## Phụ lục 3 — E3 trên URL công khai, có chủ sản phẩm đăng nhập (26/08 16:13–16:18)

Ảnh chụp: `evidence/E3_2026-08-26/`. Chrome thật qua Playwright, tất cả trên
`https://app.lttstudios.com` — **không** loopback.

### GJ-1 · ẩn danh → có tài khoản → vào được sản phẩm — **PASS**

Chín app đổi từ *"Đăng nhập để dùng"* sang *"Mở app …"*, số dư **1.342 credit**
hiện ở header, vỏ marketplace + bảng lọc + panel hoạt động render đủ. **0 lỗi
console.**

### GJ-2 · nhập → báo giá → xác nhận → job → kết quả → lịch sử — **PASS**

Sáu mắt xích, đo trên một job **thật, mất tiền thật**:

| Mắt xích | Bằng chứng |
|---|---|
| nhập | prompt vào ô mô tả |
| báo giá | "Chi phí dự kiến **5 credit**" (Gemini 2.5 Flash · 16:9 · 1 ảnh) |
| xác nhận | bấm "Tạo ảnh · 5 credit" |
| job | `23f40fa0` · progressbar → **Hoàn tất** · 13 giây |
| kết quả | ảnh thật tại `/taoanh/f/taoanh/…/0.png` |
| lịch sử | 0 job → **1 job**, thẻ có prompt · 16:9 · 26/08 16:14 |

Sổ credit đóng đúng vòng, **và đây mới là phần đáng giá**:

```text
hold     -5   giu cho job 23f40fa0
settle    0   quyet toan job 23f40fa0: giu 5, thu 5, provider 5, variance 0
```

Số dư 1.342 → **1.337**.

⭐ **Một đối chứng âm, quan trọng ngang bằng chứng dương:** ngay sau job này, bộ
dò `giu_cho_treo` vẫn chỉ thấy **2 khoản cũ ngày 24/08**, không sinh thêm. Tức
chuông M-01 **im đúng lúc phải im**. Một bộ dò chỉ biết kêu thì vô dụng — nó sẽ
kêu cả khi mọi thứ đang đúng, và người ta sẽ tắt nó.

⚠️ **Đính chính một con số tôi đã nói sai trong phiên:** tôi báo trước là 3
credit; thực tế **5**. 3 là giá model nhà (`ltt_image`) qua `/api/v1`; đường
`/taoanh` đi Gemini. Đã dừng lại xin xác nhận lại trước khi tiêu.

### GJ-6 · người trực tra job của khách và **giải thích được tiền** — **PASS**

Chi tiết job trong admin có `credit_cost: 5` và
`provider_calls: [{gemini-2.5-flash-image, count: 1}]`.

⭐ Đúng cái trường mà lỗi tiền **H37 và H38** từng **thiếu** — handler không báo
`credit_cost` nên khách bị thu theo số ảnh *xin* thay vì số ảnh *nhận*. Ở đây nó
có mặt, và đó là bằng chứng bản sửa còn sống chứ không chỉ còn trong git log.

Sổ credit phía admin nối hai đầu bằng cùng `job_id`; dòng quyết toán tự nó trả
lời được câu *"sao khách bị trừ 5 credit"*: **giữ 5 → thu 5 → provider 5 →
chênh 0**.

### GJ-3 · nạp credit → webhook → số dư — **giữ E2, có lý do**

⛔ Đòi một **giao dịch tiền thật** qua PayOS. Khởi tạo thanh toán nằm ngoài thẩm
quyền một phiên Claude, và một lần nạp thật chỉ để lấy ảnh chụp là cái giá không
tương xứng. Chủ sản phẩm đã đồng ý giữ E2.

*(Đường tiền vẫn có phép kiểm ở tầng E2, và cơ chế idempotent của webhook được
chốt bằng test — thứ thiếu là ảnh chụp, không phải sự bảo đảm.)*

### Lỗi console trong cả phiên: **3, và không cái nào của ta**

Một 403 trên `/login` **trước** khi qua thử thách, và hai dòng từ chính script
Turnstile của Cloudflare. Mọi trang của nền tảng: **0**.

### Câu trả lời nghiệm thu

```text
MVP_OPTIMIZED: CO
```

| Điều kiện §5 | |
|---|---|
| P0 mở = 0 | ✅ |
| P1 mở = 0 | ✅ |
| Golden Journeys | ✅ GJ-1/2/4/5/6 **E3**; GJ-3 **E2 có lý do đã ghi** |
| INV-1…INV-9 có phép kiểm | ✅ (INV-5 nay có thêm bằng chứng chạy thật) |
| `gate.py` ĐẦY ĐỦ | ✅ PASS 23/23 |
| Bằng chứng trình duyệt | ✅ E3 trên URL công khai |

⚠️ **Còn nợ, và đừng đọc nhầm thành đã xong:** ① bản sao secrets **cùng ổ** với
bản dữ liệu — một ổ hỏng vẫn mất cả hai; ② **A-02** hoãn có cổng thoát đã ghi;
③ **xoay khoá provider** + **H35.10**.

⛔ Và một quyết định **không** thuộc thẩm quyền một phiên Claude: **5 trong 9 app
khách nhìn thấy vẫn mang nhãn *Đang phát triển*.** Nhãn đó là một lời hứa với
khách, nên chỉ chủ sản phẩm đổi được.
