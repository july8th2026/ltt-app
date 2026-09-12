# Kho R2 không giữ tệp quá ~7 ngày — điều tra 12/09/2026

> Bắt đầu từ một ô nghiệm thu của LTT Voice (`TANG2_RC1.md` §3), nhưng **kết
> luận không thuộc về Voice**: nó chạm mọi app dùng kho.

## 1. Câu hỏi

28 hồ sơ giọng trên production có đủ hàng `voice_ref` + `voice_repr` nhưng
**không khoá R2 nào còn tồn tại**. Cái gì đã xoá chúng?

## 2. Phép đo quyết định — nhìn cả kho, không chỉ nhìn Voice

```
TONG khoa trong bucket `fb-video-storage` : 46
theo tien to cap 1                        : voice 45 · anhnoibo 1
theo thang                                : 2026-09  46   (KHONG co gi cua thang 8)
khoa CU NHAT                              : 2026-09-05 14:35 UTC
khoa MOI NHAT                             : 2026-09-11 22:59 UTC
=> khong mot object nao gia hon ~7 ngay
```

Đối chiếu với lưu lượng thật (`CLAUDE.md`, đo 28 ngày 11/08→07/09): **10.663**
lượt `ltt_llm.chat` · **1.075** `anhnoibo.generate` · **147**
`ltt_voice.synthesize`, và bảng `jobs` có **1.770** hàng.

⇒ Một kho phục vụ 1.770 job mà **không giữ nổi một object nào của tháng 8** thì
không phải "vài tệp bị mất": có một cơ chế **xoá theo TUỔI** đang chạy.

### 2.1 Quan sát trực tiếp cơ chế ấy hoạt động

Hai lượt liệt kê cách nhau ~4 giờ trong cùng ngày 12/09:

| Lúc | `thumbnail/…` |
|---|---|
| ~02:47 | **14 khoá** (mỗi khoá 208 byte) |
| ~06:35 | **0 khoá** |

Không lệnh nào của lượt nghiệm thu chạm tới tiền tố `thumbnail/`.

## 3. Loại trừ từng đường xoá trong mã — đo, không đoán

| Đường | Có phải thủ phạm? |
|---|---|
| `platform_core/job_content.py::expire_content` | **Không.** Nó chỉ xoá khoá **chứa `/{job_id}/`** (`content_keys` quét `job.params`/`job.result`). Khoá `voice/{owner}/{vc_…}/source.wav` không mang `job_id`. |
| `RETENTION_DAYS` của đường trên từng là 7 ngày? | **Không.** `git log -L` trên chính dòng ấy: nó **sinh ra đã là 30** (`6a475a5e`) và chưa từng đổi. |
| `platform_core/upload_sessions.py::sweep` / `cleanup_failed_job` | **Không.** Bảng `upload_sessions` trên production **rỗng** — Voice nhận tệp trực tiếp qua form multipart, không đi qua phiên upload. |
| `apps/ltt_voice/jobs.py` (xoá biểu diễn mồ côi) | **Không.** Chỉ chạy khi hồ sơ ở `revoked`/`loi`/`disabled`; cả 28 hồ sơ đều `active`. |
| `apps/ltt_voice/routes/_p_giong.py` (thu hồi / đổi làn) | **Không.** Cùng lý do: không hồ sơ nào bị thu hồi. |
| `apps/ltt_voice/nghe_thu.py` | **Không.** Chỉ xoá bản nghe thử khi dựng lại, không chạm `source.wav`. |

⇒ **Không đường nào trong ứng dụng xoá tệp của một hồ sơ giọng đang `active`.**

## 4. Kết luận, và đúng mức độ chắc chắn của nó

**Gần như chắc chắn:** bucket `fb-video-storage` có một **luật vòng đời
(lifecycle rule) ~7 ngày** — cơ chế nằm **ngoài** ứng dụng.

