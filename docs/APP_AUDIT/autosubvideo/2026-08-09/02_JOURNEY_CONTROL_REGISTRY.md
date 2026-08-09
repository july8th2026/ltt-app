# 02 — Journey & Control Registry: Auto Sub Studio

## Journey/state matrix

| ID | State | Kỳ vọng customer | Kết quả thật | Evidence | Verdict |
|---|---|---|---|---|---|
| J-01 | Empty | Chọn/tạo project và biết bước đầu | Tự mở project mới/gần nhất; không có project picker | EV-BR-001, EV-SRC-002 | PARTIAL |
| J-02 | Upload click | Loại/size/duration được kiểm trước lưu | Chỉ browser metadata; server tin ext/MIME/duration | EV-SRC-004 | BROKEN |
| J-03 | Drag/drop | Drop đúng như copy công bố | Không có handler drop | EV-SRC-002 | BROKEN |
| J-04 | Direct upload fail/abandon | Không orphan, retry cùng session | Ticket/blob không staging/TTL/promote | EV-SRC-004 | BROKEN |
| J-05 | Attach source | Chỉ video thật của upload session | Bất kỳ key owner-prefix đang tồn tại đều có thể attach | EV-SRC-004 | BROKEN |
| J-06 | Import transcript | SRT/VTT/ASS/JSON thành cue có QA | File thật import 3 cue, QA 100 | EV-BR-003 | LIVE |
| J-07 | Auto transcript | Capability/model/cost rõ | Nút ghi WhisperX dù có fallback; capability có thể báo chưa cấu hình | EV-BR-001, EV-SRC-006 | MISLEADING |
| J-08 | Diarize/translate | Biết giới hạn còn lại và kết quả áp dụng | 0 credit nhưng UI bỏ quota remaining; conflict không merge | EV-SRC-006/009 | BROKEN |
| J-09 | Edit cue | Undo native, timing hợp lệ, lưu bền | Global undo bắt cả textbox; autosave không outbox | EV-SRC-002/003 | BROKEN |
| J-10 | Conflict/offline | Merge/reload/copy và retry không mất dữ liệu | Chỉ message; conflict lặp, reload có thể mất edit | EV-SRC-002/003 | BROKEN |
| J-11 | Timeline | Kéo/resize/split/merge bằng chuột và bàn phím | Pointer có; keyboard/zoom/snap/mobile precision thiếu | EV-SRC-002, EV-BR-005 | PARTIAL |
| J-12 | Invalid cue | Chặn output lỗi, CTA sửa từng lỗi | QA báo lỗi nhưng quote/confirm render vẫn mở | EV-BR-004 | BROKEN |
| J-13 | Style/preview | Preview sát output, word timing thật | CSS ước lượng đều thời lượng từng từ | EV-SRC-007 | MISLEADING |
| J-14 | Quote source | Canonical từ media probe + workload | Tin duration client; 4K/source cùng 1 credit | EV-BR-004, EV-SRC-008 | BROKEN |
| J-15 | Long video | Giới hạn 120 phút thống nhất | Schema 24h; transcribe 2h; render/diarize thiếu cap route | EV-SRC-005/006/008 | BROKEN |
| J-16 | Running render | Progress, ETA, cancel, artifact atomic | Render cancel có; partial upload terminal có thể orphan | EV-SRC-008/009 | PARTIAL |
| J-17 | AI job conflict | Thấy “chưa áp dụng” và chọn merge | UI báo hoàn tất rồi reload dù worker trả conflict | EV-SRC-002/006 | BROKEN |
| J-18 | History/project | Tìm, mở, duplicate, archive/delete, >100 job | Chỉ project active đầu tiên; scan top-100 rồi filter | EV-SRC-002/009 | BROKEN |
| J-19 | Download | Đúng tên/MIME/range, owner scoped | Owner/range local tốt; R2 redirect không disposition, MKV/WebM là MP4 MIME | EV-SRC-010 | PARTIAL |
| J-20 | EN/mobile | VI+EN A-Z, responsive/keyboard | `/en/` vẫn VI; mobile 390 timeline cắt ngang | EV-BR-005/006 | BROKEN |

