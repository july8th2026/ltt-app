
### ket_qua_am35/am35 (AM: 1 server, 2 luot khoi dong bo, trung vi [min–max])


#### am35: nap

| nhan | build | n_ctx | slots | dedicated MiB | shared MiB | VRAM card MiB | bien MiB | nen truoc nap | giay nap | args them |
|---|---|---|---|---|---|---|---|---|---|---|
| np3_am | b10883-91f6a6cf3 | 262144 | 3 | 15256.8 | 640.0 | 15670 | 641 | 415 | 11.5 | -np 3 -c 262144  |
| np3_am SAU TAI | | | | 15374.8 | 678.0 | 15788 | 523 | | | |
- {"su_kien": "khoi_dong_bo", "nhan": "ngan", "luot": {"ttft_s": 0.525, "token_ra": 64, "decode_tps_khach": 70.03, "decode_tps_server": 69.00064072023527, "prompt_n": 229, "cache_n": 0, "prefill_tps": 442.18481780633846, "ket_thuc": "length", "loi": null, "bi_huy": false, "noi_dung_ky_tu": 0, "suy_nghi_ky_tu": 262, "rong": true}, "luc": "2026-09-17T17:30:41"}
- {"su_kien": "khoi_dong_bo", "nhan": "32k", "luot": {"ttft_s": 15.643, "token_ra": 64, "decode_tps_khach": 60.36, "decode_tps_server": 59.47250718154124, "prompt_n": 31720, "cache_n": 0, "prefill_tps": 2036.952318619414, "ket_thuc": "length", "loi": null, "bi_huy": false, "noi_dung_ky_tu": 0, "suy_nghi_ky_tu": 267, "rong": true}, "luc": "2026-09-17T17:30:58"}
- {"su_kien": "tai_on_dinh", "giay": 624.0, "he_thong": {"cpu_pct": 17.7, "ram_dung_gb": 98.4, "ram_trong_gb": 93.5, "ram_tai_pct": 51}, "luot": 53, "token_ra": 46379, "loi": 0, "rong": 52, "luc": "2026-09-17T17:50:56"}

#### pha am_moi: dong thoi

| k | prompt | tong tok/s khi ca k decode | moi luong decode tok/s (server, gop moi luong) | TTFT s luong 1k | TTFT s luong dai nhat | prefill tok/s luong dai nhat |
|---|---|---|---|---|---|---|
| 1 | 1k | 54.8 [54.8–56.6] n=3 | 54.7 [54.7–56.4] n=3 | 1.02 [0.69–1.12] n=3 | 1.02 [0.69–1.12] n=3 | 1295.0 [1124.0–1503.0] n=3 |
| 1 | 32k | 48.4 [47.0–58.0] n=3 | 48.3 [46.9–57.9] n=3 | 19.71 [19.65–22.39] n=3 | 19.71 [19.65–22.39] n=3 | 1612.0 [1435.0–1702.0] n=3 |
| 2 | 1k,8k | 81.5 [78.7–82.8] n=3 | 41.0 [32.5–42.8] n=6 | 6.31 [5.24–6.99] n=3 | 6.99 [6.31–7.44] n=3 | 1255.0 [1230.0–1396.0] n=3 |
| 3 | 1k,8k,32k | 106.5 [102.6–112.7] n=3 | 31.1 [12.5–37.0] n=9 | 25.48 [4.81–29.66] n=3 | 25.48 [22.21–29.66] n=3 | 1314.0 [1287.0–1537.0] n=3 |

#### pha am_moi: hai job

| job2 | job1 truoc | job1 trong prefill job2 | lang max s | job1 khi ca hai decode | job1 sau | job2 TTFT s | job2 prefill tok/s | job2 decode tok/s |
|---|---|---|---|---|---|---|---|---|
| 1000 | 55.1 [47.3–56.4] n=3 | 3.5 [3.2–3.5] n=3 | 1.26 [1.18–1.35] n=3 | 47.3 [46.6–52.1] n=3 | 61.5 [54.8–67.2] n=3 | 1.74 [1.73–1.87] n=3 | 1121.0 [1102.0–1336.0] n=3 | 47.8 [47.1–51.8] n=3 |
| 32000 | 73.0 [69.6–94.0] n=3 | 2.1 [2.0–2.9] n=3 | 1.22 [1.21–1.22] n=3 | 47.2 [46.7–57.3] n=3 | 57.9 [52.3–58.1] n=3 | 17.79 [17.77–17.89] n=3 | 1817.0 [1807.0–1822.0] n=3 | 46.2 [43.6–46.4] n=3 |

#### pha sau_10_phut_tai: dong thoi

| k | prompt | tong tok/s khi ca k decode | moi luong decode tok/s (server, gop moi luong) | TTFT s luong 1k | TTFT s luong dai nhat | prefill tok/s luong dai nhat |
|---|---|---|---|---|---|---|
| 1 | 1k | 53.1 [50.1–55.5] n=3 | 53.0 [50.0–55.3] n=3 | 1.24 [0.96–1.98] n=3 | 1.24 [0.96–1.98] n=3 | 1291.0 [1212.0–1401.0] n=3 |
| 1 | 32k | 47.2 [44.8–47.2] n=3 | 47.1 [44.7–47.1] n=3 | 20.91 [20.57–21.68] n=3 | 20.91 [20.57–21.68] n=3 | 1559.0 [1506.0–1566.0] n=3 |
| 2 | 1k,8k | 78.5 [76.3–81.1] n=3 | 38.6 [34.5–39.8] n=6 | 7.67 [5.4–7.74] n=3 | 7.7 [7.67–7.74] n=3 | 1195.0 [1195.0–1273.0] n=3 |
| 3 | 1k,8k,32k | 113.2 [98.9–114.1] n=3 | 30.0 [13.5–39.9] n=9 | 5.47 [4.59–29.95] n=3 | 25.05 [21.57–26.56] n=3 | 1586.0 [1261.0–1704.0] n=3 |

#### pha sau_10_phut_tai: hai job

