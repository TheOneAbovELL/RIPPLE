from ripple.core.retrieval_contract import RetrievalPath
from ripple.retrieval.backend import SearchHit
from ripple.retrieval.fusion import RRF_K, reciprocal_rank_fusion


def _hits(*ids: str) -> list[SearchHit]:
    return [SearchHit(memory_id, score=float(len(ids) - i)) for i, memory_id in enumerate(ids)]


def test_fusion_item_in_both_lists_beats_single_list_leaders():
    fused = reciprocal_rank_fusion(
        [(RetrievalPath.LEXICAL, _hits("a", "both")), (RetrievalPath.DENSE, _hits("b", "both"))]
    )
    assert fused[0].memory_id == "both"
    assert fused[0].score == 2 / (RRF_K + 2)  # rank 2 in both lists beats rank 1 in one


def test_fusion_single_list_preserves_rank_order():
    fused = reciprocal_rank_fusion([(RetrievalPath.LEXICAL, _hits("x", "y", "z"))])
    assert [f.memory_id for f in fused] == ["x", "y", "z"]
    assert all(f.via is RetrievalPath.LEXICAL for f in fused)


def test_fusion_via_is_the_path_that_ranked_the_item_best():
    fused = reciprocal_rank_fusion(
        [(RetrievalPath.LEXICAL, _hits("a", "b")), (RetrievalPath.DENSE, _hits("b", "a"))]
    )
    via = {f.memory_id: f.via for f in fused}
    assert via == {"a": RetrievalPath.LEXICAL, "b": RetrievalPath.DENSE}


def test_fusion_equal_scores_break_ties_by_memory_id():
    fused = reciprocal_rank_fusion(
        [(RetrievalPath.LEXICAL, _hits("b")), (RetrievalPath.DENSE, _hits("a"))]
    )
    assert [f.memory_id for f in fused] == ["a", "b"]
    assert fused[0].via is RetrievalPath.DENSE  # ranked first in its own list


def test_fusion_of_nothing_is_nothing():
    assert reciprocal_rank_fusion([(RetrievalPath.LEXICAL, [])]) == []
