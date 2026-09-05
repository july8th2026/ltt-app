# Hai mươi mốt cái bẫy trong chính cổng chất lượng

**2026-08-25.** Không phải bẫy trong sản phẩm — bẫy trong **thứ dùng để chứng
minh sản phẩm đúng**. Tất cả đều cùng một hình dạng:

> Một phép kiểm **tồn tại**, nên không ai viết lại nó.
> Nó **không đo thứ nó có vẻ đang đo**, nên nó không cảnh gì cả.
> Và nó báo **PASS**, nên cái PASS đó đọc y hệt một cái PASS thật.

Sáu cái đầu lộ ra trong một ngày, vì trong ngày đó có **hai phiên làm việc song
song trên cùng một cây nguồn** — điều kiện làm mọi giả định "chỉ có một người"
gãy cùng lúc.

---

## Bẫy 1 — Bánh cóc đếm SỐ LƯỢNG thay vì chốt TẬP HỢP

`tools/check_so_test.py` chốt *"24 số tệp test bị trùng, không được nhiều hơn"*.

Ngày 25/08 hai phiên cùng tạo `test_303_*`. Bánh cóc báo **PASS** — vì trong
cùng lượt đó một va chạm **cũ** vừa được dọn. Tổng vẫn 24.

Nó không sai theo cách nó khai. Nó **đo nhầm đối tượng**: thứ cần chặn là *"một
số MỚI bị trùng"*, không phải *"tổng số tăng"*.

**Đã sửa.** `check_so_test.moc` nay là một tập hợp, dòng đầu `# tap-hop-so-bi-trung`.
Đọc được cả tệp mốc đời cũ và nói rõ đã chuyển đời — không nới lỏng im lặng.

> ⭐ **Luật rút ra, và nó áp cho cả ba bánh cóc thêm sau:** một bánh cóc đếm số
> lượng luôn có một cửa hoán đổi một-đổi-một đi lọt. Chốt tập hợp.

---

## Bẫy 2 — `--quick` báo PASS y hệt gate đầy đủ

`gate --quick` **đúng** khi bỏ `pytest` — đó là mục đích nó khai. Lỗi nằm ở dòng
kết quả: nó in `RESULT: PASS`, **không thêm một chữ nào**.

Cả hai phiên đều đọc dòng đó là "mọi thứ xanh". Và **mọi lỗi thật hôm đó đều nằm
ở đúng bước `pytest` mà chế độ này bỏ**:

| Lỗi | Vì sao `--quick` không thấy |
|---|---|
| Migration `pve_ve` dùng `ALTER COLUMN … TYPE` — vỡ trên SQLite | chỉ chạy trong pytest |
| Liên kết điều khoản VPS trỏ tới đường 404 | chỉ chạy trong pytest |
| Hai tệp `test_303_*` trùng số | bánh cóc bẫy 1 |

**Đã sửa.** `--quick` nay in:

```
RESULT: PASS  [--quick: KHONG chay bat bien da tien trinh, pytest]
        Chua phai bang chung day du - moi loi THAT ngay
        25/08 deu nam o buoc `pytest` ma che do nay bo qua.
```

---

## Bẫy 3 — Chuỗi đã vào `.po` rồi mà `msgstr` vẫn rỗng

`tools/check_i18n.py` canh chuỗi **chưa được bọc `_()`** — chuỗi không bao giờ
vào được tệp dịch. Không có gì canh bước **sau** đó.

Đo 25/08 trên `locale/en/LC_MESSAGES/messages.po`: 2.352 mục, trong đó **203 mục
`msgstr` rỗng** và **76 mục `#, fuzzy`**.

⛔ **Fuzzy đếm như rỗng.** `msgfmt` **bỏ qua** mọi mục `#, fuzzy` khi sinh `.mo`.
Một bản dịch fuzzy không bao giờ tới mắt người dùng — nó giống hệt một `msgstr`
rỗng khi chạy, chỉ khác là nó **trông như đã làm xong** khi đọc tệp `.po`.

**Đã sửa.** `tools/check_dich_thieu.py` + mốc 279 mục. Chốt tập hợp, nên ca hoán
đổi (dịch một mục cũ + thêm một mục mới, tổng không đổi) vẫn đỏ — có test chốt
đúng ca đó.

**Không dịch hết 279 mục ngay**, vì chúng nằm ở khu socialbot đóng băng, các app
cũ và trang admin — những chỗ bản tiếng Anh chưa ai xem — và dịch hết là một
buổi làm không ai kiểm lại được, mà vẫn không sửa nguyên nhân. Khu `/api/v1` và
khu VPS đã về **0% tiếng Việt** trong bản EN (`test_299`, `test_304`, `test_305`);
mốc này giữ cho phần còn lại không xấu đi trong lúc đó.

---

## Bẫy 4 — Test frontend đỏ vì hạn chờ viết cứng, và tôi chẩn đoán sai

Ba test vitest đỏ rải rác. Tôi suy ra *"quá hạn khi máy tải nặng"* từ con số
3.288ms so với hạn mặc định 5.000ms — một suy luận nghe hợp lý và **sai**.

Dòng lỗi thật đã bắt được:

```
2381ms … Unable to find role="button" and name "Tải bản mới"
```

Không phải 5.000ms. Là một `{timeout: 1900}` **viết cứng trong chính test đó**.

**Đã sửa.** Ba chỗ trong `CanvasShell.test.tsx` và một chỗ trong
`StudioShell.test.tsx` nâng lên `10_000`; cả ba `vite.config.ts` đặt
`testTimeout: 20_000, hookTimeout: 20_000`.

> ⭐ Bài học không phải "đặt hạn dài hơn" mà: **đừng suy ra nguyên nhân từ một
> con số khi dòng lỗi thật vẫn còn đọc được.**

---

## Bẫy 5 — Kết quả gate nói về một cây nguồn đã không còn tồn tại

Một lượt gate đầy đủ mất **2,9–4,4 giờ**. Trên kho này — hai phiên song song —
cây đổi vài phút một lần.