| job2 | job1 truoc | job1 trong prefill job2 | lang max s | job1 khi ca hai decode | job1 sau | job2 TTFT s | job2 prefill tok/s | job2 decode tok/s |
|---|---|---|---|---|---|---|---|---|
| 1000 | 59.3 [45.9–66.2] n=3 | 4.2 [2.7–5.5] n=3 | 1.2 [0.83–1.21] n=3 | 48.1 [46.1–48.5] n=3 | 59.3 [54.4–63.5] n=3 | 1.74 [1.39–1.77] n=3 | 1142.0 [1072.0–1146.0] n=3 | 45.5 [44.7–46.4] n=3 |
| 32000 | 68.7 [68.4–71.0] n=3 | 2.3 [2.1–2.5] n=3 | 1.21 [1.21–1.21] n=3 | 48.6 [46.6–49.7] n=3 | 59.5 [55.0–60.8] n=3 | 17.76 [17.48–17.78] n=3 | 1823.0 [1818.0–1834.0] n=3 | 44.6 [44.4–45.6] n=3 |

### ket_qua_am38/am38 (AM: 1 server, 2 luot khoi dong bo, trung vi [min–max])


#### am38: nap

| nhan | build | n_ctx | slots | dedicated MiB | shared MiB | VRAM card MiB | bien MiB | nen truoc nap | giay nap | args them |
|---|---|---|---|---|---|---|---|---|---|---|
| np3_am | b10883-91f6a6cf3 | 221184 | 3 | 23970.9 | 568.0 | 24036 | 540 | 66 | 17.7 | -np 3 -c 221184  |
| np3_am SAU TAI | | | | 24007.0 | 614.0 | 24072 | 504 | | | |
- {"su_kien": "khoi_dong_bo", "nhan": "ngan", "luot": {"ttft_s": 0.871, "token_ra": 64, "decode_tps_khach": 56.14, "decode_tps_server": 55.30677262156735, "prompt_n": 260, "cache_n": 0, "prefill_tps": 306.3212933356268, "ket_thuc": "length", "loi": null, "bi_huy": false, "noi_dung_ky_tu": 0, "suy_nghi_ky_tu": 242, "rong": true}, "luc": "2026-09-17T17:19:39"}
- {"su_kien": "khoi_dong_bo", "nhan": "32k", "luot": {"ttft_s": 28.052, "token_ra": 64, "decode_tps_khach": 49.79, "decode_tps_server": 49.069203933948174, "prompt_n": 31611, "cache_n": 0, "prefill_tps": 1129.551127866324, "ket_thuc": "length", "loi": null, "bi_huy": false, "noi_dung_ky_tu": 0, "suy_nghi_ky_tu": 280, "rong": true}, "luc": "2026-09-17T17:20:08"}
- {"su_kien": "tai_on_dinh", "giay": 621.4, "he_thong": {"cpu_pct": 20.5, "ram_dung_gb": 97.8, "ram_trong_gb": 94.0, "ram_tai_pct": 50}, "luot": 46, "token_ra": 24472, "loi": 0, "rong": 17, "luc": "2026-09-17T17:44:13"}

#### pha am_moi: dong thoi

| k | prompt | tong tok/s khi ca k decode | moi luong decode tok/s (server, gop moi luong) | TTFT s luong 1k | TTFT s luong dai nhat | prefill tok/s luong dai nhat |
|---|---|---|---|---|---|---|
| 1 | 1k | 48.6 [44.2–51.5] n=3 | 48.5 [44.1–51.4] n=3 | 2.13 [1.48–2.19] n=3 | 2.13 [1.48–2.19] n=3 | 694.0 [601.0–730.0] n=3 |
| 1 | 32k | 42.5 [38.7–45.5] n=3 | 42.4 [38.6–45.4] n=3 | 37.05 [36.33–43.09] n=3 | 37.05 [36.33–43.09] n=3 | 862.0 [747.0–908.0] n=3 |
| 2 | 1k,8k | 62.4 [56.8–66.4] n=3 | 29.5 [24.3–34.6] n=6 | 11.83 [9.55–13.15] n=3 | 13.15 [11.83–13.71] n=3 | 658.0 [640.0–740.0] n=3 |
| 3 | 1k,8k,32k | 84.7 [76.8–86.5] n=3 | 22.9 [7.4–28.3] n=9 | 16.62 [8.65–56.39] n=3 | 48.99 [41.66–56.39] n=3 | 801.0 [674.0–802.0] n=3 |

#### pha am_moi: hai job

| job2 | job1 truoc | job1 trong prefill job2 | lang max s | job1 khi ca hai decode | job1 sau | job2 TTFT s | job2 prefill tok/s | job2 decode tok/s |
|---|---|---|---|---|---|---|---|---|
| 1000 | 60.7 [52.4–62.7] n=3 | 2.1 [2.1–2.3] n=3 | 2.17 [1.9–2.26] n=3 | 38.1 [36.4–47.1] n=3 | 59.0 [49.0–61.3] n=3 | 3.09 [2.86–3.17] n=3 | 610.0 [583.0–620.0] n=3 | 41.6 [34.0–46.3] n=3 |
| 32000 | 59.8 [57.2–65.5] n=3 | 1.5 [1.4–1.5] n=3 | 2.68 [2.52–2.71] n=3 | 44.9 [35.3–47.5] n=3 | 48.7 [45.8–62.3] n=3 | 34.58 [34.12–34.64] n=3 | 934.0 [934.0–943.0] n=3 | 36.1 [34.2–38.2] n=3 |

#### pha sau_10_phut_tai: dong thoi

