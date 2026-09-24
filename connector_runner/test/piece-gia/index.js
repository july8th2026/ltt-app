'use strict';
// `@ltt/piece-gia` — piece GIA cho test (spec §18.1).
//
// ⛔ Chi nap duoc khi `LTT_TEST=1` (`src/piece_nap.js`). Ly do khong phai ve
//    su gon gang: hai action duoi day co tinh **thoat ranh gioi** (goi thang
//    ra Internet, va de mot tien trinh con goi ho). Chung la **phep nghiem
//    thu** cua `vo_boc.py`, va mot ban nap duoc tren production la dung thu
//    ma ca phase nay sinh ra de chan.
//
// ⭐ Piece nay KHONG phu thuoc `@activepieces/pieces-framework`: no chi phai
//    tra ve dung HINH DANG ma `runner.js` doc (`metadata()`, `actions()`,
//    `triggers()`). Phu thuoc vao framework de lam mot piece gia la buoc phep
//    kiem cua ta phu thuoc vao mot ban cap nhat cua ben thu ba.

const { spawnSync } = require('child_process');

function action(name, run, props) {
  return { name, displayName: name, description: '', props: props || {}, run };
}

const actions = {
  // --- duong binh thuong -------------------------------------------------
  thanh_cong: action('thanh_cong', async (ctx) => ({
    ok: true, nhan_duoc: ctx.propsValue, auth_co: ctx.auth !== null,
  })),

  loi_dau_vao: action('loi_dau_vao', async () => {
    throw new Error('dau vao sai: thieu truong `kenh`');
  }),

  loi_429: action('loi_429', async () => {
    const loi = new Error('Too Many Requests');
    loi.response = { status: 429, headers: { 'retry-after': '7' } };
    throw loi;
  }),

  cham: action('cham', async (ctx) => {
    const ms = Number((ctx.propsValue || {}).ms || 5000);
    await new Promise((r) => setTimeout(r, ms));
    return { ngu_ms: ms };
  }),

  mo_ho: action('mo_ho', async () => {
    // "Job xong nhung ket qua khong dung duoc" — ca da do that tren may B
    // (10-12/09): HTTP 200, status SUCCEEDED, noi dung RONG.
    return { content: '' };
  }),

  che_bi_mat: action('che_bi_mat', async () => ({
    authorization: 'Bearer xoxb-that-su-bi-mat',
    long: { api_key: 'sk-that-su-bi-mat', an_toan: 'giu lai' },
  })),

  ghi_store: action('ghi_store', async (ctx) => {
    const cu = await ctx.store.get('dem');
    const moi = Number(cu || 0) + 1;
    await ctx.store.put('dem', moi);
    return { dem: moi, cu: cu };
  }),

  ghi_tep: action('ghi_tep', async (ctx) => {
    const d = await ctx.files.write({ fileName: 'ra.txt', data: 'noi dung gia' });
    return { duong: d };
  }),

  dung_waitpoint: action('dung_waitpoint', async (ctx) => {
    // `xuat_catalog` phai LOAI action nay bang phep kiem tinh; neu no chay
    // duoc thi phep kiem tinh da hong.
    return ctx.run.createWaitpoint({});
  }),

  // --- phep nghiem thu RANH GIOI ----------------------------------------
  thoat_truc_tiep: action('thoat_truc_tiep', async (ctx) => {
    const dich = String((ctx.propsValue || {}).url || 'https://example.com/');
    return await new Promise((giai) => {
      const xong = (s) => giai({ ket_qua: s });
      try {
        require('https').get(dich, (r) => xong('REACHED ' + r.statusCode))
          .on('error', (e) => xong('BLOCKED ' + (e.code || e.message)));
      } catch (e) {
        xong('BLOCKED ' + (e.code || e.message));
      }
    });
  }),

  thoat_bang_tien_trinh_con: action('thoat_bang_tien_trinh_con', async (ctx) => {
    // 🔴 DAY LA PHEP NGHIEM THU. Ban sao NGUYEN VEN cua logic trong
    //    `spike/egress/piece-child-process.js`, chay BEN TRONG runner that:
    //    `-r <preload>` khong di theo `spawn`, nen moi lop va trong-tien-trinh
    //    bi di vong. Chi ranh gioi o muc HDH (AppContainer) chan duoc no.
    //
    // ⚠️ `stdio: 'inherit'`, ⛔ khong dung ong: do 24/09, ong treo cung ben
    //    trong AppContainer, nen mot phep thu bang ong khong phan biet duoc
    //    "con bi chan mang" voi "spawn hong".
    const dich = String((ctx.propsValue || {}).url || 'https://example.com/');
    const ma = "require('https').get(" + JSON.stringify(dich) + ", r => {"
      + "process.stdout.write('CHILD_REACHED ' + r.statusCode + '\\n');process.exit(0);})"
      + ".on('error', e => {process.stdout.write('CHILD_BLOCKED ' + (e.code||e.message) + '\\n');process.exit(0);});";
    // ⭐ GO SACH bien proxy truoc khi de con chay: mot piece CO Y se lam dung
    //    the. Neu khong go, Node 24 (`NODE_USE_ENV_PROXY=1`) se lai dat con
    //    di qua proxy cua ta va phep do se do NHAM — no se do proxy chan,
    //    chu khong do AppContainer chan.
    const moi = Object.assign({}, process.env);
    for (const k of ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy',
      'NODE_USE_ENV_PROXY', 'NO_PROXY']) delete moi[k];
    const r = spawnSync(process.execPath, ['-e', ma],
      { stdio: 'inherit', timeout: 20000, env: moi });
    return { spawn_status: r.status, spawn_err: r.error ? (r.error.code || r.error.message) : 'none' };
  }),
};

const triggers = {
  poll_gia: {
    name: 'poll_gia',
    displayName: 'Poll gia',
    description: 'Tra ve cac ban ghi tu `ban_ghi` chua thay o lan poll truoc.',
    type: 'POLLING',
    props: {},
    async onEnable(ctx) { await ctx.store.put('da_bat', true); return null; },
    async onDisable(ctx) { await ctx.store.delete('da_bat'); return null; },
    async run(ctx) {
      const moi = ((ctx.propsValue || {}).ban_ghi) || [];
      const daThay = (await ctx.store.get('da_thay')) || [];
      const ra = moi.filter((x) => daThay.indexOf(String(x.id)) < 0);
      await ctx.store.put('da_thay', daThay.concat(ra.map((x) => String(x.id))));
      return ra;
    },
  },
};

const pieceGia = {
  metadata() {
    return {
      displayName: 'LTT Gia',
      logoUrl: '',
      description: 'piece gia cho test',
      auth: { type: 'SECRET_TEXT', props: {} },
      categories: [],
      authors: [],
    };
  },
  actions() { return actions; },
  triggers() { return triggers; },
};

module.exports = { pieceGia };
