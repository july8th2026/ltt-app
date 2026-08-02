"""Vietnamese vocabulary sets for editorial intelligence."""

# Emotional intensity
EMOTION_HIGH = frozenset({
    "kinh khủng", "tuyệt vời", "không thể tin", "choáng váng", "sốc",
    "đỉnh cao", "phi thường", "khủng khiếp", "đáng sợ", "điên rồ",
    "siêu", "cực kỳ", "vô cùng", "đáng kinh ngạc", "chấn động",
    "hủy diệt", "hoàn hảo", "đẳng cấp", "xuất sắc", "bá đạo",
})
EMOTION_MEDIUM = frozenset({
    "hay", "dở", "đẹp", "xấu", "tốt", "tệ", "ghê", "kinh",
    "tuyệt", "thất vọng", "ấn tượng", "bất ngờ", "thú vị",
    "hấp dẫn", "đáng tiếc", "ngoạn mục", "đặc biệt", "khó tin",
})
EMOTION_MILD = frozenset({
    "được", "ổn", "vui", "buồn", "ngạc nhiên", "bình thường",
    "dễ thương", "lạ", "khó", "dễ", "nhanh", "chậm",
})

# Narrative markers
SETUP_MARKERS = frozenset({
    "hôm nay", "bây giờ", "nào", "đầu tiên", "trước tiên",
    "mình sẽ", "để mình", "các bạn ơi", "xin chào",
    "câu chuyện là", "sự thật là", "vấn đề là",
})
DEVELOPMENT_MARKERS = frozenset({
    "nhưng mà", "tuy nhiên", "vì vậy", "bởi vì", "thế là",
    "và rồi", "sau đó", "tiếp theo", "không ngờ",
    "vấn đề là", "điều quan trọng", "thực ra", "hóa ra",
})
RESOLUTION_MARKERS = frozenset({
    "cuối cùng", "tóm lại", "kết luận", "vậy là", "thế nên",
    "bài học là", "ý nghĩa là", "quan trọng nhất",
    "đó là lý do", "và đó là", "tất cả là", "xong rồi",
})

# Filler words
FILLER_WORDS = frozenset({
    "ừm", "à", "ờ", "thì", "là", "kiểu", "cơ bản là",
    "nói chung là", "thật ra là", "đại loại là", "kiểu như",
    "ý là", "tức là", "nói thật là", "mình nghĩ là",
})

# Stop words
STOP_WORDS = frozenset({
    "là", "của", "và", "có", "được", "cho", "với", "từ",
    "đã", "sẽ", "đang", "này", "đó", "khi", "nếu",
    "thì", "mà", "để", "các", "một", "không", "cũng",
    "như", "về", "trong", "ra", "lên", "xuống", "vào",
    "tôi", "mình", "bạn", "anh", "chị", "em", "nó",
    "họ", "chúng", "ta", "những", "nhiều", "ít",
    "rất", "quá", "lắm", "hơn", "nhất",
})

# Hook patterns
CURIOSITY_PATTERNS = (
    "điều điên rồ là", "bạn sẽ không tin", "không ai nói cho bạn",
    "bí mật là", "sự thật là", "hãy tưởng tượng", "nếu như",
    "bạn có biết", "thử nghĩ xem", "điều gì xảy ra",
)
CONFLICT_WORDS = frozenset({
    "sai", "vấn đề", "tranh cãi", "không đồng ý", "phản đối",
    "quan điểm ngược", "thực ra không", "dừng lại", "huyền thoại",
    "lừa dối", "sự thật là", "mọi người đều sai",
})

# Debate/argument markers (for SHOCK intent)
DEBATE_MARKERS = frozenset({
    "nh\u01b0ng m\u00e0", "tuy nhi\u00ean", "m\u1eb7t kh\u00e1c", "c\u00f3 ng\u01b0\u1eddi n\u00f3i",
    "nhi\u1ec1u ng\u01b0\u1eddi cho r\u1eb1ng", "c\u00e2u h\u1ecfi l\u00e0", "c\u00f2n v\u1ec1",
    "ng\u01b0\u1eddi ta ngh\u0129", "v\u1ea5n \u0111\u1ec1 v\u1edbi", "b\u1ea1n c\u00f3 th\u1ec3 tranh lu\u1eadn",
})

