import sys
from unittest.mock import patch
from app.progress.iter import progress_iter


def test_yields_all_items_without_tqdm():
    with patch("app.progress.iter.tqdm", None):
        result = list(progress_iter(range(5), desc="test", total=5))
    assert result == [0, 1, 2, 3, 4]


def test_yields_all_items_with_tqdm():
    result = list(progress_iter(range(5), desc="test", total=5))
    assert result == [0, 1, 2, 3, 4]


def test_works_with_list_input():
    data = ["a", "b", "c"]
    result = list(progress_iter(data, desc="letters"))
    assert result == data


def test_works_with_generator():
    gen = (x * 2 for x in range(4))
    result = list(progress_iter(gen, desc="gen", total=4))
    assert result == [0, 2, 4, 6]


def test_empty_iterable():
    result = list(progress_iter([], desc="empty"))
    assert result == []