**Vì sao chưa xác nhận trực tiếp được:** khoá S3 của ứng dụng bị `AccessDenied`
ở cả `GetBucketLifecycleConfiguration` lẫn `GetBucketVersioning`, và
`secrets/app.env` **không có** Cloudflare API token — chỉ có bốn biến `LTT_R2_*`
kiểu S3.

⇒ Người duy nhất xác nhận được là **chủ dự án**, qua dashboard Cloudflare R2:
*R2 → bucket `fb-video-storage` → Settings → Object lifecycle rules*.

### 4.1 Vì sao `voice/mau/` vẫn còn — và nó xác nhận giả thuyết

20 giọng mẫu vẫn nghe được, nhưng không phải vì chúng được miễn: chúng được
**ghi lại liên tục**. Dấu thời gian tự khai điều đó — cùng một bộ 20 giọng xuất
hiện hai lần với hai vân tay engine khác nhau:

```
2026-09-08 13:53 → 17:46   voice/mau/*/v2-d3de79229324.wav   (20 tep)
2026-09-10 18:43 → 09-11 00:43  voice/mau/*/v2-fe0932ce0990.wav  (20 tep)
```

Đó là `nghe_thu`/`bao_tri` dựng lại bản nghe thử khi tham số engine đổi. Một
tiền tố được ghi lại mỗi vài ngày thì **không bao giờ đủ già để bị xoá** — nên
nó sống sót *bất chấp* luật, không phải *nhờ* được loại trừ.

## 5. Vì sao đây là việc đáng làm dù Voice không thiệt hại

28 hồ sơ mất tệp đều thuộc **một tài khoản THỬ** (`thu.giongnoi@lttstudios.local`,
đuôi `.local`) ⇒ không khách nào bị ảnh hưởng **hôm nay**. Nhưng:

| | |
|---|---|
| Mã khai | nội dung job giữ **30 ngày** (`RETENTION_DAYS`), input promoted giữ **30 ngày** (`PROMOTED_RETENTION_DAYS`) |
| Kho làm | xoá sau **~7 ngày** |

Hai tầng nói hai điều khác nhau, và **tầng thật thắng**. Mọi phép kiểm dựa trên
con số 30 trong mã — hạn tải lại của khách, đối chiếu hoá đơn, "tạo lại" của Dự
án Voice — đang đo một thế giới không tồn tại.

⚠️ Và hậu quả không giới hạn ở Voice: ảnh `anhnoibo`, output video, thumbnail —
**mọi thứ** trong bucket đều đi theo cùng một luật.

## 6. Vật mốc đã đặt — để lượt sau đo được ngưỡng CHÍNH XÁC

Vì không đọc được cấu hình, cách đo duy nhất còn lại là một vật mốc:

```
chan_doan/moc-vong-doi-20260912T003354Z.txt
chan_doan/moc-vong-doi-moi-nhat.txt
```

Tiền tố `chan_doan/` không app nào đọc. Nội dung tệp tự khai giờ đặt và mục
đích. **Khi nó biến mất, hiệu số tuổi chính là ngưỡng** — đó là con số mà mọi
hằng số retention trong mã phải khớp lại.

## 7. Việc tiếp theo

| Việc | Ai làm |
|---|---|
| Mở dashboard Cloudflare R2 → bucket `fb-video-storage` → Object lifecycle rules, đọc luật thật | **chủ dự án** (chỉ tài khoản đó có quyền) |
| Quyết: nới luật cho khớp mã, hay hạ hằng số trong mã cho khớp luật | chủ dự án + phiên nền tảng |
| Sau khi chốt: sửa `RETENTION_DAYS` / `PROMOTED_RETENTION_DAYS` và mọi câu tài liệu nói "30 ngày" | phiên nền tảng |
| Theo dõi vật mốc ở §6 để có ngưỡng đo được | phiên bất kỳ |

⛔ Đừng dựng lại 28 hồ sơ giọng đã mất tệp trước khi luật vòng đời được chốt —
dựng lại vào một kho vẫn đang xoá là làm lại cùng một việc sau bảy ngày.