| k | prompt | tong tok/s khi ca k decode | moi luong decode tok/s (server, gop moi luong) | TTFT s luong 1k | TTFT s luong dai nhat | prefill tok/s luong dai nhat |
|---|---|---|---|---|---|---|
| 1 | 1k | 43.4 [41.8–47.4] n=3 | 43.3 [41.7–47.2] n=3 | 2.68 [2.34–3.76] n=3 | 2.68 [2.34–3.76] n=3 | 593.0 [588.0–685.0] n=3 |
| 1 | 32k | 46.5 [41.3–55.0] n=3 | 46.4 [41.2–54.9] n=3 | 38.36 [35.56–42.72] n=3 | 38.36 [35.56–42.72] n=3 | 851.0 [748.0–912.0] n=3 |
| 2 | 1k,8k | 66.6 [65.9–68.8] n=3 | 33.3 [32.0–35.9] n=6 | 12.78 [11.32–14.53] n=3 | 12.78 [11.32–14.53] n=3 | 669.0 [667.0–762.0] n=3 |
| 3 | 1k,8k,32k | 82.6 [79.2–87.5] n=3 | 26.2 [7.8–31.0] n=9 | 52.89 [17.27–53.56] n=3 | 48.03 [46.66–53.56] n=3 | 711.0 [710.0–843.0] n=3 |

#### pha sau_10_phut_tai: hai job

| job2 | job1 truoc | job1 trong prefill job2 | lang max s | job1 khi ca hai decode | job1 sau | job2 TTFT s | job2 prefill tok/s | job2 decode tok/s |
|---|---|---|---|---|---|---|---|---|
| 1000 | 54.0 [54.0–55.8] n=3 | 2.5 [2.2–2.7] n=3 | 1.81 [1.44–2.08] n=3 | 46.7 [37.7–47.2] n=3 | 62.4 [43.0–63.2] n=3 | 2.72 [2.52–3.03] n=3 | 608.0 [528.0–631.0] n=3 | 36.2 [35.6–42.6] n=3 |
| 32000 | 64.2 [53.4–66.2] n=3 | 1.4 [1.4–1.5] n=3 | 2.75 [2.6–2.76] n=3 | 47.6 [32.6–47.6] n=3 | 62.4 [53.4–63.2] n=3 | 34.26 [34.24–34.42] n=3 | 939.0 [938.0–942.0] n=3 | 35.6 [34.3–35.7] n=3 |

### ket_qua/m1


#### ket_qua/m1: nap

| nhan | build | n_ctx | slots | dedicated MiB | shared MiB | VRAM card MiB | bien MiB | nen truoc nap | giay nap | args them |
|---|---|---|---|---|---|---|---|---|---|---|
| np3 | b10883-91f6a6cf3 | 262144 | 3 | 15256.8 | 640.0 | 15670 | 641 | 415 | 10.6 | -np 3 -c 262144  |
| np3 SAU TAI | | | | 15374.8 | 678.0 | 15788 | 523 | | | |

#### ket_qua/m1: hai job (job1 1k->8000 mot minh; job2 vao sau 15 s)

| nhan | job2 prompt | job1 truoc | job1 trong prefill job2 | lang max s | job1 khi ca hai decode | job1 sau | job2 TTFT s | job2 prefill tok/s | job2 decode tok/s |
|---|---|---|---|---|---|---|---|---|---|
| np3 | 1000 | 73.5 | - | 0.3 | 61.2 | 73.9 | 0.75 | 1478.0 | 56.8 |
| np3 | 32000 | 77.4 | 2.8 | 1.21 | 49.9 | 56.8 | 17.705 | 1828.0 | 42.8 |

#### ket_qua/m1: dong thoi (max_tokens 400, ignore_eos)

| nhan | k | prompt | tong tok/s khi ca k decode | cua so s | tong ca dot | moi luong decode tok/s (server) | TTFT s | prefill tok/s | loi |
|---|---|---|---|---|---|---|---|---|---|
| np3 | 1 | 1k | 72.2 | 5.5 | 63.2 | 72.0 | 0.8 | 1845.0 | 0 |
| np3 | 1 | 8k | 69.6 | 5.7 | 41.0 | 69.5 | 4.0 | 2098.0 | 0 |
| np3 | 1 | 32k | 55.0 | 7.3 | 16.2 | 54.9 | 17.4 | 1852.0 | 0 |
| np3 | 2 | 1k,8k | 90.3 | 8.6 | 52.9 | 37.8 / 44.8 | 4.2 / 6.2 | 276.0 / 1378.0 | 0 |
| np3 | 3 | 1k,8k,32k | 117.2 | 8.8 | 34.4 | 13.9 / 16.1 / 39.4 | 4.9 / 9.5 / 24.7 | 268.0 / 953.0 / 1708.0 | 0 |
| np3 | 4 | 1k,8k,32k,1k | - | -17.8 | 40.2 | 19.8 / 27.0 / 54.8 / 38.7 | 4.5 / 6.5 / 32.5 / 4.5 | 338.0 / 1571.0 / 1808.0 / 340.0 | 0 |
| np3 | 5 | 1k,8k,32k,1k,8k | - | -22.3 | 43.0 | 46.2 / 30.3 / 46.2 / 22.5 / 41.4 | 6.6 / 6.5 / 37.5 / 6.5 / 36.8 | 450.0 / 1464.0 / 1808.0 / 462.0 / 369.0 | 0 |
| np3 | 6 | 1k,8k,32k,1k,8k,32k | - | -45.9 | 33.2 | 15.6 / 30.1 / 33.7 / 40.0 / 8.0 / 23.3 | 4.7 / 6.8 / 60.5 / 4.7 / 19.2 / 54.0 | 343.0 / 1583.0 / 789.0 / 344.0 / 1862.0 / 1343.0 | 0 |

#### ket_qua/m1: prefill dai chen vao 2 luong dang decode

| b | prompt | 2 luong truoc | trong prefill | sau | lang max s | giay prefill | prefill tok/s | loi |
|---|---|---|---|---|---|---|---|---|

#### ket_qua/m1: cap slot / kiem rong

- cap np3 [0]: [68.4]
- cap np3 [2]: [55.5]
- cap np3 [0, 1]: [54.8, 55.0]
- cap np3 [1, 2]: [56.6, 45.1]
- cap np3 [0, 2]: [54.3, 56.5]
- kiem_rong np3 k=3 lan=0: rong=0 token_ra=[2143, 326, 1325] ket_thuc=['stop', 'stop', 'stop']
- kiem_rong np3 k=3 lan=1: rong=0 token_ra=[271, 1818, 1750] ket_thuc=['stop', 'stop', 'stop']

