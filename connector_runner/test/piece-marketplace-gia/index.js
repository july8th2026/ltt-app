'use strict';
// Hình dạng tối thiểu để `piece_nap.js::napPiece` nhận ra ("mot gia tri co
// .metadata la ham"), khớp `connector_runner/test/piece-gia/index.js`.
module.exports.pieceMarketplaceGia = {
  metadata() {
    return { displayName: 'Marketplace Gia', logoUrl: '' };
  },
  actions() {
    return {
      lam: {
        displayName: 'Lam',
        description: 'Hanh dong gia cho test marketplace',
        props: {},
        async run() {
          return { ok: true };
        },
      },
    };
  },
  triggers() {
    return {};
  },
};