Ngày 25/08 có ba lượt đầy đủ. Lượt 4,4 giờ báo lỗi ở **một tệp đã đổi tên từ
nhiều giờ trước**. Kết quả ấy không sai lúc nó đo; nó **trả lời về quá khứ**. Đọc
nó như bằng chứng cho hiện tại là cách sinh ra ba vòng sửa những thứ không còn hỏng.

**Đã sửa.** Gate lấy dấu vân tay cây nguồn ở **cả hai đầu** và nói ra khi lệch:

```
CAY DA DOI TRONG LUC CHAY (a1b2… -> c3d4…).
Ket qua duoi day noi ve cay luc BAT DAU, khong phai cay hien tai.
```

---

## Bẫy 6 — Test bị bỏ qua là test không canh gì cả

`pytest -q` in **một chữ `s`** cho mỗi test bị bỏ qua. Một chữ `s` giữa ba nghìn
dấu chấm là vô hình, và gate chỉ giữ **4 dòng cuối** của đầu ra — nên ngay cả
`-rs` cũng không tới mắt ai.

Cụm VPS chạy sạch **503 passed, 2 skipped**. Hai cái `s` đó là
`test_293_vps_dung_lai_cong_vao.py`, và chúng không phải hai phép kiểm phụ:
chúng là **hai phép kiểm duy nhất** chốt rằng kịch bản dựng lại cổng vào còn
khớp bộ luật nftables đang chạy thật. Chúng bỏ qua vì `secrets/cong_vao/` không
bao giờ được commit — nghĩa là trên **mọi** máy làm việc chúng chưa từng chạy,
và bộ luật có thể trôi bao lâu cũng được.

**Đã sửa — nhưng không bằng cách ép chúng chạy.** Phần lớn chỗ bỏ qua ở đây là
đúng: không có PostgreSQL, không có ffmpeg, không có bucket R2 vứt đi, không
phải Windows. Ép chúng chạy trên máy không có điều kiện là đổi một phép kiểm im
lặng lấy một phép kiểm báo động giả.

`tools/check_bo_qua.py` **bắt mọi chỗ bỏ qua phải được KHAI BÁO**: in hết danh
sách 12 chỗ ở mỗi lượt gate (nên `test_293` được **gọi tên** mỗi lần), và báo đỏ
khi xuất hiện một chỗ **mới** chưa có trong mốc.

---

## Bẫy 7 — `__pycache__` mồ côi làm sống lại một app đã xoá

*Tìm ra bởi phiên xoá app socialbot, 26/08.*

Sau một lượt `git stash` / `stash pop`, Python kịp import và ghi lại
`apps/socialbot/__pycache__/`. Tệp `.py` đã đi, `.pyc` ở lại — và gate báo:

```
[ERROR] socialbot: thieu manifest.py
```

cho một thư mục **rỗng**. Quét cả kho thì có **hai** `__pycache__` mồ côi
(`core/`, `scripts/`).

Cùng hình dạng với sáu cái trên: phép kiểm chạy đúng, nói về một thứ **không còn
tồn tại**, và câu báo lỗi chỉ sai hướng hoàn toàn — nó mời người ta đi tìm một
`manifest.py` cho một app đã chết.

---

## Bẫy 8 — câu báo lỗi nêu đích danh một nghi phạm vô tội

`tools/build_release.py` băm **toàn bộ** cây nguồn frontend để biết bundle còn
mới không — kể cả thư mục `tests/`. Nên đổi một con số `timeout` trong một tệp
test làm gói phát hành bị đánh dấu stale, **dù JS xuất ra giống hệt từng byte**.

Phép kiểm không sai; nó chọn phía an toàn. Vấn đề nằm ở câu nó nói:

```
frontend/agent-canvas bundle is stale or built with the wrong Node
```

Node vẫn đúng `24.17.0`, và bản Node là một **hằng số trong test**. Câu báo lỗi
nêu tên một nghi phạm không thể sai, nên người đọc đi kiểm Node trước.

⭐ **Một câu báo lỗi nêu sai tên còn tốn thời gian hơn một câu báo lỗi mơ hồ.**
Cách sửa rẻ nhất là tách nó làm hai vế: *"nguồn đã đổi"* ≠ *"Node sai bản"*.

⚠️ Và `test_44` `SystemExit` ở bundle đầu tiên, nên nó chỉ báo **một** trong ba
bundle hỏng. Sửa xong cái đầu thì nó báo cái thứ hai.

---

## Bẫy 9 — chuỗi đã bọc `_()` mà **không có trong catalog**

Một chuỗi phải qua **ba** cửa mới tới được mắt người đọc bản tiếng Anh:

| # | Cửa | Ai canh |
|---|---|---|
| 1 | được bọc `_()` | `check_i18n.py` |
| 2 | **có mặt trong `.po`** | *(không ai — cho tới 26/08)* |
| 3 | `msgstr` không rỗng | `check_dich_thieu.py` |

Cửa thứ hai đã lọt thật. Hai chuỗi ở chân trang dùng chung — `Giá API` và
`Hướng dẫn API` — ra **tiếng Việt trên mọi trang của bản EN**. Chúng bọc `_()`
từ lâu nên `check_i18n` báo đẹp; chúng **không có một dòng nào** trong `.po` nên
phép đếm mục rỗng cũng không thấy. Chúng chỉ hỏng ở chỗ không ai nhìn.

Nguyên nhân: **`.po` trôi lại phía sau mã nguồn**. Ai đó thêm một chuỗi đã bọc
`_()` và không chạy `i18n.py trich` — và không trách được họ, vì `trich` có giá
riêng của nó (xem dưới). Đo lúc thêm phép kiểm: **67 chuỗi** đang ở trạng thái đó.

**Đã sửa.** `check_dich_thieu.py` nay trích msgid từ mã nguồn **trong bộ nhớ**
(không ghi gì) và báo loại `VANG` cho chuỗi vắng khỏi catalog.

