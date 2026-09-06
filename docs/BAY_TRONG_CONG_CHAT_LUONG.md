# Những cái bẫy trong chính cổng chất lượng

**2026-08-25, cập nhật 2026-09-06.** Không phải bẫy trong sản phẩm — bẫy trong
**thứ dùng để chứng minh sản phẩm đúng**. Tất cả đều cùng một hình dạng:

> Một phép kiểm **tồn tại**, nên không ai viết lại nó.
> Nó **không đo thứ nó có vẻ đang đo**, nên nó không cảnh gì cả.
> Và nó báo **PASS**, nên cái PASS đó đọc y hệt một cái PASS thật.

Sáu cái đầu lộ ra trong một ngày, vì trong ngày đó có **hai phiên làm việc song
song trên cùng một cây nguồn** — điều kiện làm mọi giả định "chỉ có một người"
gãy cùng lúc.

⭐ **Bẫy 22–24 đến từ một đêm có BỐN phiên song song** (05→06/09), và chúng khác
ba nhóm trước ở một điểm: không cái nào là bẫy của **một** phiên. Cả bốn phiên
đều đo trước, đều báo nhau, đều tuân luật — và máy vẫn chồng ba lượt gate. Ba
mục ấy được ghép từ phép đo của cả bốn, và mỗi phần ghi rõ nguồn.

⛔ **Tiêu đề tệp này từng là một con số** ("Hai mươi mốt cái bẫy"), và nó đã cũ
đi ngay lần thêm mục kế tiếp — tức nó vướng đúng **Bẫy 1** của chính nó: chốt
**số lượng** thay vì chốt **tập hợp**. Đã bỏ con số khỏi tiêu đề.

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

### 🔴 Một bước bỏ qua ỔN ĐỊNH nguy hiểm hơn một bước bỏ qua THẤT THƯỜNG

*(phiên Mobile V1 đối chiếu hai cây, 06/09)*

Cùng ba bước ấy, ở **cây chính**, chúng **chạy được**:

```
frontend agent-canvas    PASS 14,8s
frontend autosub-studio  PASS  4,1s
frontend prompt-ai-ommi  PASS  4,5s
```

⇒ `BOQUA` ở một worktree là thuộc tính của **cây đó** (thiếu `node_modules`),
**không** phải một giới hạn của kho. `npm ci` ba thư mục là gỡ hẳn.

⚠️ Và đây là chỗ nó thành bẫy: **nguyên nhân bỏ qua không liên quan gì tới nội
dung đang sửa.** Nên ba lượt gate liên tiếp cùng bỏ đúng ba bước ấy là một trạng
thái **ổn định** — và **ổn định là thứ người ta ngừng đọc**. Ngày ai đó chạm vào
`agent-canvas` trên cây ấy, bước phủ nó sẽ **vẫn** bỏ qua, im lặng, đúng lúc nó
cần nói nhất.

🔑 So hai ca cho rõ:

| Ca | Bỏ bước | Vì sao nó sống lâu |
|---|---|---|
| Mobile V1 | **đúng** bước phủ phần vừa sửa (77 phép kiểm) | đập vào mặt ⇒ bị bắt ngay |
| H44 | ba bước **không liên quan** | không đập vào mặt ⇒ **sống lâu hơn** |

⇒ Ghi trong hồ sơ bàn giao của mỗi cây: *"ba bước này bỏ qua vì cây thiếu
bundle, **không phải** vì chúng không áp dụng"* — để người sau không đọc `BOQUA`
thành *"không liên quan"*.

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


---

## Bẫy 22 — `cua_so_yen` chỉ thấy ai **XIN** khoá, và `test_nhanh.py` không xin

**Đo 2026-09-05, 23:30–23:59.** Ba phiên, hai lần suýt reset máy, và cả ba lần
cùng một câu trả lời sai:

```
python tools\cua_so_yen.py trang-thai
RANH - khong tai nguyen nao dang bi giu.
```

...trong khi máy đang chạy một lượt nghiệm thu `demucs + Whisper + NVENC`, hoặc
hai lượt gate đầy đủ.

⛔ **Câu trả lời ấy KHÔNG sai về mặt kỹ thuật.** Nó trả lời đúng câu hỏi của nó —
*"có tệp khoá nào trong `gettempdir()` không"* — và người đọc nghe thành *"máy có
rảnh không"*. Hai câu khác nhau, và chúng khác nhau ở đúng chỗ nguy hiểm.

### Ba đường đi vòng qua khoá, đọc được từ mã

| # | Đường | Dòng |
|---|---|---|
| 1 | **`tools/test_nhanh.py` không lấy khoá — không một dòng nào** | `grep cua_so_yen tools/test_nhanh.py` → rỗng |
| 2 | `python -m pytest` gõ tay: cũng không | — |
| 3 | `gate.py` có đường **chạy KHÔNG khoá, cố ý** | `cua_so_yen.py:298-314` |

Đường 3 đáng đọc kỹ: `CuaSoYen.chay_khong_khoa` — hết `--cho` mà khoá vẫn bị giữ
thì lượt sau **chèn**, chạy tiếp mà **không giữ gì**, chỉ in
`[cua so yen] dang CHEN`. Ngân sách lõi tự tụt bằng phép trừ per-máy nên về lõi
nó không ẩu; nhưng hệ quả là **một lượt gate đang chạy có thể không có tệp khoá
nào cả**.

⇒ Chỉ `gate.py` (dòng 1384, `with CuaSoYen(...)`) xin khoá, và cả nó cũng có
đường không xin. Mọi thứ khác — `test_nhanh.py`, `pytest` trần, `demucs` do
người chạy tay — **vô hình**.

### Một đường xoá khoá của người đang sống — đọc được, CHƯA tái hiện

`thu_giu` (`cua_so_yen.py:165-180`) tạo tệp bằng `O_EXCL` **rỗng**, rồi mới ghi
nội dung. Giữa hai mốc ấy tệp **tồn tại nhưng rỗng**; một lượt khác đọc vào đó
thì `_doc` trả `None`, và nhánh `if cu is None:` **`tep.unlink()` rồi giành
khoá** — tức xoá khoá của một lượt đang sống, không cần `--ep`.

⛔ Cửa sổ tính bằng micro-giây và **chưa ai tái hiện được**. Ghi ở đây vì nó là
đường duy nhất trong mã xoá được khoá không phải của mình mà không ai gọi `nha`.

### Không phải lệch thư mục TEMP — đã đo và loại

Nghi ngờ hợp lý: `dang_giu()` glob `tempfile.gettempdir()`, mà `TEMP` là biến
**của từng tiến trình**, nên hai phiên có thể nhìn hai thư mục. Đo:
`C:\Users\THANGT~1\...\Temp` và `C:\Users\Thang Tuong\...\Temp` là **cùng
một thư mục** (tên 8.3), và cả ba nơi đều 0 tệp khoá. Giả thuyết chết.

### `timeout.exe` tự fork một bản sao — một lượt gate hiện ra BA dòng

⚠️ `timeout.exe` của Git for Windows tạo **hai** tiến trình, cái sau là con của
cái trước, rồi mới exec lệnh con. Cả hai mang **nguyên** cmdline. Đo trên một
lượt `timeout 2400 python tools/gate.py` thật:

```
25128  ppid=21576  timeout.exe 2400 python tools/gate.py
26396  ppid=25128  timeout.exe 2400 python tools/gate.py   <- CON cua 25128
21592  ppid=26396  python.exe   tools/gate.py              <- gate THAT, chi MOT
```

🔴 Ai khớp chuỗi con `gate.py` trong cmdline mà **không lọc `Name='python.exe'`
trước** sẽ đếm ra **hai lượt gate mồ côi** cho một lượt duy nhất. Và "cái mồ
côi" ấy là `timeout.exe` **cha** — giết nó là gỡ mất cái phanh của một lượt đang
chạy, hoặc giết luôn cả lượt.

05/09 một phiên đã đếm kiểu ấy và gần kết luận có một gate vô chủ đang ăn lõi.
Thứ cứu họ là luật *"đừng giết theo một bản tóm tắt"*.

⭐ Lọc `Name == "python.exe"` **rồi mới** khớp cmdline; hoặc dựng cây bằng `ppid`
và chỉ đếm gốc. Và phân biệt cho được **cùng một lượt** với **hai lượt**: hai
`gate.py` khác pid, mỗi cái có `test_nhanh` con riêng và `-n` khác nhau, thì đó
là hai lượt thật — fork của `timeout.exe` chỉ nhân đôi lớp `timeout.exe`.

### Ba phiên báo nhau tử tế, và vẫn chồng lên nhau

Đo **06/09 00:09:31**, lọc `Name='python.exe'` trước nên không có `timeout.exe`
nào lọt vào:

```
00:03:04  ltt-llm-api-http-guide  gate.py            -> test_nhanh.py -n 6 -> pytest
00:04:56  auto-scan-video-v4-mvp  gate.py --phien... -> test_nhanh.py -n 6 -> pytest
00:07:36  mobile-v1               gate.py --vong-lap -> test_nhanh --lf   -> pytest

CPU toan may: 93,2 %      RAM trong: 10,3 GiB
```

Ba lượt × `-n 6` = tới **18 worker trên 10 lõi** — đúng cấu hình đã làm máy
production **reset cứng hai lần** ngày 03/09.

