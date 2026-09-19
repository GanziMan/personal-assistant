import math

from assistant.memory.fusion import reciprocal_rank_fusion
from assistant.memory.models import Episode, Fact
from assistant.memory.promote import candidates, confidence_from_evidence, should_supersede
from assistant.memory.vectors import cosine, normalize, pack, unpack


def test_pack_unpack_roundtrip():
    vec = [0.5, -0.25, 1.0]
    assert [round(v, 5) for v in unpack(pack(vec))] == vec


def test_normalize_gives_unit_length():
    assert math.isclose(sum(v * v for v in normalize([3.0, 4.0])), 1.0, rel_tol=1e-6)


def test_normalize_survives_zero_vector():
    assert normalize([0.0, 0.0]) == [0.0, 0.0]


def test_cosine_bounds():
    assert math.isclose(cosine([1, 0], [1, 0]), 1.0)
    assert math.isclose(cosine([1, 0], [0, 1]), 0.0)


def test_rrf_rewards_agreement():
    # 둘 다 2등 안에 올린 문서가, 한쪽에서만 1등인 문서를 이긴다
    merged = dict(reciprocal_rank_fusion([[10, 20], [20, 30]]))
    assert merged[20] > merged[10]


def test_rrf_is_deterministic_on_ties():
    a = reciprocal_rank_fusion([[1, 2, 3]])
    b = reciprocal_rank_fusion([[1, 2, 3]])
    assert a == b


def test_rrf_respects_limit():
    assert len(reciprocal_rank_fusion([[1, 2, 3, 4, 5]], limit=2)) == 2


def test_confidence_never_reaches_certainty():
    assert confidence_from_evidence(1000) < 1.0, "비서가 100% 확신하면 안 된다"
    assert confidence_from_evidence(0) == 0.0


def test_confidence_is_monotonic():
    values = [confidence_from_evidence(n) for n in range(1, 10)]
    assert values == sorted(values)


def test_promotion_needs_repetition():
    eps = [Episode(title="매주 금요일 배포") for _ in range(2)]
    assert candidates(eps) == []
    eps.append(Episode(title="매주 금요일 배포"))
    assert [f.subject for f in candidates(eps)] == ["매주 금요일 배포"]


def test_supersede_only_on_higher_confidence():
    old = Fact("에디터", "VS Code", confidence=0.8)
    weaker = Fact("에디터", "Vim", confidence=0.5)
    stronger = Fact("에디터", "Vim", confidence=0.9)
    same = Fact("에디터", "VS Code", confidence=0.9)

    assert not should_supersede(old, weaker)
    assert should_supersede(old, stronger)
    assert not should_supersede(old, same), "내용이 같으면 대체할 이유가 없다"
