'use strict';
// Runner connector — **mot lenh = mot tien trinh** (spec §11.1).
//
//     node src/runner.js <vao.json> <ra.json>
//
// 🔴 CHO CO Y LECH SPEC: giao thuc di bang TEP, khong bang stdin/stdout.
//    Spec §11.1 viet "ghi MOT JSON vao stdin, doc MOT JSON tu stdout". Do that
//    24/09: **ong (pipe) treo cung ben trong AppContainer** — treo vuot ca
//    `timeout` cua chinh Node. Ma AppContainer la ranh gioi an ninh cua ca
//    phase, nen thu phai doi la giao thuc. Tep `vao.json`/`ra.json` nam trong
//    `tmp_dir` cua dung lenh do, va Python xoa ca thu muc sau moi lenh.
//
// ⛔ KHONG dung engine/worker/API cua Activepieces. Goi thang
//    `action.run(ctx)` / `trigger.run(ctx)`. Ly do o spec §11.1 va o
//    `activepieces#11547`: engine cua ho keo theo mot mo hinh thuc thi (va mot
//    be mat tan cong) ma ta khong can.
const fs = require('fs');
const path = require('path');
const { napPiece } = require('./piece_nap');

const VAO = process.argv[2];
const RA = process.argv[3];

function ghi(obj) {
  fs.writeFileSync(RA, JSON.stringify(obj));
}

//: Ma loi cong bo (spec §11.1). ⛔ Danh sach DONG: `cau_noi` cua Python anh xa
//  tung ma nay sang trang thai node, nen mot ma thu nam se roi vao nhanh
//  "khong biet" va im lang thanh FAILED khong ly do.
const MA = {
  provider: 'provider_loi',
  dauVao: 'dau_vao_sai',
  hetGio: 'het_gio',
  heThong: 'loi_he_thong',
};

function maTuLoi(loi) {
  const st = loi && loi.response && loi.response.status;
  if (st) return { ma: MA.provider, status: Number(st) };
  const code = (loi && loi.code) || '';
  if (code === 'ETIMEDOUT' || code === 'ECONNABORTED' || code === 'ERR_CANCELED') {
    return { ma: MA.hetGio, status: 0 };
  }
  if (code === 'EGRESS_CHAN' || code === 'EGRESS_CHAN_DNS') {
    // ⭐ Khong gop vao `provider_loi`: mot piece bi chan egress la loi CUA TA
    //    (thieu mot mien trong allowlist), khong phai provider hong. Gop hai
    //    thu nay lam mot la tu bit duong chan doan.
    return { ma: MA.heThong, status: 0 };
  }
  return { ma: MA.provider, status: 0 };
}

//: Bi mat KHONG bao gio duoc ra `ra.json`. Che theo TEN, ca hai chieu (spec §9.4).
const CHE = ['authorization', 'cookie', 'set-cookie', 'x-api-key', 'token',
  'access_token', 'refresh_token', 'client_secret', 'api_key', 'password',
  'bot_token', 'private_key'];

function cheBiMat(v, sau = 0) {
  if (sau > 8 || v === null || v === undefined) return v;
  if (Array.isArray(v)) return v.map((x) => cheBiMat(x, sau + 1));
  if (typeof v === 'object') {
    const ra = {};
    for (const k of Object.keys(v)) {
      ra[k] = CHE.indexOf(String(k).toLowerCase()) >= 0
        ? '«da che»' : cheBiMat(v[k], sau + 1);
    }
    return ra;
  }
  return v;
}

function dungCtx(yc, nhatKy, storeOps, tep) {
  const store = Object.assign({}, yc.store || {});
  const camWaitpoint = () => {
    // ⛔ Nem, ⛔ khong tra `undefined`. `xuat_catalog` da loai action dung
    //    waitpoint bang phep kiem tinh; day la luoi thu hai cho ngay phep kiem
    //    tinh doc nham mot ham da bi minify.
    throw new Error('waitpoint_khong_ho_tro: runner LTT khong chay engine cua Activepieces');
  };
  return {
    auth: yc.auth === undefined ? null : yc.auth,
    propsValue: yc.props || {},
    store: {
      async get(khoa) { return store[khoa] === undefined ? null : store[khoa]; },
      async put(khoa, gia) {
        store[khoa] = gia;
        storeOps.push({ op: 'put', key: String(khoa), value: gia });
        return gia;
      },
      async delete(khoa) {
        delete store[khoa];
        storeOps.push({ op: 'delete', key: String(khoa) });
      },
    },
    files: {
      async write({ fileName, data }) {
        const ten = path.basename(String(fileName || 'tep'));
        const duong = path.join(yc.tmp_dir, ten);
        fs.writeFileSync(duong, Buffer.isBuffer(data) ? data : Buffer.from(data));
        tep.push({ path: duong, name: ten, mime: '' });
        return duong;
      },
    },
    server: { publicUrl: String(yc.public_url || ''), token: '' },
    run: {
      id: String(yc.run_id || ''),
      stop() {},
      pause: camWaitpoint,
      createWaitpoint: camWaitpoint,
    },
    project: { id: String(yc.project_id || '') },
    connections: {
      get: async () => { throw new Error('connections_khong_ho_tro'); },
    },
    generateResumeUrl: camWaitpoint,
    executionType: 'BEGIN',
    logger: {
      info: (...a) => nhatKy.push('info ' + a.map(String).join(' ')),
      warn: (...a) => nhatKy.push('warn ' + a.map(String).join(' ')),
      error: (...a) => nhatKy.push('error ' + a.map(String).join(' ')),
      debug: () => {},
    },
  };
}