# Insight markers \u2014 dense info / key learning (for INSIGHT intent)
INSIGHT_MARKERS = frozenset({
    "ch\u00eca kh\u00f3a l\u00e0", "\u0111\u00e2y l\u00e0 l\u00fd do", "b\u00ed quy\u1ebft l\u00e0",
    "d\u1eef li\u1ec7u cho th\u1ea5y", "nghi\u00ean c\u1ee9u cho th\u1ea5y",
    "\u0111i\u1ec1u quan tr\u1ecdng", "nh\u1edb \u0111i\u1ec1u n\u00e0y", "m\u1eb9o hay",
    "n\u00f3i c\u00e1ch kh\u00e1c", "k\u1ebft lu\u1eadn l\u00e0", "t\u00f3m l\u1ea1i",
    "\u0111i\u1ec1u b\u1ea1n c\u1ea7n bi\u1ebft", "khoa h\u1ecdc \u0111\u1eb1ng sau",
    "c\u00e2u tr\u1ea3 l\u1eddi th\u1eadt s\u1ef1", "\u00edt ai bi\u1ebft",
    "s\u1ef1 th\u1eadt l\u00e0", "b\u00e0i h\u1ecdc r\u00fat ra",
})

# Loop markers \u2014 satisfying / replay-worthy (for LOOP intent)
LOOP_MARKERS = frozenset({
    "\u0111\u1ee3i \u0111\u00e3", "xem n\u00e0y", "nh\u00ecn n\u00e0y", "xem \u0111i",
    "tr\u1eddi \u01a1i", "kh\u00f4ng th\u1ec3 tin", "\u0111i\u00ean th\u1eadt",
    "qu\u00e1 \u0111\u1ec9nh", "s\u1ed1c", "ch\u1ea5t l\u01b0\u1ee3ng",
    "m\u01b0\u1ee3t qu\u00e1", "xu\u1ea5t s\u1eafc", "tho\u1ea3 m\u00e3n",
    "\u0111\u00e3 m\u1eaft", "si\u00eau \u0111\u1ec9nh",
})

# CTA/outro patterns
OUTRO_PATTERNS = (
    "cảm ơn các bạn", "cảm ơn đã xem", "đăng ký kênh",
    "like và share", "bấm chuông", "hẹn gặp lại",
    "theo dõi mình", "link ở", "đừng quên",
    "nhớ đăng ký", "ủng hộ kênh",
)

# Payoff/resolution words (with + without diacritics for Whisper compatibility)
RESOLUTION_WORDS = frozenset({
    # With diacritics (standard Vietnamese)
    "c\u00e2u tr\u1ea3 l\u1eddi", "b\u1edfi v\u00ec", "l\u00fd do l\u00e0", "v\u00ec v\u1eady",
    "c\u00e1ch l\u00e0m", "b\u00ed quy\u1ebft l\u00e0", "ch\u00eca kh\u00f3a l\u00e0",
    "v\u00ed d\u1ee5", "b\u1eb1ng ch\u1ee9ng", "cu\u1ed1i c\u00f9ng", "ho\u00e0n th\u00e0nh",
    "tr\u01b0\u1edbc sau", "k\u1ebft qu\u1ea3", "bi\u1ebfn \u0111\u1ed5i",
    "t\u00f3m l\u1ea1i", "k\u1ebft lu\u1eadn",
    # Without diacritics (fallback for inconsistent ASR)
    "cuoi cung", "ket qua", "hoan thanh", "vi vay",
    "tom lai", "ket luan", "cach lam", "ly do",
})

# Incomplete ending indicators
INCOMPLETE_ENDINGS = frozenset({
    "và", "nhưng", "hoặc", "vì", "nên", "mà", "khi",
    "nếu", "trong khi", "mặc dù", "trước", "sau",
    "của", "với", "cho", "về", "là", "các",
})
