# W1 — CHUỖI LỜI GỌI THÔ của `localize.chay()` (tham chiếu cấp triển khai)

Nguồn: `D:\Viral\resources\app-src\localize.py` (CHỈ ĐỌC). Đây là danh sách **thô**,
**nguyên văn**, theo **đúng thứ tự thực thi** — không phải bản tóm. Bản tóm/hình dạng
đã có ở `docs/auto_scan_video_final/B14_SO_SANH_VIRAL/V6_CHUOI_BUOC.md` (đọc trước,
V6 khớp các mốc dòng dưới đây ở 4/4 điểm đối chiếu được: nhánh scan `else:` tại
`:16381`, dò dải che `if che_chu:` tại `:18204`, lồng tiếng `if lam_long_tieng:`
tại `:19186`, và biên hàm `:15021-20576`).

## Khai độ phủ (bằng số)

- **Biên hàm xác nhận lại:** `def chay(...)` mở tại dòng **15021**; thân hàm kết
  thúc ở `return ket` dòng **20576** (dòng 20577-20578 trống, `def main():` mở ở
  **20579** — xác nhận bằng cách tìm `^def ` tiếp theo sau 15021). Khớp với biên
  V6 đã ghi (`:15021-20576`).
- **Tổng số dòng trong biên:** `20576 - 15021 + 1 = 5556` dòng (gồm dòng trống,
  comment, docstring rải rác).
- **Số câu lệnh cấp 1** (thụt đúng 4 dấu cách, không rỗng, không phải comment
  thuần) trích được: **150 / 150** — tức **100 %** số câu cấp 1 của thân hàm
  (đếm bằng script quét toàn bộ 5556 dòng, không lấy mẫu).
- **Số khối cấp 1** (mở bằng `if`/`elif`/`else`/`try`/`except`/`for`/`while`) có
  trích tiếp cấp 2 (thụt đúng 8 dấu cách, trực tiếp bên trong khối đó): **69**
  khối, sinh ra **282** hàng cấp 2 (đánh số `x.1`, `x.2`, …). Tổng bảng dưới:
  **150 + 282 = 432 hàng**.
- **Khối lớn nhất theo số hàng cấp 2:** #115 `else:` (nhánh KHÔNG có SRT sẵn —
  scan/ASR/OCR + dịch, `:16381-18109`) — 69 hàng cấp-2; #133 `if che_chu:` (dò
  dải che, `:18204-18913`) — 26 hàng; #114 `if srt_co_san...:` (`:16235-16380`)
  — 23 hàng; #141 `if lam_long_tieng:` (`:19186-20463`) — 14 hàng; #144
  `try:` (ghi PROFILE cuối, `:20518-20555`) — 13 hàng.

## ⛔ KHÔNG trích (ngoài phạm vi bảng này)

- **Cấp 3 trở xuống** trong mọi khối — ví dụ ruột của `if _pd is None:`
  (`141.10`, `:19376-19806`, nơi gọi `long_tieng_omnivoice` sáu nhánh engine)
  và ruột `if blur_band and _che_dong:` (`133.26`, `:18689-18913`). Bảng chỉ
  đi tới cấp 2 theo đúng yêu cầu — đây là **thứ tự**, không phải **ruột**.
- **Thân các hàm được định nghĩa ở nơi khác** mà `chay()` gọi trực tiếp:
  `burn_phude` (định nghĩa `:6560`, gọi ở hàng `142.6`, đánh dấu
  `[THÂN Ở HÀM KHÁC: burn_phude:6560]` — W3 lo phần này). `_ghep_track_khop`
  (định nghĩa `:8965`) **không** xuất hiện như một hàng cấp 1/2 riêng vì nó chỉ
  được gọi gián tiếp qua `long_tieng_omnivoice` (`:10705`, gọi `_ghep_track_khop`
  ở `:10977`), bản thân nằm ở cấp 3+ bên trong `141.10`/`141.11` — ngoài phạm
  vi cấp 2 của bảng này.
- **Thân hai hàm lồng bên trong `chay()`** (`def _tg` ở hàng `46`, `:15333-15357`;
  `def _tinh_band_key` ở hàng `88`, `:15799-15857`) — hai hàng này liệt kê như
  một câu lệnh cấp 1 (chữ ký `def`), ⛔ không mở thân vì `def` không phải
  `if`/`try`/`for` nên không thuộc diện "mở khối" theo luật trích.
- **Các hàm phụ trợ khác được gọi rải rác** (`_nap_ocrbox`, `_sua_sub_truoc_burn`,
  `_bo_vi_trung_lien_tiep`, `_khop_giong_theo_gio`, `doc_giong_json`, `_dep_demucs`,
  `doc_srt`, `_thoi_luong`, `_han_la_loi`, `_sk`/`_sk_bat_dau`/`_sk_xuat`, …) —
  chỉ ghi **lời gọi** (nếu nó xuất hiện ở cấp 1/2), ⛔ không mở thân của chúng.
- **`elif`/`except` nối tiếp một khối cấp 1** được đánh số là **hàng cấp-1 riêng**
  (ví dụ hàng `72` `if _xn_dub_only:` / `73` `elif _xn_giu_giong:` / `74` `elif
  xoa_nhac...:` là ba hàng độc lập, không phải `72.x`) — vì chúng thụt đúng 4
  dấu cách như mọi câu cấp 1 khác; đây là quy ước nhất quán trong toàn bảng.

## Bảng — 432 hàng, đúng thứ tự thực thi

