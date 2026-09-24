'use strict';
// Nap piece theo allowlist. ⛔ MOT noi duy nhat biet cach lay `piece` ra khoi
// mot module Activepieces -- ca `runner.js` lan `xuat_catalog.js` goi vao day.
//
// ⭐ Loader tinh theo piece NAP, khong theo catalog: khong bao gio `require`
//    mot piece ngoai allowlist, ke ca khi no co trong node_modules.
const fs = require('fs');
const path = require('path');

const GOC = path.resolve(__dirname, '..');

function docAllowlist() {
  const j = JSON.parse(fs.readFileSync(path.join(GOC, 'allowlist.json'), 'utf8'));
  return j;
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
  const pkg = require(`${ten}/package.json`);
  if (String(pkg.version) !== String(ban)) {
    // ⛔ Khong "gan dung": allowlist la NGUON DUY NHAT (spec §11.3). Mot ban
    //    khac ban da chot nghia la lock va allowlist da lech nhau.
    throw new Error(`phien_ban_lech: ${ten} cai ${pkg.version} != allowlist ${ban}`);
  }
  const M = require(ten);
  const piece = Object.values(M).find((v) => v && typeof v.metadata === 'function');
  if (!piece) throw new Error(`khong_tim_thay_piece_trong_module: ${ten}`);
  return { piece, version: pkg.version };
}

module.exports = { docAllowlist, napPiece, GOC, PIECE_GIA };
