'use strict';
// CHỈ chạy nếu npm KHÔNG dùng `--ignore-scripts`. `test_4239` đo sự VẮNG MẶT
// của tệp này sau một lượt cài `--ignore-scripts` -- và đo sự CÓ MẶT của nó
// sau một lượt cố ý bỏ cờ, để phép kiểm không xanh vì "kênh chết" (cùng luật
// `test_3500`: mọi phép chạm vỏ phải có đối chứng).
const fs = require('fs');
const path = require('path');

fs.writeFileSync(path.join(__dirname, 'POSTINSTALL_DA_CHAY.txt'),
  'postinstall chay luc ' + new Date().toISOString() + '\n');
