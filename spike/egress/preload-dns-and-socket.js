// Phuong an (b) day du - dung nhu khuyen nghi trong plan:
// va CA dns.lookup LAN net.Socket.prototype.connect.
require(require('path').join(__dirname, 'preload-dns-only.js'));
require(require('path').join(__dirname, 'preload-socket-only.js'));
console.error('[preload-dns-and-socket] active (ca hai)');
