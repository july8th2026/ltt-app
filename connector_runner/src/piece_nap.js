'use strict';
// Nap piece theo allowlist. ⛔ MOT noi duy nhat biet cach lay `piece` ra khoi
// mot module Activepieces -- ca `runner.js` lan `xuat_catalog.js` goi vao day.
//
// ⭐ Loader tinh theo piece NAP, khong theo catalog: khong bao gio `require`
//    mot piece ngoai allowlist, ke ca khi no co trong node_modules.
//
// ## Marketplace (plan wfm, 25/09) -- MOT nguon THEM, khong thay nguon cu
//
// Allowlist TINH (`allowlist.json` canh tep nay) van la nguon DUY NHAT cho
// bay piece da qua review lam san. Marketplace la mot allowlist THU HAI, o
// NGOAI `GOC` (thu muc nay bi thay TOAN BO moi lan deploy -- xem docstring
// `connector.py`/`code_sandbox.py`), duong cua no chi den tu MOT bien moi
// truong (`LTT_MARKETPLACE_ALLOWLIST`). Khong bien -> khong tep -> khong
// piece marketplace nao ca -- fail CLOSED, dung mac dinh cua Node khi thieu
// tep la object rong, khong phai nem.
//
// Mot piece o CA HAI ben (trung ten) la loi cau hinh -- nem ngay luc doc,
// khong de mot ben am tham thang: allowlist tinh da qua review nguoi, allow-
// list marketplace di qua cong duyet runtime (`platform_core/workflow/
// marketplace.py`) -- hai nguon khac quyen, trung ten la dau hieu MOT trong
// hai bi cau hinh nham, khong phai thu tu tin cay.
const fs = require('fs');
const path = require('path');

const GOC = path.resolve(__dirname, '..');

function duongAllowlistMarketplace() {
  return process.env.LTT_MARKETPLACE_ALLOWLIST || '';
}

function duongThuMucMarketplace() {
  return process.env.LTT_MARKETPLACE_DIR || '';
}

function duongNodeModulesMarketplace() {
  const dir = duongThuMucMarketplace();
  return dir ? path.join(dir, 'node_modules') : '';
}

function docAllowlistTinh() {
  const j = JSON.parse(fs.readFileSync(path.join(GOC, 'allowlist.json'), 'utf8'));
  return j;
}

function docAllowlistMarketplace() {
  const duong = duongAllowlistMarketplace();
  if (!duong || !fs.existsSync(duong)) {
    return { pieces: {}, mien: {}, palette: {} };
  }
  return JSON.parse(fs.readFileSync(duong, 'utf8'));
}

//: Allowlist GOP. `_marketplace` la tap ten piece den tu nguon marketplace --
//  dung de `napPiece` biet phai `require` tu dau (khong phai mot phan cua
//  hinh dang JSON, chi la mot ket qua tinh trong bo nho).
function docAllowlist() {
  const tinh = docAllowlistTinh();
  const mkt = docAllowlistMarketplace();
  const tenTinh = new Set(Object.keys(tinh.pieces || {}));
  const trung = Object.keys(mkt.pieces || {}).filter((t) => tenTinh.has(t));
  if (trung.length) {
    throw new Error(`piece_trung_ten_tinh_va_marketplace: ${trung.join(',')}`);
  }
  return {
    pieces: Object.assign({}, tinh.pieces, mkt.pieces),
    mien: Object.assign({}, tinh.mien, mkt.mien),
    palette: Object.assign({}, tinh.palette, mkt.palette),
    _marketplace: new Set(Object.keys(mkt.pieces || {})),
  };
}

//: Piece GIA cho test (spec §18.1). ⛔ Chi nap khi `LTT_TEST=1` — no co mot
//  action co tinh THOAT RANH GIOI, va mot ban dung nap duoc tren production la
//  dung thu nay sinh ra de chan.
const PIECE_GIA = '@ltt/piece-gia';

function napPiece(ten) {
  if (ten === PIECE_GIA) {
    if (process.env.LTT_TEST !== '1') {
      throw new Error('piece_gia_chi_nap_khi_LTT_TEST=1');
    }
    const M = require('../test/piece-gia');
    return { piece: M.pieceGia, version: '0.0.0' };
  }
  const al = docAllowlist();
  const ban = al.pieces[ten];
  if (!ban) throw new Error(`piece_ngoai_allowlist: ${ten}`);

  let pkg;
  let M;
  if (al._marketplace.has(ten)) {
    // Piece marketplace: KHONG nam trong `node_modules` cua connector_runner
    // (viet vao GOC luc chay bi cam) -- no nam trong thu muc rieng, ghi boi
    // `platform_core/workflow/marketplace.py::cai_dat()` sau khi qua het cong
    // duyet + xac minh toan ven.
    const nodeModules = duongNodeModulesMarketplace();
    if (!nodeModules) {
      throw new Error(`marketplace_chua_cau_hinh_thu_muc: ${ten}`);
    }
    const goiDir = path.join(nodeModules, ...ten.split('/'));
    pkg = JSON.parse(fs.readFileSync(path.join(goiDir, 'package.json'), 'utf8'));
    if (String(pkg.version) !== String(ban)) {
      // ⛔ Khong "gan dung" -- cung luat voi nhanh tinh ben duoi.
      throw new Error(`phien_ban_lech: ${ten} cai ${pkg.version} != allowlist ${ban}`);
    }
    M = require(goiDir);
  } else {
    pkg = require(`${ten}/package.json`);
    if (String(pkg.version) !== String(ban)) {
      // ⛔ Khong "gan dung": allowlist la NGUON DUY NHAT (spec §11.3). Mot ban
      //    khac ban da chot nghia la lock va allowlist da lech nhau.
      throw new Error(`phien_ban_lech: ${ten} cai ${pkg.version} != allowlist ${ban}`);
    }
    M = require(ten);
  }
  const piece = Object.values(M).find((v) => v && typeof v.metadata === 'function');
  if (!piece) throw new Error(`khong_tim_thay_piece_trong_module: ${ten}`);
  return { piece, version: pkg.version };
}

module.exports = {
  docAllowlist, docAllowlistTinh, docAllowlistMarketplace, napPiece, GOC,
  PIECE_GIA, duongAllowlistMarketplace, duongThuMucMarketplace,
  duongNodeModulesMarketplace,
};
