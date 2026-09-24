# P8 Task 3 + 4 — Supervisor có luật · bánh cóc **cơ học** cho hành động cấm

## Nguồn (⛔ không tự suy)

`langchain-ai/langgraph-swarm-py` `langgraph_swarm/handoff.py`:
`create_handoff_tool(agent_name=…)` sinh **một công cụ cho mỗi đích được
phép**, và `get_handoff_destinations(agent)` đọc ngược tập quyền **từ những
công cụ có thật trong đồ thị** (`tool.metadata[METADATA_KEY_HANDOFF_DESTINATION]`),
không từ một bảng khai song song. ⇒ Quyền là một **sự kiện về mã**, đo được.
Đó là hình dạng `HANH_DONG` + `test_2933`.

## Task 3 — `platform_core/agent/supervisor.py`

Sổ **đóng**, `lam()` là cửa duy nhất, mọi lượt (làm **và** từ chối) ghi
`SupervisorDecision`:

| Hành động | Luật cưỡng chế |
|---|---|
| `thu_lai_node` | node `FAILED` · `thu_lai.con_luot` (retry.max còn lại) · ⛔ `thu_lai.KHONG_THU_LAI` (`ABANDONED`/`CANCELLED`/…) |
| `di_nhanh_loi` | phải có cạnh `kind="ERROR"` ra từ node; supervisor **không** tự chọn node kế, chỉ đánh thức động cơ |
| `hoi_nguoi` | mở waitpoint `HUMAN` |
| `bo_qua_node` | `settings.khong_quan_trong is True` (⛔ `is True`, không truthy) |

`may_trang_thai.NODE_CHUYEN` thêm **đúng hai lối**
`FAILED → {RETRY_SCHEDULED, SKIPPED}` — không có chúng thì hai hành động trên
không tồn tại được. ⛔ Cố ý **không** thêm `FAILED → READY`: quay thẳng về
READY là bỏ qua `retry.max`, backoff và `_khoa_idem` theo lượt.

### 🔴 Hai chỗ §12.4 phải THU HẸP — đo được

1. **Không đụng run đã kết sổ.** §12.4 nói đọc run *"FAILED/WAITING lâu"*,
   nhưng `FAILED ∈ RUN_KET_THUC` và run kết thúc là run `ket_so` đã quyết toán
   (`hold_id` đã xoá). Chạy tiếp nó = chạy **không còn tiền bị giam**. ⇒
   `quet()` chỉ trả `RUNNING`/`WAITING`; `lam()` từ chối `run_da_ket_so`.
2. **`doi_model` KHÔNG đăng ký.** `params` sống trong `workflow_version.graph`,
   **bất biến** (§4.2) ⇒ ghi đè nó chính là *"sửa version đã publish"*, thứ
   §12.4 cấm. Cần một ô ghi đè **theo run**. Lược đồ đề xuất (⛔ chưa làm —
   ngoài ranh giới làn):

   ```
   workflow_node_override(run_id PK, node_id PK, params JSON, by, at)
   -- cau_noi.nop_job: sau `giai_tham_so`, trộn override CHỈ khi
   --   NodeDefinition.tham_so.properties[k].enum chứa giá trị mới.
   ```

   ⛔ Không đăng ký một cửa luôn từ chối: một hành động **vắng mặt** đọc được,
   một cửa giả thì không (nợ §5 của plan sinh ra đúng từ những cửa như thế).

## Task 4 — `tests/test_2933_banh_coc_hanh_dong_cam.py`

Dựng đồ thị gọi bằng `ast` trên **toàn bộ** `platform_core/` (giải bí danh
`import`, cả import trong thân hàm), BFS từ `supervisor.HANH_DONG` +
`lam`/`quet` và từ `ke_hoach_v3.soan_draft`. `CAM` = **13 địa chỉ hàm có
thật**, mỗi địa chỉ một gạch đầu dòng §12.4 (hold, `ket_so`, `credit.*`,
`dinh_nghia.xuat_ban*`/`luu_draft`, `api_keys.*credential`, `jobs.submit`).

Ba lỗ được bịt bằng luật khác, không bằng hy vọng: gọi **động**
(`getattr`/`eval`/`exec`/`__import__`/`globals` bị cấm trong tập với tới được),
**SQL thô** trong `supervisor.py`, và `CAM` phải toàn địa chỉ **có thật** (đối
chiếu bằng `ast`, nếu không một tên gõ sai làm bánh cóc xanh vĩnh viễn).

### Số đo

```
ham doc duoc: 1969
supervisor voi toi: 37 | soan_draft voi toi: 78
cham CAM: []
```

### ⭐ Bánh cóc CẮN THẬT — tiêm lỗi (⛔ không ghi vào cây)

| Tiêm | Kết quả |
|---|---|
| `hoi_nguoi` gọi thẳng `tien.giu_cho_run` | phát hiện, đường dài 2 |
| … `dinh_nghia.xuat_ban` | phát hiện |
| … `api_keys.dat_credential` | phát hiện |
| `hoi_nguoi` → `_len_tay()` → `tien.giu_cho_run` (**một tầng trung gian**) | phát hiện, đường dài **3** |

Mỗi ca có **vế đối chứng**: bản thật không có cạnh ấy.

## Đỏ trước / xanh sau

```
test_2932: 3 failed, 15 passed   (settings đặt sai tầng; `WorkflowRun` không có `updated_at`)
test_2932: 18 passed in 4.82s
test_2933: 10 passed in 9.93s    (gồm 4 ca tiêm lỗi — bánh cóc cắn)
```

## Chưa làm được / không phủ

- Đồ thị tĩnh **không thấy** lời gọi qua phương thức đối tượng (`x.f()` khi
  `x` không phải bí danh mô-đun). Lỗ này hẹp vì mọi hàm trong `CAM` là hàm cấp
  mô-đun, nhưng nó **có thật** và phải được nói ra.
- Supervisor **chưa có job định kỳ** chạy `quet()` (§12.4 *"chạy như job định
  kỳ"*): đăng ký một job nền chạm `apps/*/jobs.py` + sổ job, ngoài phạm vi
  task. `quet()` đã có và đã đo.
- `quet()` dùng `coalesce(started_at, created_at)` vì `workflow_run` **không
  có** `updated_at` ⇒ nó đo *"sống từ bao giờ"*, ⛔ không phải *"lần cuối có
  tiến triển"*. Vì thế mọi hành động tự kiểm lại điều kiện, không tin `quet()`.
