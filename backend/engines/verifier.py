import re

_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of",
    "is", "are", "was", "were", "be", "been", "by", "with", "as", "that",
    "this", "it", "its", "from", "their", "they", "he", "she", "his", "her",
    "has", "have", "had", "not", "no", "so", "than", "then", "which", "who",
    "whom", "about", "into", "over", "under", "after", "before", "between",
    "during", "while", "because", "if", "when", "where", "what", "why", "how",
    "all", "any", "both", "can", "did", "does", "doing", "each", "few",
    "more", "most", "other", "some", "such", "only", "own", "same", "too",
    "very", "will", "would", "could", "should",
}

_NUMBER_RE = re.compile(r"\d+\.?\d*")
_WORD_RE = re.compile(r"[a-z]+")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")

_COVERAGE_THRESHOLD = 0.35


def _content_words(text: str) -> set[str]:
    return {w for w in _WORD_RE.findall(text.lower()) if w not in _STOPWORDS and len(w) > 2}


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_RE.split(text.strip()) if s.strip()]


def verify(answer: str, evidence_texts: list[str]) -> dict:
    evidence_blob = " ".join(evidence_texts)
    evidence_words = _content_words(evidence_blob)
    evidence_numbers = set(_NUMBER_RE.findall(evidence_blob))

    sentences = _sentences(answer)
    unsupported = []
    for sentence in sentences:
        words = _content_words(sentence)
        overlap = len(words & evidence_words) / len(words) if words else 1.0
        numbers = set(_NUMBER_RE.findall(sentence))
        if overlap < _COVERAGE_THRESHOLD or not numbers.issubset(evidence_numbers):
            unsupported.append(sentence)

    checked = len(sentences)
    coverage = (checked - len(unsupported)) / checked if checked else 1.0
    return {
        "verified": len(unsupported) == 0,
        "coverage": round(coverage, 2),
        "checked_sentences": checked,
        "unsupported": unsupported,
        "method": "lexical",
    }
