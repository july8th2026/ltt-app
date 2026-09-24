# P3 · Task 5 — `foreach` · `foreach_end` · `join` (PORT `shouldReleaseBarrier`)

## Nguồn đã tra — và PORT đã trả lãi ngay

`activepieces/activepieces@17e2ac0b`:

- `packages/core/execution/src/lib/flow-run/waitpoint/index.ts` —
  `shouldReleaseBarrier({ policy, sealed, counts })`, `UNFAVOURABLE_SIGNAL_STATUSES`.
- `brain/knowledge/decisions/000015-fan-in-is-an-event-driven-waitpoint-barrier.md`
  — *"Release is an **unconditional floor rule**: a sealed barrier releases once
  no signal is still PENDING. **No configuration can produce a hang**; `policy`
  only ever releases sooner"*; và *"Counts are taken once, from a single
  `GROUP BY status`, and handed to a pure predicate"*.
- `brain/knowledge/flows-execution/flow-runs.md` — hình dạng bảng waitpoint/signal.

### 🔴 PORT bắt được một TREO THẬT trong mã ta

`cho_doi.da_mo` cũ đặt `required_successes` ở nhánh **loại trừ**. Với `can = 2`,
nếu cả ba nhánh đã báo mà chỉ một nhánh `SUCCEEDED`, nó trả `False` **mãi mãi** —
không còn tín hiệu nào sẽ tới. Run đứng tới `TRAN_RUN` 20 giờ **với tiền vẫn bị
giữ**. Luật sàn của họ đứng **sau** policy, nên không cấu hình nào treo được.
Khác biệt thứ hai: veto của ta bỏ sót `NOT_DISPATCHED`.

## Đỏ trước

```
$ python -m pytest tests/test_1784_wf_barrier_va_foreach.py -q
20 failed, 2 passed in 2.42s
```

Phép passed là đối chứng `test_doi_chung_join_ALL_van_cho_khi_thieu_mot_nhanh`.

## Xanh sau

```
$ python -m pytest tests/test_1784_wf_barrier_va_foreach.py -q
24 passed in 4.56s
$ …chay_nang.py --phien p3 -- pytest <20 tep wf> -q -n 6
286 passed  (1 failed = cái chuông test_1714, đã trả lời — xem dưới)
$ python -m pytest tests/test_1714… tests/test_1783… tests/test_1784… -q
83 passed in 6.86s
```

## Lỗ THỨ HAI, phát hiện khi trả lời cái chuông

Cổng tổ tiên §6.2 (*"một cổng an ninh về tiền"*) chỉ soi các đoạn `{{ … }}`.
Nhưng tham số node lõi là biểu thức **trần** (`core.if.dieu_kien =
"nodes.a.output.text == 'co'"`) — `doan_bieu_thuc` không thấy gì, nên **một node
đọc output của một node KHÔNG phải tổ tiên đi lọt qua publish**. Vá:
`bien_dich.KIEU_BIEU_THUC` — lược đồ tham số **nói ra** tham số nào là biểu thức,
và `_tham_chieu_node_loi` trích từ đúng những tham số đó. ⛔ Không đoán theo tên
tham số: đó là một bảng thứ hai sẽ trôi.

## Cái chuông `test_1714` — câu trả lời, không phải việc xoá phép kiểm

**Luật tổ tiên KHÔNG đổi.** Thân vòng lặp là một đoạn của chính đồ thị đã biên
dịch; node thân đọc được node thân đứng trước vì node ấy **là** tổ tiên theo
`graph.thu_tu`. Không có luật thứ hai. Thứ Task 5 thêm là **giá trị**, không phải
**quan hệ**: trong thân, `nodes.<x>.output` trả giá trị của **vòng đang chạy**
(`_mt_than` phủ ảnh chụp CSDL bằng output của vòng ấy) và `loop.*` tồn tại; ngoài
thân, cùng tham chiếu trả giá trị của **vòng cuối** — muốn cả tập thì đọc
`foreach_end.output.results`. Phép kiểm mới cũng chứng minh luật tổ tiên **vẫn
cắn trong thân** (`x` đọc `y` ⇒ `tham_chieu_khong_phai_to_tien`).

## ⛔ RANH GIỚI ĐÃ KHAI: thân `foreach` chỉ nhận node `inline`

`node_run` khoá `(run_id, node_id)`. Một node thân chạy 30 lần cần 30 trạng thái,
và mô hình C **cấm sửa ảnh chụp** — không có chỗ cho chúng sống. Activepieces
giải đúng bài này bằng **khoá theo đường thi hành**; ta đã làm cho `wakeup`
(Task 1) nhưng chưa cho `node_run`, và đó là **migration trên bảng đang chạy
thật** mà plan không mở. ⇒ Thân có node job bị từ chối **lúc publish**
(`than_foreach_co_node_job`), phải đi qua run con (`body_workflow`, §5.9) —
Task 7. Từ chối ở publish trung thực hơn là chạy nửa vòng rồi treo.

## Việc đã làm

- `join.nen_mo_barrier` — hàm **thuần**, PORT nguyên luật + `TIN_HIEU_XAU` có
  `NOT_DISPATCHED`. `cho_doi.dem_tin_hieu` — **một** câu `GROUP BY` (có phép
  kiểm đếm câu SQL thật bằng `before_cursor_execute`); `da_mo` chỉ còn việc quy
  trạng thái CSDL của ta về `dem[PENDING]`.
- `bao_gia.than_foreach` tách ra làm **một nguồn** cho câu hỏi "node nào trong
  thân nào"; `he_so_lap` và động cơ hỏi cùng chỗ.
- `nut_loi/vong_lap.py`: `core.transform`, `core.foreach` (lái cả vòng lặp),
  `core.foreach_end`, `core.join`. `on_item_error ∈ {fail, skip, collect}`.
- `dong_co._nguong_join`: `ANY`/`N_OF_M` hạ **ngưỡng READY** — luật READY sống ở
  lan truyền, không trong bộ thi hành (một node chỉ chạy KHI ĐÃ READY).

## Chưa làm được

- `parallelism` được nhận và ghi vào `ForeachVong` nhưng thân chạy **tuần tự**
  (thân inline không có I/O, nên song song hoá chưa mua được gì đo được).
- `foreach` lồng nhau chưa có phép kiểm chạy thật (`he_so_lap` thì có).
- Ngữ cảnh vòng lặp chưa được truyền vào `thu_lai.hen(vong=…)` — thân chưa có
  node job nên chưa có đường sinh wakeup trong thân; phép kiểm hiện đo
  `than_cua` + `duong_thi_hanh` khớp nhau, **không** đo đường chạy thật.
- Chưa chạy trên PostgreSQL thật (Task 8).