### ket_qua_35/m1


#### ket_qua_35/m1: nap

| nhan | build | n_ctx | slots | dedicated MiB | shared MiB | VRAM card MiB | bien MiB | nen truoc nap | giay nap | args them |
|---|---|---|---|---|---|---|---|---|---|---|
| np4 | b10883-91f6a6cf3 | 262144 | 4 | 15406.8 | 644.0 | 15820 | 491 | 415 | 10.6 | -np 4 -c 262144  |
| np4 SAU TAI | | | | 15524.9 | 684.0 | 15938 | 373 | | | |
| np6 | b10883-91f6a6cf3 | 262144 | 6 | 15527.2 | 844.0 | 15940 | 371 | 415 | 12.6 | -np 6 -c 262144  |
| np6 SAU TAI | | | | 15549.4 | 984.0 | 15962 | 349 | | | |

#### ket_qua_35/m1: hai job (job1 1k->8000 mot minh; job2 vao sau 15 s)

| nhan | job2 prompt | job1 truoc | job1 trong prefill job2 | lang max s | job1 khi ca hai decode | job1 sau | job2 TTFT s | job2 prefill tok/s | job2 decode tok/s |
|---|---|---|---|---|---|---|---|---|---|

#### ket_qua_35/m1: dong thoi (max_tokens 400, ignore_eos)

| nhan | k | prompt | tong tok/s khi ca k decode | cua so s | tong ca dot | moi luong decode tok/s (server) | TTFT s | prefill tok/s | loi |
|---|---|---|---|---|---|---|---|---|---|
| np4 | 1 | 1k | 69.0 | 5.8 | 60.3 | 68.9 | 0.8 | 1812.0 | 0 |
| np4 | 1 | 8k | 64.4 | 6.2 | 38.3 | 64.3 | 4.2 | 2042.0 | 0 |
| np4 | 1 | 32k | 54.7 | 7.3 | 15.9 | 54.6 | 17.8 | 1819.0 | 0 |
| np4 | 2 | 1k,8k | 83.7 | 9.2 | 49.1 | 34.9 / 41.9 | 4.5 / 6.7 | 258.0 / 1296.0 | 0 |
| np4 | 3 | 1k,8k,32k | 87.5 | 12.5 | 25.6 | 21.0 / 32.0 / 24.8 | 27.9 / 31.4 / 27.9 | 195.0 / 910.0 / 1204.0 | 0 |
| np4 | 4 | 1k,8k,32k,1k | 123.5 | 11.5 | 37.5 | 30.8 / 12.7 / 31.2 / 31.8 | 29.6 / 9.7 / 29.6 / 29.6 | 378.0 / 1000.0 / 1334.0 / 387.0 | 0 |
| np4 | 5 | 1k,8k,32k,1k,8k | - | -19.0 | 42.5 | 19.0 / 33.4 / 56.1 / 13.9 / 16.8 | 4.7 / 9.0 / 40.0 / 11.4 / 11.3 | 336.0 / 1103.0 / 1712.0 / 437.0 / 1427.0 | 0 |
| np4 | 6 | 1k,8k,32k,1k,8k,32k | - | -42.6 | 31.7 | 23.8 / 19.3 / 36.8 / 17.4 / 12.8 / 13.5 | 5.6 / 12.4 / 64.9 / 10.2 / 10.2 / 45.5 | 266.0 / 1428.0 / 1355.0 / 295.0 / 942.0 / 1389.0 | 0 |
| np6 | 1 | 1k | 67.2 | 6.0 | 60.7 | 67.0 | 0.6 | 1697.0 | 0 |
| np6 | 1 | 8k | 67.2 | 6.0 | 40.0 | 67.0 | 4.0 | 1983.0 | 0 |
| np6 | 1 | 32k | 52.1 | 7.7 | 15.3 | 51.9 | 18.5 | 1745.0 | 0 |
| np6 | 2 | 1k,8k | 81.9 | 9.6 | 48.6 | 40.4 / 41.5 | 6.6 / 6.6 | 469.0 / 1317.0 | 0 |
| np6 | 3 | 1k,8k,32k | 95.0 | 11.7 | 27.6 | 10.5 / 32.1 / 26.0 | 4.7 / 31.1 / 27.6 | 252.0 / 912.0 / 1177.0 | 0 |
| np6 | 4 | 1k,8k,32k,1k | 115.2 | 12.1 | 32.1 | 11.5 / 11.2 / 29.1 / 9.5 | 13.5 / 13.5 / 36.1 / 6.7 | 198.0 / 686.0 / 1140.0 / 213.0 | 0 |
| np6 | 5 | 1k,8k,32k,1k,8k | 118.0 | 14.5 | 30.7 | 23.6 / 23.7 / 18.6 / 22.3 / 8.1 | 47.3 / 47.3 / 41.9 / 47.3 / 12.3 | 317.0 / 701.0 / 918.0 / 303.0 / 789.0 | 0 |
| np6 | 6 | 1k,8k,32k,1k,8k,32k | 143.5 | 12.5 | 29.6 | 6.9 / 6.4 / 26.0 / 5.8 / 7.0 / 11.0 | 22.3 / 16.2 / 65.8 / 9.1 / 22.3 / 44.4 | 231.0 / 608.0 / 1219.0 / 171.0 / 713.0 / 1192.0 | 0 |

#### ket_qua_35/m1: prefill dai chen vao 2 luong dang decode

| b | prompt | 2 luong truoc | trong prefill | sau | lang max s | giay prefill | prefill tok/s | loi |
|---|---|---|---|---|---|---|---|---|

#### ket_qua_35/m1: cap slot / kiem rong

