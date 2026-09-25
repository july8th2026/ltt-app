'use strict';
// `xuat_catalog` — spec §11.1 / §11.6. Sinh `catalog.json` TU `piece.metadata()`
// cua dung phien ban da ghim, ⛔ khong tu bang doan trong spec.
//
// ⭐ VI SAO TEP NAY CHAY TRUOC MOI THU KHAC CUA PHASE
//    Spec §11.6 tu khai rang cot "action/trigger" cua no la DICH CAN TRA, khong
//    phai ten da xac minh. Do lan dau 24/09 tren cac ban ghim: 8/13 ten doan
//    trong spec KHONG TON TAI (xem `docs/superpowers/reports/p6-connector/`).
//    Nen `catalog.json` la nguon, con bang cua spec la lich su.
//
//    node src/xuat_catalog.js --liet-ke      # in MOI ten that (buoc doi chieu)
//    node src/xuat_catalog.js                # ghi catalog.json theo `palette`
//
// ⛔ KHONG mo rong tu vung kieu o day. `platform_core/workflow/luoc_do.py` la
//    noi duy nhat biet tu vung tham so cua LTT; prop nao khong anh xa duoc thi
//    BO, va neu no `required` thi BO CA ACTION -- bo im lang mot tham so bat
//    buoc la dung mot form thieu o ma khach khong biet.
const fs = require('fs');
const path = require('path');
const { docAllowlist, napPiece, GOC } = require('./piece_nap');

//: AP prop type -> tu vung tham so LTT (`luoc_do._KHUNG`).
const KIEU = {
  SHORT_TEXT: 'string',
  LONG_TEXT: 'text',
  SECRET_TEXT: 'string',
  NUMBER: 'number',
  CHECKBOX: 'bool',
  STATIC_DROPDOWN: 'enum',
  DROPDOWN: 'string',
  DATE_TIME: 'string',
  JSON: 'json',
  OBJECT: 'json',
  CUSTOM: 'json',
  COLOR: 'string',
  FILE: 'string',
  // ⭐ `DYNAMIC` (Activepieces `packages/pieces/community/framework/src/lib/
  //    property/input/dynamic-prop.ts`, tag 0.32.0): gia tri thuc thi cua no
  //    la `DynamicPropsValue = Type.Record(Type.String(), DynamicProp)` --
  //    tuc VE MAT DAY, no la mot JSON object phang, giong het `OBJECT`. Cai
  //    "dong" (`props(propsValue, ctx) -> Promise<Record<string, DynamicProp>>`)
  //    chi quyet dinh CANH BAO/GOI Y hinh dang cua object do luc SOAN (piece
  //    tu goi API de biet co nhung cot nao) -- runner cua ta khong dung UI
  //    dong cua Activepieces (spec Sec11.1: goi thang `action.run(ctx)`), nen
  //    o day chi anh xa DUNG kieu day: 'json'. Nguoi soan tu dien object
  //    (vd `{"A": "gia tri"}` cho Google Sheets `insert_row`/`update_row`).
  DYNAMIC: 'json',
};

//: Prop chi de HIEN THI, khong phai o nhap -> bo han, khong tinh la "khong
//  anh xa duoc".
const CHI_HIEN_THI = new Set(['MARKDOWN']);

//: Kieu auth cua Activepieces -> `credential.kieu` cua LTT (spec §11.5).
const KIEU_AUTH = {
  SECRET_TEXT: 'api_key',
  BASIC_AUTH: 'basic',
  CUSTOM_AUTH: 'piece_custom',
  OAUTH2: 'oauth2',
};

//: Chuoi trong ma nguon `run` cho thay action dung co che WAITPOINT cua
//  Activepieces. Runner cua ta KHONG dung engine cua ho nen `ctx.run.pause` /
//  `createWaitpoint` se la `undefined` luc chay -> action treo im lang.
//  Spec §11.1: loai khoi allowlist bang PHEP KIEM TINH, khong bang tri nho.
const CAM = ['createWaitpoint', 'run.pause'];

function docPhepKiemTinh(fn) {
  let src = '';
  try { src = String(fn); } catch (_) { return []; }
  return CAM.filter(function (c) { return src.indexOf(c) >= 0; });
}

function motProp(ten, p) {
  if (!p || CHI_HIEN_THI.has(p.type)) return null;
  const kieu = KIEU[p.type];
  if (!kieu) return { _khong_anh_xa: p.type, required: !!p.required };
  const rule = { type: kieu, required: !!p.required };
  if (p.description) rule.description = String(p.description).slice(0, 400);
  if (p.defaultValue !== undefined && p.defaultValue !== null) {
    rule.default = p.defaultValue;
  }
  if (kieu === 'enum') {
    const opts = (p.options && p.options.options) || [];
    rule.values = opts.map(function (o) { return o.value; });
    rule.options = opts.map(function (o) {
      return { value: o.value, label: String(o.label) };
    });
    if (!rule.values.length) {
      return { _khong_anh_xa: 'STATIC_DROPDOWN_RONG', required: !!p.required };
    }
  }
  if (p.type === 'DROPDOWN') {
    rule.description = ('[tuy chon dong cua piece] ' + (rule.description || '')).trim();
  }
  if (p.type === 'FILE') {
    rule.description = ('[artifact_ref] ' + (rule.description || '')).trim();
  }
  if (p.type === 'DYNAMIC') {
    // `refreshers` (framework `DynamicProperties.refreshers: string[]`) la
    // ten cac tham so KHAC ma piece doc de quyet dinh hinh dang object -- ghi
    // ra de nguoi soan biet dien object nay THEO gi, ⛔ khong doan.
    const ref = Array.isArray(p.refreshers) ? p.refreshers.join(', ') : '';
    rule.description = (
      '[JSON dong -- phu thuoc: ' + (ref || 'khong ro') + '] '
      + (rule.description || '')
    ).trim();
  }
  return rule;
}

