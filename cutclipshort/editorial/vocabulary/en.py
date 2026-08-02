"""English vocabulary sets for editorial intelligence."""

# Emotional intensity
EMOTION_HIGH = frozenset({
    "incredible", "amazing", "terrifying", "devastating", "spectacular",
    "heartbreaking", "mind-blowing", "shocking", "insane", "unbelievable",
    "extraordinary", "horrifying", "breathtaking", "life-changing", "jaw-dropping",
})
EMOTION_MEDIUM = frozenset({
    "great", "terrible", "exciting", "scary", "beautiful", "awful",
    "fantastic", "horrible", "wonderful", "disgusting", "impressive",
    "disappointing", "fascinating", "frustrating", "brilliant",
})
EMOTION_MILD = frozenset({
    "good", "bad", "nice", "interesting", "cool", "weird", "funny",
    "sad", "happy", "angry", "surprised", "confused", "annoyed",
})

# Narrative markers
SETUP_MARKERS = frozenset({
    "so", "okay", "alright", "now", "here's the thing",
    "let me tell you", "picture this", "imagine",
})
DEVELOPMENT_MARKERS = frozenset({
    "and then", "but", "however", "meanwhile", "because",
    "the problem is", "what happened was", "turns out",
    "so basically", "the thing is", "here's why",
})
RESOLUTION_MARKERS = frozenset({
    "so that's", "and that's how", "in the end", "finally",
    "the takeaway", "the point is", "bottom line", "moral of the story",
    "long story short", "to sum up", "the result",
})

# Filler words
FILLER_WORDS = frozenset({
    "um", "uh", "like", "basically", "literally", "actually",
    "you know", "i mean", "kind of", "sort of", "just",
    "really", "very", "quite", "pretty much", "anyway",
})

# Stop words
STOP_WORDS = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "shall", "can",
    "to", "of", "in", "for", "on", "with", "at", "by", "from",
    "as", "into", "about", "between", "through", "after", "before",
    "during", "without", "it", "this", "that", "these", "those",
    "i", "you", "he", "she", "we", "they", "me", "him", "her",
    "us", "them", "my", "your", "his", "its", "our", "their",
    "and", "or", "but", "not", "so", "if", "then", "than",
})

# Hook patterns
CURIOSITY_PATTERNS = (
    "the crazy thing", "you won't believe", "nobody tells",
    "the secret", "what if", "imagine", "here's what",
)
CONFLICT_WORDS = frozenset({
    "wrong", "problem", "controversial", "disagree", "debate",
    "unpopular opinion", "hot take", "most people",
    "actually no", "stop", "myth", "lie", "truth is",
})

# CTA/outro patterns
OUTRO_PATTERNS = (
    "thank you for watching", "thanks for watching",
    "subscribe", "like and share", "hit the bell",
    "see you next time", "follow me on", "check out my",
    "link in", "don't forget to", "make sure to subscribe",
)

# Payoff/resolution words
RESOLUTION_WORDS = frozenset({
    "the answer", "because", "the reason", "that's why",
    "here's how", "the trick is", "the key is",
    "for example", "proof", "finally", "complete",
    "before and after", "transformation", "the result",
})

# Debate/argument markers (for SHOCK intent)
DEBATE_MARKERS = frozenset({
    "but", "however", "on the other hand", "some say",
    "others argue", "the real question", "what about",
    "people think", "the problem with", "you could argue",
})

# Insight markers — dense info / key learning (for INSIGHT intent)
INSIGHT_MARKERS = frozenset({
    "the key is", "here's why", "the reason", "what this means",
    "the trick is", "the secret", "most people don't know",
    "the data shows", "research shows", "studies show",
    "the important thing", "remember this", "pro tip",
    "in other words", "the takeaway", "bottom line",
    "here's what you need to know", "the science behind",
    "one thing to remember", "the real answer",
})

# Loop markers — satisfying / replay-worthy (for LOOP intent)
LOOP_MARKERS = frozenset({
    "wait for it", "watch this", "look at this", "check this out",
    "omg", "oh my god", "no way", "this is insane", "wow",
    "can you believe", "satisfying", "so smooth",
    "oddly satisfying", "mesmerizing", "hypnotic",
})

# Incomplete ending indicators
INCOMPLETE_ENDINGS = frozenset({
    "and", "but", "or", "so", "because", "which", "that", "when",
    "if", "while", "although", "since", "before", "after", "the",
    "a", "an", "to", "for", "with", "in", "of", "is", "are",
})
