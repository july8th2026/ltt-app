'use strict';
// Lop THU HAI cho `core.code` (chua dang ky node — P-D muc 2), dat BEN TRONG
// vo AppContainer da co (`platform_core/workflow/vo_boc.py`).
//
// 🔴 Vai dung cua tep nay, va CHI vai do: chan mot piece THUONG kem — no
//    KHONG phai ranh gioi an ninh. Ranh gioi an ninh van la AppContainer.
//    Ly do (chot trong plan, doc `vo_boc.py` §11.2, va CVE-2026-25049 cua n8n
//    — thoat sandbox trong `vm`/`isolated-vm` sau khi ho da bo `vm2`): mot
//    sandbox JS trong-tien-trinh la mot be mat co lich su CVE dai; ta dung no
//    lam LOP SIET THEM (het gio nhanh hon, tran bo nho rieng, khong `require`
//    trong isolate), khong dung no thay AppContainer.
//
// Nguon PORT (MIT, ⛔ ngoai packages/ee/): activepieces/activepieces
// `packages/server/engine/src/lib/core/code/v8-isolate-code-sandbox.ts`.
// Sao lai dung hinh dang core: Isolate({memoryLimit}) + createContext +
// ExternalCopy cho input + compileScript + script.run({timeout, reference,
// promise}) + boc CJS KHONG dinh nghia `require` (chan moi built-in cua Node
// tu BEN TRONG isolate — script khong the `require('fs')` vi `require`
// khong ton tai, khong phai vi no bi chan bang mot danh sach den).
//
// ⭐ MOT CHO SUA so voi ban goc — do duoc, khong phai suy doan:
//    `isolate.dispose()` trong `finally` cua ban goc GIA DINH isolate con
//    song. Do 25/09 tren spike rieng (memoryLimit=32, vong lap cap phat vo
//    han): khi V8 tu HUY isolate vi cham tran bo nho, `script.run()` nem
//    "Isolate was disposed during execution due to memory limit" — DUNG —
//    nhung goi `isolate.dispose()` LAN NUA trong `finally` nem
//    "Isolate is already disposed", VA lan nay tien trinh Node **segfault**
//    (khong phai mot loi doc duoc, ma la tien trinh chet). Vá: kiem
//    `isolate.isDisposed` truoc khi goi `dispose()`.
const ONE_HUNDRED_TWENTY_EIGHT_MB = 128;
const HAN_MAC_DINH_MS = 8000;

let ivmCache;
function _layIvm() {
  if (!ivmCache) ivmCache = require('isolated-vm');
  return ivmCache;
}

// Boc CJS: `exports`/`module` co dinh nghia nhung `require` THI KHONG — day
// la toan bo co che chan Node builtin tu ben trong isolate. `inputs` da duoc
// bom vao nhu mot global (xem `_khoiContext`).
function boiCjs(nguon) {
  return `(function() {
  const exports = Object.create(null);
  const module = { exports };
  ${nguon}
  return module.exports.code(inputs);
})()`;
}

async function _khoiContext(isolate, inputs) {
  const ivm = _layIvm();
  const ctx = await isolate.createContext();
  await ctx.global.set(
    'inputs', new ivm.ExternalCopy(inputs === undefined ? {} : inputs).copyInto());
  return ctx;
}

function _huyAnToan(isolate) {
  // ⭐ Diem sua duy nhat so voi ban goc — xem docstring dau tep.
  try {
    if (!isolate.isDisposed) isolate.dispose();
  } catch (_e) {
    // isolate co the da tu huy giua kiem tra va goi (dua CPU) — nuot, day la
    // duong DON DEP, khong phai duong bao loi.
  }
}

/**
 * Chay `nguon` (mot module CJS voi `module.exports.code = function(inputs)`)
 * trong mot V8 Isolate rieng. Nem neu source loi, het gio, hoac cham tran
 * bo nho — nguoi goi (runner.js) bat va anh xa sang giao thuc §11.1.
 */
async function chayCode({ nguon, inputs, han_ms, bo_nho_mb }) {
  const ivm = _layIvm();
  const isolate = new ivm.Isolate({
    memoryLimit: Number(bo_nho_mb || ONE_HUNDRED_TWENTY_EIGHT_MB),
  });
  try {
    const ctx = await _khoiContext(isolate, inputs);
    const script = await isolate.compileScript(boiCjs(String(nguon || '')));
    const outRef = await script.run(ctx, {
      timeout: Number(han_ms || HAN_MAC_DINH_MS),
      reference: true,
      promise: true,
    });
    return outRef.copy();
  } finally {
    _huyAnToan(isolate);
  }
}

module.exports = { boiCjs, chayCode };