🔴 Và điều đáng học là **không ai làm sai luật**. Cả ba phiên đều đo trước, đều
nhắn trước, đều nhắn lại khi xong. Thứ hỏng là **tin nhắn cũ đi nhanh hơn ta
gõ**:

| Tin | Đúng lúc gõ | Sai lúc đọc |
|---|---|---|
| *"tôi cần một lượt gate, xếp sau bạn"* | ✅ | đọc thành *"nó sắp chạy"* |
| *"gate của BẠN đang chạy, tôi đang nhường"* | ❌ ngay lúc gõ | lượt ấy đã dừng 4 phút trước |
| *"xong tôi nhắn ngay, máy là của bạn"* | ✅ | không ai biết phiên **thứ tư** tồn tại |

⇒ **Một lời NHƯỜNG máy cũng có hạn sử dụng.** Nó chỉ đúng tại thời điểm gõ, và
người **nhận** phải đo lại ngay trước khi bấm — đừng coi nó là một suất đã đặt
chỗ. Đây là dòng 3 của giao ước, áp cho **cả hai đầu** của tin nhắn chứ không
chỉ đầu người gửi.

⛔ Và **không phải** vì thiếu người trong danh sách — tôi đã viết thế và **sai**.

Bản đầu của mục này ghi *"`mobile-v1` không đọc tin của ai"*. Tôi **không đo điều
đó**; tôi suy nó từ việc chính tôi chưa từng nhắn họ. Phiên VIDEO AI đính chính:
họ trao đổi với `mobile-v1` cả tối, và chính `mobile-v1` kiểm chéo hộ đợt đổi tên
`test_700→710` và tìm ra bốn tham chiếu sót trong `docs/NHAT_KY.md`.

🔴 Giao ước có **bốn** người, và bốn người đều báo nhau, và máy **vẫn** chồng ba
lượt. Nên cái hỏng không phải *"thiếu người trong danh sách"* — nếu là thế thì
bản vá sẽ là thêm tên vào danh sách, và bản vá ấy **không sửa được gì**. Cái hỏng
là **độ trễ**: mỗi người bấm dựa trên ảnh chụp của một phút trước.

⭐ Cùng lỗi với thứ mục này đang mô tả, chỉ đổi chiều: tôi **suy từ sự vắng mặt**
trong hộp thư của chính mình rồi phát biểu nó như một sự thật về máy.

### Chồng gate làm nó CHẬM, không làm nó SAI — đo được, 06/09

Câu hỏi thật khi thấy ba lượt chồng nhau không phải *"có nguy hiểm không"* mà
*"nguy hiểm KIỂU GÌ"*. Hai kiểu khác hẳn nhau và cần hai phản ứng khác hẳn:

| Kiểu | Phản ứng đúng |
|---|---|
| làm lượt **SAI** (đỏ giả, timeout, lease hết hạn) | phải dừng, kết quả vô giá trị |
| làm lượt **CHẬM** | chạy nốt — dừng rồi chạy lại làm **tổng tải tăng** |

Đo được, cùng một bước, cùng một cây:

```
490,0s   chay mot minh
613,6s   chay cung HAI luot gate khac   -> cham 25%, va VAN XANH
```

⇒ **Chậm, không sai.** Ba bộ test Python thuần bão hoà CPU thì các lượt chia
nhau lõi; chúng không đầu độc kết quả của nhau.

⛔ Và đây là chỗ phải phân biệt cho đúng với 03/09 — ngày máy **reset cứng hai
lần**. Cấu hình hôm ấy là **12 tiến trình `demucs`, mỗi cái 460–984 % CPU**, tức
mỗi worker pytest tự nở thành một bầy luồng torch (`-n 6` đếm **worker**, không
đếm thứ mỗi worker sinh ra). Gọi ba lượt test Python thuần là *"đúng cấu hình
03/09"* là **nói quá** — và nói quá thì lần sau người ta bỏ qua lời cảnh báo
thật.

🔑 Nên khi thấy chồng lượt, hỏi: **có tiến trình nào NẠP MODEL không?** Đó mới là
biến phân biệt hai kiểu nguy hiểm, chứ không phải số lượt.

⭐ Ngưỡng tự dừng nên đặt **trước khi biết kết quả**. Phiên VIDEO AI đặt "tự dừng
nếu RAM < 6 GiB" lúc RAM còn 9,6 GiB; nó không bao giờ bị chạm. Đặt sau khi nhìn
số thì con số ấy trôi theo điều mình muốn — họ tự nói: *"nếu tôi đặt sau khi
thấy 9,6 thì tôi đã đặt 5"*.

### Kiểm RỒI MỚI chạy — `check && run` biến phép kiểm thành lời bình luận

*(phiên Mobile V1, đo 06/09)*

Họ gọi `cua_so_yen.py trang-thai` **và** phóng lệnh nặng trong **cùng một dòng
shell**. Cảnh báo `[cpu_nhieu] pid 19272 ... 4 phút` in ra **sau khi** quyết định
đã bấm.

🔑 Đây **không** phải một biến thể của *"hãy đo trước"* — nó là lỗi **nhân quả**.
`check && run` trông y hệt một quy trình đúng; thứ hỏng là **thời điểm câu trả
lời tới nơi**, không phải tính trung thực của nó. Cùng gốc với mọi thứ trong bẫy
này.

⇒ Hai lệnh **tách rời**, đọc kết quả giữa chừng. Gộp một dòng thì phép kiểm biến
thành lời bình luận.

### RSS trả lời được câu "tiến trình này có NẠP MODEL không"

*(phiên VIDEO AI, đo 06/09; H44 xác nhận một mẫu độc lập)*

Biến phân biệt hai kiểu nguy hiểm là *"có nạp model không"*, nhưng câu ấy khó hỏi
trực tiếp. `p.memory_info().rss` trả lời được:

**Cách đo — và cách đo SAI đã lừa cả hai phiên:**

⛔ Đừng lọc theo cmdline. `pytest-xdist` sinh worker qua `execnet`, và cmdline
của chúng **không chứa chữ `pytest`**. Lấy **cây con của `gate.py`** bằng
`children(recursive=True)`.

Đo đỉnh một lượt gate thật (06/09 00:49:20, phiên VIDEO AI) — **10 tiến trình,
tổng RSS 0,94 GiB**:

```
0,359 GiB   tien trinh lon nhat trong cay
0,119 / 0,119 / 0,115 / 0,099 GiB
0,051 / 0,050 GiB
0,022 GiB   gate.py
0,005 / 0,005 GiB
─────────
0,94 GiB    TONG mot luot gate
   tinh bang GiB (mot tien trinh)   neu da nap torch + mot model that
```

🔴 **Ba con số từng trao đổi giữa hai phiên đều SAI, và đây là bản đo thay
chúng:** một lượt gate là **0,94 GiB** chứ không phải ~0,6 (phép nhân
`6 × 0,1` thiếu **1,6 lần**, vì đếm sai cả **số** tiến trình — 10 chứ không phải
6 — lẫn **cỡ**); và tiến trình lớn nhất là **0,359 GiB**, không phải 0,10 —
mẫu 0,08–0,10 mà cả hai phiên lấy là **tiến trình điều phối**, và nó **không**
phải cái to nhất trong cây.

⭐ **Nhưng kết luận sống sót, và nó sống sót vì đúng lý do làm biến này dùng
được:** khoảng cách tới một tiến trình đã nạp torch + model thật vẫn là **một
bậc độ lớn** (0,36 GiB so với hàng GiB). **Một phép đo sai 3,5 lần vẫn không lật
được kết luận** — đó là dấu hiệu của một ngưỡng chọn đúng chỗ.

⇒ Chênh **một bậc độ lớn**, nên ngưỡng không cần chính xác — và đó là điều làm nó
dùng được.

⭐ RSS hơn hai cách đoán kia ở chỗ nó đo **thứ đã thực sự được nạp**: nó miễn
nhiễm với `-n` (đếm worker, không đếm bầy luồng mỗi worker sinh) **và** với tên
tệp test (một tên vô hại vẫn có thể `import torch`).

### 🔑 MỘT KHOẢNG LẶNG KHÔNG PHẢI GIẤY PHÉP

*(phiên Mobile V1 đúc, 06/09, từ một lần H44 **không** bấm)*

Đo 09:18:31, đếm mọi tiến trình (không chỉ `python`), CPU tích luỹ ≥ 5s:

```
CPU 7,2 %  |  RAM trong 18,5 GiB  |  cay ASV: 0 tien trinh
RSS lon nhat toan may: 0,16 GiB   <- bac pytest thuan, khong phai torch
```

Số ấy **nói thật**. Nhưng một khoảng lặng có **ba** nguyên nhân trông y hệt nhau:

| | Nguyên nhân | Hệ quả nếu ta bấm |
|---|---|---|
| 1 | lượt kia đang **chờ máy B** | tải bung lên **sau** khi ta đã cam kết |
| 2 | lượt kia đã **chết** | máy thật sự rảnh — **chỉ ca này là giấy phép** |
| 3 | lượt kia **chưa bắt đầu** | rảnh bây giờ, bận một phút nữa |

🔴 Ca 1 tệ nhất: dừng **sau khi đã bấm** đắt hơn hẳn không bấm — lượt bị bỏ dở
phải chạy lại, nên tổng tải **tăng**.

