from backend.rag.retriever import get_retriever


def test_chunks_loaded_from_knowledge_pack():
    retriever = get_retriever()
    assert len(retriever.chunks) == 9
    titles = {c["title"] for c in retriever.chunks}
    assert "Law 11 — Offside Offence" in titles
    assert "Law 12 — Handball" in titles


def test_search_returns_ranked_results_with_score():
    retriever = get_retriever()
    results = retriever.search("offside margin centimeters VAR", k=3)
    assert len(results) == 3
    for r in results:
        for field in ["source", "title", "text", "score"]:
            assert field in r
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)


def test_search_topical_relevance_for_each_section():
    retriever = get_retriever()
    queries_to_titles = {
        "offside line camera frame uncertainty limb tracking calibrated": "Law 11 — Offside Offence",
        "handball deflection reaction time penalty": "Law 12 — Handball",
        "VAR clear and obvious error review": "VAR Protocol",
        "formation 4-3-3 4-4-2 halftime tactical shift": "Formation Changes and Tactical Shifts",
        "winger substitution fresh legs full-back": "Substitutions and Game Management",
        "left side overload winger fullback cutback": "Wide Overloads and Attacking Patterns",
        "corner second phase rebound routine": "Set-Piece and Second-Phase Routines",
        "fatigue pressing intensity PPDA sprint decline": "Fatigue, Pressing Intensity, and Late-Game Decline",
        "human reaction time officiating perception": "Human Reaction Time and Officiating Benchmarks",
    }
    for query, expected_title in queries_to_titles.items():
        results = retriever.search(query, k=1)
        assert results[0]["title"] == expected_title, f"query {query!r} -> {results[0]['title']!r}"


def test_singleton_returns_same_instance():
    assert get_retriever() is get_retriever()