## Control registry

| ID | Control | Action/cost | State/error/recovery | Keyboard/mobile | Verdict |
|---|---|---|---|---|---|
| C-01 | Tên project | Debounced save | Không conflict recovery | Text input; global undo can thiệp | BROKEN |
| C-02 | Upload zone | Chọn file/source attach | Không drop, replace cleanup | Label clickable | PARTIAL |
| C-03 | Import transcript | Parse + revision save | Lỗi parse thân thiện | File input | LIVE |
| C-04 | WhisperX | Job 0 credit | Capability/copy/fallback mâu thuẫn | Disabled theo source, không theo capability | BROKEN |
| C-05 | Track select/add/show | Sửa track local | Không rename/delete/reorder/style riêng | Select/button | PARTIAL |
| C-06 | Diarize | Job 0 credit | Không hiển thị quota/conflict apply | Disabled theo capability | PARTIAL |
| C-07 | Translate | Job 0 credit | Không quota/overwrite warning/merge | Language select | PARTIAL |
| C-08 | Search transcript | Filter list | Không find/replace/bulk correction | Keyboard tốt | PARTIAL |
| C-09 | QA issue | Seek/select cue | Không block render/out-of-source rule | Button | PARTIAL |
| C-10 | Timeline cue | Select/drag/resize | Overlap allowed; no snap/zoom | Pointer-centric, mobile clip | BROKEN |
| C-11 | Add/split/merge/delete | Mutate project | Undo full-project | Buttons | PARTIAL |
| C-12 | Cue text/time/speaker | Autosave | Offline/conflict loss | Native undo bị global handler | BROKEN |
| C-13 | Waveform | Seek | Full download; fake fallback không nhãn | Canvas không keyboard action | BROKEN |
| C-14 | Preview transport | Play/seek | Có current word | Buttons; thiếu speed/frame step | PARTIAL |
| C-15 | Preset/style/animation | Typed style | Preview-render parity unknown | Nhiều control, desktop dày | PARTIAL |
| C-16 | Output resolution | Save + quote | Price không đổi theo pixels | Select | BROKEN |
| C-17 | Format/quality/tracks | Save + quote | MIME/codec/cost incomplete | Select/check | PARTIAL |
| C-18 | Quote/confirm | Hold rồi submit | Cho qua QA error; duration client | Modal có cancel | BROKEN |
| C-19 | Job cancel/retry | Refund/rehold | Retry chỉ render; UI history ngắn | Buttons khi có state | PARTIAL |
| C-20 | Project/history manager | Không có | Không recovery/lifecycle | — | MISSING |
| C-21 | EN locale | Absolute API/path | Toàn bộ React literal VI | — | BROKEN |

## Browser matrix

| Viewport/flow | Console/network | Kết quả thật | Verdict |
|---|---|---|---|
| 1440×900 empty | 0 console error | Studio mở, nhưng không project manager | PARTIAL |
| Video thật 3 MB | Video Range + thêm GET 200 toàn file | Attach 10s/864×496; waveform tải trọn file | FAIL performance |
| Import SRT | 0 console error; POST 200 | 3 cue, QA 100, preview/timeline hoạt động | PASS |
| Cue 1–12s | PUT 200 | QA 70 báo 2 overlap nhưng dữ liệu vẫn lưu | PARTIAL |
| Quote source và 4K | POST quote 200 | Cả hai 1 credit; confirm vẫn mở khi QA lỗi | FAIL |
| 390×844 | 0 console error; full video GET lặp | Timeline/cue lane bị cắt ngang | FAIL |
| `/en/autosubvideo` | Requests 200 | Title/copy/control/status vẫn tiếng Việt | FAIL |

