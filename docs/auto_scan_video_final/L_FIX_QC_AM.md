# L_FIX_QC_AM — R-02 (T3) và R-03 (T5): sản phẩm sai hay phép đo sai?

Làn `fix-qc-am`, nhánh `phien/asv-final-fix-qc-am`, gốc `29aaacd8`.
Hai lỗi QC của lượt nghiệm thu phim khách thật (`bang_chung/NEN_V3.md`).
Câu hỏi cho mỗi lỗi: **sản phẩm sai, hay bộ đo sai?** Cả hai lần: **sản phẩm sai.**

Mọi con số dưới đây đo bằng `ffmpeg`/`ffprobe` trên **phim thật** ở
`C:\Users\…\Desktop\TEST VIDEO\`, qua **chính** `ket_xuat.dung_lenh` và
`am_master.tron_cuoi` — không phải fixture tổng hợp.

---

## §1 R-02 — T3 đỏ ở `localize_preserve_picture`

### Giả thuyết của lượt nghiệm thu đã bị BÁC

`NEN_V3.md` mục 3 nghi rằng T3 băm **tệp nguồn gốc** trong khi render sao chép
từ **bản đã chuẩn hoá** của `media_prepare`. Đọc mã thì hai đường trùng nhau:

| chỗ | đọc gì |
|---|---|
| `giai_doan_qc.chay:96` | `_duong_doc_duoc(kho, run.source_key, …)` |
| `giai_doan_ket_xuat.chay:130` | `_duong_doc_duoc(kho, run.source_key, …)` |

`media_prepare` **không sinh** bản video chuẩn hoá nào — hai artifact của nó là
`source_probe.json` và `audio_full.wav`. Vậy T3 đã so đúng thứ render sao chép,
và câu "đổi T3 sang so với artifact render thật sự chép" là một việc **không
cần làm**.

### Nguyên nhân thật: `-shortest` trên đường `-c:v copy`

Dựng lại lượt hỏng bằng chính lệnh sản phẩm trên đúng phim của NEN_V3 — **ra
đúng hai chuỗi băm mà báo cáo ghi**:

```
bam NGUON            acd497e1825e6fd978901482afa0e899   3205 gói
bam SAN PHAM         70e57a0ec644a3df40971b0384c968a1   3203 gói   ← T3 HỎNG
bam BỎ `-shortest`   acd497e1825e6fd978901482afa0e899   3205 gói   ← T3 đạt
bam remux tối giản   acd497e1825e6fd978901482afa0e899   3205 gói
```

`-shortest` kết thúc khi luồng RA ngắn nhất hết. Luồng tiếng được **mã hoá lại**
(AAC), luồng hình đi **thẳng** từ nguồn; khi luồng hình của nguồn kết thúc sau
bản phối, ffmpeg vứt các gói hình cuối. Bốn phim thật, cùng một lệnh:

| phim | hình / tiếng của nguồn (s) | `-shortest` | khung mất |
|---|---|---|---|
| 廉价的牛肠… | 265,000 / 264,961 | T3 đạt | 0 |
| 暴雨天… | 189,967 / 190,009 | T3 đạt | 0 |
| **深度解析…** (phim NEN_V3) | **106,833 / 106,816** | **T3 HỎNG** | **2** |
| 真人气枪… | 275,008 / 275,029 | T3 đạt | 0 |

Chỉ phim nào có **luồng hình dài hơn** mới lộ. Và điều kiện đó không hiếm: bản
phối bị `am_master.tron_cuoi` cắt bằng `-t {tong_giay:.3f}`, nên một video
106,833333 s cho ra bản phối 106,833 s — ngắn hơn **0,33 mili giây**, đủ để mất
2 khung (66 ms hình) **im lặng**.

⇒ **Sản phẩm sai.** Lời hứa của preset là *không một điểm ảnh nào đổi*, còn bản
giao thiếu 2 khung cuối. T3 đã hỏi đúng câu và trả lời đúng.

### T3 từng "đạt" trên đầu vào nào

Trên `lavfi`: `tests/fixtures/asv_media.tiny_mp4` dựng `testsrc` và `sine`
**cùng một `duration`**, nên luồng tiếng luôn ≥ luồng hình và `-shortest` không
có gì để cắt. `test_448` chạy cả chuỗi trên đúng loại tệp đó.

### Bản sửa

`ket_xuat.dung_lenh`: `-shortest` **chỉ còn ở đường CAT**. Ở đường sao chép nó
không bảo vệ được gì (bản phối đã bị `-t` chặn, và T16 bắt được nếu tiếng tràn),
mà chỉ có thể cắt hình. `PHIEN_BAN_KET_XUAT` 2 → 3 vì tệp ra đổi byte.

---

## §2 R-03 — T5 đỏ: đỉnh thật −0,33 dBTP

### Đỉnh thoát ở đâu

Ba nghi can của đề bài, đo từng cái trên tín hiệu thật qua đúng đường sản phẩm:

| bước | LUFS | đỉnh thật |
|---|---|---|
| bản phối (`tron_cuoi`, `loudnorm` 2 lượt, `TP=-3.5`) | −14,21 | **−3,47** |
| chỉ mã hoá AAC 192k/48k/2ch (không render) | −14,25 | **−3,04** |
| RENDER giữ hình (`sao_chep`) | −14,25 | −3,04 |
| RENDER cắt, `toc_do=1` | −14,25 | −3,04 |
| RENDER cắt, `toc_do=1,25` (có `atempo`) | −14,49 | −3,24 |

- **`loudnorm` chế độ linear/dynamic KHÔNG phải thủ phạm** — nó trúng đích LUFS
  và không vượt trần đặt cho nó.
- **`render` không thêm gì**: "chỉ AAC" và "RENDER" ra **cùng một con số**, nên
  bản mã hoá thử là đại diện đúng của bản giao.
- ⇒ **Đỉnh thoát ở bước mã hoá có mất mát**, và mức thoát là thuộc tính của
  **tín hiệu**. 16 tổ hợp trên 4 phim thật (mật độ lời × `giam_theo_loi`) cho
  vọt lọ **0,00 → 0,85 dB**; sổ đo cũ trong `am_master.py` ghi **0,13 → 2,78 dB**
  với tiếng đọc model thật. Không có hằng số nào đúng cho cả dải đó.

Phụ phát hiện: `loudnorm` **không ghim** đúng trần của chính nó. Cùng trần −3,5
trên các bản phối thật, đỉnh ra rơi từ **−5,19 đến −3,16** — tức có bản **vượt
trần 0,34 dB** ngay ở bản phối.

### Bản sửa: hạn đỉnh THẬT + vòng đo, không đoán nữa

`am_master`:

1. `loc_han_dinh(tran_db)` — `aresample=176400, alimiter=limit=…:level=0,
   aresample=44100`. Lấy mẫu **4×** là đúng hệ số của phép đo BS.1770 mà T5
   dùng, nên đây là hạn *đỉnh thật* chứ không phải hạn *đỉnh mẫu* (bẫy đã ghi ở
   pha 22). `level=0` bắt buộc: mặc định `alimiter` tự nâng mức ra.
2. `do_ban_giao(duong)` — mã hoá **thử** bằng đúng `ban_dung.CODEC_TIENG` /
   `BITRATE_TIENG` / `TAN_SO_RA` / `SO_KENH_RA` rồi đo lại.
3. `ghim_tran_phoi(...)` — hạ trần bản phối cho tới khi bản **thử** đạt trần T5
   (tối đa `SO_VONG_GHIM = 3` vòng, mỗi vòng lùi thêm `GHIM_LUI_THEM_DB = 0,3`).
   `tron_cuoi` gọi nó ở lượt 3, sau hai lượt `loudnorm`.

`BIEN_CHO_CODEC_DB = 2.0` **không còn là trần**, nó chỉ là điểm xuất phát để
vòng đầu thường trúng ngay. `kiem_ban_ra` ghi `dinh_that_giao`,
`tran_phoi_da_ghim`, `so_vong_ghim`, `vot_lo_codec` vào hồ sơ giai đoạn — tức
câu hỏi của T5 được trả lời **trước** khi tốn một suất render.
`PHIEN_BAN_MASTER` 2 → 3 vì bản phối đổi byte.

Hạn đỉnh lấy mẫu lên là **cơ chế**, còn **bảo đảm** là vòng đo: nó đo trên bản
đã mã hoá, tức đo cả phần dư của chính bộ hạn (đo được: trên âm đơn 14 kHz —
trường hợp xấu nhất của đỉnh giữa-mẫu — sai số 0,41 dB so với 1,81 dB nếu không
lấy mẫu lên).

---

## §3 TRƯỚC / SAU trên phim thật, cả hai preset

Cùng một kịch bản chạy ở cây `29aaacd8` và ở cây đã sửa: phim NEN_V3 đủ
106,833 s, nền = tiếng phim, 6 đoạn lồng tiếng cắt từ chính phim (12 s mỗi
đoạn), qua `am_master.tron_lo` → `tron_cuoi` → `ket_xuat.dung_lenh`.

| | bản phối | preset | LUFS giao | đỉnh giao | vọt lọ | T3 | T4 | T5 | khung |
|---|---|---|---|---|---|---|---|---|---|
| **TRƯỚC** | −3,45 | giữ hình | −14,27 | −2,14 | 1,31 | **HỎNG** | đạt | đạt | **3203/3205** |
| **TRƯỚC** | −3,45 | cắt | −14,27 | −2,14 | 1,31 | n/a | đạt | đạt | 3204 |
| **SAU** | −3,47 | giữ hình | −14,27 | **−2,86** | **0,61** | **đạt** | đạt | đạt | **3205/3205** |
| **SAU** | −3,47 | cắt | −14,27 | −2,86 | 0,61 | n/a | đạt | đạt | 3204 |

- T3 khép: MD5 luồng hình bản ra **bằng** nguồn, đủ 3205 khung.
- Biên an toàn của T5 rộng ra **0,72 dB** (−2,14 → −2,86) mà **LUFS không đổi**
  (−14,27 cả hai) — hạn đỉnh chỉ chạm đỉnh, không chạm độ to nghe được.
- Giá: một vòng ghim trên bản phối 107 s tốn **8,97 s** (`han_dinh` 0,77 s +
  `do_ban_giao` 8,20 s). Phép đo của `kiem_ban_ra` **dùng lại** kết quả vòng
  cuối (tham số `ghim`) thay vì mã hoá thử lần hai — hai lần chạy cùng một lệnh
  trên cùng một tệp không thể cho hai câu trả lời.

---

## §4 Phép kiểm mới — và vì sao bộ cũ không bắt được

| tệp | bài | chốt |
|---|---|---|
| `tests/test_2014_asv_t3_sao_chep_du_khung.py` | 5 | `-shortest` chỉ ở đường CAT; render sao chép thật giữ **đủ khung** và băm **bằng nguồn**; tiêm lại `-shortest` thì băm **khác**; khép vòng qua `qc.kiem` → T3 `dat` |
| `tests/test_2015_asv_ghim_dinh_that_ban_giao.py` | 10 | `loc_han_dinh` lấy mẫu 4× + `level=0`; hạn đỉnh **thật** đúng trần; đối chứng `alimiter` trần trụi **vượt** trần; vòng ghim **chạy** và hội tụ; không bao giờ làm to bản phối; `tron_cuoi` → `kiem_ban_ra["dinh_that_giao"]` ≤ trần T5 |

**Vì sao bộ cũ im lặng.**

- *T3*: `test_444`/`test_473` truyền **hai chuỗi băm giả** vào `qc.kiem` —
  chúng kiểm *câu lệnh so sánh*, không kiểm *phép sao chép*. `qc.bam_luong_hinh`
  chưa từng được gọi trên một tệp thật trong cả bộ kiểm. `test_448` có render
  thật, nhưng trên `lavfi` hình và tiếng **cùng độ dài**, nên điều kiện lộ lỗi
  không bao giờ xuất hiện.
- *T5*: `test_479`/`test_442` chốt **chuỗi lọc** của bản phối, `test_420`/
  `test_444` chốt **ngưỡng** bằng cách tiêm một con số vào `qc.kiem`. Cả hai đều
  đo ở phía PCM. Không bài nào mã hoá bản phối bằng tham số giao hàng rồi đo
  lại, nên **khoảng cách giữa bản phối và bản giao** — đúng thứ làm T5 đỏ —
  không có chốt nào.

⚠️ Giới hạn còn lại, nói thẳng: **không tái hiện được mức vọt lọ 2,78 dB** bằng
tiếng nói thay thế (cắt từ chính phim). 16 tổ hợp chỉ lên tới 0,85 dB; tín hiệu
làm nó vọt 2,78 dB là bản đọc của máy sinh tiếng thật. Nên `test_2015` chốt
**cơ chế** (bộ hạn ghim đúng đại lượng T5 đo; vòng lặp hạ trần cho tới khi bản
mã hoá thử đạt) chứ không chốt một biên độ cụ thể — và đó là lý do bản sửa
không phải một hằng số mới: **vòng đo đúng với mọi mức vọt lọ**, kể cả mức chưa
ai thấy.

---

## §5 Tệp đã đổi

```
apps/auto_scan_video/ket_xuat.py            -shortest chỉ ở CAT; PHIEN_BAN_KET_XUAT 2→3
apps/auto_scan_video/am_master.py           loc_han_dinh / han_dinh / do_ban_giao /
                                            ghim_tran_phoi; tron_cuoi lượt 3; kiem_ban_ra
                                            báo dinh_that_giao; PHIEN_BAN_MASTER 2→3
apps/auto_scan_video/giai_doan_thoi_gian.py chuyền `ghim` từ tron_cuoi sang kiem_ban_ra
tests/test_414_asv_ket_xuat.py              chốt -shortest được THU HẸP, không bị xoá
tests/test_465_asv_v6_chuan_am_hai_luot.py  tron_cuoi nay có lượt ghim (thứ tự + tệp)
tests/test_2014_… / test_2015_…             mới
```

## §6 Phép kiểm đã chạy

`app:auto_scan_video` (94 tệp, `chay_nang.py -n 6`): **1773 đạt, 16 bỏ qua,
1 xfail, 3 đỏ**. Cả ba đỏ **có sẵn ở `29aaacd8`**, đã đối chứng trên cây gốc:
`test_432::test_chi_MOT_cho_trong_app_goi_giu_cho` (làn `cache-lease` thêm
`giu_cho` vào `thi_hanh.py`), `test_448::test_moi_luot_di_HET_chuoi_giai_doan`
và `test_448::test_phien_ban_ENGINE_trong_bao_cao_van_dung_HOM_NAY`
(`chep_loi/2` vs `chep_loi/1`).
