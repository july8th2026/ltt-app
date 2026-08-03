# 09 — Release runbook

1. Frontend test/typecheck/build; targeted Python; full `pytest -q`; secret scan.
2. Kiểm bundle freshness/size; build archive; archive secret scan phải 0.
3. `update.ps1`: backup dữ liệu/PostgreSQL, giữ `app.previous`, migrate, restart.
4. Chạy `setup/4-nghiem-thu.ps1`; health loopback và Cloudflare phải ready.
5. Browser production desktop/mobile: login → Canvas → palette/search → add/select
   node → composer → typed connect → validate/quote → create/approve test-safe run;
   console 0, failed request bất ngờ 0, overflow 0.
6. Nếu P0/P1 regression: rollout Agent Canvas off hoặc chạy rollback; không sửa
   nóng production data. Secret/provider credential không đưa vào ảnh/log.

Rollback: `LTT_AGENT_CANVAS_RUN_ROLLOUT=off` cho run; release-level dùng
`C:\LTTPlatform\app\deploy\windows\rollback.ps1`. Migration hiện additive.