- cap np4 [0]: [87.7]
- cap np4 [2]: [69.0]
- cap np4 [0, 1]: [55.7, 57.6]
- cap np4 [1, 2]: [54.9, 54.7]
- cap np4 [0, 2]: [54.5, 54.7]
- cap np4 [1, 3]: [57.7, 55.6]
- cap np4 [0, 3]: [52.4, 54.1]
- kiem_rong np4 k=4 lan=0: rong=0 token_ra=[1456, 1464, 1273, 2043] ket_thuc=['stop', 'stop', 'stop', 'stop']
- kiem_rong np4 k=4 lan=1: rong=0 token_ra=[1106, 2042, 1533, 1195] ket_thuc=['stop', 'stop', 'stop', 'stop']
- cap np6 [0]: [72.6]
- cap np6 [2]: [70.1]
- cap np6 [0, 1]: [54.9, 52.7]
- cap np6 [1, 2]: [56.2, 46.4]
- cap np6 [0, 2]: [55.5, 52.6]
- cap np6 [1, 3]: [53.2, 53.2]
- cap np6 [0, 3]: [54.0, 51.7]
- kiem_rong np6 k=6 lan=0: rong=0 token_ra=[1563, 878, 2092, 1529, 2061, 1165] ket_thuc=['stop', 'stop', 'stop', 'stop', 'stop', 'stop']
- kiem_rong np6 k=6 lan=1: rong=0 token_ra=[1733, 2131, 1908, 2064, 2291, 1420] ket_thuc=['stop', 'stop', 'stop', 'stop', 'stop', 'stop']

### ket_qua_35/m3_35


#### ket_qua_35/m3_35: nap

| nhan | build | n_ctx | slots | dedicated MiB | shared MiB | VRAM card MiB | bien MiB | nen truoc nap | giay nap | args them |
|---|---|---|---|---|---|---|---|---|---|---|
| b2048 | b10883-91f6a6cf3 | 262144 | 3 | 15256.8 | 640.0 | 15670 | 641 | 415 | 11.6 | -np 3 -c 262144 -b 2048 -ub 512  |
| b512 | b10883-91f6a6cf3 | 262144 | 3 | 15256.8 | 640.0 | 15670 | 641 | 415 | 12.6 | -np 3 -c 262144 -b 512 -ub 512  |

#### ket_qua_35/m3_35: hai job (job1 1k->8000 mot minh; job2 vao sau 15 s)

| nhan | job2 prompt | job1 truoc | job1 trong prefill job2 | lang max s | job1 khi ca hai decode | job1 sau | job2 TTFT s | job2 prefill tok/s | job2 decode tok/s |
|---|---|---|---|---|---|---|---|---|---|
| b2048 | 1000 | 68.7 | - | 0.3 | 57.1 | 72.7 | 0.71 | 1500.0 | 56.0 |
| b2048 | 32000 | 67.5 | 2.6 | 1.21 | 48.5 | 65.6 | 17.629 | 1830.0 | 45.4 |
| b512 | 1000 | 75.1 | - | 0.29 | 61.3 | 75.7 | 0.707 | 1530.0 | 52.8 |
| b512 | 32000 | 69.0 | 7.2 | 0.48 | 47.7 | 60.7 | 20.233 | 1597.0 | 46.1 |

#### ket_qua_35/m3_35: dong thoi (max_tokens 400, ignore_eos)

| nhan | k | prompt | tong tok/s khi ca k decode | cua so s | tong ca dot | moi luong decode tok/s (server) | TTFT s | prefill tok/s | loi |
|---|---|---|---|---|---|---|---|---|---|

#### ket_qua_35/m3_35: prefill dai chen vao 2 luong dang decode

| b | prompt | 2 luong truoc | trong prefill | sau | lang max s | giay prefill | prefill tok/s | loi |
|---|---|---|---|---|---|---|---|---|
| 2048 | 32000 | 84.3 | 5.0 | 91.1 | [1.2, 1.2] | 17.6 | 1838.0 | None |
| 2048 | 163000 | 97.8 | 1.9 | 55.8 | [2.56, 2.56] | 133.2 | 1220.0 | None |
| 512 | 32000 | 88.9 | 12.3 | 95.9 | [0.55, 0.55] | 20.4 | 1580.0 | None |
| 512 | 163000 | 74.7 | 8.0 | 43.3 | [1.1, 1.1] | 153.7 | 1057.0 | None |

### ket_qua_35/m5


#### ket_qua_35/m5: nap

| nhan | build | n_ctx | slots | dedicated MiB | shared MiB | VRAM card MiB | bien MiB | nen truoc nap | giay nap | args them |
|---|---|---|---|---|---|---|---|---|---|---|
| c16384_np3 | b10883-91f6a6cf3 | 16384 | 3 | 8819.8 | 160.0 | 9234 | 7077 | 415 | 10.6 | -np 3 -c 16384  |

#### ket_qua_35/m5: hai job (job1 1k->8000 mot minh; job2 vao sau 15 s)

| nhan | job2 prompt | job1 truoc | job1 trong prefill job2 | lang max s | job1 khi ca hai decode | job1 sau | job2 TTFT s | job2 prefill tok/s | job2 decode tok/s |
|---|---|---|---|---|---|---|---|---|---|

#### ket_qua_35/m5: dong thoi (max_tokens 400, ignore_eos)

| nhan | k | prompt | tong tok/s khi ca k decode | cua so s | tong ca dot | moi luong decode tok/s (server) | TTFT s | prefill tok/s | loi |
|---|---|---|---|---|---|---|---|---|---|

#### ket_qua_35/m5: prefill dai chen vao 2 luong dang decode