⇒ Cùng hình dạng đếm cả đêm — *một số 0 không phân biệt được hai nguyên nhân* —
nhưng ở một trục mới: **thứ hết hạn không phải một CON SỐ, mà là SỰ IM LẶNG.**

⭐ Và phần khó không phải biết luật, mà là: **có số đo ủng hộ việc bấm và vẫn
không bấm**, vì hỏi *"số này trả lời được câu nào"* thay vì *"số này có đẹp
không"*. Một phiên khác cùng sáng ấy bấm gate khi còn 11 tiến trình ở hai cây
khác, và tự biện minh bằng chính phép đo 490s→613s.

### ⛔ "KHẨN" cũng bị lạm phát — và bản vá là một ĐỘNG TÁC

06/09, H44 gọi việc *"trang `/gia-api` hứa sai"* là **thiệt hại đang xảy ra**,
nghe ngang hạng một lỗi thu tiền. Phân biệt đúng:

| | |
|---|---|
| tiền thu sai | **không** xảy ra — C3 thu đúng từ 08:53 |
| trang tài liệu hứa sai | có, phải sửa, nhưng **không ai mất tiền** |

Và chiều lệch còn nghiêng về phía khách: trang hứa *"tối thiểu 1 credit"* trong
khi ta thu **ít hơn** thế.

🔴 Chưa đầy **mười tiếng** trước đó, chính H44 viết vào tệp này rằng *"nói quá
thì lần sau người ta bỏ qua lời cảnh báo thật"*, sau khi gọi ba lượt gate chồng
nhau là *"đúng cấu hình 03/09"*. Cùng người, cùng lỗi, trục khác: lần đầu lạm
phát **mức nguy hiểm**, lần sau lạm phát **mức khẩn**.

⇒ Nên bản vá **không** phải *"nhớ kỹ hơn"* — tri thức đã có và vẫn thua. Nó phải
là một **động tác**:

> Trước khi gọi thứ gì là **khẩn**, viết ra: **AI mất GÌ, trong BAO LÂU, nếu
> chờ thêm một giờ.** Không điền được cả ba ô ⇒ **nó không khẩn.**

⭐ Cùng khuôn với bản vá CRLF (*đọc kiểu hiện có rồi ép theo nó trong cùng một
thao tác ghi*): cả hai đổi **cái tay làm**, không thêm một dòng cho **cái đầu
nhớ**.

### 🔴 ĐẾM trả lời "AI"; chỉ CPU TÍCH LUỸ trả lời "CÓ ĐANG LÀM VIỆC KHÔNG"

*(phiên ASV nêu 06/09, từ một phép đo của H44)*

Bậc 3 (đếm mọi `python` theo `cwd`) sửa được chuyện *đếm thiếu / đếm thừa*. Nó
**không** sửa được chuyện phân biệt **bận** với **đông cứng**:

```
chatltt-v3-agentic   7 tien trinh /   30 giay CPU trong 22-46 phut  -> RAC
CAY-CHINH           10 tien trinh / 1842 giay CPU trong  6 phut     -> DANG CAY
```

⇒ Hai con số **7 và 10 gần như nhau**, hai kết luận **ngược nhau**. Không có cột
CPU tích luỹ thì cả hai đọc thành *"cây kia đang bận"*.

🔴 **Và hệ quả lệch về phía nguy hiểm theo một chiều rất khó thấy.** Phiên ASV
**chờ 8 phút** một phần vì 6–7 tiến trình `chatltt` mà H44 vừa chứng minh là
**xác chết** — cặn của ba lượt `check_multiproc`.

⛔ Cái giá của lỗi này là **thời gian không xảy ra chuyện gì**, nên nó **không
để lại dấu vết nào**: không ai đỏ, không ai treo, không ai than. Mọi phiên sẽ
nhường nhầm, **đều đặn**, và không ai biết.

⭐ Cùng cơ chế với *"lỗi không phạt người gây ra là lỗi sống rất dai"* — chỉ
khác: ở đây **không ai** bị phạt cả, kể cả người sau. Đó là loại lỗi bền nhất.

⇒ Bậc 3 đủ **ba** cột, không phải một: **cây · số tiến trình · CPU tích luỹ**.
Và đọc CPU **tích luỹ** chứ không phải một mẫu `cpu_percent` — một lượt đang chờ
I/O đo ra 0 %, còn một xác chết cũng đo ra 0 %.

### Bậc 5 — KẾT NỐI TCP phân biệt "đang chờ" với "đã chết"

*(phiên ASV, 06/09)*

CPU tích luỹ (bậc 3) phân biệt được **đang cày** với **xác chết**. Nó **không**
phân biệt được **đang chờ mạng** với **đã chết** — cả hai đều 0 %.

```
ESTABLISHED -> 192.168.2.66:8299     <- dang SINH CHU tren may B, khong treo
khong ket noi nao                    <- da chet, hoac chua bat dau
```

⇒ Năm bậc, mỗi bậc trả một câu **khác**:

| Bậc | Trả lời |
|---|---|
| 1 khớp cmdline | *"có tên công cụ nào không"* — đếm **thừa** (`timeout.exe`) |
| 2 cây con | *"cây con của gốc nào"* — đếm **thiếu** (mồ côi rơi khỏi cây) |
| 3 `cwd` + CPU tích luỹ | *"cây nào, và có cày không"* |
| 4 nhật ký quyết định | *"nó **định** làm gì"* (`hoan_s=None` = chưa từng hoãn) |
| **5 kết nối TCP** | *"nó đang **chờ ai**"* |

⛔ Và không bậc nào thấy được **deploy** — PowerShell chép tệp, không tiến trình
mang tên công cụ nào, không kết nối nào. Kênh duy nhất là tệp `.ket.txt` của
chính nó, tức lại là bậc 4.

⭐ Bài học chung: **mỗi bậc trả lời một câu hẹp, và không bậc nào là "phép đo
đúng"** — thứ sai là hỏi một bậc câu của bậc khác.

### 🔑 `cmdline` nói dối theo CẢ HAI chiều — trong cùng một đêm

Đây là lần thứ **hai** một phép lọc theo cmdline lừa được cả nhóm, và hai lần
lệch **ngược nhau**:

| Cơ chế | Sai chiều nào | Hậu quả suýt xảy ra |
|---|---|---|
| `timeout.exe` tự fork một bản sao | đếm **THỪA** — 3 dòng cho 1 lượt gate | giết "gate mồ côi", tức giết cái phanh của lượt đang chạy |
| `execnet` không mang chữ `pytest` | đếm **THIẾU** — bỏ sót mọi worker | báo "worker chỉ 0,1 GiB" trong khi cái to nhất là 0,36 |

⇒ Cùng một nguyên nhân: **`cmdline` là thứ ĐẠI DIỆN; cây tiến trình là thứ
THẬT.** Hỏi bằng `ppid` / `children(recursive=True)`, đừng hỏi bằng chuỗi.

⛔ Và con số `3 × 6 × 0,1 = 1,8 GiB` từng được trao đổi giữa hai phiên là một
**phép nhân**, không phải phép đo. Việc nó "khớp" với RAM tụt 0,9 GiB rồi hồi là
một **sự phù hợp** — đúng thứ [[gia-thuyet-khop-qua-vua-ket-thuc-dieu-tra]] cảnh
báo: một con số khớp làm người ta **thôi đo**.

### 🔴 Khe giữa ĐO và BẤM không có đáy — nên nhắn tin không phải cơ chế loại trừ

Đo 06/09: hai phiên bấm gate cách nhau **25 giây**, và **cả hai đều vừa đo thấy
máy trống**. Không ai sai, không ai bỏ bước.

⛔ Dù nhắn nhanh tới đâu, khoảng thời gian giữa *đo* và *bấm* của hai người vẫn
có thể chồng. **25 giây chỉ là con số gặp phải tối nay; nó có thể là 2 giây.**
Suốt buổi, bốn phiên dùng tin nhắn **như thể** nó là một cơ chế loại trừ lẫn
nhau. Nó không phải, và không thể trở thành.

⇒ Thứ duy nhất đóng được khe ấy là **một cái khoá lấy trước khi chạy**. Mà lượt
nặng nhất trên máy này — `tools/test_nhanh.py` — **không xin khoá dòng nào**.

### ✅ ĐÃ LÀM 06/09 — chủ dự án duyệt, phiên Mobile V1 thi hành ở cây chính

Bản vá gồm **ba nửa**, và nửa thứ nhất là nửa không ai nghĩ tới:

```
tools/cua_so_yen.py   + phien_nay_dang_giu()  -> khoa TAI NHAP theo PHIEN
tools/gate.py         + os.environ["LTT_PHIEN"] = phien   (truyen xuong con)
tools/test_nhanh.py   + with CuaSoYen(...)    -> gio no CO xin khoa
```

🔴 **Bản vá ngây thơ — chỉ cho `test_nhanh` xin khoá — không vô ích, nó TÁI TẠO
ĐÚNG TAI NẠN CŨ.** `gate.py` gọi `test_nhanh.py`, nên nếu khoá không tái nhập
thì lượt con **đợi hết `--cho` (mặc định 15 phút) ở BỐN chỗ** rồi chạy chèn. Đo
bằng cách tiêm lại hành vi cũ:

```
ban MOI (long nhau)         doi 0,0s   dang_chen=False
ban CU  (khong biet long)   doi 3,0s   dang_chen=True
```

⛔ Và triệu chứng **không** phải *"khoá chết"* — nó là **"gate treo ở bước
`bo test`"**. Đúng cái triệu chứng đã khiến một phiên đi **giết worker của một
lượt đang chạy** ngày 05/09 (xem dòng 4 của giao ước). Một bản vá cho vấn đề
điều phối, làm sai, sẽ đẻ ra lại chính tai nạn điều phối nó định chữa.

⚠️ **Hệ quả vận hành sau khi ff:** `tools/test_nhanh.py` nay **xin khoá thật** —
gõ tay nó lúc máy bận sẽ **xếp hàng** thay vì chạy ngay. Có `--khong-khoa` khi
chắc máy rảnh, và `--cho <phút>` (mặc định 15).

⭐ Kiểm bằng **ba** phép kiểm đã chứng minh đỏ được (tiêm bản cũ, khôi phục khớp
byte) **cộng một đối chứng dương** — không có nó thì phép kiểm lồng-nhau vẫn
xanh khi khoá hỏng theo kiểu *"không bao giờ đợi ai"*. Đúng luật Bẫy 24.
`tests/test_361_cua_so_yen.py`: **19 passed**.

### 💡 Đề xuất ban đầu, giữ lại vì nó ghi một ranh giới

*(phiên VIDEO AI nêu; H44 ghi lại, KHÔNG tự thi hành)*

Bản vá một lớp lỗi mà bốn phiên đã trả tiền suốt một buổi tối: bọc thân
`test_nhanh.py` trong `CuaSoYen` y như `gate.py:1384` đang làm.

⛔ **Cố ý chưa làm, và lý do nên nằm bằng chữ:**

1. `tools/` là **hạ tầng dùng chung**, ngoài ranh giới của bất kỳ chương trình
   ứng dụng nào. `CLAUDE.md` yêu cầu dừng lại và nói rõ vì sao trước khi sửa nền
   tảng — đây là chỗ dừng.
2. **Mỗi worktree chạy một bản `tools/` riêng.** Sửa ở một cây thì bốn cây kia
   không đổi, nên nó **không** giải quyết vấn đề chung mà chỉ đẻ ra phân kỳ —
   đúng cơ chế đã ghi ở `~/.claude/CLAUDE.md` (bốn cây cũ vẫn `-n 14` trong khi
   `auto` = 10).
3. Một phiên khác **đề nghị** không phải một phiên khác **cho phép**.

⇒ Việc này thuộc về chủ dự án hoặc phiên giữ `tools/`. Ghi ở đây để nó không
biến mất cùng cửa sổ chat đã tìm ra nó.

⭐ **Và đường đi ấy đã chạy đúng như thế.** Ba phiên lần lượt từ chối tự thi hành
— mỗi phiên áp cùng một lý do cho **chính mình** — rồi đặt nó trước mặt chủ dự
án **kèm vật liệu** (hai phát hiện làm bản vá nhỏ đi: `_treo()`/`_con_song()` đã
viết đúng cho Windows, và khoá đánh theo **phiên** nên chỉ cần kế thừa biến
`phien` của tiến trình cha). Chủ dự án duyệt; phiên đứng ở **trunk** thi hành.

🔑 Ba phiên dựng gần trọn một bản vá mà **không phiên nào có quyền đóng nó**, và
việc đó không bế tắc — vì thứ chuyển giao không phải một yêu cầu, mà là **một
quyết định đã được chuẩn bị đủ để người có quyền chỉ cần nói có hoặc không**.

### 🔴 Hai chuẩn: lọc cứng cho CÂY MÌNH, liếc bảng cho CÂY NGƯỜI

*(phiên VIDEO AI tự chẩn, 06/09 — cùng một người, cùng một phút)*

Họ báo **ba** tiến trình mồ côi ở cây H44. Đo đúng thì **hai**: cái thứ ba có cha
`bash.exe` còn sống, và nó là một **bộ lấy mẫu đang chạy có chủ đích**.

Chỗ đáng ghi không phải con số sai, mà là **cùng một người áp hai chuẩn trong
cùng một phút**:

| | Cây của mình | Cây của người |
|---|---|---|
| cách lọc | ba tầng **cứng trong mã**: `cwd` + cha `NoSuchProcess` + cmdline | *"CPU thấp + tuổi cao"*, liếc bảng rồi gõ |

⛔ Và chỉ số phân biệt — **cha còn sống không** — chính là chỉ số họ **dặn người
kia dùng trong cùng tin nhắn ấy**. Phương pháp đúng đã được viết ra; nó chỉ không
được áp cho phần mình không phải chịu hậu quả.

🔑 Vì sao nó lọt: cả ba tiến trình trông **y hệt nhau ở hai chỉ số dễ đo nhất**
(CPU thấp, tuổi cao). Một phép lọc rẻ đủ dùng cho việc của mình — nơi mình biết
mình vừa chạy gì — nhưng **không** đủ cho cây người, nơi mình không có ngữ cảnh
ấy. Thiếu ngữ cảnh đòi **nhiều** chứng cứ hơn, không phải ít hơn.

⇒ **Báo cáo về cây người khác phải chặt hơn báo cáo về cây mình**, chứ không lỏng
hơn. Nếu không thì hậu quả rơi vào người không có dữ liệu để phản biện.

⭐ Ở ca này cái sai dừng ở **một dòng báo cáo** thay vì thành một hành động — và
dừng vì người nhận **đo lại trước khi dừng**, không vì người gửi cẩn thận. Đó là
lý do dòng 4 của giao ước nằm ở phía **người hành động**, không ở phía người báo.

### 🔑 Luật khái quát: CÁI TÊN đi xa hơn dòng chữ

*(phiên Mobile V1 đúc, 06/09 — và nó gom được cả bốn ca của đêm)*

Mỗi công cụ ở đây đều **nói thật**, và mỗi công cụ đều có một **cái tên hứa rộng
hơn thứ nó đo**. Dòng chữ đính kèm thì đúng, nhưng **cái tên là thứ người ta
nhớ**:

| Cái tên hứa | Thứ công cụ thật sự đo | Ai đọc nhầm |
|---|---|---|
| `cua_so_yen trang-thai` → *"máy có rảnh không"* | có **tệp khoá** nào không | 3 phiên, 3 lần |
| `--vong-lap` → *"15 giây"* | `--lf`, và **chạy toàn bộ** khi cache toàn id chết | H44, 300+ giây |
| `master` → *"nhánh chính"* | một nhãn đi **sau trunk 125 commit**; bản đang phục vụ khách **không nằm trên nó** | VIDEO AI |
| `RESULT: PASS` | PASS **của những bước đã chạy** | Mobile V1, 77 phép kiểm frontend |

⭐ Cả bốn đều **có** một dòng chữ nói đúng ngay cạnh: `--vong-lap` in thẳng rằng
nó không phải bằng chứng; `RESULT` in thẳng tên bước bỏ qua. **Dòng chữ thua cái
tên**, vì cái tên là thứ đi vào câu nói và vào trí nhớ.

⇒ **Chỗ nào cái tên hứa rộng hơn thứ công cụ đo được, chỗ đó sẽ có người đọc
nhầm — và người đọc nhầm sẽ là ta, vào lúc mệt.**

#### Và thứ hứa quá nhiều không phải lúc nào cũng là một cái TÊN

`returncode` cũng vậy, và nó lừa được **cả hai phiên trong cùng một giờ** — dù
đó đúng là kênh ta vừa khuyên nhau dùng thay cho việc khớp mẫu stdout.

Console của công cụ Bash trên máy này là **cp1252**. Một `print` chứa emoji hay
tiếng Việt có dấu ném `UnicodeEncodeError` ⇒ **`returncode=1`**, trong khi
**việc thật đã xong**:

| Ca | Việc thật | `returncode` |
|---|---|---|
| H44, script tiêm `con_cho_job` | đo xong, đã kết luận, đã khôi phục **khớp từng byte** | **1** (chết ở dòng in `✅`) |
| Mobile V1, lệnh ghi bộ nhớ | ghi **3 tệp thành công** | **1** (chết ở `print` cuối) |

🔴 Ca thứ hai nguy hiểm hơn: đọc mã trả về rồi kết luận *"ghi hỏng"* dẫn tới
**ghi đè lại một tệp đã đúng**.

🔑 `returncode` **gộp** *"việc hỏng"* với *"báo cáo hỏng"* thành **cùng một số**.
Nó vẫn hơn hẳn khớp mẫu stdout — nhưng nó không phải một kênh sạch, nó là một
kênh **hẹp hơn**, và ta lại đang đọc nó rộng hơn thứ nó đo.

⇒ Bản vá có **hai** vế, và **thứ tự này là cố ý**:

**1. Đặt mọi `print` SAU khi việc đã xong.** Không cần thư viện, không đổi trạng
thái toàn cục, **không có ngoại lệ** — nó chỉ là *thứ tự*. Tầng báo cáo chết thì
nó không kéo theo mã trả về của tầng làm việc.

**2.** *(chỉ trong script dùng một lần)* ép luồng ra về UTF-8:

```python
import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
```

