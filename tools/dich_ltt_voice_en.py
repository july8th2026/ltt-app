"""
dich_ltt_voice_en.py — ban dich EN cua LTT VOICE, duoi dang MOT SCRIPT.

    python -X utf8 tools/dich_ltt_voice_en.py && python tools/i18n.py bien-dich

⭐ VI SAO LA MOT SCRIPT CHU KHONG PHAI MOT LUOT SUA TAY.

   Ngay 2026-08-30, `locale/en/LC_MESSAGES/messages.po` bi xoa sach **ba lan**
   trong mot buoi: `tests/test_306` ghi de tep THAT roi khoi phuc trong
   `finally`, va khi co hai tien trinh (hai luot gate, hoac mot luot gate cong
   mot nguoi dang sua) thi "khoi phuc" ghi de bang mot ban chup da cu.

   Ca ba lan deu vo hai, vi 78 muc dich song trong tep nay chu khong song trong
   mot lan go tay. Ap lai mat ba giay.

⇒ Bai hoc chung, khong rieng cho .po: **mot thay doi thu cong vao mot tep SINH RA
  thi nen ton tai duoi dang mot script.** Tep sinh ra se bi sinh lai, bi checkout,
  bi khoi phuc nham — va khi do cau hoi duy nhat la ta co duong tai tao khong.

⛔ THEM TAY (msgid + msgstr), KHONG chay `i18n.py trich`. Cac muc nay la `VANG`
   (chua tung vao catalog); `msgmerge` se DOAN ban dich cho chung tu cac muc gan
   giong, va sap xep lai ca tep.

Script IDEMPOTENT: muc da co trong .po thi bo qua.
"""
import pathlib

