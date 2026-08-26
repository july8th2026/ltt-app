/* Hien ten tep da chon cho o `.ltt-file`.
 *
 * ⭐ TANG CUONG DAN — giong `cam_chon.js`. Khong co JS thi `<label for>` van mo
 *    hop thoai chon tep, tep van vao form, `multipart` van gui di. Script nay
 *    chi THEM phan hoi bang mat; no khong the lam hong viec chon tep.
 *
 * 🔴 VI SAO CAN. Primitive `.ltt-file` an input native di (rong 1px). Neu khong
 *    hien ten tep thi nguoi dung chon xong khong biet minh da chon gi — do la
 *    doi mot loi hien thi lay mot loi te hon: UI noi doi ve trang thai that.
 *
 * ⛔ TEN TEP PHAI DUOC CAT. `.ltt-file-name` co `text-overflow:ellipsis` va
 *    `white-space:nowrap` trong `ltt.css`. Bo mot trong hai la mot ten tep dai
 *    dung lai dung cai tran ngang ma primitive nay sinh ra de diet.
 */
(function () {
  'use strict';

  function nhan(input) {
    var ds = input.files;
    if (!ds || !ds.length) return '';
    if (ds.length === 1) return ds[0].name;
    return ds.length + ' tệp đã chọn';
  }

  function capNhat(input) {
    var o = input.closest('.ltt-file');
    if (!o) return;
    var ten = nhan(input);
    var oTen = o.querySelector('.ltt-file-name');
    if (oTen) {
      // `textContent` chu khong phai `innerHTML`: ten tep la du lieu nguoi dung
      // dat, va mot tep ten `<img onerror=…>` khong duoc tro thanh the HTML.
      oTen.textContent = ten || oTen.dataset.trong || '';
    }
    if (ten) o.setAttribute('data-co-tep', '1');
    else o.removeAttribute('data-co-tep');
  }

  function gan(goc) {
    (goc || document).querySelectorAll('.ltt-file input[type=file]')
      .forEach(function (input) {
        if (input.dataset.daGan) return;
        input.dataset.daGan = '1';
        input.addEventListener('change', function () { capNhat(input); });
        capNhat(input);   // form co the giu lai lua chon sau khi tai lai trang
      });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { gan(); });
  } else {
    gan();
  }

  // htmx thay noi dung tai cho o vai trang (vd `/taoanh/thumbnail`), nen phai
  // gan lai cho phan vua duoc thay — neu khong, o chon tep moi se im lang.
  document.body && document.body.addEventListener('htmx:afterSwap', function (e) {
    gan(e.target);
  });
})();