| b | prompt | 2 luong truoc | trong prefill | sau | lang max s | giay prefill | prefill tok/s | loi |
|---|---|---|---|---|---|---|---|---|
- {"su_kien": "tran_kv", "nhan": "doi_chung_vua", "tong_can_token": 7500, "pool": 16384, "server_sau": {"status": "ok"}, "exit": null, "tung_luong": [[1500, "length", null, 49.5, 1.854], [1500, "length", null, 62.5, 1.855], [1500, "length", null, 54.1, 1.991]], "luc": "2026-09-17T17:21:24"}
- {"su_kien": "luot_moi_sau_doi_chung_vua", "luot": {"ttft_s": 0.682, "token_ra": 200, "decode_tps_khach": 80.38, "decode_tps_server": 79.97697949052655, "prompt_n": 510, "cache_n": 0, "prefill_tps": 1703.05983082939, "ket_thuc": "length", "loi": null, "bi_huy": false, "noi_dung_ky_tu": 0, "suy_nghi_ky_tu": 771, "rong": true}, "luc": "2026-09-17T17:21:28"}
- {"su_kien": "tran_kv", "nhan": "tran_co_y", "tong_can_token": 21000, "pool": 16384, "server_sau": {"status": "ok"}, "exit": null, "tung_luong": [[2359, null, "{\"code\": 500, \"message\": \"got exception: speculative batch index 6 is not inside the current sub-batch [0, 4)\", \"type\": \"server_error\"}", "-", 5.67], [2448, null, "{\"code\": 500, \"message\": \"got exception: speculative batch index 4 is not inside the current sub-batch [0, 4)\", \"type\": \"server_error\"}", "-", 5.245], [4000, "length", null, 58.1, 4.928]], "luc": "2026-09-17T17:22:41"}
- {"su_kien": "luot_moi_sau_tran_co_y", "luot": {"ttft_s": 0.392, "token_ra": 200, "decode_tps_khach": 79.57, "decode_tps_server": 79.18853636504723, "prompt_n": 552, "cache_n": 0, "prefill_tps": 1438.0317721657489, "ket_thuc": "length", "loi": null, "bi_huy": false, "noi_dung_ky_tu": 0, "suy_nghi_ky_tu": 762, "rong": true}, "luc": "2026-09-17T17:22:44"}
- {"su_kien": "log_server", "dong": ["0.08.610.446 I common_speculative_init_result: creating MTP draft context against the target model 'H:/LTT_LLM/models/Qwen3.5-9B-Q6_K-unsloth.gguf'", "0.40.051.846 I slot      release: id  2 | task 1 | stop processing: n_tokens = 2525, truncated = 0", "0.43.940.095 I slot      release: id  0 | task 3 | stop processing: n_tokens = 2493, truncated = 0", "0.46.379.138 I slot      release: id  1 | task 0 | stop processing: n_tokens = 2536, truncated = 0", "0.49.552.720 I slot      release: id  2 | task 729 | stop processing: n_tokens = 709, truncated = 0", "1.42.671.961 E init_batch: failed to prepare attention ubatches", "1.42.671.967 W decode: failed to find a memory slot for batch of size 9", "1.42.671.983 W srv        decode: failed to find free space in the KV cache, retrying with smaller batch size, off = 0, n_batch = 1024, ret = 1", "1.42.672.264 E init_batch: failed to prepare attention ubatches", "1.42.672.272 W decode: failed to find a memory slot for batch of size 9", "1.42.672.281 W srv        decode: failed to find free space in the KV cache, retrying with smaller batch size, off = 0, n_batch = 512, ret = 1", "1.42.672.558 E init_batch: failed to prepare attention ubatches", "1.42.672.562 W decode: failed to find a memory slot for batch of size 9", "1.42.672.579 W srv        decode: failed to find free space in the KV cache, retrying with smaller batch size, off = 0, n_batch = 256, ret = 1", "1.42.672.859 E init_batch: failed to pr

### ket_qua_35/m6


#### ket_qua_35/m6: nap

| nhan | build | n_ctx | slots | dedicated MiB | shared MiB | VRAM card MiB | bien MiB | nen truoc nap | giay nap | args them |
|---|---|---|---|---|---|---|---|---|---|---|
| cache_ram_mac_dinh | b10883-91f6a6cf3 | 262144 | 3 | 15256.8 | 640.0 | 15670 | 641 | 415 | 9.5 | -np 3 -c 262144  |
| cache_ram_0 | b10883-91f6a6cf3 | 262144 | 3 | 15256.8 | 640.0 | 15670 | 641 | 415 | 11.6 | -np 3 -c 262144 --cache-ram 0  |

#### ket_qua_35/m6: hai job (job1 1k->8000 mot minh; job2 vao sau 15 s)

| nhan | job2 prompt | job1 truoc | job1 trong prefill job2 | lang max s | job1 khi ca hai decode | job1 sau | job2 TTFT s | job2 prefill tok/s | job2 decode tok/s |
|---|---|---|---|---|---|---|---|---|---|

#### ket_qua_35/m6: dong thoi (max_tokens 400, ignore_eos)

| nhan | k | prompt | tong tok/s khi ca k decode | cua so s | tong ca dot | moi luong decode tok/s (server) | TTFT s | prefill tok/s | loi |
|---|---|---|---|---|---|---|---|---|---|

#### ket_qua_35/m6: prefill dai chen vao 2 luong dang decode

| b | prompt | 2 luong truoc | trong prefill | sau | lang max s | giay prefill | prefill tok/s | loi |
|---|---|---|---|---|---|---|---|---|
- {"su_kien": "cache", "nhan": "cache_ram_mac_dinh", "so_luot": 35, "metrics_prompt_tokens": 171553.0, "metrics_prompt_tokens_cached": 0.0, "ty_le_trung_metrics": 0.0, "ghi_chu": "prompt_tokens_total co the chi dem token DA XU LY; ty le = cached/(processed+cached)", "ttft_hoi_p50": 3.266, "cache_n_tong": 0, "prompt_n_tong": 151570, "tung_luot": "<35 luot>", "luc": "2026-09-17T17:25:27"}
- {"su_kien": "cache", "nhan": "cache_ram_0", "so_luot": 35, "metrics_prompt_tokens": 171498.0, "metrics_prompt_tokens_cached": 0.0, "ty_le_trung_metrics": 0.0, "ghi_chu": "prompt_tokens_total co the chi dem token DA XU LY; ty le = cached/(processed+cached)", "ttft_hoi_p50": 4.9425, "cache_n_tong": 0, "prompt_n_tong": 151570, "tung_luot": "<35 luot>", "luc": "2026-09-17T17:28:11"}

### ket_qua_38/m3_38


#### ket_qua_38/m3_38: nap

| nhan | build | n_ctx | slots | dedicated MiB | shared MiB | VRAM card MiB | bien MiB | nen truoc nap | giay nap | args them |
|---|---|---|---|---|---|---|---|---|---|---|
| b2048 | b10883-91f6a6cf3 | 221184 | 3 | 23970.9 | 568.0 | 24036 | 540 | 66 | 19.8 | -np 3 -c 221184 -b 2048 -ub 512  |
| b512 | b10883-91f6a6cf3 | 221184 | 3 | 23970.9 | 568.0 | 24036 | 540 | 66 | 18.7 | -np 3 -c 221184 -b 512 -ub 512  |

#### ket_qua_38/m3_38: hai job (job1 1k->8000 mot minh; job2 vao sau 15 s)

| nhan | job2 prompt | job1 truoc | job1 trong prefill job2 | lang max s | job1 khi ca hai decode | job1 sau | job2 TTFT s | job2 prefill tok/s | job2 decode tok/s |
|---|---|---|---|---|---|---|---|---|---|
| b2048 | 1000 | 64.8 | 5.3 | 0.54 | 53.8 | 74.6 | 1.428 | 781.0 | 41.7 |
| b2048 | 32000 | 71.4 | 1.2 | 2.23 | 33.7 | 60.5 | 31.804 | 1010.0 | 35.4 |
| b512 | 1000 | 75.4 | 4.4 | 0.51 | 41.2 | 74.0 | 1.429 | 751.0 | 53.9 |
| b512 | 32000 | 63.5 | 5.3 | 0.88 | 46.1 | 61.5 | 35.092 | 917.0 | 33.9 |

#### ket_qua_38/m3_38: dong thoi (max_tokens 400, ignore_eos)

| nhan | k | prompt | tong tok/s khi ca k decode | cua so s | tong ca dot | moi luong decode tok/s (server) | TTFT s | prefill tok/s | loi |
|---|---|---|---|---|---|---|---|---|---|

#### ket_qua_38/m3_38: prefill dai chen vao 2 luong dang decode

| b | prompt | 2 luong truoc | trong prefill | sau | lang max s | giay prefill | prefill tok/s | loi |
|---|---|---|---|---|---|---|---|---|
| 2048 | 32000 | 64.0 | 3.2 | 79.7 | [2.21, 2.21] | 31.4 | 1031.0 | None |
| 2048 | 128000 | 68.0 | 2.0 | 57.3 | [3.91, 3.91] | 176.0 | 723.0 | None |
| 512 | 32000 | 69.4 | 7.7 | 69.2 | [0.95, 1.08] | 35.2 | 916.0 | None |
| 512 | 128000 | 71.6 | 7.0 | 69.5 | [1.41, 1.41] | 195.6 | 651.0 | None |

### ket_qua_38/m2


#### ket_qua_38/m2: nap

| nhan | build | n_ctx | slots | dedicated MiB | shared MiB | VRAM card MiB | bien MiB | nen truoc nap | giay nap | args them |
|---|---|---|---|---|---|---|---|---|---|---|
| np3_c221184 | b10883-91f6a6cf3 | 221184 | 3 | 23970.9 | 568.0 | 24036 | 540 | 66 | 18.7 | -np 3 -c 221184  |
| np3_c221184 SAU TAI | | | | 23999.0 | 614.0 | 24064 | 512 | | | |
| np4_c200704 | b10883-91f6a6cf3 | 200704 | 4 | 23858.9 | 532.0 | 23924 | 652 | 66 | 17.7 | -np 4 -c 200704  |
| np5_c184320 | b10883-91f6a6cf3 | 184320 | 5 | 23860.8 | 506.0 | 23926 | 650 | 66 | 19.6 | -np 5 -c 184320  |
| np5_c184320 SAU TAI | | | | 23894.9 | 556.0 | 23960 | 616 | | | |

#### ket_qua_38/m2: hai job (job1 1k->8000 mot minh; job2 vao sau 15 s)

| nhan | job2 prompt | job1 truoc | job1 trong prefill job2 | lang max s | job1 khi ca hai decode | job1 sau | job2 TTFT s | job2 prefill tok/s | job2 decode tok/s |
|---|---|---|---|---|---|---|---|---|---|

#### ket_qua_38/m2: dong thoi (max_tokens 400, ignore_eos)

| nhan | k | prompt | tong tok/s khi ca k decode | cua so s | tong ca dot | moi luong decode tok/s (server) | TTFT s | prefill tok/s | loi |
|---|---|---|---|---|---|---|---|---|---|
| np3_c221184 | 1 | 1k | 62.0 | 6.4 | 51.4 | 61.9 | 1.3 | 914.0 | 0 |
| np3_c221184 | 2 | 1k,8k | 75.4 | 10.5 | 42.1 | 38.1 / 37.1 | 8.2 / 8.2 | 352.0 / 1014.0 | 0 |
| np3_c221184 | 3 | 1k,8k,32k | 86.5 | 12.4 | 21.8 | 28.3 / 28.7 / 22.8 | 40.9 / 40.9 / 35.8 | 357.0 / 665.0 / 912.0 | 0 |
| np5_c184320 | 1 | 1k | 57.0 | 7.0 | 47.9 | 56.8 | 1.3 | 836.0 | 0 |
| np5_c184320 | 2 | 1k,8k | 76.5 | 10.2 | 41.3 | 37.4 / 39.0 | 8.7 / 8.7 | 332.0 / 918.0 | 0 |
| np5_c184320 | 3 | 1k,8k,32k | 89.3 | 12.0 | 20.4 | 29.6 / 33.3 / 20.8 | 44.8 / 44.8 / 39.5 | 373.0 / 610.0 / 824.0 | 0 |
| np5_c184320 | 4 | 1k,8k,32k,1k | 92.5 | 12.1 | 21.0 | 6.7 / 7.6 / 22.7 / 21.8 | 10.2 / 20.6 / 57.8 / 57.8 | 128.0 / 432.0 / 706.0 / 204.0 | 0 |
| np5_c184320 | 5 | 1k,8k,32k,1k,8k | 114.9 | 14.6 | 24.1 | 5.8 / 8.5 / 23.4 / 6.0 / 7.2 | 13.4 / 34.7 / 65.8 / 13.4 / 25.5 | 107.0 / 432.0 / 851.0 / 106.0 / 368.0 | 0 |

#### ket_qua_38/m2: prefill dai chen vao 2 luong dang decode

| b | prompt | 2 luong truoc | trong prefill | sau | lang max s | giay prefill | prefill tok/s | loi |
|---|---|---|---|---|---|---|---|---|

#### ket_qua_38/m2: cap slot / kiem rong

- kiem_rong np3_c221184 k=3 lan=0: rong=0 token_ra=[179, 198, 318] ket_thuc=['stop', 'stop', 'stop']
- kiem_rong np5_c184320 k=5 lan=0: rong=0 token_ra=[85, 148, 247, 341, 388] ket_thuc=['stop', 'stop', 'stop', 'stop', 'stop']
- {"su_kien": "ke_hoach", "cau_hinh": [[3, 221184], [4, 200704], [5, 184320]], "cong_thuc": "c = 221184 - ceil((np-3)*449/224*8192 /4096)*4096", "luc": "2026-09-17T17:07:48"}
- {"su_kien": "kiem_tran", "nhan": "np3_c221184", "tran": false, "shared_mib": 568.0, "shared_goc_np3": 568.0, "bien_mib": 540, "luc": "2026-09-17T17:08:20"}
- {"su_kien": "cong_decode_don", "nhan": "np3_c221184", "tps": [78.14012435748481, 57.673120939744564, 71.55722239228537], "trung_vi": 71.55722239228537, "dat_60": true, "luc": "2026-09-17T17:08:46"}
- {"su_kien": "kiem_tran", "nhan": "np4_c200704", "tran": false, "shared_mib": 532.0, "shared_goc_np3": 568.0, "bien_mib": 652, "luc": "2026-09-17T17:10:59"}
- {"su_kien": "cong_decode_don", "nhan": "np4_c200704", "tps": [60.07134265446212, 56.56845563577354, 54.08773623559729], "trung_vi": 56.56845563577354, "dat_60": false, "luc": "2026-09-17T17:11:30"}
- {"su_kien": "kiem_tran", "nhan": "np5_c184320", "tran": false, "shared_mib": 506.0, "shared_goc_np3": 568.0, "bien_mib": 650, "luc": "2026-09-17T17:12:10"}
- {"su_kien": "cong_decode_don", "nhan": "np5_c184320", "tps": [77.1777880211615, 59.35185451896425, 75.00910824885878], "trung_vi": 75.00910824885878, "dat_60": true, "luc": "2026-09-17T17:12:37"}

### doi chung ctrl

| card | dieu kien | decode don tok/s (3 luot) | trung vi | prefill 32k tok/s | TTFT 32k s | cpu% truoc luot |
|---|---|---|---|---|---|---|
| ctrl35 | co lap | [69.5, 70.7, 83.8] | 70.7 | [1999.0] | [16.018] | [8.3, 8.3, 11.8] |
|  | gpu luc bat dau tung luot | [{'b03e78': {'used': 66, 'total': 24576, 'util': 0}, '6dc1df': {'used': 15670, 'total': 16311, 'util': 0}}, {'b03e78': {'used': 66, 'total': 24576, 'util': 1}, '6dc1df': {'used': 15786, 'total': 16311, 'util': 77}}, {'b03e78': {'used': 66, 'total': 24576, 'util': 1}, '6dc1df': {'used': 15786, 'total': 16311, 'util': 84}}] | | | | |
| ctrl35 | song song | [85.1, 73.9, 81.5] | 81.5 | [1990.0] | [16.099] | [16.6, 14.7, 16.4] |
|  | gpu luc bat dau tung luot | [{'b03e78': {'used': 15300, 'total': 24576, 'util': 25}, '6dc1df': {'used': 15670, 'total': 16311, 'util': 0}}, {'b03e78': {'used': 24058, 'total': 24576, 'util': 47}, '6dc1df': {'used': 15786, 'total': 16311, 'util': 82}}, {'b03e78': {'used': 24060, 'total': 24576, 'util': 44}, '6dc1df': {'used': 15786, 'total': 16311, 'util': 83}}] | | | | |
| ctrl38 | co lap | [65.4, 58.7, 56.0] | 58.7 | [1095.0] | [29.227] | [12.0, 14.3, 4.7] |
|  | gpu luc bat dau tung luot | [{'b03e78': {'used': 24036, 'total': 24576, 'util': 0}, '6dc1df': {'used': 415, 'total': 16311, 'util': 0}}, {'b03e78': {'used': 24060, 'total': 24576, 'util': 45}, '6dc1df': {'used': 415, 'total': 16311, 'util': 0}}, {'b03e78': {'used': 24060, 'total': 24576, 'util': 87}, '6dc1df': {'used': 415, 'total': 16311, 'util': 0}}] | | | | |
| ctrl38 | song song | [76.2, 59.9, 59.0] | 59.9 | [1092.0] | [29.269] | [12.0, 19.2, 19.8] |
|  | gpu luc bat dau tung luot | [{'b03e78': {'used': 24036, 'total': 24576, 'util': 0}, '6dc1df': {'used': 15786, 'total': 16311, 'util': 84}}, {'b03e78': {'used': 24060, 'total': 24576, 'util': 81}, '6dc1df': {'used': 15786, 'total': 16311, 'util': 82}}, {'b03e78': {'used': 24060, 'total': 24576, 'util': 54}, '6dc1df': {'used': 15786, 'total': 16311, 'util': 99}}] | | | | |

- he_thong ket_qua_35: n=218 cpu% p50=14.5 max=30.9; RAM trong min=73.2 GB max=114.1 GB; tu 2026-09-17T16:51:38 den 2026-09-17T17:28:10

- he_thong ket_qua_38: n=152 cpu% p50=14.5 max=30.9; RAM trong min=73.2 GB max=114.1 GB; tu 2026-09-17T16:51:38 den 2026-09-17T17:17:03

- he_thong ket_qua_ctrl_co_lap: n=17 cpu% p50=8.6 max=13.7; RAM trong min=96.2 GB max=114.4 GB; tu 2026-09-17T16:48:21 den 2026-09-17T16:51:02
