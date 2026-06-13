import math
import re
from pathlib import Path

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "data" / "knowledge"

_WORD_RE = re.compile(r"[a-z]+")


def _tokenize(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


def _split_sections(content: str) -> list[tuple[str, str]]:
    sections = []
    current_title = None
    current_lines: list[str] = []
    for line in content.splitlines():
        if line.startswith("## "):
            if current_title is not None:
                sections.append((current_title, "\n".join(current_lines).strip()))
            current_title = line[3:].strip()
            current_lines = []
        elif current_title is not None:
            current_lines.append(line)
    if current_title is not None:
        sections.append((current_title, "\n".join(current_lines).strip()))
    return sections


class Retriever:
    def __init__(self, knowledge_dir: Path = KNOWLEDGE_DIR):
        self.chunks: list[dict] = []
        for md_file in sorted(knowledge_dir.glob("*.md")):
            content = md_file.read_text(encoding="utf-8")
            for title, text in _split_sections(content):
                self.chunks.append({"source": md_file.name, "title": title, "text": text})

        self._doc_tokens = [_tokenize(chunk["text"]) for chunk in self.chunks]
        self._idf = self._build_idf(self._doc_tokens)
        self._doc_vectors = [self._vectorize(tokens) for tokens in self._doc_tokens]

    def _build_idf(self, doc_tokens: list[list[str]]) -> dict[str, float]:
        n_docs = len(doc_tokens)
        df: dict[str, int] = {}
        for tokens in doc_tokens:
            for term in set(tokens):
                df[term] = df.get(term, 0) + 1
        return {term: math.log((1 + n_docs) / (1 + freq)) + 1 for term, freq in df.items()}

    def _vectorize(self, tokens: list[str]) -> dict:
        tf: dict[str, int] = {}
        for term in tokens:
            tf[term] = tf.get(term, 0) + 1
        vec = {term: count * self._idf.get(term, 0.0) for term, count in tf.items()}
        norm = math.sqrt(sum(value * value for value in vec.values()))
        return {"vec": vec, "norm": norm}

    def _cosine(self, query_vec: dict, doc_vec: dict) -> float:
        if query_vec["norm"] == 0 or doc_vec["norm"] == 0:
            return 0.0
        dot = sum(weight * doc_vec["vec"].get(term, 0.0) for term, weight in query_vec["vec"].items())
        return dot / (query_vec["norm"] * doc_vec["norm"])

    def search(self, query: str, k: int = 3) -> list[dict]:
        query_vec = self._vectorize(_tokenize(query))
        scored = [
            (self._cosine(query_vec, doc_vec), chunk)
            for chunk, doc_vec in zip(self.chunks, self._doc_vectors)
        ]
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [
            {**chunk, "score": round(score, 4)}
            for score, chunk in scored[:k]
        ]


_retriever_instance: Retriever | None = None


def get_retriever() -> Retriever:
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = Retriever()
    return _retriever_instance
