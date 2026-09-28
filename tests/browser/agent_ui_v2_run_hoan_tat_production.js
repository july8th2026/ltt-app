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

  const goi = async (duong, body, phuong = 'POST', themHeader = {}) => {
    const r = await page.request.fetch(GOC + duong, {
      method: phuong,
      headers: { 'content-type': 'application/json', 'x-csrf-token': csrf,
                 ...themHeader },
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
  // ⚠️ `/runs` (SO NHIEU) — doc tu `runs_v3.py:465`, ⛔ khong doan.
  //
  // 🔴 Toi doan HAI duong dan trong kich ban nay va CA HAI sai:
  //      `GET  /agent/api/v3/mau`               -> 404 (cua ay KHONG TON TAI)
  //      `POST /agent/api/v3/workflows/{id}/run` -> 404 (that la `/runs`)
  //
  //    Moi lan toi suy duong dan tu **ten mien nghiep vu** thay vi doc bang dinh
  //    tuyen. Va ca hai lan phep do ⛔ khong bao dat — no bao 404, tuc no that
  //    bai **ve phia an toan**. Nhung no ton mot luot chay production moi lan.
  //
  // ⭐ Cach re hon: `grep "@router.post" apps/agent/routes/<tep>.py` TRUOC khi
  //    viet mot loi goi. Mot phut doc doi lay mot luot chay.
  // ⭐ `Idempotency-Key` la BAT BUOC — cua tra 400 `thieu_idempotency_key` voi
  //    mot thong diep noi dung cai thieu. Do la mot thong diep loi TOT: no ⛔
  //    khong bat toi doan, khac han hai lan 404 truoc do.
  //
  // ⚠️ Khoa phai DUY NHAT moi lan do: dung lai mot khoa cu se tra ve **run cu**
  //    (dung theo thiet ke khu trung), va phep do se doc mot run ⛔ khong phai
  //    cua luot nay — mot cach "xanh tren thu da hong" rat kho thay.
  const khoaIdem = `do-run-hoan-tat-${Date.now()}`;
  so.idem_key = khoaIdem;
  const chay = await goi(`/agent/api/v3/workflows/${wid}/runs`, {}, 'POST',
                         { 'Idempotency-Key': khoaIdem });
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

  // ── 5b. KHI THAT BAI, TU IN CHAN DOAN ────────────────────────────────────
  //
  // 🔴 Luot do dau tien tra ve: `y_tuong` FAILED, `outputs = {}`, `run.error = ""`.
  //    Toi ⛔ khong chan doan duoc gi tu do, va khi di viet mot kich ban chan doan
  //    RIENG thi phat hien no can `GET /api/v3/runs` — mot cua **⛔ KHONG TON TAI**.
  //    Ma toi cung ⛔ khong co `run_id` day du, vi kich ban nay chi in 8 ky tu dau.
  //
  // ⇒ Nen chan doan phai nam **trong chinh phep do**: mot phep do that bai ma ⛔
  //   khong de lai du lieu de tim nguyen nhan thi no bat nguoi ta chay lai — va
  //   moi lan chay lai la mot run that.
  //
  // ⭐ `node.error` la cho thong diep THAT SU nam: `cau_noi.ap_ket_qua` ghi
  //    `error=f"{ma}: {chi_tiet}"` len **node**, ⛔ khong len `run`. Doc `run.error`
  //    roi ket luan "khong co thong diep" la doc sai cho.
  so.run_id_day_du = String(rid);
  // ⚠️ Doc `run.nodes` truc tiep, ⛔ KHONG dung bien `nodes` — no duoc khai bang
  //    `const` o buoc 6 (BEN DUOI), va `const` ⛔ khong hoisting nen tham chieu o
  //    day nem `ReferenceError: Cannot access 'nodes' before initialization`.
  //    Toi da mac dung loi nay o luot truoc: mot buoc chan doan them vao **truoc**
  //    cho khai bien, va no lam ca phep do vo — tuc buoc chan doan tu no thanh
  //    thu can chan doan.
  so.node_loi = (run.nodes || []).filter(n => String(n.status) === 'FAILED').map(n => ({
    id: String(n.node_id || n.id || ''),
    error: String(n.error || '(rong)').slice(0, 300),
    attempt: n.attempt_number ?? null,
    job_id: String(n.job_id || '').slice(0, 10),
  }));

  const sk = await goi(`/agent/api/v3/runs/${rid}/su-kien`, undefined, 'GET');
  so.su_kien_status = sk.status;
  const evs = Array.isArray(sk.than?.items) ? sk.than.items
            : Array.isArray(sk.than) ? sk.than : [];
  so.so_su_kien = evs.length;
  so.su_kien_cuoi = evs.slice(-10).map(e => ({
    node: String(e.node_id || '').slice(0, 12),
    sang: String(e.sang || e.status || e.loai || ''),
    mo_ta: String(e.error || e.mo_ta || e.message || '').slice(0, 180),
  }));

  // ── 6. Doc TUNG node: chinh day la cau hoi thu hai ───────────────────────
  const nodes = Array.isArray(run.nodes) ? run.nodes : [];
  so.so_node = nodes.length;
  // ⚠️ Cua tra `output_ref`, ⛔ KHONG `outputs` — doc tu `runs_v3.py:683`.
  //
  // 🔴 Lan thu BA toi doan ten mot truong/duong dan trong kich ban nay:
  //      `GET /agent/api/v3/mau`   -> khong ton tai
  //      `POST .../run`            -> that la `/runs`
  //      `n.outputs`               -> that la `n.output_ref`
  //
  //    Va lan nay no ⛔ khong bao 404: no cho ra `co_output: false` va
  //    `ai_llm_co_text: false` cho MOI node — **mot ket qua doc duoc nhu mot phat
  //    hien ve san pham**. Toi suyt bao *"`doi_dau_ra` khong chay tren production"*
  //    trong khi node do SUCCEEDED va phep do chi doc sai ten truong.
  //
  // ⚠️ Hai lan truoc that bai VE PHIA AN TOAN (404 — khong the doc thanh cai gi
  //    khac). Lan nay that bai ve phia **NGUY HIEM**: mot `false` im lang.
  //    ⇒ Doan ten mot CUA thi ta biet ngay; doan ten mot TRUONG thi ta nhan mot
  //      gia tri mac dinh, va gia tri mac dinh **tron giong mot cau tra loi**.
  so.node = nodes.map(n => ({
    id: String(n.node_id || n.id || '').slice(0, 12),
    status: String(n.status || ''),
    output_ref: JSON.stringify(n.output_ref ?? null).slice(0, 220),
  }));

  // `ai.llm` phai co output `text` KHONG RONG — do la ve chung minh
  // `doi_dau_ra` chay that, thu ⛔ khong phep kiem cuc bo nao lam duoc.
  const ai = nodes.find(n => String(n.node_id || n.id || '').includes('y_tuong'));
  if (ai) {
    const out = ai.output_ref || {};
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