⚠️ Vế 2 **có bẫy riêng đã trả giá ở kho này**: một công cụ trong `tools/` đổi
`sys.stdout` thành `TextIOWrapper` làm **vỡ pytest**, vì bản gốc bị thu gom rác
và đóng luôn buffer thật. Đừng nhét nó vào công cụ dùng chung.

🔑 **Và thứ tự hai vế là một bài học riêng.** Bản đầu của mục này kê vế 2 trước —
tức đặt một lời khuyên **có ngoại lệ** trước một lời khuyên **không ngoại lệ**.
Người đọc vội lấy cái đầu tiên, nên cách kê ấy phát cái nguy hiểm hơn cho đúng
người ít thời gian nhất. *(phiên Mobile V1 chỉ ra)*

### Phân loại một phép đọc sai: nó GỢI RA HÀNH ĐỘNG GÌ?

Hai ca `returncode` ở trên có **cùng** một sai số, và khác nhau ở hệ quả:

| Ca | Phép đọc sai dẫn tới |
|---|---|
| H44 — script tiêm | **kết luận sai** (*"script thất bại"* trong khi nó thành công). Mất công, dừng ở đó |
| Mobile V1 — lệnh ghi bộ nhớ | **hành động phá hoại**: *"ghi hỏng"* là một lời mời **ghi lại**, và lần ghi lại đè lên một tệp **đã đúng** |

🔑 Nên câu phân loại đáng nhớ không phải *"đọc sai nặng hay nhẹ"* mà **"phép đọc
sai ấy gợi ra hành động gì?"** Cùng một sai số, nếu nó đẩy về phía **hành động**
thì nó thuộc nhóm đắt nhất.

⇒ Cùng họ với luật đã có của kho: **một phép đo lệch chiều thì phải BỎ, không
phải SỬA** — vì sai số đẩy về phía hành động không có bản vá nào cứu được.

### Luật

🔑 **`cua_so_yen trang-thai` là điều kiện CẦN, không đủ. Vế quyết định là CÂY
TIẾN TRÌNH.** Trước lệnh nặng phải hỏi cả hai, và vế thứ hai mới có quyền phủ
quyết.

⚠️ Và đọc cây tiến trình cũng có hai cách đọc sai — cả hai xảy ra thật tối 05/09:

| Đọc | Vì sao lừa được |
|---|---|
| `cpu_percent()` một nhát | mẫu **tức thời**: không phân biệt "đã chết" với "đang chờ I/O". Một lượt nghiệm thu đang chạy đo ra **0,0 %** |
| `create_time` in ra `23:41:22` | **không có ngày** — người đọc tự điền, và điền thành "đêm qua". Nó là 15 phút trước |

⇒ In `create_time` **kèm ngày**, và dùng `cpu_times()` **tích luỹ** thay vì lấy
một mẫu. Hai thứ này đã làm một phiên kết luận "máy rảnh" rồi bấm gate chồng lên
lượt nghiệm thu của phiên khác — lượt mà phiên kia **đã báo trước 15 phút**.

⭐ Cùng họ với Bẫy 17 và Bẫy 21: một công cụ trả lời **thành thật** cho câu hỏi
hẹp của nó, và cái hỏng nằm ở khoảng cách giữa câu hỏi ấy với câu ta đang hỏi.


---

## Bẫy 23 — Kết dòng: bánh cóc bảo vệ CÂY LÀM VIỆC, không bảo vệ LỊCH SỬ

**Và khi lịch sử sai thì nó quay ra cản bản sửa.**

`tools/gate.py:530` **có** bước `kieu xuong dong` → `tools/check_xuong_dong.py`.

⛔ Bản đầu của tài liệu này viết ngược lại — *"gate không có bước kiểm kết dòng
nào"* — và đã bị commit hai lần. Nguyên nhân: `grep gate.py` bằng **tên hiện
tượng** (`crlf`, `ket dong`) chứ không bằng **tên bước** (`xuong_dong`).

🔑 Một `grep` không thấy chỉ chứng minh **chuỗi ấy** không có. Nó **không** chứng
minh **năng lực ấy** không có. Câu này áp được cho cả `test_453` (bánh cóc mồ
côi tìm người gọi bằng AST — một năng lực gọi qua chuỗi hay `getattr` sẽ vô hình
y hệt).

### Lưới ấy căng ở đâu

`check_xuong_dong.py` soi tệp **đang sửa** (`git status --porcelain`), so **kiểu
thuần** (LF/CRLF/trộn) với bản ở `HEAD`, bỏ qua tệp mới và tệp nhị phân. Luật của
nó **không** phải *"cả kho dùng LF"* mà *"khớp đúng thứ git đang giữ cho từng
tệp"* — vì vài tệp **vốn là CRLF** (`DEVELOPER_GUIDE.md` do công cụ sinh,
`i18n_baseline.json`), ép chúng về LF là mở một vòng lặp không ai thắng.

⇒ Nó bắt **cú lật kết dòng trong cây làm việc**. Nó **không** thấy nội dung đã
được **commit** kèm CRLF — lúc ấy `git status` sạch, không có gì để so.

🔴 **Hai phiên cùng lọt qua đúng khe đó trong một đêm** (H44: 17 tệp docs rồi 3
tệp mã; ASV: 4 tệp) — cùng một cách: **commit trong cùng nhịp với lúc ghi**, nên
không bao giờ đi qua lưới. Không phải lưới thủng; là ta bước qua trước khi lưới
được căng.

### Đo hậu quả bằng số, không bằng cảm giác

Cách đo: `git diff --numstat` so với `git diff --ignore-cr-at-eol --numstat`.

| tệp | ở BASE | diff thô | thật | **nhiễu** |
|---|---|---|---|---|
| `apps/chatltt/services/tao_media.py` | **LF** | 703 | 111 | **592** |
| `luot_v3.py`, `test_819.py` | (mới) | — | — | 0 |

Cùng ca với hai lần trước mà docstring đã ghi: 26/08 `messages.po` lệch **10.465
dòng**; 30/08 **25 tệp**, trong đó `CLAUDE.md` hiện **919 dòng đổi cho 1 dòng
thật**.

### 🔴 Công cụ CHỐNG LẠI bản sửa

Sau khi trả ba tệp về LF, `check_xuong_dong.py` ra **`RESULT: FAIL`**:

```
tao_media.py   HEAD=CRLF -> hien tai=LF   (thay doi THAT: 0 dong)
```

Vì nó neo vào `HEAD`, mà `HEAD` đang giữ bản sai. ⇒ **Một khi kết dòng hỏng đã
commit, cái bánh cóc trở thành lực cản.**

⭐ Nhưng chính nó cũng in ra bằng chứng bản sửa an toàn: **"thay đổi THẬT: 0
dòng"**. Đổi kết dòng không chạm một ký tự nội dung nào. Commit xong thì nó `PASS`
lại — nên đường đi đúng là **sửa và commit trong một nhịp**, đừng chạy gate ở
giữa.

### Hai nguồn sinh CRLF, và bản vá cho cái này không chữa cái kia

⛔ **Bản đầu của mục này đổ tội cho công cụ `Write`, và ĐÓ LÀ MỘT CHẨN ĐOÁN
CHƯA ĐO.** Tôi suy nó ra: `test_819.py` do `Write` tạo, tệp ấy CRLF ⇒ `Write`
sinh CRLF. Phiên Mobile V1 chất vấn, và phép đo bác bỏ:

```
Write tao tep MOI          ->  b'dong mot\ndong hai\ndong ba\n'   CRLF 0
Write GHI DE len tep CRLF  ->  b'moi mot\nmoi hai\n'              CRLF 0
write_text len tep LF      ->  b'X\r\ny\r\n'                      <- thu pham THAT
```

`test_819.py` thành CRLF vì sau khi `Write` tạo nó, tôi sửa nó **hai lần bằng
`pathlib.write_text`**. Thủ phạm chỉ có một, và nó là cái đã biết từ đầu.

| Nguồn | Kết dòng sinh ra | Bản vá |
|---|---|---|
| `pathlib.write_text` (mặc định `newline=None`) | 🔴 **CRLF** | `write_bytes(s.encode())`, hoặc `newline="\n"` (Python ≥ 3.10) |
| Công cụ `Write` của harness | ⚠️ **cưỡng chế LF** | xem cảnh báo dưới |
| Công cụ `Edit` của harness | ✅ **giữ nguyên** | — |
| `sed -i` trong Git Bash | ✅ LF | — |

⚠️ **`Write` cưỡng chế LF, và nó không hỏi ai.** Với ~90 % tệp trong kho thì đó
là thứ ta muốn. Nhưng vài tệp **vốn là CRLF trong git** — `DEVELOPER_GUIDE.md`
(công cụ sinh ra), `i18n_baseline.json` — và `Write` lên chúng là **lật ngược
chúng, im lặng**. Nên câu đúng không phải *"`Write` không bảo vệ gì"* mà:
**`Write` an toàn cho tệp LF và nguy hiểm cho đúng những tệp phải giữ CRLF.**

⭐ **Hai dòng cuối bảng là lối thoát rẻ nhất, và đều đo được:**
`bo_chay_tool.py` từng là CRLF (ghi bằng `write_text`) rồi **tự lành** khi tôi
chạy một `sed -i` sửa lỗi chính tả. Và một `Edit` vào `CLAUDE.md` (299 dòng LF)
để lại **0 CRLF**.