### 🔴 Và đây là lý do không dọn bằng cách trích lại

Một phiên khác thử `i18n.py trich` để dọn chuỗi của app vừa xoá:

```
muc      2.353 -> 2.344   (chỉ bớt 9)
fuzzy       76 ->   101   (+25)
```

`msgmerge` **đoán** bản dịch cho msgid mới bằng cách khớp gần đúng với msgid vừa
biến mất — nên nó tự sinh **25 bản dịch sai mới** (`Ngân sách của bạn` →
`Your scripts`). Dọn ít hơn phần nó làm hỏng.

⭐ **Luật: hạ mốc dịch bằng cách DỊCH, không bao giờ bằng cách TRÍCH LẠI.**

### Một cửa thoát, và nó bị chặn hai phía

Thêm một **loại** kiểm tra mới vào bánh cóc thì lượt chạy đầu luôn thấy "hàng
chục mục mới" — chúng không mới, chúng vừa được nhìn thấy lần đầu. `--accept` từ
chối (đúng), nên có `--khoi-tao-loai VANG`. Nó **chỉ** nhận mục của đúng loại
được gọi tên; mọi loại khác vẫn phải sạch trước. Một cửa thoát không giới hạn sẽ
thành cách người ta làm im lặng mọi thứ khác.

---

## Bẫy 10 — một lượt test bị giết để lại rác trong tệp đã commit

`tests/test_209_versioning_status.py` **sửa** `docs/PUBLIC_API/CONTRACT_BASELINE.json`
rồi khôi phục trong `finally`. Chạy một mình thì sạch — đã đo: 32 passed, tệp
không bẩn.

Nhưng cái `finally` chỉ chạy khi tiến trình **sống tới đó**. Giết một lượt gate
giữa chừng (hoặc để hai lượt test chồng lên nhau, khi lượt này đọc `saved` trong
lúc lượt kia đang sửa) thì con ma ở lại trong tệp:

```
[BREAKING] header: X-Ghost removed clients read it
```

Và từ đó **mọi** phép kiểm tương thích đều đỏ, vì cái chúng so với đã hỏng. Đã
gặp hai lần trong một giờ, mỗi lần một con ma khác (`X-Ghost`, `ghost_field`).

Chữa: `git checkout -- docs/PUBLIC_API/CONTRACT_BASELINE.json`, **trước** khi
chẩn đoán bất cứ thứ gì khác.

⭐ Bài học chung: một test sửa tệp đã commit chỉ an toàn khi nó **luôn** tới được
phần dọn dẹp — và trên một kho có nhiều phiên làm việc song song, điều đó không
được bảo đảm.

---

## Bẫy 11 — Một phép kiểm bảo mật đỏ **vì lý do khác** vẫn là một phép kiểm bảo mật không chạy

`tools/build_release.py` có đường chặn: phát hiện bí mật trong gói phát hành thì
`SystemExit`. Phép kiểm canh nó là
`test_44_release_build::test_secret_abort_path_reports_location_and_exits`.

Phép kiểm đó **đỏ nhiều ngày** — và không phải vì đường chặn hỏng:

```
AssertionError: assert '1 secret finding' in
  'frontend/agent-canvas bundle is stale or built with the wrong Node'
```

Chốt "bundle cũ" bắn **trước**, ném `SystemExit` của chính nó, và **nuốt mất**
`SystemExit` mà phép kiểm định bắt.

⛔ Một gốc (ba bundle lệch hash nguồn), **hai** triệu chứng — và triệu chứng thứ
hai đáng lo hơn hẳn: suốt thời gian đó **không ai kiểm đường chặn rò rỉ bí mật**,
trong khi bảng kết quả chỉ hiện *"2 failed"* trông như một lỗi build tầm thường.

⭐ **Bài học:** khi một phép kiểm đỏ, đọc **thông điệp**, không đọc **số**. Hai
test đỏ cùng một tệp có thể là hai vấn đề, và cái thứ hai có thể đang bị cái thứ
nhất che.

*(Đóng 2026-08-26 ở `a5274bf`: dựng lại ba bundle ⇒ 35 passed, phép kiểm bí mật
chạy lại.)*

---

## Bẫy 12 — Con số PASS nói về một tập hợp khác với tập hợp bạn tưởng

`tools/check_bien_dich.py` báo **"2.101 tệp .py đã kiểm | hỏng: 0"**. Nghe như
toàn bộ kho đã biên dịch được.

Ngày 26/08, sau khi gỡ một git worktree bỏ quên trong `.claude/worktrees/`, con
số tụt xuống **1.357**. Chênh **744 tệp** chính là một **bản sao cũ của cả kho**
— có `core/`, có `apps/socialbot`, có `test_152` đã xoá.

⇒ Suốt thời gian đó cổng biên dịch **thổi phồng độ phủ ~35 %**. Kết quả PASS
không sai, nhưng nó nói về một tập hợp **rộng hơn và cũ hơn** tập hợp người đọc
tưởng. Và `tmp/h26-canary-*/` (1,8 GB, 695 tệp `.py`) vẫn còn đó, vẫn được đếm.

⚠️ Cùng bản sao bóng đó suýt tạo một kết luận sai khác: lần quét
`LTT_SOCIALBOT_ROUTES` đầu tiên trả **13 kết quả từ worktree** trước khi tới kết
quả thật — đủ để báo *"còn residue socialbot"* trong khi nguồn đã sạch.

⭐ **Bài học:** mọi lệnh quét toàn kho phải mang `| grep -v '\.claude/worktrees/'`,
và khi một cổng in ra một con số lớn, hỏi *"con số đó đếm những gì"* trước khi
thấy yên tâm.

---

## Bẫy 13 — Cái chuông đã đúc mà chưa ai treo

Bốn ca trong một đợt audit, cùng một hình dạng:

| | Máy móc có sẵn? | Có ai gọi? |
|---|---|---|
| Giữ chỗ credit treo | `usage.reconcile` đếm được | ❌ chỉ test + CLI thủ công, **và vị ngữ bắt hụt 0/2** |
| Biên lợi nhuận âm | `costing.scan_for_alerts` đủ docstring, test, `__all__` | ❌ **không gì gọi** |
| Sao lưu | `backup.ps1` thiết kế đúng | ❌ **chưa từng chạy** |
| Link 404 trong nav | bài học đã viết trong chú thích `anhnoibo` | ❌ chưa thành phép kiểm |

⛔ **Một hàm cảnh báo không được cắm vào đâu trông Y HỆT một hàm cảnh báo đang
chạy.** Nó có docstring, có test, có trong `__all__` — mọi dấu hiệu bề ngoài của
một thứ đang hoạt động, trừ chính việc hoạt động.

Ca đắt nhất: cảnh báo *"đang bán dưới giá vốn"* nằm trong mã **suốt 22 ngày nền
tảng bán ảnh ở 45–57 % giá vốn**. Nó không im vì hỏng — im vì không ai cắm dây.

⭐ Vì vậy `test_307` và `test_308` chốt bằng `inspect.getsource` rằng các hàm quét
**ĐƯỢC GỌI**, không chỉ **tồn tại**. Và `tools/check_chuong_chua_treo.py` (trong
gate) luật hoá điều đó: mọi hàm quét/cảnh báo trong `platform_core/` phải có ít
nhất một người gọi ngoài `tests/`.

⚠️ Giới hạn nói thẳng: nó không bắt được ca sao lưu (PowerShell) và ca link-404
(một chú thích). Nó bắt hai ca nguy hiểm nhất, và bắt chắc chắn.

---

## Bẫy 14 — Công cụ chạy đúng khi bạn gọi tay, vỡ khi có thứ khác hứng đầu ra

Ngày 26/08, `gate.py` đỏ ở bước `bo test (song song)` sau **0,1 giây** — tức
**trước khi** bộ test kịp chạy lấy một phép kiểm nào:

```text
UnicodeEncodeError: 'charmap' codec can't encode characters in position 2-71
```

Nguyên nhân: `tools/test_nhanh.py` in một đường kẻ khung `─` làm nhãn bước. Gọi
tay thì console là UTF-8 nên nó luôn xanh. Nhưng gate **hứng** đầu ra, stdout
không còn là console, Python rơi về `cp1252`, và một dấu gạch trang trí làm hỏng
cả bước.

⭐ **Điều đáng học không phải chuyện mã hoá.** Là chuyện một công cụ có thể **xanh
100% khi người viết nó thử** và **luôn đỏ ở nơi nó thật sự chạy** — vì môi trường
khác nhau ở một chỗ không ai nghĩ tới. Nó vỡ ở đúng nơi ít người nhìn nhất.

⛔ Và nó **không nằm trong bộ test**. Không phép kiểm nào chạy `test_nhanh.py`
dưới stdout bị hứng, nên bộ test xanh trong khi công cụ chạy bộ test thì hỏng.
*Thứ chạy phép kiểm không tự nó được kiểm.*

**Đã bịt bằng hai lớp, và lớp thứ hai là lớp không được vắng:**

1. `_ep_utf8()` ép `stdout`/`stderr` về UTF-8 — nhưng `reconfigure` chỉ có trên
   `io.TextIOWrapper`, và dưới một trình hứng khác nó có thể **biến mất không báo
   gì**;
2. chuỗi in ra là **ASCII thuần**, nên không phụ thuộc lớp (1) nữa.

`test_309` chốt cả hai: một phép kiểm dựng lại đúng `cp1252` bị hứng, một phép
kiểm đọc mã và từ chối ký tự ngoài ASCII trong dòng `print` của `_chay`.

⇒ **Luật rút ra:** công cụ trong `tools/` phải được thử **dưới đúng cách gate gọi
nó** (đầu ra bị hứng), không chỉ dưới cách bạn gọi nó.

---

## Bẫy 15 — Cái chuông của Bẫy 5 kêu ở **mọi** lượt gate đầy đủ

Bẫy 5 đã được sửa đúng: gate lấy dấu vân tay cây nguồn ở hai đầu và nói ra khi
lệch. Nhưng ngày 26/08, **bốn lượt gate đầy đủ liên tiếp** đều in dòng đó — kể
cả lượt chạy khi không phiên nào khác còn sống.

Nguyên nhân không phải phiên song song. Nó là **chính bộ test**:

| | |
|---|---|
| `_dau_van_tay_cay()` băm `đường dẫn : kích thước : **mtime**` | `tools/gate.py:265` |
| ba tệp trong `TEP_NOI_TIEP` **ghi đè tệp thật rồi khôi phục trong `finally`** | `tools/test_nhanh.py:71` |
| `test_306` ghi đè `locale/en/LC_MESSAGES/messages.po` và `tools/check_dich_thieu.moc` | đúng như thiết kế — nó kiểm chính bánh cóc dịch |

Khôi phục **nội dung** không khôi phục **mtime**. Nên dấu vân tay cuối luôn khác
dấu vân tay đầu, và cảnh báo nổ ở mọi lượt.

⛔ **Vì sao nó tệ hơn là không có cảnh báo nào.** Một cảnh báo kêu mọi lần là một
cảnh báo không ai đọc. Đến lượt gate mà cây **thật sự** bị một phiên khác đổi
giữa chừng — đúng tình huống Bẫy 5 sinh ra để bắt — dòng chữ đó trông y hệt bốn
lần trước, và nó bị lướt qua.

⭐ **Đo được ngày 26/08.** Ba tệp bị ghi trong lượt gate, giờ theo mtime:

```
21:40:23  server/templates/vps_dieu_khoan.html
21:40:25  locale/en/LC_MESSAGES/messages.po
21:40:25  tools/check_dich_thieu.moc
```

Và `git diff` chứng minh **nội dung không hề bị hỏng**: `.po` có 479 dòng thêm,
**0 dòng xoá**, không con ma nào, vẫn LF. Tệp được khôi phục đúng. Chỉ mtime là
không.

