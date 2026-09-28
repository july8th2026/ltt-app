// Mot RUN HOAN TAT tren PRODUCTION — dai luong duy nhat con lai cua plan UI V2.
//
// ## 🔴 Vi sao phep do nay phai ton tai, va vi sao no DAT
//
// UI-7 va UI-11 deu ghi ro mot thu chung **KHONG do duoc**: *run co that su hoan
// tat khong*. Ly do ho ghi la *"can worker chay duoi LocalSystem"*. Ly do ay nay
// **da het dung** — worker production LA LocalSystem. Thu con lai la mot ly do
// KHAC han: mot run that **tieu credit that cua mot khach that**.
//
// ⇒ Nen phep do nay ⛔ khong phai "mot bai test nua". No la mot **giao dich co
//   gia**, va chu du an da cho phep. Mau 4 bao gia **17 credit toi da / 11 uoc
//   tinh** (`bao_gia.bao_gia_do_thi`, tat dinh).
//
// ⭐ Chon mau 4 (`ai-viet-mo-ta-roi-sinh-anh`) chu ⛔ khong mau 1 (3 credit) co ly
//    do: mau 4 di qua `ai.llm` **roi** mot node DOC dau ra ay
//    (`app.image.generate` nhan `prompt` tu `nodes.y_tuong.output.text`). Nen mot
//    lan chay no tra loi HAI cau:
//
//      1. run co hoan tat tren production khong?
//      2. `NodeDefinition.doi_dau_ra` (them 28/09) co that su dich `content` ->
//         `text` tren duong SAN PHAM khong?
//
//    Mau 1 chi tra loi cau 1. Muoi bon credit chenh lech mua duoc cau thu hai —
//    va cau thu hai la thu **⛔ khong phep kiem cuc bo nao** chung minh duoc: moi
//    bai `test_5611` deu goi ham dich TRUC TIEP, ⛔ khong qua `cau_noi.ap_ket_qua`
//    that voi mot job that.
//
// ## ⚠️ Thu kich ban nay ⛔ KHONG lam
//
// ⛔ Khong `publish` hay chay workflow nao **cua khach khac**. Chi tai khoan thu.
// ⛔ Khong doi han muc, khong nap credit, khong cham `credit.py`.
// ⛔ Khong ket luan "hoan tat" tu trang thai `QUEUED` hay `RUNNING`: phep do nay
//    **cho** toi mot trang thai KET THUC, va neu het gio thi no bao **het gio**
//    chu ⛔ khong bao dat. Mot phep do het gio la mot phep do CHUA CO.
//
//   python tools\chay_web_that.py tests\browser\agent_ui_v2_run_hoan_tat_production.js --phien runthat
async page => {
  const COOKIE = '__LTT_COOKIE__';
  if (!COOKIE || COOKIE.startsWith('__LTT_'))
    throw new Error('chua dien cookie - chay qua `python tools/chay_web_that.py`');

  const GOC = 'https://app.lttstudios.com';
  const so = {};
  const loi = [];
  const check = (dk, msg) => { if (!dk) loi.push(msg) };

  await page.context().addCookies([{
    name: 'session', value: COOKIE, domain: 'app.lttstudios.com',
    path: '/', httpOnly: true, secure: true, sameSite: 'Lax',
  }]);

  // ── CSRF: cung khuon cac kich ban v3 khac ────────────────────────────────
  await page.goto(GOC + '/agent/workflows', { waitUntil: 'domcontentloaded',
                                              timeout: 60000 });
  const csrf = await page.evaluate(() => {
    const m = document.querySelector('meta[name="csrf-token"]');
    if (m) return m.getAttribute('content') || '';
    const i = document.querySelector('input[name="csrf_token"]');
    return i ? i.value : '';
  });
  check(Boolean(csrf), 'khong lay duoc CSRF tu /agent/workflows');
  if (!csrf) return { status: 'FAIL', loi, so };

  const goi = async (duong, body, phuong = 'POST') => {
    const r = await page.request.fetch(GOC + duong, {
      method: phuong,
      headers: { 'content-type': 'application/json', 'x-csrf-token': csrf },
      data: body === undefined ? undefined : { ...body, csrf_token: csrf },
    });
    let than = null;
    try { than = await r.json() } catch { than = await r.text() }
    return { status: r.status(), than };
  };

  // ── 1-2. BAM NUT "Dung mau nay" — dung duong NGUOI DUNG di ───────────────
  //
  // 🔴 Ban dau toi goi `GET /agent/api/v3/mau` va nhan **404**: cua do ⛔ KHONG
  //    TON TAI. Toi **doan** mot duong dan API tu ten mien nghiep vu.
  //
  //    Su that: mau ⛔ khong co cua API nao. Chung duoc **nhung vao HTML** qua
  //    `mau_json` (`agent_templates.html`), va nut `[data-mau-dung]` goi
  //    `POST /agent/api/v3/workflows` voi `document` lay tu bien `MAU` trong
  //    module scope — tuc ⛔ khong doc duoc tu ngoai.
  //
  // ⭐ Nen phep do dung la **bam nut**, ⛔ khong phai goi mot cua ta tuong co.
  //    Va no TOT HON ban cu ve mat do luong: no di dung duong khach di, nen no
  //    kiem luon rang nut ay **con hoat dong** — thu mot loi goi API truc tiep
  //    ⛔ khong bao gio noi duoc.
  await page.goto(GOC + '/agent/templates',
                  { waitUntil: 'domcontentloaded', timeout: 60000 });

  const nut = page.locator('[data-mau-dung="ai-viet-mo-ta-roi-sinh-anh"]');
  so.thay_nut_mau_4 = await nut.count() > 0;
  check(so.thay_nut_mau_4,
        'khong thay nut [data-mau-dung="ai-viet-mo-ta-roi-sinh-anh"] tren '
        + '/agent/templates. Production da co mau 4 chua?');
  if (!so.thay_nut_mau_4) return { status: 'FAIL', loi, so };

  // Bam, roi doi dieu huong sang `/agent/workflows/<id>`.
  await Promise.all([
    page.waitForURL(/\/agent\/workflows\/[0-9a-f-]{8,}/, { timeout: 60000 }),
    nut.click(),
  ]);
  const wid = (page.url().match(/\/agent\/workflows\/([0-9a-f-]+)/) || [])[1];
  so.workflow_id = String(wid || '').slice(0, 8);
  check(Boolean(wid), `khong lay duoc workflow id tu URL: ${page.url()}`);
  if (!wid) return { status: 'FAIL', loi, so };

  // ── 3. Publish ───────────────────────────────────────────────────────────
  const pub = await goi(`/agent/api/v3/workflows/${wid}/publish`, {});
  so.publish_status = pub.status;
  check(pub.status === 200, `publish -> ${pub.status} `
        + JSON.stringify(pub.than).slice(0, 200));
  if (pub.status !== 200) return { status: 'FAIL', loi, so };

  // ── 4. Chay ──────────────────────────────────────────────────────────────
  const chay = await goi(`/agent/api/v3/workflows/${wid}/run`, {});
  so.run_status = chay.status;
  check([200, 201, 202].includes(chay.status),
        `run -> ${chay.status} ` + JSON.stringify(chay.than).slice(0, 200));
  const rid = chay.than?.run_id || chay.than?.id;
  if (!rid) return { status: 'FAIL', loi, so };
  so.run_id = String(rid).slice(0, 8);

  // ── 5. CHO toi trang thai KET THUC ───────────────────────────────────────
  //
  // ⚠️ `SUCCEEDED` ⛔ khong phai trang thai ket thuc duy nhat. Doi ca tap, neu
  //    khong mot run `FAILED` se lam vong nay cho het gio roi bao "het gio" —
  //    tuc bao SAI LOAI van de.
  const KET_THUC = new Set(['SUCCEEDED', 'FAILED', 'CANCELLED', 'ABANDONED',
                            'TIMED_OUT']);
  const HAN_MS = 8 * 60 * 1000;
  const t0 = Date.now();
  let run = null;
  let vong = 0;
  while (Date.now() - t0 < HAN_MS) {
    const r = await goi(`/agent/api/v3/runs/${rid}`, undefined, 'GET');
    run = r.than;
    vong += 1;
    if (run && KET_THUC.has(String(run.status))) break;
    await page.waitForTimeout(5000);
  }
  so.so_vong_hoi = vong;
  so.giay_cho = Math.round((Date.now() - t0) / 1000);
  so.trang_thai_cuoi = run ? String(run.status) : '(khong doc duoc)';

  if (!run || !KET_THUC.has(String(run.status))) {
    // ⛔ HET GIO ⛔ KHONG phai FAIL cua san pham — la phep do CHUA CO ket qua.
    //    Noi dung loai de khong ai doc no thanh "run hong".
    loi.push(`HET GIO sau ${so.giay_cho}s: run con o \`${so.trang_thai_cuoi}\`. `
             + 'Day la phep do CHUA CO ket qua, ⛔ KHONG phai bang chung run hong.');
    return { status: 'CHUA_DO_DUOC', loi, so };
  }

  // ── 6. Doc TUNG node: chinh day la cau hoi thu hai ───────────────────────
  const nodes = Array.isArray(run.nodes) ? run.nodes : [];
  so.so_node = nodes.length;
  so.node = nodes.map(n => ({
    id: String(n.node_id || n.id || '').slice(0, 12),
    status: String(n.status || ''),
    co_output: Boolean(n.outputs || n.output_ref),
  }));

  // `ai.llm` phai co output `text` KHONG RONG — do la ve chung minh
  // `doi_dau_ra` chay that, thu ⛔ khong phep kiem cuc bo nao lam duoc.
  const ai = nodes.find(n => String(n.node_id || n.id || '').includes('y_tuong'));
  if (ai) {
    const out = ai.outputs || {};
    so.ai_llm_status = String(ai.status || '');
    so.ai_llm_co_text = typeof out.text === 'string' && out.text.trim().length > 0;
    so.ai_llm_do_dai_text = typeof out.text === 'string' ? out.text.length : null;
    check(so.ai_llm_co_text,
          'node `ai.llm` KHONG co output `text` khong rong ⇒ `doi_dau_ra` '
          + '⛔ khong chay tren duong san pham. Output doc duoc: '
          + JSON.stringify(out).slice(0, 200));
  } else {
    loi.push('khong tim thay node `y_tuong` trong run — doc sai hinh dang?');
  }

  check(String(run.status) === 'SUCCEEDED',
        `run ket thuc o \`${run.status}\`, ⛔ khong phai SUCCEEDED. `
        + `Loi: ${JSON.stringify(run.error || run.loi || '').slice(0, 200)}`);

  so.credit = run.actual_cost ?? run.cost_credit ?? null;
  return { status: loi.length ? 'FAIL' : 'PASS', loi, so };
}
