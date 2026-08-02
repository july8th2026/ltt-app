"""Genre-specific scoring weights and heuristic parameters.

Each genre profile defines:
- How to weight different scoring signals (hook, pacing, content, audio, visual)
- Hook keyword lists and patterns
- Payoff/closure patterns
- Duration sweet spots
- Boundary snapping preferences

These are data tables, not logic. The scoring engines read these.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class GenreWeights:
    """Scoring weights for a specific genre. Must sum to ~1.0."""
    hook_strength: float = 0.25
    pacing: float = 0.15
    completeness: float = 0.20
    visual_quality: float = 0.15
    audio_quality: float = 0.10
    content_density: float = 0.15

    def as_dict(self) -> dict[str, float]:
        return {
            "hook_strength": self.hook_strength,
            "pacing": self.pacing,
            "completeness": self.completeness,
            "visual_quality": self.visual_quality,
            "audio_quality": self.audio_quality,
            "content_density": self.content_density,
        }


@dataclass(frozen=True)
class GenreProfile:
    """Complete editorial profile for a content genre."""
    name: str
    display_name: str

    # Scoring weights
    weights: GenreWeights

    # Duration preferences (seconds)
    ideal_min_sec: float = 20.0
    ideal_max_sec: float = 45.0
    sweet_spot_sec: float = 30.0

    # Hook detection config
    hook_keywords: tuple[str, ...] = ()
    hook_keywords_vi: tuple[str, ...] = ()  # Vietnamese hook keywords
    hook_patterns: tuple[str, ...] = ()  # regex patterns
    hook_patterns_vi: tuple[str, ...] = ()  # Vietnamese regex patterns
    question_bonus: float = 0.15  # Extra score for opening questions
    bold_statement_bonus: float = 0.10

    # Payoff / closure detection
    payoff_keywords: tuple[str, ...] = ()
    payoff_keywords_vi: tuple[str, ...] = ()  # Vietnamese payoff keywords
    needs_closure: bool = True  # Penalize clips that end mid-thought
    closure_penalty: float = 0.20  # Score reduction for incomplete clips

    # Boundary snapping
    prefer_sentence_boundary: bool = True
    prefer_silence_boundary: bool = True
    prefer_scene_boundary: bool = False
    silence_gap_threshold_sec: float = 0.8

    # Content requirements
    require_speech: bool = True
    require_person: bool = False
    min_speech_ratio: float = 0.5  # At least 50% of clip should be speech
    max_silence_ratio: float = 0.15

    # Pacing
    ideal_wpm_min: float = 100.0
    ideal_wpm_max: float = 180.0

    # Visual
    person_presence_bonus: float = 0.10
    high_motion_bonus: float = 0.0  # Most genres don't reward high motion

    # Style defaults
    default_color_preset: str = "original"
    default_caption_enabled: bool = True
    default_speed_factor: float = 1.0


# ── Genre Profile Registry ───────────────────────────────────────────────

TALKING_HEAD = GenreProfile(
    name="talking_head",
    display_name="Talking Head",
    weights=GenreWeights(
        hook_strength=0.25,
        pacing=0.15,
        completeness=0.20,
        visual_quality=0.15,
        audio_quality=0.10,
        content_density=0.15,
    ),
    ideal_min_sec=20.0,
    ideal_max_sec=50.0,
    sweet_spot_sec=30.0,
    hook_keywords=(
        "here's", "the thing is", "listen", "so", "look",
        "the biggest", "number one", "the secret", "what if",
        "i'm going to", "let me tell you", "you need to",
        "this is why", "the truth is", "stop doing",
        "the problem is", "here's what", "nobody tells you",
    ),
    hook_keywords_vi=(
        "này nhé", "vấn đề là", "nghe này", "nói thật",
        "bí mật là", "điều quan trọng nhất", "sai lầm lớn nhất",
        "không ai nói cho bạn", "sự thật là", "đừng bao giờ",
        "hãy nghe", "mình sẽ chỉ", "bạn cần phải",
        "tại sao", "lý do", "bạn có biết",
    ),
    hook_patterns=(
        r"^(how|why|what|when|where|who|did you|have you|do you)\b",
        r"^(the \w+ (thing|reason|mistake|secret|problem))",
        r"^\d+ (ways|things|reasons|tips|mistakes)",
    ),
    hook_patterns_vi=(
        r"^(tại sao|vì sao|làm sao|như thế nào|bao giờ|ở đâu|ai)\b",
        r"^\d+ (cách|điều|lý do|mẹo|sai lầm|bước|thứ)",
        r"^(điều|thứ|cái|lý do) (quan trọng|lớn nhất|tệ nhất)",
    ),
    question_bonus=0.15,
    bold_statement_bonus=0.10,
    payoff_keywords=(
        "so that's", "and that's", "that's why", "the point is",
        "bottom line", "in conclusion", "the takeaway", "remember",
        "so the answer", "and that is",
    ),
    payoff_keywords_vi=(
        "đó là lý do", "vì vậy", "tóm lại", "kết luận là",
        "điểm chính là", "hãy nhớ", "bài học là",
        "đó chính là", "và đó là", "nên nhớ",
    ),
    needs_closure=True,
    closure_penalty=0.20,
    require_speech=True,
    require_person=True,
    person_presence_bonus=0.10,
    default_caption_enabled=True,
)

PODCAST = GenreProfile(
    name="podcast",
    display_name="Podcast",
    weights=GenreWeights(
        hook_strength=0.20,
        pacing=0.10,
        completeness=0.15,  # Conversations can trail off naturally
        visual_quality=0.05,
        audio_quality=0.20,  # Multi-speaker audio quality matters
        content_density=0.30,  # Dense ideas matter most in podcast
    ),
    ideal_min_sec=25.0,
    ideal_max_sec=55.0,
    sweet_spot_sec=40.0,
    hook_keywords=(
        "the crazy thing is", "i think", "the real question",
        "here's the thing", "what people don't realize",
        "let me push back", "that's interesting because",
        "okay so", "wait", "hold on", "actually",
    ),
    hook_keywords_vi=(
        "điều điên rồ là", "tôi nghĩ", "câu hỏi thật sự là",
        "vấn đề là thế này", "mọi người không nhận ra",
        "khoan đã", "thật ra", "nói thật nhé",
        "hay ở chỗ", "thú vị là", "quan trọng là",
    ),
    hook_patterns=(
        r"^(but |so |okay |wait |actually )",
        r"^(i think|i believe|in my opinion|my take)",
    ),
    hook_patterns_vi=(
        r"^(nhưng |vậy |khoan |thật ra )",
        r"^(tôi nghĩ|theo tôi|ý kiến của tôi)",
    ),
    question_bonus=0.20,
    payoff_keywords=(
        "exactly", "right", "yeah that's", "so basically",
        "and that's the", "i think that's",
    ),
    payoff_keywords_vi=(
        "chính xác", "đúng rồi", "nói chung là",
        "cơ bản là", "và đó chính là", "tôi nghĩ đó là",
    ),
    needs_closure=True,
    closure_penalty=0.15,
    require_speech=True,
    require_person=False,
    min_speech_ratio=0.6,
    ideal_wpm_min=120.0,
    ideal_wpm_max=200.0,
    default_caption_enabled=True,
)

INTERVIEW = GenreProfile(
    name="interview",
    display_name="Interview",
    weights=GenreWeights(
        hook_strength=0.20,
        pacing=0.10,
        completeness=0.35,  # Q&A arcs MUST resolve — answer the question
        visual_quality=0.10,
        audio_quality=0.10,
        content_density=0.15,  # Not fact-heavy, personal stories matter
    ),
    ideal_min_sec=15.0,   # Short answer extracts work on TikTok
    ideal_max_sec=60.0,   # Full story arcs also work
    sweet_spot_sec=35.0,
    hook_keywords=(
        "tell me about", "how did you", "what was it like",
        "the moment when", "i remember", "the turning point",
    ),
    hook_keywords_vi=(
        "kể cho tôi", "bạn đã", "cảm giác lúc đó",
        "khoảnh khắc", "tôi nhớ", "bước ngoặt",
        "điều gì khiến bạn", "lúc đó bạn nghĩ gì",
    ),
    hook_patterns=(
        r"^(so |tell me|how |what |when |why )",
    ),
    hook_patterns_vi=(
        r"^(kể |hãy |bạn đã|điều gì|lúc đó)",
    ),
    question_bonus=0.20,
    payoff_keywords=(
        "and that's", "so yeah", "that was", "looking back",
    ),
    payoff_keywords_vi=(
        "và đó là", "ừ thì", "đó là lúc", "nhìn lại",
        "từ đó", "bây giờ nghĩ lại",
    ),
    needs_closure=True,
    closure_penalty=0.25,
    require_speech=True,
    require_person=True,
    person_presence_bonus=0.05,
    default_caption_enabled=True,
    default_color_preset="clear_fresh",
)

REVIEW = GenreProfile(
    name="review",
    display_name="Review",
    weights=GenreWeights(
        hook_strength=0.25,
        pacing=0.10,
        completeness=0.25,
        visual_quality=0.15,
        audio_quality=0.10,
        content_density=0.15,
    ),
    ideal_min_sec=20.0,
    ideal_max_sec=50.0,
    sweet_spot_sec=35.0,
    hook_keywords=(
        "is it worth", "should you buy", "the verdict",
        "after using", "my honest", "the best", "the worst",
        "compared to", "pros and cons", "deal breaker",
        "this vs", "versus", "better than", "budget",
    ),
    hook_keywords_vi=(
        "có đáng mua", "nên mua không", "đánh giá thật",
        "sau khi dùng", "thật lòng mà nói", "tốt nhất", "tệ nhất",
        "so sánh với", "ưu nhược điểm", "điểm trừ lớn nhất",
        "so với", "cái nào tốt hơn", "giá rẻ",
    ),
    hook_patterns=(
        r"^(is it|should you|the (best|worst)|after \d+)",
        r"^(this is (the|my|a)|let me show)",
    ),
    hook_patterns_vi=(
        r"^(có nên|có đáng|sau \d+|đây là|để tôi cho)",
    ),
    question_bonus=0.15,
    payoff_keywords=(
        "overall", "final verdict", "would i recommend",
        "buy it", "skip it", "worth it", "the winner",
        "in summary", "my recommendation",
        "worth the price", "for the money", "better than",
        "compared to", "if you need", "bottom line",
    ),
    payoff_keywords_vi=(
        "tổng kết", "kết luận cuối", "tôi có khuyên mua",
        "nên mua", "đừng mua", "đáng tiền", "người thắng là",
        "tóm lại", "khuyến nghị của tôi",
        "đáng giá", "so với", "nếu bạn cần", "xứng đáng",
    ),
    needs_closure=True,
    closure_penalty=0.20,
    require_speech=True,
    default_caption_enabled=True,
    default_color_preset="clear_fresh",
)

STORYTELLING = GenreProfile(
    name="storytelling",
    display_name="Storytelling",
    weights=GenreWeights(
        hook_strength=0.30,
        pacing=0.15,
        completeness=0.25,
        visual_quality=0.10,
        audio_quality=0.05,
        content_density=0.15,
    ),
    ideal_min_sec=25.0,
    ideal_max_sec=55.0,
    sweet_spot_sec=40.0,
    hook_keywords=(
        "so this happened", "i couldn't believe", "the craziest thing",
        "picture this", "imagine", "one day", "it all started",
        "nobody expected", "out of nowhere", "i'll never forget",
    ),
    hook_keywords_vi=(
        "chuyện là thế này", "tôi không thể tin", "điên rồ nhất là",
        "hãy tưởng tượng", "ngày xưa", "ngày nọ", "mọi chuyện bắt đầu",
        "không ai ngờ", "bất ngờ là", "tôi không bao giờ quên",
        "có một lần", "hồi đó", "chuyện xảy ra là",
    ),
    hook_patterns=(
        r"^(so |one day|i was|when i|it was|there was)",
        r"^(the (day|moment|time|night) (i|we|they))",
    ),
    hook_patterns_vi=(
        r"^(ngày (xưa|nọ|đó)|hồi đó|có một|lúc đó|chuyện là)",
        r"^(tôi (đã|đang|không)|khi tôi|mọi chuyện)",
    ),
    question_bonus=0.10,
    bold_statement_bonus=0.15,
    payoff_keywords=(
        "and that's when", "turns out", "the twist",
        "i learned", "moral of the story", "to this day",
        "and that changed", "i never",
    ),
    payoff_keywords_vi=(
        "và đó là lúc", "hóa ra", "bất ngờ là",
        "tôi đã học được", "bài học là", "cho đến tận bây giờ",
        "và điều đó thay đổi", "từ đó", "kết cục là",
        "cuối cùng thì", "thì ra",
    ),
    needs_closure=True,
    closure_penalty=0.15,  # Reduced: cliffhangers/teasers are valid on TikTok
    require_speech=True,
    min_speech_ratio=0.5,
    default_caption_enabled=True,
    default_color_preset="cinematic",
)

COMEDY = GenreProfile(
    name="comedy",
    display_name="Comedy",
    weights=GenreWeights(
        hook_strength=0.20,
        pacing=0.25,
        completeness=0.25,
        visual_quality=0.10,
        audio_quality=0.05,
        content_density=0.15,
    ),
    ideal_min_sec=15.0,
    ideal_max_sec=40.0,
    sweet_spot_sec=25.0,
    hook_keywords=(
        "so", "okay so", "you know when", "have you ever",
        "the funniest thing", "bro", "dude", "literally",
    ),
    hook_keywords_vi=(
        "mọi người ơi", "bó tay", "buồn cười nhất là",
        "nói thật", "các bạn biết không", "ông bà ơi",
        "trời ơi", "không đùa đâu", "thề luôn",
    ),
    hook_patterns=(
        r"^(so |okay |you know|have you|bro |dude )",
        r"^(i swear|i literally|no but seriously)",
    ),
    hook_patterns_vi=(
        r"^(mọi người|trời ơi|bó tay|nói thật|ê )",
        r"^(tôi thề|không đùa|nói thiệt)",
    ),
    question_bonus=0.10,
    payoff_keywords=(
        "and that's why", "get it", "i'm done", "can't believe",
        "that's the thing", "i'm telling you", "that happened",
    ),
    payoff_keywords_vi=(
        "đó là lý do", "hiểu chưa", "xong rồi", "không tin nổi",
        "thề luôn", "nói thật đấy", "chuyện có thật",
    ),
    needs_closure=True,
    closure_penalty=0.15,  # Punchlines are often silence/laughter, not text
    require_speech=True,
    min_speech_ratio=0.4,
    max_silence_ratio=0.20,  # Pause after punchline is OK
    ideal_wpm_min=130.0,
    ideal_wpm_max=220.0,
    default_caption_enabled=True,
    default_color_preset="clear_fresh",
)

EDUCATION = GenreProfile(
    name="education",
    display_name="Education",
    weights=GenreWeights(
        hook_strength=0.15,  # Education hooks are setup, not clickbait
        pacing=0.10,
        completeness=0.25,  # Must complete the lesson
        visual_quality=0.10,
        audio_quality=0.10,
        content_density=0.30,  # Information density is king for education
    ),
    ideal_min_sec=15.0,   # Micro-lessons work on TikTok
    ideal_max_sec=50.0,
    sweet_spot_sec=30.0,   # Tighter for viral education
    hook_keywords=(
        "today i'll", "let me show you", "did you know",
        "the key concept", "step one", "first",
        "the most important", "a common mistake",
    ),
    hook_keywords_vi=(
        "hôm nay mình sẽ", "để mình chỉ cho", "bạn có biết",
        "khái niệm chính", "bước một", "đầu tiên",
        "quan trọng nhất", "sai lầm phổ biến", "mẹo hay là",
    ),
    hook_patterns=(
        r"^(today|let me|step \d|first|the (key|most|main))",
        r"^(did you know|here's (how|why|what))",
    ),
    hook_patterns_vi=(
        r"^(hôm nay|để mình|bước \d|đầu tiên|điều (quan trọng|chính))",
        r"^(bạn có biết|đây là (cách|lý do))",
    ),
    question_bonus=0.15,
    payoff_keywords=(
        "so remember", "to recap", "the key takeaway",
        "now you know", "and that's how", "practice this",
    ),
    payoff_keywords_vi=(
        "hãy nhớ", "tóm lại", "điểm chính cần nhớ",
        "giờ bạn đã biết", "và đó là cách", "hãy thực hành",
        "vậy nhé", "nhớ áp dụng",
    ),
    needs_closure=True,
    closure_penalty=0.25,  # Education clips need clear ending
    require_speech=True,
    min_speech_ratio=0.55,
    ideal_wpm_min=110.0,
    ideal_wpm_max=170.0,
    default_caption_enabled=True,
    default_color_preset="clear_fresh",
)

NEWS_COMMENTARY = GenreProfile(
    name="news_commentary",
    display_name="News Commentary",
    weights=GenreWeights(
        hook_strength=0.30,
        pacing=0.15,
        completeness=0.20,
        visual_quality=0.10,
        audio_quality=0.10,
        content_density=0.15,
    ),
    ideal_min_sec=15.0,
    ideal_max_sec=45.0,
    sweet_spot_sec=30.0,
    hook_keywords=(
        "breaking", "this just happened", "can you believe",
        "they just", "so apparently", "hot take",
        "unpopular opinion", "nobody's talking about",
    ),
    hook_keywords_vi=(
        "nóng", "vừa xảy ra", "tin được không",
        "họ vừa", "hóa ra là", "quan điểm nóng",
        "ý kiến trái chiều", "không ai nói về",
        "sốc", "khẩn cấp", "mới nhất",
        "gây tranh cãi", "bùng nổ", "chấn động",
    ),
    hook_patterns=(
        r"^(so |they |this |can you|apparently|breaking)",
        r"^(unpopular opinion|hot take|nobody)",
    ),
    hook_patterns_vi=(
        r"^(nóng|vừa |họ vừa|tin được|hóa ra)",
        r"^(ý kiến trái|quan điểm|không ai)",
    ),
    question_bonus=0.15,
    bold_statement_bonus=0.15,
    payoff_keywords=(
        "that's my take", "thoughts", "what do you think",
        "let me know", "bottom line",
    ),
    payoff_keywords_vi=(
        "đó là quan điểm của tôi", "các bạn nghĩ sao",
        "bạn nghĩ gì", "comment cho mình biết", "tóm lại là",
    ),
    needs_closure=True,
    closure_penalty=0.15,
    require_speech=True,
    ideal_wpm_min=140.0,
    ideal_wpm_max=210.0,
    default_caption_enabled=True,
)


# ── Entertainment genres (v3) ────────────────────────────────────────────

NATURE = GenreProfile(
    name="nature",
    display_name="Thiên nhiên",
    weights=GenreWeights(
        hook_strength=0.20,
        pacing=0.10,
        completeness=0.10,
        visual_quality=0.35,  # Nature = visual-first
        audio_quality=0.10,   # Ambient sound matters
        content_density=0.15,
    ),
    ideal_min_sec=15.0,
    ideal_max_sec=45.0,
    sweet_spot_sec=30.0,
    hook_keywords=(
        "look at", "watch", "incredible", "amazing", "beautiful",
        "you won't believe", "rare", "nature", "wild",
    ),
    hook_keywords_vi=(
        "nhìn kìa", "xem này", "không thể tin", "tuyệt đẹp", "đẹp quá",
        "hiếm có", "thiên nhiên", "hoang dã", "kỳ vĩ",
        "choáng ngợp", "ngoạn mục", "thần kỳ",
    ),
    hook_patterns=(
        r"^(look at|watch|see|amazing|incredible)",
    ),
    hook_patterns_vi=(
        r"^(nhìn |xem |đẹp |tuyệt|không thể tin)",
    ),
    question_bonus=0.10,
    bold_statement_bonus=0.15,
    payoff_keywords=(
        "beautiful", "incredible", "amazing", "stunning",
        "breathtaking", "majestic", "nature is",
    ),
    payoff_keywords_vi=(
        "tuyệt đẹp", "không thể tin", "ngoạn mục", "choáng ngợp",
        "thiên nhiên thật", "kỳ diệu", "đẹp đến ngỡ ngàng",
    ),
    needs_closure=False,
    closure_penalty=0.10,
    require_speech=False,
    require_person=False,
    min_speech_ratio=0.0,  # Nature doesn't need speech — 0% is fine
    max_silence_ratio=0.40,  # Nature ambient silence is content
    high_motion_bonus=0.10,
    default_caption_enabled=True,
    default_color_preset="cinematic",
)

HISTORY = GenreProfile(
    name="history",
    display_name="Lịch sử",
    weights=GenreWeights(
        hook_strength=0.25,
        pacing=0.10,
        completeness=0.25,
        visual_quality=0.10,
        audio_quality=0.10,
        content_density=0.20,
    ),
    ideal_min_sec=20.0,
    ideal_max_sec=55.0,
    sweet_spot_sec=40.0,
    hook_keywords=(
        "did you know", "the truth about", "history", "secret",
        "nobody knows", "the real story", "what happened",
    ),
    hook_keywords_vi=(
        "bạn có biết", "sự thật về", "lịch sử", "bí mật",
        "không ai biết", "câu chuyện thật", "chuyện gì đã xảy ra",
        "thời kỳ", "triều đại", "năm đó", "hàng trăm năm trước",
    ),
    hook_patterns=(
        r"^(did you know|the (truth|real|secret|hidden))",
        r"^(in \d+|back in|\d+ years ago)",
    ),
    hook_patterns_vi=(
        r"^(bạn có biết|sự thật|bí mật|câu chuyện thật)",
        r"^(năm \d+|vào thời|\d+ năm trước|thế kỷ)",
    ),
    question_bonus=0.20,
    bold_statement_bonus=0.15,
    payoff_keywords=(
        "and that's how", "the truth is", "to this day",
        "changed everything", "lesson", "legacy",
    ),
    payoff_keywords_vi=(
        "và đó là cách", "sự thật là", "cho đến ngày nay",
        "thay đổi tất cả", "bài học", "di sản",
        "lịch sử ghi nhận", "từ đó về sau",
    ),
    needs_closure=True,
    closure_penalty=0.25,
    require_speech=True,
    min_speech_ratio=0.5,
    default_caption_enabled=True,
)

ACTION = GenreProfile(
    name="action",
    display_name="Hành động",
    weights=GenreWeights(
        hook_strength=0.10,  # Action hooks are visual, not text
        pacing=0.25,
        completeness=0.05,  # Action clips don't need narrative closure
        visual_quality=0.35,  # Action = visual-first
        audio_quality=0.10,  # Sound effects matter
        content_density=0.15,
    ),
    ideal_min_sec=10.0,
    ideal_max_sec=40.0,
    sweet_spot_sec=25.0,
    hook_keywords=(
        "watch this", "let's go", "ready", "incoming",
        "attack", "run", "go go go",
    ),
    hook_keywords_vi=(
        "xem này", "đi thôi", "sẵn sàng", "chuẩn bị",
        "tấn công", "chạy", "nhanh lên", "coi chừng",
        "bắt đầu", "chiến thôi", "lên nào",
    ),
    hook_patterns=(
        r"^(watch|ready|let's|go|here we)",
    ),
    hook_patterns_vi=(
        r"^(xem |đi |sẵn sàng|chuẩn bị|nhanh|chiến)",
    ),
    question_bonus=0.05,
    bold_statement_bonus=0.10,
    payoff_keywords=(),
    payoff_keywords_vi=(),  # Action không cần closure text
    needs_closure=False,
    closure_penalty=0.0,  # Action doesn't need closure — no penalty
    require_speech=False,
    require_person=False,
    min_speech_ratio=0.1,
    max_silence_ratio=0.30,
    ideal_wpm_min=80.0,
    ideal_wpm_max=250.0,
    high_motion_bonus=0.15,
    default_caption_enabled=False,
    default_speed_factor=1.0,
)

KIDS_MUSIC = GenreProfile(
    name="kids_music",
    display_name="Nhạc thiếu nhi",
    weights=GenreWeights(
        hook_strength=0.15,
        pacing=0.25,
        completeness=0.20,
        visual_quality=0.15,
        audio_quality=0.15,
        content_density=0.10,
    ),
    ideal_min_sec=15.0,
    ideal_max_sec=45.0,
    sweet_spot_sec=30.0,
    hook_keywords=(
        "sing", "dance", "come on", "let's", "together",
    ),
    hook_keywords_vi=(
        "hát", "nhảy", "nào các bạn", "cùng nhau", "la la",
        "vui quá", "bạn ơi", "nào nào", "múa",
        "các bạn nhỏ", "bé ơi",
    ),
    hook_patterns=(),
    hook_patterns_vi=(
        r"^(nào |hát |nhảy |cùng |la la|bé ơi)",
    ),
    question_bonus=0.05,
    payoff_keywords=(
        "one more time", "sing along", "the end", "again",
    ),
    payoff_keywords_vi=(
        "hát lại nào", "cùng hát", "hết rồi", "lần nữa",
        "cuối bài", "vỗ tay nào",
    ),
    needs_closure=False,
    closure_penalty=0.0,  # Music doesn't need closure — no penalty
    require_speech=False,
    min_speech_ratio=0.1,
    max_silence_ratio=0.10,
    default_caption_enabled=True,
    default_color_preset="clear_fresh",
)

ANIMATION = GenreProfile(
    name="animation",
    display_name="Hoạt hình",
    weights=GenreWeights(
        hook_strength=0.20,
        pacing=0.15,
        completeness=0.20,
        visual_quality=0.30,  # Animation = visual storytelling
        audio_quality=0.05,
        content_density=0.10,
    ),
    ideal_min_sec=15.0,
    ideal_max_sec=50.0,
    sweet_spot_sec=30.0,
    hook_keywords=(
        "oh no", "what", "look", "help", "wow",
    ),
    hook_keywords_vi=(
        "ôi không", "cái gì", "nhìn kìa", "cứu", "oa",
        "trời ơi", "chết rồi", "chạy đi", "cẩn thận",
        "bạn ơi", "anh hùng", "nguy hiểm",
    ),
    hook_patterns=(
        r"^(oh no|what|look|help|wow)",
    ),
    hook_patterns_vi=(
        r"^(ôi |cái gì|nhìn |cứu|trời ơi|chạy )",
    ),
    question_bonus=0.10,
    bold_statement_bonus=0.10,
    payoff_keywords=(
        "the end", "and they", "happily", "lesson",
    ),
    payoff_keywords_vi=(
        "hết", "và họ", "hạnh phúc", "bài học",
        "thế là", "từ đó", "câu chuyện kết thúc",
    ),
    needs_closure=True,
    closure_penalty=0.20,
    require_speech=False,
    min_speech_ratio=0.1,  # Animation has some dialogue but not required
    high_motion_bonus=0.10,
    default_caption_enabled=True,
    default_color_preset="clear_fresh",
)


# ── Registry ─────────────────────────────────────────────────────────────

_PROFILES: dict[str, GenreProfile] = {
    "talking_head": TALKING_HEAD,
    "podcast": PODCAST,
    "interview": INTERVIEW,
    "review": REVIEW,
    "storytelling": STORYTELLING,
    "comedy": COMEDY,
    "education": EDUCATION,
    "news_commentary": NEWS_COMMENTARY,
    # Entertainment genres (v3)
    "nature": NATURE,
    "history": HISTORY,
    "action": ACTION,
    "kids_music": KIDS_MUSIC,
    "animation": ANIMATION,
}


def get_profile(genre: str) -> GenreProfile:
    """Get genre profile by name. Falls back to talking_head with warning."""
    if genre not in _PROFILES:
        import logging
        logging.getLogger(__name__).warning(
            "Unknown genre '%s', falling back to talking_head. Available: %s",
            genre, ", ".join(sorted(_PROFILES.keys())),
        )
        return TALKING_HEAD
    return _PROFILES[genre]


def list_profiles() -> list[str]:
    """List all registered genre profile names."""
    return list(_PROFILES.keys())