async function main() {
  let yc;
  try {
    yc = JSON.parse(fs.readFileSync(VAO, 'utf8'));
  } catch (loi) {
    ghi({ ok: false, error: { ma: MA.heThong, thong_diep: 'khong doc duoc vao.json: ' + loi.message } });
    return 2;
  }

  // Lop phong thu theo chieu sau — bat TRUOC khi `require` bat cu piece nao.
  if (yc.proxy_port) {
    require('./chan_trong_tien_trinh').batDau('127.0.0.1', yc.proxy_port);
  }

  const nhatKy = [];
  const storeOps = [];
  const tep = [];
  try {
    const nap = napPiece(yc.piece);
    if (String(nap.version) !== String(yc.version)) {
      throw Object.assign(new Error(
        `phien_ban_lech: yeu cau ${yc.version}, cai ${nap.version}`),
      { code: 'LECH_BAN' });
    }
    const piece = nap.piece;
    const ctx = dungCtx(yc, nhatKy, storeOps, tep);
    let ra;
    if (yc.op === 'run_action') {
      const a = piece.actions()[yc.name];
      if (!a) throw Object.assign(new Error('action_khong_ton_tai: ' + yc.name), { code: 'KHONG_CO' });
      ra = await a.run(ctx);
    } else if (yc.op === 'run_trigger') {
      const t = piece.triggers()[yc.name];
      if (!t) throw Object.assign(new Error('trigger_khong_ton_tai: ' + yc.name), { code: 'KHONG_CO' });
      if (t.type !== 'POLLING') {
        throw Object.assign(new Error('trigger_khong_phai_POLLING: ' + t.type), { code: 'KHONG_CO' });
      }
      ra = await t.run(ctx);
    } else if (yc.op === 'trigger_on_enable' || yc.op === 'trigger_on_disable') {
      const t = piece.triggers()[yc.name];
      if (!t) throw Object.assign(new Error('trigger_khong_ton_tai: ' + yc.name), { code: 'KHONG_CO' });
      const ham = yc.op === 'trigger_on_enable' ? t.onEnable : t.onDisable;
      ra = ham ? await ham(ctx) : null;
    } else if (yc.op === 'run_property') {
      const a = piece.actions()[yc.name] || piece.triggers()[yc.name];
      if (!a) throw Object.assign(new Error('action_khong_ton_tai: ' + yc.name), { code: 'KHONG_CO' });
      const p = (a.props || {})[yc.prop];
      if (!p || typeof p.options !== 'function') {
        throw Object.assign(new Error('prop_khong_co_options: ' + yc.prop), { code: 'KHONG_CO' });
      }
      ra = await p.options(ctx, {});
    } else {
      throw Object.assign(new Error('op_khong_biet: ' + yc.op), { code: 'KHONG_CO' });
    }
    ghi({
      ok: true,
      output: cheBiMat(ra === undefined ? null : ra),
      store_ops: storeOps,
      files: tep,
      logs: nhatKy.slice(-50),
    });
    return 0;
  } catch (loi) {
    const m = (loi && (loi.code === 'KHONG_CO' || loi.code === 'LECH_BAN'))
      ? { ma: MA.dauVao, status: 0 } : maTuLoi(loi);
    ghi({
      ok: false,
      error: {
        ma: m.ma,
        thong_diep: String((loi && loi.message) || loi).slice(0, 2000),
        status: m.status,
      },
      store_ops: storeOps,
      logs: nhatKy.slice(-50),
    });
    return 1;
  }
}

main().then((ma) => process.exit(ma)).catch((loi) => {
  try {
    ghi({ ok: false, error: { ma: MA.heThong, thong_diep: String(loi && loi.message) } });
  } catch (_) { /* het duong */ }
  process.exit(3);
});
