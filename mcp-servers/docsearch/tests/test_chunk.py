from docsearch.chunk import MAX_CHARS, MIN_CHARS, split


def test_short_document_is_one_chunk():
    text = "짧은 문서입니다. " * 10
    assert len(split(text)) == 1


def test_empty_input():
    assert split("") == []
    assert split("\n\n\n") == []


def test_tiny_fragments_are_dropped():
    assert split("짧음") == []


def test_long_document_is_split():
    text = "\n\n".join(f"문단 {i}. " + "내용 " * 80 for i in range(10))
    chunks = split(text)
    assert len(chunks) > 1


def test_no_chunk_exceeds_hard_limit():
    text = "\n\n".join("가" * 500 for _ in range(20))
    assert all(len(c.text) <= MAX_CHARS * 2 for c in split(text))


def test_single_huge_paragraph_is_broken_up():
    text = "\n".join(f"줄 {i} " + "내용 " * 40 for i in range(40))
    assert len(split(text)) > 1


def test_chunks_are_indexed_in_order():
    text = "\n\n".join(f"문단 {i}. " + "내용 " * 80 for i in range(6))
    assert [c.index for c in split(text)] == list(range(len(split(text))))


def test_chunks_overlap_for_boundary_sentences():
    """경계에 걸친 문장이 양쪽 어디서도 안 잡히면 안 된다."""
    text = "\n\n".join(f"문단{i} " + "내용 " * 90 for i in range(4))
    chunks = split(text)
    assert len(chunks) >= 2
    # 두 번째 덩어리 앞부분에 첫 덩어리 꼬리가 섞여 있어야 한다
    assert any(chunks[0].text[-40:].strip()[:20] in c.text for c in chunks[1:])


def test_every_chunk_meets_minimum():
    text = "\n\n".join("내용 " * 60 for _ in range(5))
    assert all(len(c.text) >= MIN_CHARS for c in split(text))


def test_preview_is_truncated():
    text = "긴 " * 500
    assert split(text)[0].preview.endswith("…")
