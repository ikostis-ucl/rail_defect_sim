from collections.abc import Iterable, Iterator
from typing import TypeVar

T = TypeVar("T")

try:
    from tqdm import tqdm
except ModuleNotFoundError:
    tqdm = None


def progress_iter(
    iterable: Iterable[T],
    *,
    desc: str,
    total: int | None = None,
    unit: str = "item",
    leave: bool = False,
) -> Iterable[T] | Iterator[T]:
    """Wrap an iterable in a tqdm progress bar when tqdm is available."""
    if tqdm is None:
        return iterable
    return tqdm(iterable, desc=desc, total=total, unit=unit, dynamic_ncols=True, leave=leave)
