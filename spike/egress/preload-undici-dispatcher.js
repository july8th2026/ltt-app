// Phuong an (a) trong spec: undici global dispatcher.
// Gia thuyet can kiem: no CHI chan fetch()/undici client, KHONG chan require('http'/'https').
const path = require('path');
const { setGlobalDispatcher, Agent } = require(path.join(__dirname, 'node_modules', 'undici'));

class BlockingDispatcher extends Agent {
  dispatch(opts, handler) {
    const err = new Error('EGRESS_BLOCKED:undici-dispatcher');
    err.code = 'EGRESS_BLOCKED';
    if (handler.onError) {
      handler.onError(err);
    } else {
      throw err;
    }
    return false;
  }
}

setGlobalDispatcher(new BlockingDispatcher());
console.error('[preload-undici-dispatcher] active (chi anh huong fetch()/undici, KHONG anh huong http/https module)');
