// Driver: chay het to hop (preload x piece x target), gom ket qua, in bang markdown.
const { spawn, spawnSync } = require('child_process');
const path = require('path');

const PORT_V4 = 18199;
const PORT_V6 = 18299;

const TARGETS = {
  local_ip_v4: `http://127.0.0.1:${PORT_V4}/probe`,
  local_hostname: `http://localhost:${PORT_V4}/probe`,
  local_ipv6: `http://[::1]:${PORT_V6}/probe`,
  external_hostname: 'http://example.com/',
  external_ip: null, // dien luc chay: giai example.com ra IP THAT truoc khi va dns, roi goi thang IP
};

const PRELOADS = {
  'a_undici_dispatcher': 'preload-undici-dispatcher.js',
  'b1_dns_only': 'preload-dns-only.js',
  'b2_socket_only': 'preload-socket-only.js',
  'b3_dns_and_socket': 'preload-dns-and-socket.js',
  'z_none_doi_chung': 'preload-none.js',
};

const PIECES = ['piece-https.js', 'piece-axios.js', 'piece-fetch.js'];

function runOne(preloadFile, pieceFile, target) {
  const args = ['-r', path.join(__dirname, preloadFile), path.join(__dirname, pieceFile)];
  const res = spawnSync(process.execPath, args, {
    env: { ...process.env, TARGET: target },
    timeout: 8000,
    encoding: 'utf8',
  });
  let parsed = null;
  try {
    const lastLine = (res.stdout || '').trim().split('\n').filter(Boolean).pop();
    parsed = JSON.parse(lastLine);
  } catch (e) {
    parsed = { ok: false, error: 'NO_JSON_OUTPUT', raw_stdout: (res.stdout || '').slice(0, 200), raw_stderr: (res.stderr || '').slice(0, 200) };
  }
  let verdict;
  if (parsed && parsed.ok) verdict = 'REACHED (khong chan)';
  else if (parsed && (parsed.error === 'EGRESS_BLOCKED' || String(parsed.error || '').startsWith('EGRESS_BLOCKED'))) verdict = 'CHAN';
  else verdict = `LOI KHAC (${parsed ? parsed.error : 'unknown'})`;
  return { verdict, detail: parsed };
}

async function resolveExternalIp() {
  // Dung dns that (truoc khi preload chay) de lay 1 IP that cua example.com.
  const dns = require('dns').promises;
  try {
    const { address } = await dns.lookup('example.com', { family: 4 });
    return `http://${address}/`;
  } catch (e) {
    return null;
  }
}

async function main() {
  TARGETS.external_ip = await resolveExternalIp();
  if (!TARGETS.external_ip) {
    console.error('[run-all] KHONG lay duoc IP that cua example.com (mang hong hoac DNS chan) - bo qua hang external_ip');
    delete TARGETS.external_ip;
  }

  const catcher = spawn(process.execPath, [path.join(__dirname, 'catcher-server.js')], { stdio: 'pipe' });
  catcher.stdout.on('data', (d) => process.stderr.write(`[catcher] ${d}`));
  catcher.stderr.on('data', (d) => process.stderr.write(`[catcher-err] ${d}`));
  await new Promise((r) => setTimeout(r, 800)); // doi catcher len

  const rows = [];
  for (const [pName, pFile] of Object.entries(PRELOADS)) {
    for (const piece of PIECES) {
      for (const [tName, tUrl] of Object.entries(TARGETS)) {
        if (!tUrl) continue;
        const { verdict, detail } = runOne(pFile, piece, tUrl);
        rows.push({ preload: pName, piece, target: tName, url: tUrl, verdict, detail });
        console.error(`${pName.padEnd(20)} ${piece.padEnd(16)} ${tName.padEnd(18)} -> ${verdict}`);
      }
    }
  }

  catcher.kill();

  console.log(JSON.stringify(rows, null, 2));

  // In bang markdown ra stderr de de doc trong console (stdout danh cho JSON thuan)
  console.error('\n\n=== BANG KET QUA (markdown) ===');
  console.error('| preload | piece | target | verdict |');
  console.error('|---|---|---|---|');
  for (const r of rows) {
    console.error(`| ${r.preload} | ${r.piece} | ${r.target} | ${r.verdict} |`);
  }
}

main();