⇒ **Sửa tệp có sẵn thì dùng `Edit`, đừng đọc-sửa-ghi-đè cả tệp.** Nó tránh cùng
lúc **ba** thứ: lật kết dòng · cắt trắng tệp khi phép mã hoá vỡ · và một diff
toàn tệp. Chỉ dùng `Write`/`write_bytes` cho tệp **mới**, rồi đo lại bằng byte.

### 🔑 Và cách cái sai này sống được là bài học riêng của nó

Chẩn đoán sai (**`Write`**) nhưng lời khuyên kèm theo đúng (*"đo lại bằng
byte"*), nên **không có gì đỏ để lộ nó ra**. Phiên Mobile V1 vừa bị đúng thế ở
một mục khác: họ viết *"heredoc nuốt backslash"*, đo lại thì thủ phạm là đường
truyền `command` của công cụ Bash — **chẩn đoán sai, lời khuyên vẫn đúng, nên nó
sống ba tuần**.

⇒ Một mục tài liệu nêu **nguyên nhân** thì phải kèm **phép đo tái hiện được**,
đúng như mọi mục khác trong tệp này. Nếu chỉ có lời khuyên mà chưa có phép đo,
ghi thẳng **"CHƯA ĐO ĐƯỢC"** — cùng luật với Bẫy 24.

⚠️ Ghi chú cũ khuyên *"dùng `Write` thay heredoc"* để tránh bẫy nuốt backslash.
**Đúng cho bẫy đó, và không bảo vệ gì trước kết dòng.** Hai bẫy khác nhau; một
bản vá không chữa được cả hai.

### Vì sao có tài liệu mà vẫn dính — trục CƠ CHẾ và trục THÓI QUEN

*(phiên ASV)*

Cả memory lẫn docstring đều nằm ở trục **"cơ chế"**: chúng trả lời *"chuyện gì đã
xảy ra"*. Thứ thiếu nằm ở trục **"thói quen kiểm"** — nhìn *nội dung* tệp sau mỗi
lần ghi, chưa bao giờ nhìn *byte*.

🔑 **Bài học nằm đúng chỗ mà vẫn không chặn được, vì nó không nằm trong động
tác.** Hai phiên, cùng một tài liệu, cùng một đêm, cùng dính — trong đó một phiên
đã **trích dẫn chính docstring ấy** cho phiên kia rồi vẫn viết như thể vừa phát
hiện.

⇒ Bản vá dùng được không phải "ghi thêm một mục" (đã có ba mục) mà là **đổi động
tác mặc định** thành bốn dòng:

```python
data = s.encode("utf-8")                    # ma hoa TRUOC khi cham tep
assert b"\r\n" not in data                  # kiem TRUOC
p.write_bytes(data)                         # ghi
assert p.read_bytes() == data               # do lai bang BYTE
```

Ba trong bốn dòng ấy sửa **ba lỗi khác nhau** đã gặp: kết dòng · tệp bị cắt trắng
khi phép mã hoá vỡ · `read_text` dịch ngược nên không kiểm được phép ghi.


---

## Bẫy 24 — Một kết quả ÂM không có đối chứng trông giống một PHÁT HIỆN

*(phiên Mobile V1, 06/09)*

Họ kéo bằng cảm ứng trên canvas React Flow. **Không pan.** Kết luận:
*"`panOnDrag` dạng mảng chặn cảm ứng"* — kèm một lý thuyết đẹp đọc được trong mã
`@xyflow/system`.

Canvas đang **rỗng**. Chuột trái cũng không pan. Chuột giữa cũng không. **Ba đầu
vào, ba số 0** — không phải vì đầu vào bị chặn, mà vì **không có gì để dịch
chuyển**. Sau khi gieo 2 nút, cảm ứng pan được ngay.

🔴 **Chỗ nguy hiểm hơn mọi bẫy khác trong tệp này:** một kết quả âm **không trông
giống một giới hạn** — nó trông giống một **thành quả**. *"Tôi tìm ra một lỗi
mobile"* có hình dạng của việc đã làm được, nên nó đi thẳng vào báo cáo và không
ai chất vấn. Các bẫy khác gây khó chịu khi đọc lại; cái này đọc lại thấy **hài
lòng**.

### Luật

⇒ Trước khi ghi một kết quả âm thành phát hiện, hỏi: **"điều kiện nào ĐÁNG LẼ
phải cho kết quả DƯƠNG ở đây?"** rồi chạy đúng điều kiện đó.

Không nghĩ ra được một điều kiện như thế ⇒ **phép đo không phân biệt được**, và
số 0 chưa nói gì. Lúc ấy ghi **"CHƯA ĐO ĐƯỢC"**, đừng ghi "không có lỗi".

### Cùng luật, áp cho PHÉP KIỂM

`test_819::test_nguoi_KHAC_khong_thay_buoc_cho_job` chỉ khẳng định
`con_cho_job(user_id="u-nguoi-la") is False`. Nó **vẫn xanh** nếu `con_cho_job`
hỏng và luôn trả `False` — không phân biệt được *"chặn đúng người lạ"* với
*"chặn tất cả"*. Đối chứng dương **có** tồn tại, nhưng ở một hàm khác; xoá hàm ấy
thì phép kiểm này thành rỗng mà không ai biết.

⇒ **Đối chứng dương phải nằm trong CÙNG phép kiểm.** Đã sửa: chủ sở hữu `True`,
người lạ `False`, cùng một hàm.

### Chụp ảnh SAU khi sự kiện bắt đầu ⇒ bộ canh không thể thấy nó

*(H44, lượt deploy 06/09)*

Vòng canh deploy chụp danh sách tệp `.ket.txt` **hiện có** rồi rình tệp **MỚI**:

```
08:51:59   deploy bat dau, tao deploy-20260906-085159.ket.txt
08:52:26   vong canh chup anh -> tep ay nam trong tap "CU"
08:53:55   deploy xong, ghi EXITCODE=0 vao dung tep do
09:12:26   vong canh HET GIO (20 phut), thoat ma 2
```

⛔ Nó **không có khả năng** thấy lượt ấy — không phải vì chờ chưa đủ, mà vì thứ
nó rình (**tệp mới**) không bao giờ xuất hiện. Chờ thêm một tiếng cũng vậy.

🔑 Lỗi nằm ở **thứ tự**: ảnh chụp "trạng thái trước" được lấy **sau** khi sự kiện
đã bắt đầu, nên sự kiện nằm sẵn trong nền. Cùng họ với `check && run` (Bẫy 22):
ở đó phép kiểm chạy **sau** quyết định; ở đây mốc so chụp **sau** sự kiện.

⭐ **Thứ cứu ở đây là một luật đã viết sẵn:** vòng canh có hạn và **thoát mã 2**,
nên im lặng **không** trông giống thành công. Không có nó thì 20 phút im lặng đã
thành *"deploy hỏng"*, và câu trả lời đúng đã bị một câu sai che mất.

⇒ Sửa: đừng rình **tệp mới**, hãy rình **nội dung của tệp mới nhất**, hoặc ghi
mốc thời gian **trước** khi kích hoạt rồi tìm tệp có `mtime` sau mốc ấy.

⛔ Và bài học lớn hơn: **câu trả lời thật đến từ một kênh khác** — đối chiếu băm
523 tệp `.py` và `curl /health/version`. Một kênh chuyên trách (`EXITCODE`) im
lặng, còn hai phép đo độc lập trả lời dứt khoát. Đừng để một kênh chuyên trách
làm nguồn duy nhất chỉ vì nó *có vẻ* được sinh ra cho câu hỏi ấy.

### 🔑 Ước BÁN KÍNH theo NGUYÊN NHÂN bỏ sót đúng những phép kiểm TỐT NHẤT

*(H44 đo 05→06/09 khi đổi chính sách làm tròn tiền; phiên Mobile V1 khái quát)*

Đổi một chính sách ở tầng quyết toán. Để biết phải sửa những phép kiểm nào, tôi
quét theo **tên nguồn**: `thanh_toan|toi_thieu_moi_luot|quyet_toan_luot|lam_tron`.
Sửa 9 tệp, tuyên bố xong. Gate ra **đỏ** vì một tệp thứ mười.

```
05/09  "ba tep da nang kich ban ... nen ngay bat C3 khong do lan nua"  -> do 9
06/09  quet theo ten module, sua 9, tuyen bo xong                      -> con 1
```

Tệp lọt (`test_618`) khẳng định trên **`ex.credit_thu`** — một thuộc tính của
**bảng** — nên nó không nhắc tên module tính tiền nào, và **mọi** phép quét theo
tên module đi ngang qua nó.

⇒ **Phép quét của tôi tìm theo NGUỒN, còn phép kiểm thì neo vào KẾT QUẢ.**

🔴 Và đây là chỗ đau: **neo vào hệ quả là thứ làm một phép kiểm TỐT** — nó bất
biến với cách cài đặt, nên nó sống sót qua những lần viết lại mà phép kiểm neo
vào nguồn thì chết. ⇒ **Càng viết phép kiểm tốt, phép quét theo nguồn càng bỏ
sót nhiều.** Hai thứ ta muốn lại kéo ngược nhau.

**Cách quét thay thế — theo HỆ QUẢ, không theo nguồn:**

```
git grep -n "credit_thu|thu_credit|credit_charged" -- 'tests/*.py'
  | grep -E ">=? *1|> *0|== *1"
```

tức tìm **tên trường kết quả** + **hình dạng khẳng định**, không tìm tên module.

⭐ Và ghi **cả hai** lần ước sai (9 → 1), đừng chỉ ghi lần cuối: con số 9→1 là
thứ nói cho người sau biết phải quét rộng cỡ nào. *"Còn 1"* không mang tin ấy.

### Ranh giới của gate — và nó KHÔNG được đọc thành "gate vô dụng"

Đêm 05→06/09, bốn phiên tìm ra **tám** cái sai và **không cái nào** bị một lượt
gate bắt; cả tám đều do **một người khác đọc lại con số của mình**. Nhưng ca thứ
chín (`test_618`) thì **gate bắt**, còn không phiên nào đọc ra.

🔑 Ranh giới đúng: **gate bắt một phép kiểm thật chạy trên mã thật; nó không bắt
được một suy luận sai VỀ mã.** Tám ca kia là suy luận (chẩn đoán sai nguồn CRLF ·
"gate không có bước kiểm" · RSS đo nhầm loại tiến trình · nói quá về cấu hình
03/09 · ước sai bán kính). `test_618` là mã.

⛔ Không lớp nào thay được lớp kia, và bảng "tám cái sai" ở trên **không** được
đọc thành *"gate vô dụng"* — kết luận ấy sai, và nguy hiểm hơn hẳn cái nó thay.

### 🔴 Phép kiểm TỰ DỰNG đầu vào chỉ đo phía TIÊU THỤ — phía SẢN XUẤT trôi tự do

*(phiên ASV, 06/09 — và nó là ca đắt nhất trong loạt này vì nó chạm tiền)*

Một job hỏng vì máy B bận. Đáng lẽ nó phải được **hoãn**; thực tế nó thành
`failed_terminal`:

```
auto_scan_video.content_process | hoan_s=None
  AiError: khong provider nao phuc vu duoc: ltt_llm: ban
```

`AiError` — **không** phải `KhongCoProviderNao`. `ai.py` bọc **mọi** ngoại lệ
thành `AiError`, làm **mất lớp gốc**, nên `phan_loai` ra `TAM_THOI` thay vì
`BAN`, và nền tảng đọc `"retry"` thay vì `"resource_wait"`. Job **không bao giờ**
được hoãn. `hoan_s=None` là dấu vết.

🔴 **Và triệu chứng ấy đã được "sửa" một hôm trước, rồi báo là xong.** Bản vá
không chạm tới chỗ này, vì chốt của nó **tự dựng `KhongCoProviderNao` bằng tay**
— tức **bỏ qua đúng cái lớp đang làm mất tín hiệu**.

⇒ Chốt xanh, sản phẩm hỏng, báo cáo sai. Ba thứ cùng lúc, và không thứ nào kêu.

🔑 Cơ chế là **vòng phản hồi một phía**, cùng luật với *"chặt với cây mình, lỏng
với cây người"*: một phép kiểm tự dựng đầu vào có vòng phản hồi với **phía tiêu
thụ** (hàm phân loại) và **không có** vòng nào với **phía sản xuất** (chỗ ném
ngoại lệ). Phía không ai đo thì trôi tự do — và nó trôi **im lặng**, vì phép kiểm
vẫn xanh.

⛔ Và giá của nó là **tiền**: một job `failed_terminal` **trừ credit cho việc
chưa từng chạy** (đúng như docstring `giong_noi.MayBan` đã ghi). Đường giọng học
bài ấy từ lâu; đường AI thì chưa.

⇒ **Phép kiểm phải bắt đầu từ RANH GIỚI THẬT**, và không được phép biết tên lớp
trung gian nào. Nếu nó cần gọi tên một lớp nội bộ để dựng đầu vào, nó đang đo
**bản mô phỏng của mình**, không đo sản phẩm.

⭐ Đối chứng ở đường khác cùng kho: `test_819::test_job_hong_thi_tien_HOAN_het`
chốt rằng job hỏng thì `credit_thu == 0` và `credit_hoan == credit_giu`. Nó dựng
job hỏng qua `tao_media.dong_bo` — tức **qua ranh giới thật**, không tự chế
trạng thái.

### Và một biến thể khi ĐẾM

*(cùng phiên)* `grep -r` không phân biệt **thứ sẽ merge** với **thứ tự sinh ra**:
nó trả `Binary file ... matches` từ `.pyc`, và cho một phiên khác **129/133 dòng
là cache** (`.pytest_cache/v/cache/nodeids`, `.playwright-cli/*.yml`).

⇒ Dùng **`git grep`** — ranh giới *"git có theo dõi không"* chính là ranh giới ta
cần.

---

## Bẫy 25 — `short test summary` của pytest **không phải** bảng kết quả của gate

Đo 06/09. Một lượt `gate.py --vong-lap` kết thúc, tôi đọc phần đuôi và thấy:

    FAILED tests/test_299_khu_api_da_dich.py::...
    FAILED tests/test_616_chatltt_bang_va_migration.py::...
    2 failed, 6517 passed, 48 skipped ... in 415.07s
    RESULT: FAIL (3/21)

Tôi sửa **hai** thứ rồi chạy gate đầy đủ để chốt. Nó đỏ.

⭐ Câu trả lời nằm ngay trong dòng tôi vừa đọc: **`(3/21)`**, không phải `(2/21)`.
Gate có **21 bước**; `pytest` chỉ là **một** trong số đó. `short test summary`
liệt kê những phép kiểm đỏ **bên trong bước ấy** — nó không biết gì về hai mươi
bước còn lại. Bước thứ ba đỏ là `bo qua im lang`, một bánh cóc chốt tập hợp lượt
bỏ qua, và nó **không xuất hiện** trong bất kỳ dòng `FAILED` nào.

### Vì sao cái nhầm này dễ tới thế

Cả hai đều là "danh sách những thứ đỏ", cùng nằm ở đuôi cùng một luồng ra, và
danh sách của pytest **dài hơn** nên nó trông đầy đủ hơn. Thứ ngắn hơn — một cặp
số trong ngoặc — mới là thứ nói đúng.

### Cách hỏi đúng

Gate ghi bảng bước ra JSON. Đọc nó, đừng đọc đuôi stdout:

    ls -t test-results/gates/*.json | head -1     # luot gan nhat
    # moi hang: {'ten': ..., 'ket': 'PASS'|'FAIL', 'giay': ...}

Bảng ấy trả lời **bước nào** đỏ. `short test summary` trả lời **phép kiểm nào**
đỏ, và chỉ khi bước đỏ tình cờ là bước chạy pytest.

### Cái giá, và nó không phải thời gian

Lượt gate đầy đủ ấy tốn ~7 phút và **không dùng được làm bằng chứng** — vì tôi
đã sửa `check_bo_qua.moc` **trong lúc nó đang chạy**. Gate tự phát hiện và nói
thẳng:

    CAY DA DOI TRONG LUC CHAY:  M tools/check_bo_qua.moc (891 -> 936 byte)
    Ket qua duoi day noi ve cay luc BAT DAU, khong phai cay hien tai.

⇒ Hai luật, và luật thứ hai là hệ quả của luật thứ nhất:

1. Đọc **bảng bước**, không đọc đuôi pytest. Sửa cho **hết** rồi mới chạy.
2. Gate là công cụ ra **phán quyết**. Một phán quyết về một cây **đang đổi** thì
   không phán quyết gì cả — đúng như chính nó tự in ra.

### Phụ lục — bộ lọc khớp vào **chính nó**, và nó tự giết cha mình

Ngay sau khi viết mục trên, tôi dừng lượt gate hỏng bằng một đoạn Python lọc
tiến trình theo `'gate.py' in cmdline`. Đoạn ấy thoát với mã **15** (SIGTERM), và
ba tiến trình `gate.py` vẫn "còn". Đo tiếp thì cả ba là **shell của chính tôi**:

    pid=23712 ppid=27464  bash.exe -c source '/c/Users/.../snapshot-bash...'
    pid=27464 ppid=27748  bash.exe -c ...
    pid=27748 ppid=10944  bash.exe -c ...

Chuỗi `gate.py` nằm trong **mã nguồn** tôi truyền cho shell, nên nó có mặt trong
`cmdline` của shell. Bộ lọc khớp vào công cụ đo, và lệnh `kill` đi ngược lên cây
cha của chính nó.

⭐ Đây là Bẫy 22 tầng 1 (*khớp `cmdline` đếm thừa*) ở một hình dạng mới: không
phải `timeout.exe` tự nhân bản, mà **câu hỏi xuất hiện bên trong câu hỏi**.

⇒ Lọc tiến trình để **giết** thì `cmdline` không đủ. Điều kiện phải là thứ tiến
trình đo *không thể tự thoả*: `cwd` bằng đúng cây, **và** `pid` khác `os.getpid()`
cùng toàn bộ chuỗi cha của nó.

---

## Bẫy 26 — Bánh cóc chỉ đỏ khi **TĂNG**, nên nó xanh khi phép đo **teo lại**

*(Ghi 06/09/2026 trên nhánh `phien/video-v2-wangp`. Số bẫy có thể trùng với một
bẫy khác đang viết song song trên `claude/chatltt-v3-agentic` — đánh lại số khi
hợp nhất.)*

### Chuyện gì xảy ra

Phiên `LTTCHAT V3` báo `tools/check_mypy.py` **đỏ từ trước mọi thay đổi của
họ**: `arg-type 119 → 120`, `assignment 59 → 61`. Họ kiểm bốn phép đo độc lập,
gồm cả **hai cha** của commit hợp nhất, và **cố ý không chạy `--accept`** — dời
mốc xuống dưới commit của mình là giặt phần trôi của người khác thành phần của
mình.

**Kiểm độc lập trên một nhánh khác hẳn** (`phien/video-v2-wangp`): **đúng hai mã
ấy, đúng hai con số ấy**. Hai nhánh độc lập cùng đỏ ⇒ chỗ trôi nằm ở **tổ tiên
chung**, không phải của ai trong hai phiên. Kết luận của họ đứng vững.

### 🔴 Nhưng thứ đáng sợ hơn nằm trong **biên bản gate**, không nằm ở ba lỗi

Đọc `test-results/gates/*.json` trên **cùng một cây**:

| Lượt | `mypy` | Giây |
|---|---|---|
| 13:53 | **FAIL** | 3,2 |
| 14:19 | **PASS** | 2,2 |
| 15:49 | **PASS** | 3,1 |
| gõ tay, ngay sau | **FAIL** | 7,9 |

Chạy tay ba lượt liền: **3/3 FAIL**, cùng một thông điệp ⇒ *bây giờ* nó tất
định. Gate **không** đặt biến môi trường nào, **không** chụp cây, và bước `mypy`
gọi **đúng** `tools/check_mypy.py`. Vậy hai lượt PASS kia đo một thứ khác.

### Lỗ hổng: `giam` **in ghi chú rồi trả 0**

```python
tang = {... if so > moc.get(ma, 0)}
giam = {... if hien.get(ma, 0) < moc[ma]}
if tang:  ...  return 1
...
if giam:  print("da GIAM ...")
return 0          # <- GIAM luon XANH
```

⇒ Bất cứ điều gì làm mypy **quét được ít hơn** — một gói không nạp được, một
thư mục rơi khỏi phạm vi, một lượt dừng sớm ở một nhánh — đều làm số đếm **giảm**
và bánh cóc **xanh**.

⭐ Cay nhất: chính docstring của `check_mypy.py` đã cảnh báo đúng lớp lỗi này —
*"một thư mục bị đổi tên sẽ âm thầm rơi khỏi phạm vi quét, và số phát hiện GIẢM
— trông y hệt một cải thiện"* — và tôi đã canh **`THU_MUC`** (truyền tường minh,
không tự bỏ qua thư mục thiếu) nhưng **không canh khối lượng thật sự được
kiểm**. Canh danh sách đầu vào không thay được việc canh sản lượng đầu ra.

### ⛔ Đừng đuổi theo cột GIÂY

Phiên kia đề xuất *"thấy `mypy` xanh dưới ~6 giây thì đừng tin"*. **Đo được: đó
là cache tăng dần của mypy** (`.mypy_cache/`), không phải dấu hiệu hỏng — lượt
nguội ~15 giây, lượt ấm ~2–3 giây, và lượt **FAIL** ở 13:53 cũng chỉ mất **3,2
giây**. Một lượt đỏ nhanh bác bỏ chính quy tắc ấy. Lấy nó làm dấu hiệu sẽ đẩy
các phiên sau đi đuổi một cái bóng.

### Bản sửa — và vì sao **chưa** vá

Sửa đúng lớp: ghi thêm vào `.moc` **số tệp mypy thật sự kiểm**, và đỏ khi nó
**giảm**. Đầu vào đã canh; đây là canh đầu ra.

⛔ Chưa vá, theo `AGENTS.md` §4c: mỗi worktree chạy bản `tools/` của riêng nó,
nên một bản vá một phía **phạt đúng cây đã sửa** (cây mới thì đỏ, cây cũ chạy
tự do), và một trường mới trong `.moc` thì bản cũ đọc qua không thấy. Phải lan
cùng lúc, hoặc không lan.

⛔ Và **không `--accept`**: mốc hiện tại chưa từng được chứng minh là khớp cây
nào. Dời nó xuống là khoá vĩnh viễn ba lỗi chưa ai truy ra nguồn.

### ❌ KẾT LUẬN ĐẦU CỦA TÔI — **SAI**. Giữ lại vì cách nó sai mới là bài học

Tôi giải nén **đúng commit đã sinh ra mốc** (`4ece48f8`) ra một cây riêng, chạy
mypy trên đó, thấy `120/61` trong khi `.moc` commit kèm ghi `119/59`, và kết
luận: *"mốc sai từ lúc sinh ra"*.

⛔ **Phép đo ấy không chứng minh được điều đó.** Nó giải nén cây **cũ** nhưng
chạy trong môi trường **hôm nay** — nên nó không phân biệt nổi hai giả thuyết:

| | Giả thuyết | Nó giải thích được gì |
|---|---|---|
| (a) | mốc chưa từng khớp | mỗi con số lệch |
| (b) | **phụ thuộc đã đổi** kể từ lúc chốt | số lệch · **hai nhánh độc lập cùng đỏ** · **không nằm trong commit nào** |

Tôi chọn (a) — cái giải thích **ít hơn**. Đây đúng *"giả thuyết khớp quá vừa kết
thúc điều tra"*: (a) khớp con số một cách hoàn hảo, nên tôi ngừng hỏi.

### ✅ ĐÃ GIẢI — 07/09: **một bản nâng phụ thuộc, không nằm trong commit nào**

Phiên `LTTCHAT V3` đưa mảnh tôi thiếu: **`pillow 12` đổi stub kiểu**. Phép đo
quyết định là **dấu thời gian**, không phải số đếm:

```
commit chot moc `4ece48f8`      06/09  17:02
pillow-12.3.0.dist-info mtime   06/09  22:57      <- SAU gan 6 tieng
```

⇒ Lúc viết, mốc **đúng**. Gần sáu tiếng sau, một bản nâng trong `site-packages`
**dùng chung** thêm 3 lỗi vào mọi cây cùng lúc. Không nhánh nào chứa nó, vì nó
không nằm trong Git.

### 🔴 Lỗ hổng thật, tổng quát hơn cả hai bánh cóc

**Một bánh cóc chốt SỐ ĐẾM mà không chốt MÔI TRƯỜNG sinh ra số đếm ấy.**

`check_mypy.moc` ghi *"arg-type = 119"* như thể đó là tính chất của **mã**. Nó
không phải — nó là tính chất của **mã cộng với phiên bản mọi thư viện có stub**.
Hai cây giống hệt nhau từng byte cho hai con số khác nhau nếu `pillow` khác bản.

Và nó nguy hiểm theo **chiều ngược lại** nhiều hơn: một bản nâng phụ thuộc làm
**giảm** số lỗi sẽ **hạ chuẩn thật** mà bánh cóc vẫn xanh — vì nhánh `giam` luôn
`return 0`. Ta sẽ mất một tầng bảo vệ mà không có gì đỏ lên.

⇒ `--accept` ngày 07/09 vẫn là hành động **đúng**, nhưng vì lý do khác lý do tôi
ghi: đây là **chốt lại mốc sau một bản nâng phụ thuộc**, không phải sửa một mốc
sai từ đầu. Và `.moc` nên ghi kèm phiên bản của những thư viện nó phụ thuộc,
để lần sau câu hỏi *"vì sao số đổi"* có chỗ tra.


Phép đo quyết định: giải nén **đúng commit đã sinh ra mốc** (`4ece48f8`, *"H9 —
mypy làm bánh cóc thứ tư"*) ra một cây riêng ngoài kho, rồi chạy mypy trên đó.

```
tep `check_mypy.moc` COMMIT KEM:   arg-type = 119   assignment = 59
mypy tren CHINH CAY DO:            arg-type = 120   assignment = 61
```

⇒ Không phải phần trôi của ai đó chưa commit. **Mốc sai từ lúc sinh ra** — nó
được `--accept` trên một cây, rồi cây đổi trước khi commit.

Điều đó cũng giải thích các lượt gate `PASS` xen kẽ mà không lời giải thích nào
khớp: mốc lệch **cố định 3 lỗi**, nên bất cứ điều gì làm mypy đếm ra **ít hơn 3
lỗi so với đầy đủ** đều biến nó thành xanh — và nhánh `giam` thì **luôn trả 0**.

⇒ `--accept` ở đây **không** phải giặt phần trôi của người khác. Nó là sửa một
mốc chưa bao giờ đúng, và diff chứng minh điều đó: **chỉ hai dòng đổi**, không
có mã lỗi nào khác trôi theo.

⛔ **Lỗ hổng cấu trúc thì vẫn còn**: nhánh `giam` in ghi chú rồi `return 0`, nên
bánh cóc vẫn xanh khi phép đo teo lại — và như trên, một bản nâng phụ thuộc là
đúng cái làm nó teo. Bản sửa (ghi **số tệp mypy thật sự kiểm** + **phiên bản phụ
thuộc** vào `.moc`, đỏ khi số tệp giảm) **chưa làm**, theo `AGENTS.md` §4c: mỗi
worktree chạy bản `tools/` riêng nên một bản vá một phía phạt đúng cây đã sửa.