| # | dòng | lời gọi / câu lệnh | điều kiện bao quanh |
|---|---|---|---|
| 1 | 15039 | `globals()["_LAST_DICH_THAT_BAI"] = False` |  |
| 2 | 15042 | `try:` |  |
| 2.1 | 15043 | `import chat_luong as _cl0` | `try:` |
| 2.2 | 15044 | `_cl0.dat_lai()` | `try:` |
| 3 | 15045 | `except Exception:` |  |
| 3.1 | 15046 | `pass` | `except Exception:` |
| 4 | 15049 | `try:` |  |
| 4.1 | 15050 | `import capcut_tts as _cc0` | `try:` |
| 4.2 | 15051 | `_cc0.dat_lai()` | `try:` |
| 5 | 15052 | `except Exception:` |  |
| 5.1 | 15053 | `pass` | `except Exception:` |
| 6 | 15079 | `try:` |  |
| 6.1 | 15080 | `_fit_ep = (os.environ.get("DUB_FIT_EP", "") or "").strip()` | `try:` |
| 6.2 | 15081 | `_can_ngan = bool(lam_long_tieng or chi_dub or da_giong)   # (b) có giọng phải đọc kịp khe` | `try:` |
| 6.3 | 15098 | `import ngon_ngu as _nn_fit` | `try:` |
| 6.4 | 15099 | `_fit_mac = (_nn_fit.target_lang() or "").lower()[:2] not in ("", "vi")` | `try:` |
| 6.5 | 15100 | `_fit_dich = (_fit_ep == "1") if _fit_ep in ("0", "1") else _fit_mac   # (a) neo SỐ` | `try:` |
| 6.6 | 15101 | `os.environ["DUB_FIT_LEN"] = "1" if _fit_dich else "0"` | `try:` |
| 6.7 | 15102 | `os.environ["DUB_NEN"] = "1" if _can_ngan else "0"` | `try:` |
| 7 | 15103 | `except Exception:` |  |
| 7.1 | 15104 | `_fit_dich, _can_ngan = False, True` | `except Exception:` |
| 8 | 15121 | `try:` |  |
| 8.1 | 15122 | `if not _VC_WPS_EP:` | `try:` |
| 9 | 15139 | `except Exception:` |  |
| 9.1 | 15140 | `os.environ.pop("DUB_WPS", None)` | `except Exception:` |
| 10 | 15157 | `if _TTS_SOM[0] is not None and os.environ.get("TTS_SOM_DON", "1") != "0":` |  |
| 10.1 | 15158 | `log_fn("ℹ Dọn bộ đọc-trước còn sót từ video trước (job trước kết thúc bất thường).")` | `if _TTS_SOM[0] is not None and os.environ.get("TTS_SOM_DON", "1") != "0":` |
| 10.2 | 15159 | `try:` | `if _TTS_SOM[0] is not None and os.environ.get("TTS_SOM_DON", "1") != "0":` |
| 10.3 | 15161 | `except Exception:` | `if _TTS_SOM[0] is not None and os.environ.get("TTS_SOM_DON", "1") != "0":` |
| 10.4 | 15163 | `_TTS_SOM[0] = None` | `if _TTS_SOM[0] is not None and os.environ.get("TTS_SOM_DON", "1") != "0":` |
| 11 | 15170 | `if (che_chu and zoom and float(zoom) >= 1.3 and not (video_goc and os.path.isfile(video_go…` |  |
| 11.1 | 15172 | `log_fn("⚠ Bạn bật Zoom %.2f× CÙNG Cắt đầu/cuối. Zoom cao cắt mất phần chữ gốc ở đáy khung…` | `if (che_chu and zoom and float(zoom) >= 1.3 and not (video_goc and os.path.isfile(video_go…` |
| 12 | 15175 | `_ocr_video = (video_goc if (video_goc and os.path.isfile(video_goc) and zoom and zoom > 1.…` |  |
| 13 | 15181 | `try:` |  |
| 13.1 | 15182 | `os.environ["OCR_Y_GATE"] = ("%.4f,%.4f" % (float(che_band_manual[0]), float(che_band_manua…` | `try:` |
| 14 | 15184 | `except Exception:` |  |
| 14.1 | 15185 | `os.environ["OCR_Y_GATE"] = ""` | `except Exception:` |
| 15 | 15193 | `os.environ["OCR_LOAI_VUNG"] = ""` |  |
| 16 | 15194 | `if banner_boxes:` |  |
| 16.1 | 15195 | `try:` | `if banner_boxes:` |
| 16.2 | 15216 | `except Exception as _e:` | `if banner_boxes:` |
| 17 | 15226 | `os.environ["CHE_BLUR_FIT_X"] = ""` |  |
| 18 | 15227 | `os.environ["CHE_BAND_FIT"] = ""` |  |
| 19 | 15236 | `if not os.path.isfile(video):` |  |
| 19.1 | 15237 | `log_fn("⚠ Không thấy file video: " + video)` | `if not os.path.isfile(video):` |
| 19.2 | 15238 | `return None` | `if not os.path.isfile(video):` |
| 20 | 15250 | `if model_size == "medium" and os.environ.get("ASR_TURBO", "1") != "0":` |  |
| 20.1 | 15251 | `model_size = "large-v3-turbo"` | `if model_size == "medium" and os.environ.get("ASR_TURBO", "1") != "0":` |
| 20.2 | 15252 | `log_fn("⚡ Config cũ ghi 'medium' → dùng 'large-v3-turbo' (đo thật: nhanh 1.7-2.7× + chính…` | `if model_size == "medium" and os.environ.get("ASR_TURBO", "1") != "0":` |
| 21 | 15255 | `_LARGE_MODELS = {"large", "large-v1", "large-v2", "large-v3"}` |  |
| 22 | 15256 | `if model_size in _LARGE_MODELS:` |  |
| 22.1 | 15257 | `_dur_raw = _thoi_luong(video) or 0` | `if model_size in _LARGE_MODELS:` |
| 22.2 | 15258 | `if _dur_raw > 300:` | `if model_size in _LARGE_MODELS:` |
| 23 | 15270 | `_zoom_ap = 1.0` |  |
| 24 | 15271 | `if zoom_gop and zoom and zoom > 1.0:` |  |
| 24.1 | 15272 | `_zoom_ap = float(zoom)` | `if zoom_gop and zoom and zoom > 1.0:` |
| 24.2 | 15273 | `log_fn("🔎 Gộp ZOOM %.2fx vào lần encode burn (bỏ pre-encode riêng) — che dùng toạ độ GỐC,…` | `if zoom_gop and zoom and zoom > 1.0:` |
| 25 | 15275 | `burn_kw = dict(cat_cuoi=cat_cuoi,` |  |
| 26 | 15280 | `globals()["_LAST_VIDEO_SLOW"] = 1.0   # reset: chỉ _ghep_track_khop (dub MỚI) mới đặt S; c…` |  |
| 27 | 15281 | `globals()["_LAST_TIME_WARP"] = None   # reset warp per-segment (tránh dùng lại warp cũ ở c…` |  |
| 28 | 15282 | `globals()["_LAST_DUB_ONSETS"] = None  # reset bản đồ vị-trí dub (cache-hit/no-dub → giữ ph…` |  |
| 29 | 15287 | `globals()["_LAST_ASR_PARTIAL"] = None  # reset tiến độ ASR dở (worker bền chạy 30 job/tiến…` |  |
| 30 | 15288 | `globals()["_KET_ASR_HONG"] = None      # reset cờ "ASR chết vì máy/thư viện" (cùng lý do t…` |  |
| 31 | 15292 | `try:` |  |
| 31.1 | 15293 | `phu_de.reset_gpu_moi_job(log_fn)` | `try:` |
| 32 | 15294 | `except Exception:` |  |
| 32.1 | 15295 | `pass` | `except Exception:` |
| 33 | 15301 | `try:` |  |
| 33.1 | 15302 | `xu_ly_video.reset_encoder_moi_job()` | `try:` |
| 34 | 15303 | `except Exception:` |  |
| 34.1 | 15304 | `pass` | `except Exception:` |
| 35 | 15311 | `globals()["_OCR_JOB_NAY"] = False` |  |
| 36 | 15312 | `_sk_bat_dau(video)                     # mở SỔ KẾ TOÁN CÂU mới cho video này (xem _sk_xuat…` |  |
| 37 | 15318 | `globals()["_VC_SPEED"] = float(speed or 1.0)` |  |
| 38 | 15321 | `import time as _tm` |  |
| 39 | 15322 | `_TG = [_tm.time()]` |  |
| 40 | 15323 | `_PROF_T0 = _tm.time()` |  |
| 41 | 15324 | `_PROF_STAGES = []     # [(stage, giây)] → ghi jsonl cuối render để tích luỹ qua NHIỀU vide…` |  |
| 42 | 15325 | `_MOC_AUDIO.clear()    # mốc con trong chặng ghép — xem khối `_moc` trên `burn_phude`` |  |
| 43 | 15328 | `_r_chac_khong_chu = [False]` |  |
| 44 | 15330 | `os.environ.setdefault("VC_PROFILE_LOG", os.path.join(` |  |
| 45 | 15332 | `_RES = _ResMon(); _RES.start()   # đo CPU/GPU/RAM/VRAM mỗi stage → biết tài nguyên rảnh (o…` |  |
| 46 | 15333 | `def _tg(_nhan, _ma=None):` |  |
| 47 | 15358 | `print("STAGE:batdau", flush=True)   # mốc mở pipeline — web_app đặt bước "Nghe/Đọc chữ"` |  |
| 48 | 15361 | `co_extra_hinh = bool(extra_vf or wm_path or bg_path or abs(float(speed or 1.0) - 1.0) > 1e…` |  |
| 49 | 15362 | `import ngon_ngu` |  |
| 50 | 15363 | `tgt = ngon_ngu.target_lang()` |  |
| 51 | 15364 | `plat = ngon_ngu.platform_tu_duong_dan(video)` |  |
| 52 | 15367 | `_src_la_doan = False` |  |
| 53 | 15368 | `if src_lang is None and srt_co_san:` |  |
| 53.1 | 15369 | `src_lang = "zh"   # B5: có SRT dịch sẵn = luồng zh→vi (dịch thủ công) → ép zh, KHÔNG suy t…` | `if src_lang is None and srt_co_san:` |
| 54 | 15370 | `if src_lang is None:` |  |
| 54.1 | 15373 | `if _co_chu_han(os.path.basename(video)):` | `if src_lang is None:` |
| 54.2 | 15375 | `else:` | `if src_lang is None:` |
| 55 | 15464 | `if engine == "google":` |  |
| 55.1 | 15465 | `engine = "gemini"` | `if engine == "google":` |
| 56 | 15473 | `cung_ngon_ngu = (src_lang == tgt) and not _src_la_doan` |  |
| 57 | 15474 | `if (src_lang == tgt) and _src_la_doan:` |  |
| 57.1 | 15475 | `log_fn("ℹ Nguồn '%s' mới chỉ là PHỎNG ĐOÁN (chưa nghe được audio) và trùng đích → VẪN DỊCH…` | `if (src_lang == tgt) and _src_la_doan:` |
| 58 | 15479 | `if cung_ngon_ngu:` |  |
| 58.1 | 15480 | `log_fn("ℹ Nguồn cùng ngôn ngữ đích (%s) — KHÔNG dịch; %s." % (` | `if cung_ngon_ngu:` |
| 59 | 15482 | `import cache_artifact as _ca` |  |
| 60 | 15504 | `ten = srt_stem or os.path.splitext(os.path.basename(video))[0]` |  |
| 61 | 15505 | `thu_muc = os.path.dirname(os.path.abspath(video))` |  |
| 62 | 15506 | `zh_srt = os.path.join(thu_muc, ten + ".zh.srt")` |  |
| 63 | 15507 | `vi_srt = os.path.join(thu_muc, ten + ".vi.srt")` |  |
| 64 | 15513 | `_ptmp = "_p%d" % os.getpid()` |  |
| 65 | 15514 | `nhac_da_tach = ""   # nếu tách trước ASR thì giữ lại nhạc nền để dùng cho lồng tiếng` |  |
| 66 | 15521 | `_xn_kq = [None]   # holder kết quả demucs nền (đường dẫn wav CHỈ GIỌNG, hoặc None nếu tách…` |  |
| 67 | 15522 | `_xn_th = None` |  |
| 68 | 15546 | `try:` |  |
| 68.1 | 15547 | `_gv_xn = None if goc_vol is None else max(0.0, min(1.0, float(goc_vol)))` | `try:` |
| 69 | 15548 | `except (TypeError, ValueError):` |  |
| 69.1 | 15549 | `_gv_xn = None` | `except (TypeError, ValueError):` |
| 70 | 15550 | `_xn_giu_giong = bool(xoa_nhac and lam_long_tieng and not chi_asr and not chi_dich` |  |
| 71 | 15552 | `_xn_dub_only = bool(xoa_nhac and lam_long_tieng and not chi_asr and not chi_dich` |  |
| 72 | 15554 | `if _xn_dub_only:` |  |
| 72.1 | 15555 | `log_fn("🔇 'Xoá nhạc nền' + lồng tiếng (âm lượng gốc 0%%) → audio ra CHỈ còn giọng lồng tiế…` | `if _xn_dub_only:` |
| 73 | 15557 | `elif _xn_giu_giong:` |  |
| 73.1 | 15558 | `log_fn("🎵 'Xoá nhạc nền' + lồng tiếng, giữ giọng gốc %d%% → tách demucs lấy GIỌNG (bỏ nhạc…` | `elif _xn_giu_giong:` |
| 74 | 15560 | `elif xoa_nhac and not burn and not chi_asr and not chi_dich:` |  |
| 74.1 | 15561 | `log_fn("⚠ 'Xoá nhạc nền (giữ giọng gốc)' sẽ KHÔNG chạy cho video này — video này không bur…` | `elif xoa_nhac and not burn and not chi_asr and not chi_dich:` |
| 75 | 15567 | `if xoa_nhac and not lam_long_tieng and not chi_asr and not chi_dich \` |  |
| 75.1 | 15569 | `import threading as _th_xn` | `if xoa_nhac and not lam_long_tieng and not chi_asr and not chi_dich \` |
| 75.2 | 15595 | `try:` | `if xoa_nhac and not lam_long_tieng and not chi_asr and not chi_dich \` |
| 75.3 | 15597 | `except Exception:` | `if xoa_nhac and not lam_long_tieng and not chi_asr and not chi_dich \` |
| 75.4 | 15599 | `_xn_can_khe = (not _xn_gpu) or os.environ.get("XOA_NHAC_KHE_CPU") == "1"` | `if xoa_nhac and not lam_long_tieng and not chi_asr and not chi_dich \` |
| 75.5 | 15601 | `def _xn_run():` | `if xoa_nhac and not lam_long_tieng and not chi_asr and not chi_dich \` |
| 75.6 | 15611 | `_xn_th = _th_xn.Thread(target=_xn_run, daemon=True)` | `if xoa_nhac and not lam_long_tieng and not chi_asr and not chi_dich \` |
| 75.7 | 15612 | `_xn_th.start()` | `if xoa_nhac and not lam_long_tieng and not chi_asr and not chi_dich \` |
| 75.8 | 15613 | `log_fn("🎚 Tách nhạc nền (demucs) chạy NỀN — song song với nghe/dịch (%s)."` | `if xoa_nhac and not lam_long_tieng and not chi_asr and not chi_dich \` |
| 76 | 15650 | `_tn_kq = [None]` |  |
| 77 | 15651 | `_tn_th = None` |  |
| 78 | 15652 | `if (lam_tach_nhac and not tach_truoc and not chi_asr and not chi_dich` |  |
| 78.1 | 15654 | `try:` | `if (lam_tach_nhac and not tach_truoc and not chi_asr and not chi_dich` |
| 78.2 | 15656 | `except Exception:` | `if (lam_tach_nhac and not tach_truoc and not chi_asr and not chi_dich` |
| 78.3 | 15658 | `try:` | `if (lam_tach_nhac and not tach_truoc and not chi_asr and not chi_dich` |
| 78.4 | 15660 | `except ValueError:` | `if (lam_tach_nhac and not tach_truoc and not chi_asr and not chi_dich` |
| 78.5 | 15662 | `try:` | `if (lam_tach_nhac and not tach_truoc and not chi_asr and not chi_dich` |
| 78.6 | 15664 | `except Exception:` | `if (lam_tach_nhac and not tach_truoc and not chi_asr and not chi_dich` |
| 78.7 | 15675 | `_tn_du_vram = True` | `if (lam_tach_nhac and not tach_truoc and not chi_asr and not chi_dich` |
| 78.8 | 15676 | `try:` | `if (lam_tach_nhac and not tach_truoc and not chi_asr and not chi_dich` |
| 78.9 | 15678 | `except ValueError:` | `if (lam_tach_nhac and not tach_truoc and not chi_asr and not chi_dich` |
| 78.10 | 15680 | `if _tn_gpu and _tn_can > 0:` | `if (lam_tach_nhac and not tach_truoc and not chi_asr and not chi_dich` |
| 78.11 | 15693 | `if _tn_gpu and _tn_ram >= _tn_nguong and _tn_du_vram:` | `if (lam_tach_nhac and not tach_truoc and not chi_asr and not chi_dich` |
| 78.12 | 15714 | `elif _tn_gpu:` | `if (lam_tach_nhac and not tach_truoc and not chi_asr and not chi_dich` |
| 79 | 15723 | `try:` |  |
| 79.1 | 15724 | `_r_br = subprocess.run([xu_ly_video.tim_exe("ffprobe"), "-v", "error", "-show_entries",` | `try:` |
| 79.2 | 15727 | `_br = int((_r_br.stdout or "0").strip() or 0)` | `try:` |
| 79.3 | 15728 | `if _br > 0:` | `try:` |
| 80 | 15730 | `except Exception:` |  |
| 80.1 | 15731 | `os.environ.pop("VC_SRC_KBPS", None)      # không đo được → bỏ env → _enc_video giữ cq 25 n…` | `except Exception:` |
| 81 | 15732 | `_vhash = _ca.video_hash(video, log_fn=log_fn)` |  |
| 82 | 15736 | `_vhash_scan = os.environ.get("VC_SCAN_VHASH") or _vhash` |  |
| 83 | 15743 | `_cdd_kq = [None]` |  |
| 84 | 15744 | `_cdd_th = None` |  |
| 85 | 15750 | `_kick_nen = os.environ.get("CHE_DONG_KICK_NEN")` |  |
| 86 | 15751 | `_nen_can = (_kick_nen == "1") or (_kick_nen != "0" and not _la_tieng_trung(src_lang))` |  |
| 87 | 15756 | `if che_chu and os.environ.get("CHE_DONG") == "1" and _nen_can and not chi_asr and not chi_…` |  |
| 87.1 | 15766 | `_bk_early = _ca.tinh_key("boxes", _vhash=_vhash_scan, kvbx="x1", tgt=tgt,` | `if che_chu and os.environ.get("CHE_DONG") == "1" and _nen_can and not chi_asr and not chi_…` |
| 87.2 | 15772 | `if not (_bk_early and _ca.lay(_bk_early, ".boxes.json")):   # chưa có cache sẵn → mới cần…` | `if che_chu and os.environ.get("CHE_DONG") == "1" and _nen_can and not chi_asr and not chi_…` |
| 88 | 15799 | `def _tinh_band_key(_vi_srt=None):` |  |
| 89 | 15858 | `_ct_som_kq, _ct_som_th = [None], None` |  |
| 90 | 15859 | `try:` |  |
| 90.1 | 15860 | `_bk_som = (_tinh_band_key() if (_vhash_scan and che_chu` | `try:` |
| 90.2 | 15863 | `_can_do_dai = bool(_bk_som) and not _ca.lay(_bk_som, ".band.json")` | `try:` |
| 91 | 15864 | `except Exception:` |  |
| 91.1 | 15865 | `_can_do_dai = False        # nghi ngờ → giữ hành vi cũ, KHÔNG tự ý chạy thêm việc nặng` | `except Exception:` |
| 92 | 15866 | `if (che_chu and not chi_asr and not chi_dich and (dich_lai or _can_do_dai)` |  |
| 92.1 | 15868 | `import threading as _th_cts` | `if (che_chu and not chi_asr and not chi_dich and (dich_lai or _can_do_dai)` |
| 92.2 | 15870 | `def _cts_run():` | `if (che_chu and not chi_asr and not chi_dich and (dich_lai or _can_do_dai)` |
| 92.3 | 15880 | `_ct_som_th = _th_cts.Thread(target=_cts_run, daemon=True)` | `if (che_chu and not chi_asr and not chi_dich and (dich_lai or _can_do_dai)` |
| 92.4 | 15881 | `_ct_som_th.start()` | `if (che_chu and not chi_asr and not chi_dich and (dich_lai or _can_do_dai)` |
| 92.5 | 15882 | `log_fn("⚡ Dò dải che TĨNH chạy NỀN — song song với nghe/dịch (CPU rảnh vì ASR đi mạng).")` | `if (che_chu and not chi_asr and not chi_dich and (dich_lai or _can_do_dai)` |
| 93 | 15911 | `_KEY_VER_SCAN = "s5"` |  |
| 94 | 15923 | `_kw_vung = {}` |  |
| 95 | 15924 | `for _k_vung, _e_vung in (("e_ygate", "OCR_Y_GATE"), ("e_loaivung", "OCR_LOAI_VUNG")):` |  |
| 95.1 | 15925 | `_v_vung = (os.environ.get(_e_vung, "") or "").strip()` | `for _k_vung, _e_vung in (("e_ygate", "OCR_Y_GATE"), ("e_loaivung", "OCR_LOAI_VUNG")):` |
| 95.2 | 15926 | `if _v_vung:` | `for _k_vung, _e_vung in (("e_ygate", "OCR_Y_GATE"), ("e_loaivung", "OCR_LOAI_VUNG")):` |
| 96 | 15935 | `_kw_ccwpl = {}` |  |
| 97 | 15936 | `try:` |  |
| 97.1 | 15937 | `import capcut_asr as _cc_key` | `try:` |
| 97.2 | 15938 | `_w_key, _m_key = _cc_key._thong_so_dong(_cc_key.lang_code(src_lang or ""))` | `try:` |
| 97.3 | 15939 | `if (_w_key, _m_key) != (15, 1):` | `try:` |
| 98 | 15941 | `except Exception:` |  |
| 98.1 | 15942 | `_kw_ccwpl = {}` | `except Exception:` |
| 99 | 15943 | `_scan_key = _ca.tinh_key("scan", _vhash=_vhash_scan, model=model_size, src=(src_lang or ""…` |  |
| 100 | 15983 | `_obk = _ca.tinh_key("ocrbox", _vhash=_vhash_scan, kvob="o1", **_kw_vung,` |  |
| 101 | 15987 | `_ai_prov_model = ""` |  |
| 102 | 16010 | `_tm_hash = ""` |  |
| 103 | 16011 | `try:    # băm NỘI DUNG (không dùng mtime: copy/pull làm mtime đổi mà nội dung y nguyên → m…` |  |
| 103.1 | 16012 | `import glob as _glob_tm` | `try:    # băm NỘI DUNG (không dùng mtime: copy/pull làm mtime đổi mà nội dung y nguyên → m…` |
| 103.2 | 16013 | `_h_tm = hashlib.sha1()` | `try:    # băm NỘI DUNG (không dùng mtime: copy/pull làm mtime đổi mà nội dung y nguyên → m…` |
| 103.3 | 16014 | `for _f_tm in sorted(_glob_tm.glob(os.path.join("translation_memory", "*.md"))):` | `try:    # băm NỘI DUNG (không dùng mtime: copy/pull làm mtime đổi mà nội dung y nguyên → m…` |
| 103.4 | 16018 | `_tm_hash = _h_tm.hexdigest()[:12]` | `try:    # băm NỘI DUNG (không dùng mtime: copy/pull làm mtime đổi mà nội dung y nguyên → m…` |
| 104 | 16019 | `except Exception:` |  |
| 104.1 | 16020 | `_tm_hash = ""      # không đọc được → coi như không có từ điển; KHÔNG chặn render` | `except Exception:` |
| 105 | 16067 | `_KEY_VER_DICH = "h11"  # h10 (26/08): prompt cấm chép tiền tố + mã-méo-cướp-khoá + xin-thi…` |  |
| 106 | 16068 | `_trans_key = _ca.tinh_key(` |  |
| 107 | 16110 | `_srt_key = None` |  |
| 108 | 16111 | `if _vhash and not srt_co_san and not chi_asr:` |  |
| 108.1 | 16112 | `try:` | `if _vhash and not srt_co_san and not chi_asr:` |
| 108.2 | 16132 | `e_lo=os.environ.get("AI_LO", "300"),` | `if _vhash and not srt_co_san and not chi_asr:` |
| 108.3 | 16133 | `e_quytac=os.environ.get("DICH_QUY_TAC", ""), e_tm=_tm_hash,   # xem _trans_key` | `if _vhash and not srt_co_san and not chi_asr:` |
| 108.4 | 16190 | `except Exception as _e:` | `if _vhash and not srt_co_san and not chi_asr:` |
| 109 | 16194 | `_zh_tu_scan_cache = False   # đánh dấu: zh_srt vừa copy từ SCAN-CACHE đúng (không phải fil…` |  |
| 110 | 16197 | `if _trans_key and not srt_co_san and not dich_lai and not chi_asr:` |  |
| 110.1 | 16198 | `try:` | `if _trans_key and not srt_co_san and not dich_lai and not chi_asr:` |
| 110.2 | 16226 | `except Exception:` | `if _trans_key and not srt_co_san and not dich_lai and not chi_asr:` |
| 111 | 16232 | `speaker_of = None` |  |
| 112 | 16233 | `_spk_time = None` |  |
| 113 | 16234 | `segs = None   # segs Whisper (nhánh scan gán); cache-HIT-srt để None → gate diarize dùng s…` |  |
| 114 | 16235 | `if srt_co_san and os.path.isfile(srt_co_san):` |  |
| 114.1 | 16237 | `_vi_rows = doc_srt(srt_co_san)` | `if srt_co_san and os.path.isfile(srt_co_san):` |
| 114.2 | 16242 | `_zh_rows = None` | `if srt_co_san and os.path.isfile(srt_co_san):` |
| 114.3 | 16243 | `if _zh_tu_scan_cache and os.path.isfile(zh_srt):` | `if srt_co_san and os.path.isfile(srt_co_san):` |
| 114.4 | 16250 | `segs_vi = [(st, en, ((_zh_rows[i] if _zh_rows else ""), vi))` | `if srt_co_san and os.path.isfile(srt_co_san):` |
| 114.5 | 16252 | `vi_srt = srt_co_san` | `if srt_co_san and os.path.isfile(srt_co_san):` |
| 114.6 | 16253 | `log_fn(f"📄 Dùng phụ đề đã sửa: {len(segs_vi)} câu.")` | `if srt_co_san and os.path.isfile(srt_co_san):` |
| 114.7 | 16260 | `_sk("0. từ SRT có sẵn (prefetch/sửa tay)", len(segs_vi),` | `if srt_co_san and os.path.isfile(srt_co_san):` |
| 114.8 | 16270 | `try:` | `if srt_co_san and os.path.isfile(srt_co_san):` |
| 114.9 | 16272 | `except Exception:` | `if srt_co_san and os.path.isfile(srt_co_san):` |
| 114.10 | 16274 | `if _ly_do_srt:` | `if srt_co_san and os.path.isfile(srt_co_san):` |
| 114.11 | 16277 | `else:` | `if srt_co_san and os.path.isfile(srt_co_san):` |
| 114.12 | 16288 | `if not segs_vi:` | `if srt_co_san and os.path.isfile(srt_co_san):` |
| 114.13 | 16299 | `_cuu_h, _bo_h, _kt_h = 0, 0, 0` | `if srt_co_san and os.path.isfile(srt_co_san):` |
| 114.14 | 16300 | `if _han_la_loi(tgt):` | `if srt_co_san and os.path.isfile(srt_co_san):` |
| 114.15 | 16312 | `if _cuu_h:` | `if srt_co_san and os.path.isfile(srt_co_san):` |
| 114.16 | 16315 | `if _bo_h:` | `if srt_co_san and os.path.isfile(srt_co_san):` |
| 114.17 | 16330 | `_cn_env_c = os.environ.get("SUB_CHIA_NHIP", "")` | `if srt_co_san and os.path.isfile(srt_co_san):` |
| 114.18 | 16331 | `_cho_chia_c = (_cn_env_c == "1") or (` | `if srt_co_san and os.path.isfile(srt_co_san):` |
| 114.19 | 16333 | `if _cho_chia_c and any((en - st) > 8.0 or len(str(v)) > 80 for st, en, (z, v) in segs_vi):` | `if srt_co_san and os.path.isfile(srt_co_san):` |
| 114.20 | 16358 | `_hien, _co_doi = _sua_sub_truoc_burn(segs_vi, log_fn)` | `if srt_co_san and os.path.isfile(srt_co_san):` |
| 114.21 | 16363 | `if _co_doi or _cuu_h or _bo_h:` | `if srt_co_san and os.path.isfile(srt_co_san):` |
| 114.22 | 16379 | `_ocr_boxes = []` | `if srt_co_san and os.path.isfile(srt_co_san):` |
| 114.23 | 16380 | `_ocr_boxes = _nap_ocrbox(_obk, _ca, dich_lai, log_fn)` | `if srt_co_san and os.path.isfile(srt_co_san):` |
| 115 | 16381 | `else:` |  |
| 115.1 | 16385 | `asr_input = _ocr_video` | `else:` |
| 115.2 | 16386 | `if tach_truoc:` | `else:` |
| 115.3 | 16411 | `def _suy_co_engine():` | `else:` |
| 115.4 | 16418 | `dung_gemini = _suy_co_engine()` | `else:` |
| 115.5 | 16432 | `dich = None` | `else:` |
| 115.6 | 16441 | `_gem_stream = None` | `else:` |
| 115.7 | 16442 | `_gs_env = os.environ.get("GEMINI_STREAM", "")` | `else:` |
| 115.8 | 16443 | `_is_whisper = (os.environ.get("ASR_ENGINE", "").lower() == "whisper")` | `else:` |
| 115.9 | 16452 | `try:` | `else:` |
| 115.10 | 16455 | `except ValueError:` | `else:` |
| 115.11 | 16473 | `if _gs_env == "1":` | `else:` |
| 115.12 | 16475 | `elif _gs_env == "auto":   # opt-in: video đủ dài (+ whisper thì cần GPU đủ VRAM; OCR chạy…` | `else:` |
| 115.13 | 16478 | `elif _gs_env == "0":` | `else:` |
| 115.14 | 16480 | `else:` | `else:` |
| 115.15 | 16500 | `if (_gs_on and dung_gemini and not chi_asr and not chi_dich and not dich_lai):` | `else:` |
| 115.16 | 16528 | `if _gem_stream:` | `else:` |
| 115.17 | 16539 | `_ocr_boxes = []      # HỢP NHẤT: OCR đọc text + trả HỘP vị-trí mỗi câu vào đây → blur động…` | `else:` |
| 115.18 | 16542 | `segs = None` | `else:` |
| 115.19 | 16543 | `_scan_lock = False   # True = job NÀY giành lock scan → phải nha_lock sau khi lưu` | `else:` |
| 115.20 | 16544 | `if _scan_key and not dich_lai:` | `else:` |
| 115.21 | 16591 | `_lock_da_nha = [False]` | `else:` |
| 115.22 | 16592 | `_hb_stop = threading.Event()` | `else:` |
| 115.23 | 16593 | `def _hb_lock():` | `else:` |
| 115.24 | 16597 | `if _scan_lock and _scan_key:` | `else:` |
| 115.25 | 16599 | `def _nha_lock_1lan():` | `else:` |
| 115.26 | 16605 | `speaker_of = None   # ĐA GIỌNG: khởi tạo trước cache-branch (cache HIT không chạy diarize…` | `else:` |
| 115.27 | 16606 | `try:` | `else:` |
| 115.28 | 16788 | `finally:` | `else:` |
| 115.29 | 16790 | `if chi_asr:` | `else:` |
| 115.30 | 16812 | `if cung_ngon_ngu and segs and tgt != "zh":` | `else:` |
| 115.31 | 16833 | `if cung_ngon_ngu and segs and os.environ.get("NGUON_THEO_CHU", "1") != "0":` | `else:` |
| 115.32 | 16866 | `_vibatch = None` | `else:` |
| 115.33 | 16867 | `if vi_co_san and os.path.isfile(vi_co_san):` | `else:` |
| 115.34 | 16872 | `if _vibatch is not None:` | `else:` |
| 115.35 | 16908 | `elif cung_ngon_ngu:` | `else:` |
| 115.36 | 16955 | `elif dung_gemini:   # GEMINI WEB (DUY NHẤT) — dịch SAU ASR qua subprocess nền; sót → Gemin…` | `else:` |
| 115.37 | 17764 | `segs_vi = _bo_vi_trung_lien_tiep(segs_vi, log_fn)   # gộp cue dịch TRÙNG liên tiếp (OCR đọ…` | `else:` |
| 115.38 | 17778 | `_cn_env = os.environ.get("SUB_CHIA_NHIP", "")` | `else:` |
| 115.39 | 17781 | `_cho_chia = (_cn_env == "1") or (_cn_env != "0" and not globals().get("_OCR_JOB_NAY"))` | `else:` |
| 115.40 | 17792 | `if _cho_chia and _cn_env != "1":` | `else:` |
| 115.41 | 17804 | `if _cho_chia and any((en - st) > 8.0 or len(str(vi)) > 80 for st, en, (zh, vi) in segs_vi)…` | `else:` |
| 115.42 | 17817 | `if not segs_vi and segs:` | `else:` |
| 115.43 | 17826 | `_asr_cut = False` | `else:` |
| 115.44 | 17827 | `try:` | `else:` |
| 115.45 | 17837 | `except Exception:` | `else:` |
| 115.46 | 17854 | `try:` | `else:` |
| 115.47 | 17863 | `except Exception:` | `else:` |
| 115.48 | 17865 | `with open(zh_srt, "w", encoding="utf-8") as f:` | `else:` |
| 115.49 | 17881 | `try:` | `else:` |
| 115.50 | 17892 | `except Exception as _e_n2:` | `else:` |
| 115.51 | 17894 | `try:` | `else:` |
| 115.52 | 17907 | `except Exception as _e_san:` | `else:` |
| 115.53 | 17909 | `segs_hien, _ = _sua_sub_truoc_burn(segs_vi, log_fn)` | `else:` |
| 115.54 | 17910 | `try:` | `else:` |
| 115.55 | 17919 | `except Exception:` | `else:` |
| 115.56 | 17928 | `try:` | `else:` |
| 115.57 | 17936 | `except Exception:` | `else:` |
| 115.58 | 17940 | `_bak_truoc_ghi_de(vi_srt, sum(1 for _s, _e, (_z, _v) in segs_hien if (_v or "").strip()),…` | `else:` |
| 115.59 | 17941 | `with open(vi_srt, "w", encoding="utf-8") as f:` | `else:` |
| 115.60 | 17949 | `_trong_ct = sum(1 for _st, _en, (_zh, _vi) in segs_vi if not (_vi or "").strip())` | `else:` |
| 115.61 | 17950 | `_tong_ct = len(segs_vi) or 1` | `else:` |
| 115.62 | 17953 | `_sk("7. CÓ CHỮ để hiện + để đọc", _tong_ct - _trong_ct,` | `else:` |
| 115.63 | 17955 | `_sk_xuat(log_fn, video)` | `else:` |
| 115.64 | 17956 | `if _trong_ct and _trong_ct / _tong_ct >= 0.05:` | `else:` |
| 115.65 | 17961 | `else:` | `else:` |
| 115.66 | 17966 | `_dich_hong = False` | `else:` |
| 115.67 | 17967 | `if not cung_ngon_ngu:` | `else:` |
| 115.68 | 18090 | `if _srt_key and not _dich_hong and not _asr_cut:   # MISS → lưu cache cho lần xử lý LẶP sa…` | `else:` |
| 115.69 | 18096 | `if _trans_key and not _dich_hong and not _asr_cut:   # TRANS-CACHE: lưu bản dịch theo SCAN…` | `else:` |
| 116 | 18110 | `try:` |  |
| 116.1 | 18111 | `_sk_xuat(log_fn, video)` | `try:` |
| 117 | 18112 | `except Exception:` |  |
| 117.1 | 18113 | `pass          # sổ hỏng KHÔNG được làm hỏng render (cùng nguyên tắc với `_sk`)` | `except Exception:` |
| 118 | 18119 | `ket = {"zh_srt": zh_srt, "vi_srt": vi_srt, "video_phude": "", "video_longtieng": "",` |  |
| 119 | 18123 | `if chi_dich:            # PREFETCH DỊCH: đã có vi.srt (+ trans-cache) → DỪNG, KHÔNG dò-dải…` |  |
| 119.1 | 18129 | `if da_giong and not doc_giong_json(video):` | `if chi_dich:            # PREFETCH DỊCH: đã có vi.srt (+ trans-cache) → DỪNG, KHÔNG dò-dải…` |
| 119.2 | 18134 | `return ket` | `if chi_dich:            # PREFETCH DỊCH: đã có vi.srt (+ trans-cache) → DỪNG, KHÔNG dò-dải…` |
| 120 | 18137 | `import gc` |  |
| 121 | 18138 | `phu_de._MODEL = None` |  |
| 122 | 18139 | `gc.collect()` |  |
| 123 | 18142 | `try:` |  |
| 123.1 | 18143 | `import torch as _tk` | `try:` |
| 123.2 | 18144 | `if _tk.cuda.is_available():` | `try:` |
| 124 | 18146 | `except Exception:` |  |
| 124.1 | 18147 | `pass` | `except Exception:` |
| 125 | 18154 | `_segs_diar = None` |  |
| 126 | 18155 | `if da_giong:` |  |
| 126.1 | 18156 | `if segs:` | `if da_giong:` |
| 126.2 | 18158 | `elif segs_vi:` | `if da_giong:` |
| 127 | 18164 | `_gj = doc_giong_json(video) if (da_giong and os.environ.get("DA_GIONG_BO_FILE") != "1") el…` |  |
| 128 | 18165 | `if _gj and _segs_diar:` |  |
| 128.1 | 18166 | `speaker_of = _khop_giong_theo_gio(_gj, _segs_diar)` | `if _gj and _segs_diar:` |
| 128.2 | 18167 | `if speaker_of:` | `if _gj and _segs_diar:` |
| 129 | 18172 | `_asr_eng = os.environ.get("ASR_ENGINE", "").lower()` |  |
| 130 | 18173 | `if da_giong and _segs_diar and _asr_eng != "ocr":` |  |
| 130.1 | 18174 | `try:` | `if da_giong and _segs_diar and _asr_eng != "ocr":` |
| 130.2 | 18192 | `except Exception as _e:` | `if da_giong and _segs_diar and _asr_eng != "ocr":` |
| 131 | 18195 | `elif da_giong:` |  |
| 131.1 | 18196 | `log_fn("ℹ '2 giọng' cần nguồn = Giọng nói/Whisper (video có tiếng để phân giọng) → dùng 1…` | `elif da_giong:` |
| 132 | 18200 | `blur_band = blur_segs = None` |  |
| 133 | 18204 | `if che_chu:` |  |
| 133.1 | 18216 | `_ob_som = locals().get("_ocr_boxes") or []` | `if che_chu:` |
| 133.2 | 18217 | `try:` | `if che_chu:` |
| 133.3 | 18220 | `except ValueError:` | `if che_chu:` |
| 133.4 | 18222 | `_co_box_giua_som = any(len(s) >= 4 and float(s[2]) >= _tren_ng_som and float(s[3]) <= _day…` | `if che_chu:` |
| 133.5 | 18230 | `_auto_dong_som = len(_ob_som) >= 2 and os.environ.get("CHE_DONG_AUTO", "0") != "0" and _co…` | `if che_chu:` |
| 133.6 | 18231 | `_env_cd_som = os.environ.get("CHE_DONG", "")` | `if che_chu:` |
| 133.7 | 18232 | `_che_dong_som = (_env_cd_som == "1") or (_auto_dong_som and _env_cd_som != "0")` | `if che_chu:` |
| 133.8 | 18233 | `if os.environ.get("CHE_PATCH") == "1" and _env_cd_som != "1":` | `if che_chu:` |
| 133.9 | 18235 | `_bo_qua_dai_tinh = _che_dong_som and len(_ob_som) >= 2` | `if che_chu:` |
| 133.10 | 18236 | `if _bo_qua_dai_tinh:` | `if che_chu:` |
| 133.11 | 18239 | `else:` | `if che_chu:` |
| 133.12 | 18398 | `_ob0 = locals().get("_ocr_boxes") or []` | `if che_chu:` |
| 133.13 | 18399 | `_auto_dong = False` | `if che_chu:` |
| 133.14 | 18419 | `try:` | `if che_chu:` |
| 133.15 | 18421 | `except ValueError:` | `if che_chu:` |
| 133.16 | 18423 | `try:` | `if che_chu:` |
| 133.17 | 18425 | `except ValueError:` | `if che_chu:` |
| 133.18 | 18428 | `_co_box_giua = any(len(s) >= 4 and float(s[2]) >= _tren_ng and float(s[3]) <= _day_ng for…` | `if che_chu:` |
| 133.19 | 18429 | `if len(_ob0) >= 2 and os.environ.get("CHE_DONG_AUTO", "0") != "0" and _co_box_giua:   # mặ…` | `if che_chu:` |
| 133.20 | 18431 | `_env_cd = os.environ.get("CHE_DONG", "")` | `if che_chu:` |
| 133.21 | 18432 | `_che_dong = (_env_cd == "1") or (_auto_dong and _env_cd != "0")` | `if che_chu:` |
| 133.22 | 18437 | `if os.environ.get("CHE_PATCH") == "1" and _env_cd != "1":` | `if che_chu:` |
| 133.23 | 18447 | `if blur_band and not _che_dong and os.environ.get("CHE_FIT_NGANG", "1") != "0":` | `if che_chu:` |
| 133.24 | 18622 | `_chi_day = os.environ.get("CHE_DAY_CHI_DAY") == "1"` | `if che_chu:` |
| 133.25 | 18623 | `if (blur_band and os.environ.get("CHE_DAY", "1") != "0" and not _che_dong` | `if che_chu:` |
| 133.26 | 18689 | `if blur_band and _che_dong:   # blur ĐỘNG (bật tay CHE_DONG=1 HOẶC auto khi sub không ở đá…` | `if che_chu:` |
| 134 | 18914 | `if (che_chu and blur_band and len(blur_band) >= 2` |  |
| 134.1 | 18916 | `_obp = locals().get("_ocr_boxes") or []` | `if (che_chu and blur_band and len(blur_band) >= 2` |
| 134.2 | 18917 | `if len(_obp) >= 2:` | `if (che_chu and blur_band and len(blur_band) >= 2` |
| 135 | 19033 | `if che_chu and blur_band is None and blur_segs is None and os.environ.get("CHE_OCR_BOX_FAL…` |  |
| 135.1 | 19034 | `_obf = locals().get("_ocr_boxes") or []` | `if che_chu and blur_band is None and blur_segs is None and os.environ.get("CHE_OCR_BOX_FAL…` |
| 135.2 | 19035 | `if len(_obf) >= 2:` | `if che_chu and blur_band is None and blur_segs is None and os.environ.get("CHE_OCR_BOX_FAL…` |
| 136 | 19046 | `_che_manual = bool(che_band_manual) or (locals().get("_r", {}) or {}).get("source") == "ma…` |  |
| 137 | 19053 | `burn_kw["blur_band_manual"] = _che_manual` |  |
| 138 | 19054 | `if os.environ.get("CHE_MAX_OFF") != "1" and not _che_manual:` |  |
| 138.1 | 19055 | `try:` | `if os.environ.get("CHE_MAX_OFF") != "1" and not _che_manual:` |
| 138.2 | 19058 | `except ValueError:` | `if os.environ.get("CHE_MAX_OFF") != "1" and not _che_manual:` |
| 138.3 | 19060 | `if blur_band and (blur_band[1] - blur_band[0]) > _band_max:` | `if os.environ.get("CHE_MAX_OFF") != "1" and not _che_manual:` |
| 138.4 | 19064 | `if blur_segs:` | `if os.environ.get("CHE_MAX_OFF") != "1" and not _che_manual:` |
| 139 | 19138 | `if banner_boxes:` |  |
| 139.1 | 19139 | `_bn_can = [_b for _b in banner_boxes` | `if banner_boxes:` |
| 139.2 | 19145 | `for _b in list(_bn_can):` | `if banner_boxes:` |
| 139.3 | 19150 | `if _bn_can:` | `if banner_boxes:` |
| 140 | 19185 | `_tg("Che chữ + chuẩn bị burn", "che")` |  |
| 141 | 19186 | `if lam_long_tieng:` |  |
| 141.1 | 19196 | `dur = _thoi_luong(video) or 0.0` | `if lam_long_tieng:` |
| 141.2 | 19197 | `if dur <= 0:` | `if lam_long_tieng:` |
| 141.3 | 19200 | `dub_wav = os.path.join(thu_muc, ten + _ptmp + "_dub.wav")` | `if lam_long_tieng:` |
| 141.4 | 19201 | `_nhac_warp_tam = None      # stem nhạc nền đã warp (nếu có) — khối dọn cuối đọc VÔ ĐIỀU KI…` | `if lam_long_tieng:` |
| 141.5 | 19213 | `_dub_key = _ca.tinh_key(` | `if lam_long_tieng:` |
| 141.6 | 19350 | `_tg("Dịch (AI) %d câu" % len(segs_vi), "dich2")` | `if lam_long_tieng:` |
| 141.7 | 19351 | `lt = None` | `if lam_long_tieng:` |
| 141.8 | 19352 | `_pd = _ca.lay(_dub_key, ".dub.wav") if (_dub_key and not dich_lai) else None   # dich_lai…` | `if lam_long_tieng:` |
| 141.9 | 19353 | `if _pd:` | `if lam_long_tieng:` |
| 141.10 | 19376 | `if _pd is None:` | `if lam_long_tieng:` |
| 141.11 | 19807 | `if chi_dub:` | `if lam_long_tieng:` |
| 141.12 | 19834 | `if lt and os.environ.get("VC_SPLIT_DUB_ENCODE") == "1" and xu_ly_video.co_nvenc(_ffmpeg())…` | `if lam_long_tieng:` |
| 141.13 | 19836 | `if lt and os.path.isfile(dub_wav):` | `if lam_long_tieng:` |
| 141.14 | 20455 | `else:` | `if lam_long_tieng:` |
| 142 | 20464 | `elif burn:` |  |
| 142.1 | 20465 | `out_mp4 = os.path.join(thu_muc, ten + "_phude.mp4")` | `elif burn:` |
| 142.2 | 20470 | `_xn_ptmp = _ptmp        # tiền tố file tạm cho lượt tách TUẦN TỰ; đổi nếu luồng nền còn số…` | `elif burn:` |
| 142.3 | 20471 | `if _xn_th is not None:` | `elif burn:` |
| 142.4 | 20489 | `else:` | `elif burn:` |
| 142.5 | 20495 | `if xoa_nhac and not _au_xn:` | `elif burn:` |
| 142.6 | 20505 | `if burn_phude(video, vi_srt, out_mp4, che_chu=che_chu, audio_path=_au_xn, log_fn=log_fn, b… [THÂN Ở HÀM KHÁC: burn_phude:6560]` | `elif burn:` |
| 142.7 | 20509 | `if _au_xn:` | `elif burn:` |
| 143 | 20514 | `_dep_demucs(thu_muc, _ptmp)` |  |
| 144 | 20518 | `try:` |  |
| 144.1 | 20519 | `import json as _json, time as _tj` | `try:` |
| 144.2 | 20520 | `_RES.stop()` | `try:` |
| 144.3 | 20521 | `_plog = os.environ.get("VC_PROFILE_LOG") or os.path.join(` | `try:` |
| 144.4 | 20524 | `_meta = {}` | `try:` |
| 144.5 | 20525 | `try:` | `try:` |
| 144.6 | 20529 | `except Exception:` | `try:` |
| 144.7 | 20531 | `try:` | `try:` |
| 144.8 | 20533 | `except Exception:` | `try:` |
| 144.9 | 20542 | `try:` | `try:` |
| 144.10 | 20544 | `except Exception:` | `try:` |
| 144.11 | 20546 | `_rec = {"t": int(_tj.time()), "video": os.path.basename(video),` | `try:` |
| 144.12 | 20553 | `with open(_plog, "a", encoding="utf-8") as _pf:` | `try:` |
| 144.13 | 20555 | `log_fn("PROFILE\|" + _json.dumps(_rec, ensure_ascii=False))` | `try:` |
| 145 | 20556 | `except Exception:` |  |
| 145.1 | 20557 | `pass` | `except Exception:` |
| 146 | 20561 | `try:` |  |
| 146.1 | 20562 | `import chat_luong as _cl1` | `try:` |
| 146.2 | 20563 | `_cl1.dat_srt(locals().get("vi_srt"))` | `try:` |
| 146.3 | 20564 | `_cl1.dat_tgt(tgt)          # chỉ số 'ngắt xấu' chỉ đúng cho tiếng Việt — báo cáo phải biết…` | `try:` |
| 147 | 20565 | `except Exception:` |  |
| 147.1 | 20566 | `pass` | `except Exception:` |
| 148 | 20567 | `log_fn("LOCALIZE_DONE")` |  |
| 149 | 20573 | `if che_chu and _r_chac_khong_chu[0] and not (blur_band or blur_segs):` |  |
| 149.1 | 20574 | `ket["che_khong_co_chu"] = True` | `if che_chu and _r_chac_khong_chu[0] and not (blur_band or blur_segs):` |
| 150 | 20576 | `return ket` |  |
