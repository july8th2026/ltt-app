// `doi_dau_ra` co CHAY tren duong san pham khong? — do bang `core.output`.
//
// ## 🔴 Vi sao phai do bang `core.output` chu khong doc cua API
//
// Toi mat BA luot do vi tuong `GET /agent/api/v3/runs/{id}` tra output cua node:
//
//     n.outputs      -> undefined   (tra `false`, doc nhu mot cau tra loi)
//     n.output_ref   -> null        (van khong phai truong that)
//
// Doc ma thi `_nodes_json` (`runs_v3.py:374-381`) tra dung tam truong:
// `node_id · status · attempt · cost_credit · job_id · waiting_kind · het_han ·
// error`. Cua ay **CO Y** ⛔ khong tra output cua node.
//
// ⭐ ⇒ Phep do dung di qua **chinh co che san pham**: `core.output` doc bieu thuc
//    `{{ nodes.<id>.output.text }}` va dat gia tri vao **output cua RUN** — thu ma
//    cua ay CO tra. Nen bai nay ⛔ khong can mot cua noi bo nao, va no do dung thu
//    khach se thay.
//
// ## Vi sao KHONG dung mau 4
//
// Mau `ai-viet-mo-ta-roi-sinh-anh` co `app.image.generate` o giua, va node ay
// **dang hong tren production** (`Model tra loi rong` khi dich prompt — xem
// `docs/DICH_PROMPT_ANH_MODEL_TRA_RONG.md`). Mot node hong o giua lam `core.output`
// SKIPPED, nen no che mat cau hoi ta dang hoi.
//
// ⇒ Do thi phai **co lap**: `trigger.manual -> ai.llm -> core.output`. Ba node, ⛔
//   khong hon. Gia: `ai.llm` theo registry (`Gia.theo_registry("ltt_llm.chat")`).
//
// ## ⛔ Chi mot lan chay, va no tieu credit that
//
//   python tools\chay_web_that.py tests\browser\agent_ui_v2_doi_dau_ra_tren_production.js --phien doidaura
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
  await page.goto(GOC + '/agent/workflows', { waitUntil: 'domcontentloaded',
                                              timeout: 60000 });
  const csrf = await page.evaluate(() => {
    const m = document.querySelector('meta[name="csrf-token"]');
    if (m) return m.getAttribute('content') || '';
    const i = document.querySelector('input[name="csrf_token"]');
    return i ? i.value : '';
  });
  check(Boolean(csrf), 'khong lay duoc CSRF');
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

  // ── Tai lieu CO LAP: trigger -> ai.llm -> core.output ────────────────────
  //
  // ⭐ `prompt` ngan va CO CHI TIET kiem duoc: neu `text` ve tay ta chua tu
  //    "windowsill"/"window sill" thi phep dich da mat chi tiet — mot thong tin
  //    tang, mien phi.
  const PROMPT = 'Translate to English, return ONLY the translation: '
               + 'con meo tam the ngu tren bau cua so';
  const doc = {
    version: 3,
    pages: [{
      id: 'p1',
      nodes: [
        { id: 'bat_dau', type: 'trigger.manual', position: { x: 0, y: 0 } },
        { id: 'y_tuong', type: 'ai.llm', position: { x: 240, y: 0 },
          params: { prompt: PROMPT, model: 'ltt-3.8' } },
        { id: 'ra', type: 'core.output', position: { x: 480, y: 0 },
          params: { ten: 'ban_dich', gia_tri: 'nodes.y_tuong.output.text' } },
      ],
      // 🔴 CANH la BAT BUOC, va cua publish noi thang khi thieu:
      //
      //    422 tham_chieu_khong_phai_to_tien: node 'ra' doc
      //        nodes.y_tuong.output.text nhung 'y_tuong' KHONG phai to tien
      //
      //   ⇒ Thu tu thuc thi suy tu **CANH**, ⛔ khong tu vi tri trong danh sach
      //     `nodes`. Ban dau toi de `edges: []` va tuong thu tu khai la du.
      //
      // ⭐ Va day la mot cua TOT: no tu choi o `publish` — TRUOC khi khach bam
      //    Chay va TRUOC khi tieu credit — kem ten node va ten bieu thuc. So voi
      //    ba lan 404/null toi gap hom nay, thong diep nay noi dung cai thieu.
      //
      // Khuon lay tu `apps/agent/mau.py:277` (`bat_dau.event -> y_tuong.prompt`).
      edges: [
        { id: 'e1', source_node: 'bat_dau', target_node: 'y_tuong',
          source_port: 'event', target_port: 'prompt', kind: 'DATA' },
        { id: 'e2', source_node: 'y_tuong', target_node: 'ra',
          source_port: 'text', target_port: 'in', kind: 'DATA' },
      ],
    }],
  };

  const tao = await goi('/agent/api/v3/workflows',
                        { ten: 'DO doi_dau_ra 28-09', document: doc });
  so.tao = tao.status;
  const wid = tao.than?.id;
  check(Boolean(wid), `tao workflow -> ${tao.status} `
        + JSON.stringify(tao.than).slice(0, 200));
  if (!wid) return { status: 'FAIL', loi, so };
  so.workflow = String(wid).slice(0, 8);

  const pub = await goi(`/agent/api/v3/workflows/${wid}/publish`, {});
  so.publish = pub.status;
  check(pub.status === 200, `publish -> ${pub.status} `
        + JSON.stringify(pub.than).slice(0, 250));
  if (pub.status !== 200) return { status: 'FAIL', loi, so };

  // ⭐ Khoa DUY NHAT moi luot do — dung lai khoa cu se tra ve **run CU**, va
  //    phep do se doc so cua mot luot khac.
  const chay = await goi(`/agent/api/v3/workflows/${wid}/runs`, {}, 'POST',
                         { 'Idempotency-Key': `do-doi-dau-ra-${Date.now()}` });
  so.run = chay.status;
  const rid = chay.than?.run_id || chay.than?.id;
  check(Boolean(rid), `run -> ${chay.status} `
        + JSON.stringify(chay.than).slice(0, 250));
  if (!rid) return { status: 'FAIL', loi, so };
  so.run_id = String(rid).slice(0, 8);

  const KET_THUC = new Set(['SUCCEEDED', 'FAILED', 'CANCELLED', 'ABANDONED',
                            'TIMED_OUT']);
  const HAN = 6 * 60 * 1000;
  const t0 = Date.now();
  let run = null;
  while (Date.now() - t0 < HAN) {
    const r = await goi(`/agent/api/v3/runs/${rid}`, undefined, 'GET');
    run = r.than;
    if (run && KET_THUC.has(String(run.status))) break;
    await page.waitForTimeout(4000);
  }
  so.giay = Math.round((Date.now() - t0) / 1000);
  so.trang_thai = run ? String(run.status) : '(khong doc duoc)';
  so.node = (run?.nodes || []).map(n => `${n.node_id}:${n.status}`);

  if (!run || !KET_THUC.has(String(run.status))) {
    loi.push(`HET GIO sau ${so.giay}s, run con o \`${so.trang_thai}\` — phep do `
             + 'CHUA CO ket qua, ⛔ KHONG phai bang chung run hong');
    return { status: 'CHUA_DO_DUOC', loi, so };
  }

  // ── Cau hoi chinh: output cua RUN co `ban_dich` khong rong? ──────────────
  //
  // ⚠️ `core.output` dat gia tri vao output cua RUN. Doc NHIEU ten kha di roi noi
  //    ro ten nao doc duoc — ⛔ khong doan MOT ten: toi da doan sai ba lan trong
  //    kich ban truoc, va mot ten sai cho ra `undefined` **trong giong mot cau
  //    tra loi**.
  const ung_vien = { outputs: run.outputs, output: run.output,
                     ket_qua: run.ket_qua, outputs_ref: run.outputs_ref };
  so.khoa_run_doc_duoc = Object.keys(run || {});
  so.ung_vien = Object.fromEntries(Object.entries(ung_vien)
    .map(([k, v]) => [k, v === undefined ? '(khong co truong)'
                        : JSON.stringify(v).slice(0, 200)]));

  const nguon = ung_vien.outputs ?? ung_vien.output ?? ung_vien.ket_qua ?? {};
  const ban_dich = typeof nguon === 'object' && nguon
    ? (nguon.ban_dich ?? nguon['ban_dich']) : undefined;
  so.ban_dich = typeof ban_dich === 'string' ? ban_dich.slice(0, 160) : ban_dich;
  so.ban_dich_dai = typeof ban_dich === 'string' ? ban_dich.length : null;

  check(String(run.status) === 'SUCCEEDED',
        `run ket thuc o \`${run.status}\`, ⛔ khong phai SUCCEEDED. `
        + `node: ${so.node.join(' ')} · loi: `
        + JSON.stringify(run.error ?? '').slice(0, 200));
  check(typeof ban_dich === 'string' && ban_dich.trim().length > 0,
        '`core.output` ⛔ KHONG cho ra `ban_dich` khong rong ⇒ hoac `doi_dau_ra` '
        + '⛔ khong chay tren duong san pham, hoac output cua run nam o mot ten '
        + `khac. Khoa doc duoc tren run: ${so.khoa_run_doc_duoc.join(',')}`);

  // ⭐ Thong tin tang: dich co giu chi tiet khong.
  if (typeof ban_dich === 'string') {
    so.giu_bau_cua_so = /window\s?sill|windowsill/i.test(ban_dich);
    so.giu_tam_the = /calico|tortoiseshell|tri-?colou?r/i.test(ban_dich);
  }

  return { status: loi.length ? 'FAIL' : 'PASS', loi, so };
}