DICH = {
    "Giọng nói LTT": "LTT Voice",
    "Chuyển văn bản thành giọng nói tiếng Việt tự nhiên. Tạo giọng "
    "riêng của bạn từ một clip ba tới tám giây.":
        "Turn text into natural Vietnamese speech. Create your own voice from a "
        "three-to-eight-second clip.",
    "Âm thanh": "Audio",
    "MỚI": "NEW",
    "Tạo tiếng nói": "Generate speech",
    "Giọng của tôi": "My voices",
    "Dịch vụ giọng nói (LTTStudioVoice)": "Voice service (LTTStudioVoice)",
    "Chuyển văn bản thành giọng nói tiếng Việt.": "Turn text into Vietnamese speech.",

    # features / jobs
    "Chưa có văn bản để đọc.": "There is no text to read yet.",
    "Chỉ chọn một: giọng của bạn hoặc giọng có sẵn.":
        "Pick one: your own voice or a built-in voice.",
    "Không tìm thấy giọng này trong tài khoản của bạn.":
        "That voice is not in your account.",
    "Giọng này đang bị tắt. Hãy bật lại hoặc tạo giọng mới.":
        "That voice is switched off. Turn it back on, or create a new one.",
    "Giọng này chưa ghi danh xong. Hãy thử lại sau ít phút.":
        "That voice has not finished enrolling. Try again in a few minutes.",
    "Đoạn văn bản quá dài cho một lượt đọc. Hãy chia thành nhiều đoạn "
    "ngắn hơn.":
        "That passage is too long for a single read. Split it into shorter "
        "passages.",
    "Máy tạo tiếng nói chưa sẵn sàng. Vui lòng thử lại sau.":
        "The speech engine is not ready. Please try again shortly.",
    "Máy tạo tiếng nói chưa được thiết lập trên máy chủ này "
    "(thiếu LTT_VOICE_SIDECAR_TOKEN).":
        "The speech engine is not set up on this server "
        "(LTT_VOICE_SIDECAR_TOKEN is missing).",
    "Máy tạo tiếng nói chưa được thiết lập.": "The speech engine is not set up.",
    "Thiếu thông tin để ghi danh giọng.":
        "Missing information needed to enrol the voice.",
    "Không ghi danh được giọng. Vui lòng thử lại.":
        "Could not enrol the voice. Please try again.",

    # audio_input
    "Tệp âm thanh rỗng.": "The audio file is empty.",
    "Tệp vượt giới hạn {mb} MB. Clip mẫu chỉ cần vài giây, không cần cả bài.":
        "The file is over the {mb} MB limit. A sample clip only needs a few "
        "seconds, not a whole track.",
    "Không nhận ra định dạng âm thanh. Hãy gửi WAV, MP3 hoặc M4A.":
        "Unrecognised audio format. Please send WAV, MP3 or M4A.",
    "Chỉ nhận WAV, MP3 hoặc M4A.": "Only WAV, MP3 or M4A are accepted.",
    "Tệp WAV hỏng hoặc không phải PCM.":
        "The WAV file is damaged or is not PCM.",
    "Clip chỉ {co:.1f} giây. Cần ít nhất {can:.0f} giây giọng nói liên "
    "tục để nhân bản được.":
        "The clip is only {co:.1f} seconds. Cloning needs at least {can:.0f} "
        "seconds of continuous speech.",
    "Clip dài {co:.0f} giây, vượt {tran:.0f} giây. Hãy cắt lấy một đoạn "
    "nói rõ, không nhạc nền.":
        "The clip is {co:.0f} seconds, over the {tran:.0f}-second limit. Trim "
        "it to one clearly spoken passage with no background music.",
    "MIME khai '{khai}' khác nội dung thật '{that}'":
        "Declared MIME '{khai}' differs from the actual content '{that}'",
    "Không đọc được mẫu âm thanh.": "Could not read the audio samples.",
    "Âm thanh bị vỡ tiếng (thu quá to). Giọng nhân bản sẽ bị méo "
    "theo — nên thu lại nhỏ hơn.":
        "The audio is clipping (recorded too loud). The cloned voice will "
        "inherit that distortion — record it quieter.",
    "Hơn nửa clip là khoảng lặng. Hãy cắt bỏ phần im ở đầu và cuối.":
        "More than half the clip is silence. Trim the quiet parts from the "
        "start and end.",
    "Âm lượng rất nhỏ. Hãy thu lại gần micro hơn.":
        "The level is very low. Record closer to the microphone.",

    # dieu khoan
    "Giọng bạn được phép tải lên": "Whose voice you may upload",
    "Chỉ tải lên giọng của chính bạn, hoặc giọng bạn có văn bản uỷ "
    "quyền của người nói. Không tải lên giọng người nổi tiếng, giọng "
    "lấy từ phim, video hay bản ghi mà bạn không có quyền.":
        "Upload only your own voice, or a voice you hold written authorisation "
        "for. Do not upload the voice of a public figure, or a voice taken "
        "from a film, video or recording you have no rights to.",
    "Clip mẫu": "Sample clip",
    "Từ {min:.0f} đến {max:.0f} giây, tối đa {mb} MB, định dạng WAV, "
    "MP3 hoặc M4A. Chúng tôi giữ nguyên bản clip để có thể dựng lại "
    "giọng khi nâng cấp model.":
        "Between {min:.0f} and {max:.0f} seconds, up to {mb} MB, as WAV, MP3 "
        "or M4A. We keep the original clip so the voice can be rebuilt when "
        "the model is upgraded.",
    "Độ dài mỗi lượt đọc": "Length of each read",
    "Tối đa {n} ký tự cho một lượt. Văn bản dài hơn nên chia thành "
    "nhiều lượt: giọng đọc giữ được sự đồng nhất tốt hơn khi mỗi "
    "lượt ngắn.":
        "Up to {n} characters per read. Longer text should be split across "
        "several reads: the voice stays more consistent when each read is "
        "short.",
    "Tiền": "Billing",
    "Tính theo số giây tiếng nói thật sự tạo ra, không theo số ký tự "
    "gửi lên. Chúng tôi giữ tạm một khoản theo độ dài văn bản và hoàn "
    "lại phần dư ngay khi xong. Nếu không đo được kết quả, bạn không "
    "bị trừ gì.":
        "Charged by the seconds of speech actually produced, not by the "
        "characters you send. We hold an amount based on the text length and "
        "refund the remainder as soon as it finishes. If the result cannot be "
        "measured, you are charged nothing.",
    "Giữ tệp bao lâu": "How long files are kept",
    "Tệp tiếng tạo ra được giữ {n} ngày kể từ khi xong, rồi xoá. "
    "Hãy tải về trong khoảng đó. Lịch sử lượt tạo và bút toán credit "
    "vẫn giữ lại để đối chiếu, chỉ tệp là hết hạn.":
        "Audio files are kept for {n} days after completion, then "
        "deleted. Download yours within that window. Your generation "
        "history and credit entries are retained for reconciliation — "
        "only the files expire.",
    "Đóng dấu": "Watermarking",
    "Mọi tệp tiếng tạo ra đều được đóng một dấu chìm không nghe thấy "
    "để nhận diện nội dung do máy tạo.":
        "Every audio file produced carries an inaudible watermark identifying "
        "it as machine-generated.",
    "Tôi xác nhận đây là giọng của chính tôi, hoặc tôi được người nói "
    "uỷ quyền sử dụng giọng này.":
        "I confirm this is my own voice, or that the speaker has authorised me "
        "to use it.",

    # gia
    "theo giây tiếng nói sinh ra thật":
        "by the seconds of speech actually produced",
    "Tạo giọng mới (nhân bản)": "Create a new voice (cloning)",
    "thu một lần cho mỗi lần ghi danh": "charged once per enrolment",
    "một câu ~10 giây": "one sentence, ~10 seconds",
    "một đoạn ~60 giây": "one passage, ~60 seconds",
    "một bài ~5 phút": "one script, ~5 minutes",
    "Giữ chỗ tính theo số ký tự gửi lên; phần giữ dư được hoàn ngay "
    "khi job xong.":
        "The hold is based on the characters you send; the surplus is refunded "
        "as soon as the job finishes.",
    "Không đo được thời lượng tệp sinh ra thì hoàn đủ, thu 0.":
        "If the produced file's duration cannot be measured, everything is "
        "refunded and nothing is charged.",

    # giao dien
    "Chuyển văn bản thành giọng nói tiếng Việt tự nhiên. Dùng giọng có "
    "sẵn, hoặc giọng riêng bạn đã tạo.":
        "Turn text into natural Vietnamese speech. Use a built-in voice, or "
        "one you created yourself.",
    "Dịch vụ giọng nói chưa được bật trên máy chủ này. Vui lòng liên hệ "
    "quản trị.":
        "The voice service is not enabled on this server. Please contact an "
        "administrator.",
    "Văn bản": "Text",
    "Nhập đoạn văn bản bạn muốn đọc thành tiếng…":
        "Type the text you want read aloud…",
    "ký tự": "characters",
    "credit tạm giữ": "credits held",
    "Giọng đọc": "Voice",
    "Giọng mặc định": "Default voice",
    "Cách tính tiền": "How billing works",
    "Không gửi được yêu cầu. Thử lại nhé.":
        "Could not send the request. Please try again.",
    "Tạo giọng riêng từ một clip ngắn của chính bạn.":
        "Create your own voice from a short clip of yourself.",
    "Mã giọng": "Voice id",
    "Sẵn sàng": "Ready",
    "Đang ghi danh…": "Enrolling…",
    "Bạn chưa có giọng nào.": "You do not have any voices yet.",
    "Tạo giọng mới": "Create a new voice",
    "Tên giọng": "Voice name",
    "Ví dụ: Giọng dẫn của tôi": "For example: My narration voice",
    "Từ 3 đến 30 giây, nói rõ, không nhạc nền.":
        "Three to thirty seconds, clearly spoken, no background music.",
    "Tạo giọng": "Create voice",
    "Hãy đặt tên cho giọng.": "Please name the voice.",
    "Bạn cần xác nhận đây là giọng của chính bạn hoặc bạn được uỷ quyền.":
        "You need to confirm this is your own voice or that you are authorised "
        "to use it.",
    "Không tìm thấy giọng.": "Voice not found.",
    "Văn bản dài {n} ký tự, vượt giới hạn {t} cho một lượt đọc.":
        "The text is {n} characters, over the {t} limit for a single read.",
    "Lịch sử giọng nói": "Voice history",
    "Lịch sử tạo tiếng": "Speech history",
    "Chưa có lượt nào.": "Nothing generated yet.",
    "Credit": "Credits",
    # governance.STORES — bon bang cua LTT VOICE (test_211).
    "Danh tính công khai của một giọng: ai sở hữu, tên hiển thị, còn "
    "dùng được không. Là phía đối ứng của mọi lượt sinh tiếng đã tính "
    "tiền — mất nó thì lịch sử hoá đơn trỏ vào hư không.":
        "The public identity of a voice: who owns it, its display name, whether "
        "it still works. It is the counterpart to every billed generation — "
        "lose it and the invoice history points at nothing.",
    "Clip mẫu GỐC khách tải lên, giữ nguyên không xử lý. Hai việc: dựng "
    "lại giọng khi nâng cấp model, và chứng minh giọng nhân bản đến từ "
    "đúng tệp mà khách đã cam kết là của họ.":
        "The ORIGINAL sample clip the customer uploaded, kept unprocessed. It "
        "serves two purposes: rebuilding the voice when the model is upgraded, "
        "and proving the cloned voice came from the exact file the customer "
        "attested was theirs.",
    "Biểu diễn engine của một giọng, gắn với một phiên bản model cụ "
    "thể. KHÔNG BAO GIỜ ra API. Giữ lại để đối chiếu một tệp tiếng cũ với "
    "đúng bản model đã sinh ra nó.":
        "The engine representation of a voice, bound to one specific model "
        "version. NEVER leaves through the API. Kept so an old audio file can "
        "be matched to the exact model build that produced it.",
    "Cam kết sở hữu giọng: ai, lúc nào, bản điều khoản nào, hash tệp "
    "nào. Đây là bảng duy nhất trả lời được câu hỏi pháp lý, và nó là lý "
    "do consent phải là DỮ LIỆU chứ không phải một ô tick.":
        "The ownership attestation for a voice: who, when, which version of the "
        "terms, which file hash. This is the only table that can answer a legal "
        "question, and it is why consent has to be DATA rather than a tickbox.",

    # D002 / T-15 (2026-09-11): cau o o Ngon ngu van ban, Studio.
    "Chọn ngôn ngữ của văn bản. Giọng phải cùng ngôn ngữ; lượt lệch sẽ bị "
    "từ chối trước khi trừ credit.":
        "Choose the language of your script. The voice must match it; a "
        "mismatched request is refused before any credit is charged.",

    # D003/D004 (2026-09-11): bat khai lan luc ghi danh + cua khai lan gop.
    "Hãy chọn ngôn ngữ của clip giọng: Tiếng Việt hoặc Tiếng Anh.":
        "Please choose the language of the voice clip: Vietnamese or English.",
    "Clip nguồn của giọng này đo được là {lan}. Không đổi được sang ngôn "
    "ngữ khác.":
        "This voice's source clip measured as {lan}. It cannot be switched "
        "to another language.",
    "Giọng này đã bị thu hồi, không sửa được nữa.":
        "This voice has been revoked and can no longer be edited.",
    "Bạn đã có một giọng tên này. Hãy đặt tên khác.":
        "You already have a voice with this name. Please choose another one.",
    "Chọn ngôn ngữ của clip": "Choose the language of the clip",
    "Xác nhận ngôn ngữ của giọng này": "Confirm this voice's language",
    "Đo từ clip": "Measured from the clip",

    # T-07/T-14 (2026-09-11): thu hoi giong + worker khong bat lai.
    "Xoá giọng": "Delete voice",
    # review round 1, item 6 (2026-09-11b): cau cu (ban tren) da doi noi dung,
    # giu lai ban dich cu (khoa .po khong con ai tham chieu, vo hai) va them
    # ban moi cho dung chuoi hien tai.
    "Bạn có thể tắt một giọng bất cứ lúc nào để ngừng dùng nó, hoặc xoá vĩnh "
    "viễn để gỡ hẳn clip gốc và dữ liệu giọng khỏi máy chủ. Xoá vĩnh viễn "
    "không khôi phục được; lịch sử lượt đọc và bút toán credit vẫn được giữ "
    "để đối chiếu.":
        "You can turn off a voice at any time to stop using it, or delete it "
        "permanently to remove the source clip and voice data from the "
        "server. Permanent deletion cannot be undone; usage history and "
        "credit entries are still kept for reconciliation.",
    "Bạn có thể tắt một giọng bất cứ lúc nào để ngừng dùng nó, hoặc xoá vĩnh "
    "viễn để xoá clip gốc và dữ liệu giọng (biểu diễn) khỏi máy chủ — không "
    "khôi phục được. Một bản nghe thử của phiên bản engine cũ có thể còn sót "
    "tới lượt dọn kế tiếp. Lịch sử lượt đọc và bút toán credit vẫn được giữ "
    "để đối chiếu.":
        "You can turn off a voice at any time to stop using it, or delete it "
        "permanently to remove the source clip and voice data (embedding) "
        "from the server — this cannot be undone. A preview from an older "
        "engine version may remain until the next cleanup. Usage history and "
        "credit entries are still kept for reconciliation.",
    # review round 2, item E: cau round-1 (tren) hua "toi luot don ke tiep"
    # - khong ton tai. Ban nay chi noi "co the con sot lai", khong hua mot
    # hanh dong tuong lai khong co that.
    "Bạn có thể tắt một giọng bất cứ lúc nào để ngừng dùng nó, hoặc xoá vĩnh "
    "viễn để xoá clip gốc và dữ liệu giọng (biểu diễn) khỏi máy chủ — không "
    "khôi phục được. Một bản nghe thử của phiên bản engine cũ có thể vẫn còn "
    "sót lại trên máy chủ. Lịch sử lượt đọc và bút toán credit vẫn được giữ "
    "để đối chiếu.":
        "You can turn off a voice at any time to stop using it, or delete it "
        "permanently to remove the source clip and voice data (embedding) "
        "from the server — this cannot be undone. A preview from an older "
        "engine version may still remain on the server. Usage history and "
        "credit entries are still kept for reconciliation.",
    "Clip này không dùng được để ghi danh. Hãy tạo lại giọng với một clip "
    "khác.":
        "This clip cannot be used to enroll a voice. Please create the voice "
        "again with a different clip.",
    "Giọng này đã được đánh dấu lỗi ở một lượt ghi danh khác.":
        "This voice was already marked as failed by another enrollment "
        "attempt.",
    "Giọng này đã bị tắt trong lúc ghi danh.":
        "This voice was turned off while it was being enrolled.",
    "Giọng này không còn ở trạng thái ghi danh nữa.":
        "This voice is no longer in the enrolling state.",
    "Chỉ thu hồi được tối đa {n} giọng trong một lượt.":
        "You can delete at most {n} voices in one request.",
    "Giọng này đã bị thu hồi và không dùng được nữa.":
        "This voice has been deleted and can no longer be used.",
    "Ghi danh giọng này không thành công. Hãy tạo lại giọng với một clip khác.":
        "Enrolling this voice failed. Please create it again with a "
        "different clip.",
    "Giọng này đã bị thu hồi.": "This voice has already been deleted.",
    "Giọng đang ở trạng thái không tắt được.":
        "This voice is in a state where it cannot be turned off.",
    "Giọng đang ở trạng thái không thu hồi được.":
        "This voice is in a state where it cannot be deleted.",
    "Xoá vĩnh viễn": "Delete permanently",
    "Xoá vĩnh viễn thì clip gốc và dữ liệu giọng bị xoá khỏi máy chủ, không "
    "khôi phục được. Lịch sử lượt đọc và bút toán credit vẫn giữ để đối "
    "chiếu.":
        "Permanent deletion removes the source clip and voice data from the "
        "server, and cannot be undone. Usage history and credit entries are "
        "still kept for reconciliation.",
    "Xoá vĩnh viễn giọng này? Clip gốc và dữ liệu giọng sẽ bị xoá khỏi máy "
    "chủ và không khôi phục được.":
        "Delete this voice permanently? The source clip and voice data will "
        "be removed from the server and cannot be recovered.",
    "Không thu hồi được giọng này.": "Could not delete this voice.",

    # du_an — badge suy tu tep that (RC1 Task 9, D005)
    "Cần tạo lại": "Needs regenerating",
    # du_an — Task 10 extra item: phan biet nguyen nhan can_tao_lai (sua chu
    # vs tep het han), xem ltt_voice_mot_du_an.html.
    "Văn bản đã đổi — cần tạo lại.": "The text changed — needs regenerating.",
    # nghe_thu — nhan loi cua nut phat (D006, 3634412a, voice.js:baoNgheLoi)
    "Không phát được bản nghe thử": "Could not play the preview",
    # ⛔ KHÔNG khai "Lỗi" ở đây — fix round 1/5. `messages.po` đã có msgid
    #    "Lỗi" -> "Error" (server/templates/jobs.html va nhieu app khac dung
    #    chung). Script nay IDEMPOTENT nen mot dong "Lỗi": "Failed" o day
    #    khong bao gio ghi de duoc no (bo qua vi msgid da co san) — no chi la
    #    MA CHET, doc vao tuong badge Loi dich la "Failed" trong khi that ra
    #    van la "Error" nhu moi noi khac trong app.
    "Khối này đang được đọc — đợi lượt trước xong đã.":
        "This block is already being read — wait for it to finish first.",
    "Lượt đọc này không còn văn bản để lưu.":
        "This reading no longer has text to save.",

    # lich_su — het han + xoa nguoi dung + hop xac nhan (RC1 Task 8, D005)
    "Đã hết hạn": "Expired",
    "Nội dung đã hết hạn sau {n} ngày lưu trữ và được dọn. Bản ghi vẫn được "
    "giữ để đối chiếu.":
        "Content expired after {n} days of retention and was cleaned up. The "
        "record is kept for reconciliation.",
    "Đã tải": "Downloaded",
    "Bạn đã xoá lượt này. Tệp tiếng đã được xoá; bản ghi vẫn được giữ để đối "
    "chiếu.":
        "You deleted this item. The audio file has been removed; the record "
        "is kept for reconciliation.",
    "Xoá lượt này — tệp tiếng sẽ bị xoá, không lấy lại được.":
        "Delete this item — the audio file will be removed and cannot be "
        "recovered.",
    "Xoá lượt này? Tệp tiếng sẽ bị xoá và không lấy lại được. Bản ghi vẫn "
    "được giữ để đối chiếu.":
        "Delete this item? The audio file will be removed and cannot be "
        "recovered. The record is kept for reconciliation.",
    "Lượt đang xử lý chưa xoá được. Chờ nó xong hoặc huỷ trước.":
        "This item is still processing and cannot be deleted yet. Wait for "
        "it to finish or cancel it first.",
    "Không xoá được lượt này. Thử lại sau.":
        "Could not delete this item. Try again later.",
    # ⛔ Ngoặc KIỂU IN “…”, không phải `"…"` thẳng: `_()` trả về `Markup`
    #    (server/templating.py) nên Jinja KHÔNG escape nó khi chèn vào một
    #    thuộc tính HTML (`data-nhan-khoi-mot="..."`) — một dấu `"` thẳng
    #    trong chuỗi dịch (VI lẫn EN) sẽ đóng sớm thuộc tính. Xem
    #    `ltt_voice_lich_su.html` chỗ dùng chuỗi này.
    "Khối {so} trong dự án “{ten}” sẽ mất tiếng và cần tạo lại.":
        "Block {so} in project “{ten}” will lose its audio and need to be "
        "regenerated.",
    "Không kiểm được các dự án đang dùng tệp này. Việc xoá vẫn tiếp tục nếu "
    "bạn xác nhận.":
        "Could not check which projects use this file. Deleting will still "
        "go ahead if you confirm.",

    # governance.py — Store("voice_lich_su", ...) reason (RC1 Task 8)
    "Dấu người dùng đặt lên một lượt lịch sử: đã tải về chưa, đã xoá chưa. "
    "Không chứa văn bản hay tệp — chỉ hai cột thời điểm. Xoá một lượt dọn "
    "TỆP theo vòng đời của job; dòng này chỉ ghi rằng khách đã xoá.":
        "A user-set marker on a history item: whether it has been "
        "downloaded, whether it has been deleted. Holds no text or files — "
        "just two timestamps. Deleting an item removes the FILE per the "
        "job's lifecycle; this row only records that the customer deleted it.",

    # _voice_chon.html / ltt_voice_studio.html — D002 UI (RC1 Task 11)
    "Kho chung": "Shared library",
    "Chưa rõ ngôn ngữ": "Language unknown",
    "Lọc thêm": "More filters",
    "Đang hiện {n} giọng {lan}": "Showing {n} {lan} voices",
    "{n} giọng chưa khai ngôn ngữ, tạm ẩn": "{n} voices with no declared "
    "language, hidden for now",
    "Đã bỏ chọn “{ten}” vì giọng đó thuộc ngôn ngữ khác. Hãy chọn một giọng "
    "trong danh sách.":
        "Deselected “{ten}” because that voice is a different language. "
        "Pick a voice from the list.",
    "Hãy nhập nội dung cần đọc.": "Enter the text you want read aloud.",
    "Văn bản đang dài quá giới hạn một lượt đọc.":
        "The text is longer than the limit for a single read.",
}


def esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def main() -> int:
    po = pathlib.Path("locale/en/LC_MESSAGES/messages.po")
    # ⛔ ĐỌC/GHI VỚI `newline=""`: mặc định `open()`/`Path.write_text()` trên
    #    Windows DỊCH `\n` thành `\r\n` khi ghi (và ngược lại khi đọc ở chế độ
    #    text) — bẫy đã ghi trong bộ nhớ dự án (`write_text tren Windows doi ket
    #    dong`). Tệp `.po` này đang LF; một lượt chạy script không giữ
    #    `newline=""` sẽ lật CẢ TỆP sang CRLF dù nội dung chữ không đổi gì.
    noi_dung = po.read_text(encoding="utf-8", newline="")
    them, bo_qua = [], 0
    for vi, en in DICH.items():
        if 'msgid "%s"' % esc(vi) in noi_dung:
            bo_qua += 1
            continue
        them.append('\n#: apps/ltt_voice\nmsgid "%s"\nmsgstr "%s"\n'
                    % (esc(vi), esc(en)))
    po.write_text(noi_dung.rstrip("\n") + "\n" + "".join(them),
                  encoding="utf-8", newline="")
    print("da them %d muc, bo qua %d (da co san)" % (len(them), bo_qua))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
