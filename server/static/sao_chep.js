/* Nút "sao chép" cho mọi khối mã trên trang tài liệu.
 *
 * 🔴 VÌ SAO CẦN. Trang hướng dẫn tồn tại để khách **chép cấu hình**. Trước
 *    25/08 họ phải tự tô bằng chuột một khối `pre` nhiều dòng — và tô hụt một
 *    dòng trong `config.toml` thì lỗi hiện ra ở tận lúc gọi API, dưới dạng một
 *    thông điệp không liên quan gì tới việc chép thiếu.
 *
 * ⭐ Tăng cường dần (progressive enhancement): không có JS thì không có nút, và
 *    trang vẫn đọc được y nguyên. Không phụ thuộc thư viện nào.
 *
 * ⚠️ `navigator.clipboard` chỉ tồn tại trên ngữ cảnh bảo mật (https hoặc
 *    localhost). Trang này luôn https, nhưng vẫn phải kiểm — thiếu bước đó thì
 *    trên một ngữ cảnh lạ nút sẽ ném lỗi và **không nói gì**, đúng kiểu hỏng
 *    im lặng mà dự án này đã trả giá nhiều lần.
 */
(function () {
  "use strict";

  /* ⛔ Cờ "đã xử lý" là `data-chep-xong`, KHÔNG phải `data-chep`.
   *
   *    Trước 07/09 nó dùng `data-chep="1"` — **trùng tên** với dấu đánh dấu mà
   *    `_vps_mac.html` đặt lên `<code data-chep>`. Hai thứ khác hẳn nhau dùng
   *    chung một tên thuộc tính: một cái là "hãy gắn nút cho tôi", cái kia là
   *    "tôi gắn rồi". Trộn chúng là tự tạo một ô vừa-là-yêu-cầu-vừa-là-đã-xong.
   */
  function gan(pre) {
    if (!pre || pre.dataset.chepXong === "1") return;
    pre.dataset.chepXong = "1";

    var boc = document.createElement("div");
    boc.className = "khoi-ma";
    pre.parentNode.insertBefore(boc, pre);
    boc.appendChild(pre);

    var nut = document.createElement("button");
    nut.type = "button";
    nut.className = "nut-chep";
    nut.textContent = "Sao chép";
    // Người dùng bàn phím và trình đọc màn hình cũng phải dùng được.
    nut.setAttribute("aria-label", "Sao chép khối mã");
    boc.appendChild(nut);

    nut.addEventListener("click", function () {
      var chu = pre.innerText;
      var xong = function () {
        nut.textContent = "Đã chép";
        nut.classList.add("xong");
        setTimeout(function () {
          nut.textContent = "Sao chép";
          nut.classList.remove("xong");
        }, 1600);
      };
      var hong = function () {
        // Nói thật là không chép được, thay vì im lặng như chưa bấm.
        nut.textContent = "Hãy tự chọn rồi Ctrl+C";
        setTimeout(function () { nut.textContent = "Sao chép"; }, 2600);
      };
      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(chu).then(xong, hong);
      } else {
        hong();
      }
    });
  }

  /* Ô một dòng: địa chỉ IP, mã máy, khoá API — `<code data-chep>`.
   *
   * 🔴 VÌ SAO THÊM. `vps_base.html` từ trước đã ghi *"nút sao chép cho mọi khối
   *    mã **và mọi `<code data-chep>`**"* — nhưng tệp này chỉ quét `main pre`.
   *    Chú thích nói một đằng, mã làm một nẻo, và **địa chỉ IP — đúng thứ khách
   *    VPS vào trang để lấy — không có nút nào**. Đo 07/09.
   *
   * ⭐ Khác `pre`: không bọc lại DOM (ô nằm trong một dòng có nhãn, bọc thêm
   *    một `div` sẽ phá bố cục), chỉ chèn một nút NGAY SAU nó.
   */
  function gan_o(o) {
    if (!o || o.dataset.chepXong === "1") return;
    o.dataset.chepXong = "1";

    var nut = document.createElement("button");
    nut.type = "button";
    nut.className = "nut-chep nut-chep-o";
    nut.textContent = "Chép";
    // Nhãn phải nói CHÉP CÁI GÌ: một trang có nhiều ô, và "Chép" trần thì
    // trình đọc màn hình đọc ra bốn nút giống hệt nhau.
    var nhan = o.previousElementSibling;
    nut.setAttribute("aria-label",
      "Sao chép " + ((nhan && nhan.textContent) || o.textContent || "").trim());
    o.parentNode.insertBefore(nut, o.nextSibling);

    nut.addEventListener("click", function () {
      var chu = o.innerText;
      var xong = function () {
        nut.textContent = "Đã chép";
        nut.classList.add("xong");
        setTimeout(function () {
          nut.textContent = "Chép";
          nut.classList.remove("xong");
        }, 1600);
      };
      var hong = function () {
        nut.textContent = "Tự chọn rồi Ctrl+C";
        setTimeout(function () { nut.textContent = "Chép"; }, 2600);
      };
      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(chu).then(xong, hong);
      } else {
        hong();
      }
    });
  }

  function chay() {
    var ds = document.querySelectorAll("main pre");
    for (var i = 0; i < ds.length; i++) gan(ds[i]);
    // ⚠️ KHÔNG giới hạn trong `main`: dải danh tính máy của `_vps_mac.html`
    //    nằm ngoài `main` trên trang console.
    var os = document.querySelectorAll("code[data-chep]");
    for (var j = 0; j < os.length; j++) gan_o(os[j]);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", chay);
  } else {
    chay();
  }
})();