function mangProps(props) {
  const params = {};
  const bo = [];
  let chan = null;
  for (const ten of Object.keys(props || {})) {
    const rule = motProp(ten, props[ten]);
    if (rule === null) { bo.push([ten, 'chi_hien_thi']); continue; }
    if (rule._khong_anh_xa) {
      bo.push([ten, 'khong_anh_xa:' + rule._khong_anh_xa]);
      if (rule.required) chan = ten + ':' + rule._khong_anh_xa;
      continue;
    }
    params[ten] = rule;
  }
  return { params: params, bo: bo, chan: chan };
}

function authCuaPiece(meta) {
  const arr = Array.isArray(meta.auth) ? meta.auth : (meta.auth ? [meta.auth] : []);
  return arr.map(function (a) {
    return {
      ap: a.type,
      kieu: KIEU_AUTH[a.type] || null,
      props: Object.keys(a.props || {}),
    };
  });
}

function slug(s) {
  return String(s).toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
}

function main() {
  const lietKe = process.argv.indexOf('--liet-ke') >= 0;
  const al = docAllowlist();
  const ra = {
    sinh_luc: new Date().toISOString(), pieces: [], nodes: [], bo_qua: [],
  };

  for (const ten of Object.keys(al.pieces)) {
    const nap = napPiece(ten);
    const piece = nap.piece;
    const meta = piece.metadata();
    const actions = piece.actions();
    const triggers = piece.triggers();
    if (lietKe) {
      console.log('### ' + ten + '@' + nap.version);
      console.log('auth: ' + JSON.stringify(authCuaPiece(meta)));
      console.log('actions(' + Object.keys(actions).length + '): '
        + Object.keys(actions).join(','));
      console.log('triggers: ' + Object.keys(triggers).map(function (k) {
        return k + ':' + triggers[k].type;
      }).join(','));
      continue;
    }
    ra.pieces.push({
      ten: ten,
      version: nap.version,
      displayName: meta.displayName,
      logoUrl: meta.logoUrl,
      auth: authCuaPiece(meta),
      so_action: Object.keys(actions).length,
      so_trigger: Object.keys(triggers).length,
    });

    const pal = (al.palette && al.palette[ten]) || { actions: [], triggers: [] };
    const auth = authCuaPiece(meta)
      .filter(function (a) { return a.kieu; })
      .map(function (a) { return a.kieu; });
    const ns = slug(meta.displayName);

    for (const nA of (pal.actions || [])) {
      const a = actions[nA];
      if (!a) {
        ra.bo_qua.push({ piece: ten, name: nA, vi_sao: 'khong_ton_tai_o_ban_nay' });
        continue;
      }
      const cam = docPhepKiemTinh(a.run);
      if (cam.length) {
        ra.bo_qua.push({ piece: ten, name: nA, vi_sao: 'dung_waitpoint:' + cam.join('|') });
        continue;
      }
      const m = mangProps(a.props);
      if (m.chan) {
        ra.bo_qua.push({
          piece: ten, name: nA,
          vi_sao: 'tham_so_bat_buoc_khong_anh_xa:' + m.chan,
        });
        continue;
      }
      ra.nodes.push({
        type: 'piece.' + ns + '.' + slug(nA),
        type_version: 1,
        piece: ten,
        piece_version: nap.version,
        op: 'run_action',
        name: nA,
        title: a.displayName,
        description: String(a.description || '').slice(0, 400),
        icon: meta.logoUrl,
        params: m.params,
        returns: { ket_qua: 'json' },
        auth: auth,
        gia: 0,
        side_effect: 'external',
        prop_bo_qua: m.bo,
      });
    }
    for (const nT of (pal.triggers || [])) {
      const t = triggers[nT];
      if (!t) {
        ra.bo_qua.push({ piece: ten, name: nT, vi_sao: 'khong_ton_tai_o_ban_nay' });
        continue;
      }
      if (t.type !== 'POLLING') {
        // Spec §11.4: trigger WEBHOOK/APP_WEBHOOK cua piece NGOAI pham vi.
        ra.bo_qua.push({
          piece: ten, name: nT, vi_sao: 'trigger_khong_phai_POLLING:' + t.type,
        });
        continue;
      }
      const m = mangProps(t.props);
      if (m.chan) {
        ra.bo_qua.push({
          piece: ten, name: nT,
          vi_sao: 'tham_so_bat_buoc_khong_anh_xa:' + m.chan,
        });
        continue;
      }
      ra.nodes.push({
        type: 'trigger.piece.' + ns + '.' + slug(nT),
        type_version: 1,
        piece: ten,
        piece_version: nap.version,
        op: 'run_trigger',
        name: nT,
        kind: 'trigger',
        title: t.displayName,
        description: String(t.description || '').slice(0, 400),
        icon: meta.logoUrl,
        params: m.params,
        returns: { ket_qua: 'json' },
        auth: auth,
        gia: 0,
        side_effect: 'none',
        prop_bo_qua: m.bo,
      });
    }
  }
  if (lietKe) return 0;
  fs.writeFileSync(path.join(GOC, 'catalog.json'), JSON.stringify(ra, null, 1) + '\n');
  console.log('catalog.json: ' + ra.nodes.length + ' node, ' + ra.bo_qua.length + ' bo qua');
  for (const b of ra.bo_qua) console.log('  BO ' + b.piece + ' ' + b.name + ': ' + b.vi_sao);
  return 0;
}

if (require.main === module) process.exit(main());
module.exports = { KIEU, KIEU_AUTH, mangProps, docPhepKiemTinh, slug };