⚠️ Đây cũng là lý do `--quick` **không** in dòng đó: nó bỏ `pytest` đầy đủ, nên
bỏ luôn pha nối tiếp — tức bỏ luôn ba tệp ghi vào cây. Hai lệnh cho hai câu trả
lời khác nhau về cùng một câu hỏi, và câu trả lời yên tĩnh hơn lại là câu của
lệnh kiểm **ít hơn**. Ghép với Bẫy 2 thì thành một cặp khó chịu.

**Chưa sửa.** Hai đường, và cả hai đều là một dòng:

1. **Loại trừ `TEP_NOI_TIEP` + hai tệp mốc khỏi dấu vân tay.** Đơn giản nhất,
   nhưng làm mù đúng ba tệp mà một phiên khác dễ đụng vào nhất.
2. **Băm nội dung thay vì mtime cho riêng bảy thư mục đó.** Chú thích trong
   `_dau_van_tay_cay` nói không băm nội dung vì "tốn thêm hàng chục giây" — đúng
   với cả cây, nhưng ta chỉ cần băm lại **những tệp có mtime đổi**, và ngày
   thường đó là ba tệp.

⇒ **Cho tới khi sửa: đừng đọc dòng đó như tín hiệu.** Muốn biết cây có thật sự
đổi không thì đo trực tiếp:

```bash
python -c "
import pathlib,time,datetime
nguong=time.time()-60*10
for d in ('apps','platform_core','server','tools','tests','alembic','locale'):
    g=pathlib.Path(d)
    if not g.exists(): continue
    for f in g.rglob('*'):
        if f.is_file() and '__pycache__' not in f.parts and f.stat().st_mtime>=nguong:
            print(datetime.datetime.fromtimestamp(f.stat().st_mtime).strftime('%H:%M:%S'), f)"
```

Ba tệp quen mặt ⇒ là bộ test. Có tệp lạ ⇒ mới là Bẫy 5 thật.

---

## Bẫy 16 — Trạng thái NGOÀI phép kiểm rò VÀO phép kiểm

Ngày 2026-08-29, hai phiên làm song song gặp **ba** lượt gate đỏ mà không lượt
nào là lỗi mã. Ba nguyên nhân khác nhau, **một** hình dạng:

| # | Trạng thái rò vào | Triệu chứng |
|---|---|---|
| 1 | `__pycache__` cũ hơn nguồn (157 thư mục) | vài test đỏ, dọn xong xanh ngay |
| 2 | `C:\ProgramData\gpu_claims\` — claim GPU **toàn máy**, dùng chung với hộ dựng video | 6 test đỏ **tuỳ lúc** |
| 3 | Thứ tự import: `enabled` chốt lúc **nạp module**, nên `delenv` không tháo được gì | 1 test đỏ, chạy riêng thì xanh |

⭐ **Cả ba đều mất nhiều giờ, và luôn theo cùng một cách: người ta đi sửa mã.**
Cả hai phiên đều làm thế, theo hai hướng ngược nhau, và đều sai.

### Vì sao nó khó hơn một lỗi bình thường

Loại này **không đỏ đều**. Ca số 2 chỉ chảy khi claim còn trong cửa sổ 90 giây
(`_CUA_SO_NAP_MODEL_S`), nên hai phiên chạy cách nhau vài phút ra hai kết quả
trái ngược — và mỗi bên đều có "bằng chứng" cho kết luận sai của mình.

⛔ **Hệ quả: một lượt xanh cũng không chứng minh gì**, nếu nó tình cờ rơi vào
lúc trạng thái ngoài đang sạch. Tôi suýt dùng một lượt "84 passed" làm bằng
chứng; đọc lại thư mục claim thì hộ kia **đã nhả GPU trước khi tôi chạy**.

### Cách phân xử, rẻ hơn nhiều so với đọc mã

**1. Dựng một `git worktree` sạch tại `HEAD` rồi chạy ở đó.** Nó trả lời "lỗi
này có thật không" trong một phút.

```bash
git worktree add %TEMP%\sach HEAD
```

⚠️ Nhưng nhớ hai điều, cả hai đều đã trả giá:
- worktree thiếu `node_modules` và `vendor/` (Git loại trừ) ⇒ frontend và
  `test_82` đỏ **vì thiếu phụ thuộc**, không phải vì mã;
- worktree **cũng tích `__pycache__`** sau vài lượt chạy. *Một cây không có
  diff không phải một cây sạch.*

**2. Với trạng thái toàn máy, đừng chờ nó sạch — hãy TỰ TẠO nó rồi đo.** Đặt
một claim 7.168 MB với PID còn sống, rồi bật/tắt phép cô lập:

```
có fixture cô lập : 26 passed
tắt fixture       : test_chua_lai_headroom  ĐỎ
```

Đó là bằng chứng; "chạy lại tới khi xanh" thì không.

**3. `git stash` KHÔNG cất tệp chưa theo dõi.** Một lượt "đối chứng không có
thay đổi của tôi" vẫn còn tệp test mới nằm đó sẽ ra 17 đỏ vô nghĩa. Cùng lớp
lỗi: nhầm *"đã bỏ phần tôi thêm"* với *"trở về trạng thái gốc"*.

### Cách sửa gốc

Cắt phép kiểm khỏi trạng thái ngoài, **đừng** đi làm cho trạng thái ngoài sạch:

- ca 2: `tests/conftest.py::gpu_khong_claim_toan_may` (không `autouse` — tệp
  test của miền tự bọc bằng `autouse` trong phạm vi tệp);
- ca 3: dùng `_Item` giả thay vì gọi `registry.viec_bao_tri()` thật.

⚠️ **Còn hở, đã biết:** `monkeypatch` chỉ tác dụng trong **tiến trình cha**. Test
nào đẻ tiến trình worker thật (`test_151`) thì worker con vẫn đọc/ghi trạng
thái toàn máy. Bịt đúng là cho đường dẫn đọc một **biến môi trường** — tiến
trình con thừa kế env.

---

## Cái gì canh cái gì, sau ngày 25/08

| Bước gate | Chặn | Mốc |
|---|---|---|
| `trung so test` | thêm số tệp test bị trùng | `check_so_test.moc` (tập hợp) |
| `bo qua im lang` | thêm chỗ bỏ qua không khai báo | `check_bo_qua.moc` (12) |
| `chuoi chua dich` | thêm chuỗi chưa bọc `_()` | `check_i18n` |
| `dich thieu ban EN` | thêm `msgstr` rỗng / `fuzzy` / **vắng khỏi catalog** | `check_dich_thieu.moc` (344) |

Cả bốn chạy **cả ở `--quick`** — chúng chỉ đọc tệp, tốn dưới 5 giây. Ba lỗi thật
lọt lên tàu ngày 25/08 đều lọt vì phép kiểm **có** mà chỉ sống trong `pytest`,
thứ `--quick` bỏ qua.

Bằng chứng rằng cả bốn **chặn thật**, không chỉ tồn tại:
`tests/test_306_banh_coc_bo_qua_va_dich.py` (13 phép kiểm — gồm ca hoán đổi của
bẫy 1, lớp `VANG` của bẫy 9, và ca cửa-thoát-nuốt-loại-khác) cùng hai phép kiểm
mới trong `tests/test_145_gate_covers_everything.py`.

## Bẫy 17 — Một BƯỚC GATE tự bỏ qua rồi hiện ra là `[PASS]`

Bẫy 6 nói về **test** bị bỏ qua, và `check_bo_qua.py` đã bịt nó. Đây là anh em
sinh đôi ở tầng trên: một **bước gate** tự bỏ qua chính mình.

`tools/check_multiproc.py` cần một CSDL PostgreSQL để chạy `test_214`. Không có
thì nó in một khối chữ rất rõ ràng — *"BO QUA bo bat bien da tien trinh"* — rồi
`return 0`. Cái `return 0` ấy **có chủ ý và được ghi lý do ngay tại chỗ**: một
máy không có PostgreSQL vẫn phải làm việc được. Đây không phải lỗi của công cụ.

Chỗ hụt nằm ở **cách gate trình bày**. `gate.py` chỉ đọc mã thoát, nên nó in:

```
[PASS] bat bien da tien trinh          0.7s
```

và dòng tổng kết nói `RESULT: PASS` với 25/25 bước. Đọc dòng đó, người ta hiểu
là **hai mươi lăm điều đã được chứng minh**. Thật ra là hai mươi bốn.

⛔ **0,7 giây là dấu hiệu, và nó rất dễ trôi qua mắt.** Bước ấy phải tạo một CSDL
   rồi chạy một bộ test đa tiến trình; không đời nào xong trong 0,7 giây. Nhưng
   nó nằm giữa hai mươi bốn dòng khác cũng tính bằng giây, nên nó trông bình
   thường. Ngày 31/08 tôi báo *"PASS 25/25"* rồi mới quay lại soi con số đó.

⚠️ **Và đo cho đúng thì cũng có bẫy riêng.** Lần đầu tôi chạy:

```bash
python tools/check_multiproc.py 2>&1 | tail -12; echo "ma thoat = $?"
```

`$?` ở đó là mã thoát của **`tail`**, không phải của Python — nên nó luôn là 0
bất kể chuyện gì xảy ra. Phải tách ra:

```bash
python tools/check_multiproc.py > out.txt 2>&1; ma=$?; echo "$ma"
```

Đo lại đúng cách: **exit 0, 0 giây, có in `BO QUA`**.

🔴 **Hai phiên đọc CÙNG một bước ra HAI kết quả trái ngược — và lời giải đáng
giá hơn chính cái bẫy.** Một phiên song song báo `RESULT: FAIL (1/25)` và chỉ đích
danh bước này; phiên của tôi báo `[PASS]`. Cả hai cùng nhìn thấy khối chữ *"BO QUA"*.

Truy ra thì bước ấy **luôn PASS** — nó trả 0. Phiên kia có một bước khác đang đỏ
thật, đọc được thông điệp *"BO QUA"* trong nhật ký, và **gán** con số `FAIL(1/25)`
cho nó vì nó khớp câu chuyện đang kể. Bước đỏ thật không bao giờ được gọi tên.

⛔ Đó là cái giá thật của bẫy này, và nó không phải *"một bước không chạy"*. Một
   dòng chữ giải thích rất tử tế nằm cạnh một dấu `[PASS]` sẽ được đọc thành **lời
   giải thích cho một thất bại khác** — và thất bại thật ấy đi qua mà không ai tìm.

⭐ Hai phiên đều tự sửa trước khi báo với chủ sản phẩm, và cả hai đều chỉ sửa được
   vì **đo lại thay vì suy ra**: `exit=0, 505 ms` ở một phiên, `exit=0, 0 giây` ở
   phiên kia. Hai phép đo đồng ý; hai câu chuyện thì không.

**Cách dùng cho tới khi có bánh cóc:** trước khi lấy một lượt gate làm bằng
chứng, liếc cột thời gian. Bước nào nhanh một cách vô lý so với việc nó khai là
mình làm thì chạy tay bước đó và đọc đầu ra, đừng đọc mã thoát.

⛔ Và **đừng "sửa" bằng cách cho `check_multiproc.py` trả về khác 0.** Làm thế là
biến một máy không có PostgreSQL thành một máy không chạy được gate — tức đổi
một lời nói dối lấy một cản trở. Sửa đúng là cho gate có trạng thái thứ ba
(`BOQUA`) tách khỏi `PASS`, và cho dòng `RESULT` nói ra số bước đã bỏ qua.

---

## Bẫy 18 — Bánh cóc số tệp test không thấy tệp **chưa được git theo dõi**

`tools/check_so_test.py` đọc cây làm việc, nên nó **có** thấy tệp mới. Nhưng nó
chỉ thấy chúng **khi bạn chạy nó** — và giữa hai lượt chạy của hai phiên khác
nhau không có gì khóa số cả.

Ngày 31/08, ba phiên cùng xây trên một cây. **Va chạm số tệp test xảy ra ba lần
trong một buổi:**

| Phiên | Lấy | Đụng phải | Kết cục |
|---|---|---|---|
| A | `test_353` | `test_353_voice_sidecar_bo_do.py` (đã commit) | đổi → 354 |
| A | `test_354` | `test_354_so_do_khong_troi.py` (đã commit) | đổi → **364** |
| B và C | cùng `test_365` | nhau — **cả hai chưa commit** | một bên đổi → 366 |

Hai hàng đầu bánh cóc **bắt được** — tệp kia đã nằm trong git. Hàng thứ ba thì
không: hai tệp cùng tên số cùng tồn tại trên đĩa, nhưng **mỗi phiên chạy kiểm tra
trước khi phiên kia tạo tệp của mình**, nên cả hai đều thấy số đó còn trống. Cả
hai đều đúng tại thời điểm đo.

⛔ Đây **không phải** lỗi của `check_so_test.py`. Nó là một bánh cóc, không phải một
   cái khoá — và không bánh cóc nào chặn được hai người quyết định cùng lúc dựa
   trên cùng một ảnh chụp cũ.

⭐ Cùng hình dạng với Bẫy 5 (*kết quả nói về một cây đã không còn*) và với chính
   `cua_so_yen`: **cơ chế chỉ bảo vệ thứ nó nhìn thấy**, và cái nó không nhìn thấy ở
   đây là **ý định của phiên khác** — thứ chưa thành tệp lúc nó nhìn.

**Cách dùng cho tới khi có cái khoá:** khi nhiều phiên cùng xây, đừng chỉ chạy
`check_so_test.py` — **nói số mình lấy ra cho các phiên khác** trước khi tạo tệp.
Một tin nhắn một dòng rẻ hơn ba lượt đổi tên.

⚠️ Và đổi tên **không miễn phí**: số tệp test đi vào tài liệu, nhật ký và tin nhắn
   giữa các phiên. Lượt đổi 353→354→364 ở trên kéo theo ba chỗ phải sửa trong
   `VOICE_UI_EXECUTION_PLAN.md`, và một trong ba đã suýt trôi.

---

## Bẫy 19 — Một phép kiểm neo vào **khoảng cách vật lý**, và nó LÂY

Một số phép kiểm đọc **mã nguồn** của công cụ để chốt một quan hệ trong đó. Khuôn
hay dùng nhất:

```python
khuc = ma.split('ket = "PASS" if not failed')[1][:600]
assert "cay_da_doi" in khuc, "phai gan vao chinh bien `ket`, khong in roi"
```

Câu `assert` nói đúng ý định: *"phải gắn vào chính biến `ket`"*. Nhưng thứ nó **đo**
lạ là: *"nằm trong 600 ký tự kể từ một chuỗi mốc"*. Hai thứ đó trùng nhau **cho tới
khi ai đó chèn một khối chú thích tử tế vào giữa** — lúc ấy hành vi vẫn đúng và phép
kiểm đỏ. Ngày 31/08 đúng thế: một bản vá thêm 9 dòng chú thích ngay sau mốc.

🔴 **NHƯNG ĐÓ CHƯA PHẢI PHẦN ĐÁNG GHI.** Sau khi cái thứ nhất được chỉ ra và
chẩn đoán rõ ràng, phiên sửa nó viết một tệp test **mới** — và chép **đúng khuôn đó
thêm hai lần nữa** (`[:900]` × 2), trong vòng một giờ.

⭐ Vì sao khuôn này lây trong khi các bẫy khác thì không: **nó trông chặt chẽ.** Một
   `assert` đọc thẳng mã nguồn, có cắt cửa sổ, có câu báo lỗi giải thích ý định —
   nó mang **mọi dấu hiệu bề ngoài của một phép kiểm tốt**. Ta không tránh nó vì ta
   không nhận ra dạng của nó, kể cả ngay sau khi vừa đọc chẩn đoán về chính nó.

**Đã sửa — bằng một phép đo QUAN HỆ, không phải một cửa sổ rộng hơn.** Nới `[:600]`
thành `[:2000]` chỉ dời ngày nó gãy. Cả ba chỗ nay hỏi `ast`: *khối nào trong hàm
`main` có sửa biến `ket`*, rồi đòi cờ xuất hiện trong một trong số đó. Chèn bao nhiêu
chú thích cũng không làm nó đỏ.

⚠️ **Dấu hiệu nhận dạng cho lần sau:** trong một phép kiểm đọc mã nguồn, mọi con
   số đo **ký tự hoặc dòng** (`[:600]`, `splitlines()[i:i+20]`, `± 3 dòng`) đều là một
   xấp xỉ cho một quan hệ cú pháp. `ast` biết quan hệ đó; chỉ cần hỏi nó.

---

## Bẫy 20 — Sửa một tầng bỏ qua không làm lộ tầng bỏ qua **bên dưới nó**

Bẫy 17 nói về một **bước gate** tự bỏ qua rồi hiện ra là `[PASS]`. Sửa xong nó, ta
tưởng đã nhìn thấu xuống đáy. Chưa.

Ngày 31/08, sau khi bước `bat bien da tien trinh` đã được vá để tự khai lúc nó bỏ
qua, một phiên gọi thẳng bộ test bên dưới:

```
pytest tests/test_214_multi_process_runtime.py
sssssss   7 skipped in 0.26s
```

**Bảy phép kiểm, bảy chữ `s`.** Chúng bỏ qua vì một lý do **khác hẳn** lý do của
bước gate: chúng đòi một **CSDL test riêng** (`LTT_TEST_DATABASE_URL`), còn
`app.env` chỉ có `LTT_DATABASE_URL` của production. Chúng **đúng khi từ chối** —
không bộ test nào được phép chạy trên CSDL thật.

⇒ Hai tầng bỏ qua **chồng lên nhau cho cùng một bất biến**, mỗi tầng một nguyên
  nhân. Gỡ tầng trên ra không làm tầng dưới hiện lên; nó chỉ đổi câu trả lời từ
  *"không biết"* thành *"không biết, và tôi có nói ra"*.

⛔ **HỆ QUẢ THỰC HÀNH, và nó trái trực giác:** không được thay `check_multiproc.py`
   bằng một lệnh `pytest` *"tương đương"*. Công cụ ấy không phải một lớp bọc — **nó
   là thứ TẠO RA cái CSDL test** mà bộ test đòi. Gọi pytest trực tiếp trông như một
   đường tắt sạch hơn, và nó trả về bảy chữ `s` trong 0,26 giây — **nhanh, xanh, và
   rỗng**.

⭐ **Cách nhìn ra nó:** khi một bước bỏ qua được sửa để *"nói ra"*, đừng dừng ở đó.
   Hỏi tiếp: **nếu tầng này chạy được thật thì tầng dưới có chạy không?** Ở đây câu
   trả lời là không, và chỉ lộ ra vì có người gọi tay tầng dưới một lần.

✅ **Kết cục có hậu, và đáng ghi đủ:** đi đúng đường thì nó chạy — **7 passed /
134,61 s**, lần đầu tiên trên máy này. Đường đó: `setup/chay_voi_env.ps1` nạp
`secrets\app.env` vào riêng tiến trình nó, gọi qua Nexus (LocalSystem đọc được
`secrets\`), và chạy bằng **Scheduled Task** — vì `Start-Process` tách rời từ một
lượt `exec` của Nexus **chết theo phiên**, và nó chết **im lặng**: 40 phút trôi qua
trước khi ai đó đo CPU và thấy không có lấy một `python.exe` nào.

---

⚠️ Bẫy 7, 8, 10, 18, 20 và 21 **chưa có bánh cóc** (Bẫy 17 và 19 đã có, vá 31/08).
Chúng được ghi ở đây vì cả năm đều là
loại chỉ nhận ra khi đã biết trước — và cái giá của việc không biết là một vòng
chẩn đoán đi sai hướng ngay từ câu đầu tiên.

---

## Bẫy 21 — Cache `--lf` có id nhưng **không id nào còn sống**: trạng thái thứ ba

**2026-09-05.** `--vong-lap` tốn **531 giây** thay vì ~15 giây (một phiên khác đo
`113 giây` ở lượt khác). Nhưng nguyên nhân **không** phải cái tôi viết lần đầu.

### ⚠️ Đính chính chính bản ghi đầu tiên của mục này

Tôi viết: *"nguyên nhân là `--lfnf=all`, mặc định của pytest"* và *"`--vong-lap`
chậm ngay sau mỗi lượt xanh"*. **Cả hai đều sai với kho này** — vì tôi đọc dòng
**mô tả** `--lf` trong `gate.py` thay vì đọc **lệnh nó thật sự chạy**:

```
tools/test_nhanh.py --lf --lf-rong-thi-khong-chay
```

Ca *"sau mỗi lượt xanh"* **đã được vá 27/08**: `test_nhanh._doc_lastfailed()`
phân biệt ba trạng thái trên đĩa (vắng mặt / đọc được / đọc hỏng) và có hẳn khối
chú thích kể lại đúng lần hỏng ấy (đo 27/08: 3 phút 35 thay vì 15 giây).

⇒ Tôi mô tả lại một cái bẫy **đã có bánh cóc**, và bỏ sót cái đang cắn. Đúng
hình dạng của cả tài liệu này: đọc một **bản tóm tắt** thay vì đọc thứ thật —
lần này bản tóm tắt là một dòng tài liệu trong chính công cụ.

### Trạng thái thứ ba, đo trên hai cây

| cache `lastfailed` | `--lf` trần | `--lf --lfnf=none` | `--lf-rong-thi-khong-chay` |
|---|---|---|---|
| **vắng mặt / rỗng** | ❌ chạy tất | ✅ deselect tất | ✅ không chạy |
| **có id, TẤT CẢ chết** | ❌ chạy tất | ❌ **chạy tất** | ❌ **chạy tất** |
| có ≥1 id sống | ✅ 1/14 | ✅ 1/14 | ✅ thu hẹp |
| 1 sống + 1 chết | ✅ 1/14 | — | — |

🔑 **Cả hai lớp bảo vệ chỉ đếm "có bao nhiêu id", không hỏi "id nào còn phân giải
được".** Cache có 4 id ⇒ trông như có việc ⇒ truyền xuống pytest ⇒ pytest không
phân giải được cái nào ⇒ chạy toàn bộ, **im lặng**.

⛔ **Đừng rút ra "đổi tên test làm hỏng `--lf`"** — hàng cuối bác điều đó: một id
chết cạnh một id sống thì vẫn thu hẹp. Đổi tên chỉ hại khi nó giết **id sống
cuối cùng**. Và id chết theo cách **lành mạnh**: gỡ một chốt đã hết lý do tồn
tại là việc kho này khuyến khích.

### Vì sao khó thấy

`--lf` nhanh **đúng khi đang đỏ**, và ca hỏng này chỉ hiện khi **mọi** id đỏ cũ
đã biến mất — tức đúng sau một pha dọn dẹp thành công. Nó thưởng cho việc làm
đúng bằng một lượt 9 phút mang tên "15 giây".

### Bản vá: gỡ im lặng, không đổi hành vi

Phiên ASV V4 đã vá ở cây họ (`aa0dce89`):

```
[--lf] N id trong cache va KHONG id nao con phan giai duoc ... se chay TOAN BO
```

⭐ **Không** cho chạy rỗng — một id không phân giải được vẫn có thể là lỗi thu
gom tạm thời, và chính `test_nhanh.py` cảnh báo ở chỗ khác rằng *"chạy rỗng và
chạy hết rồi xanh in ra gần giống nhau"*.

🔑 **Chưa vá ở cây này.** `CLAUDE.md:115` và `gate.py:6,14` vẫn ghi "~15 giây".
