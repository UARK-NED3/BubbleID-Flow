from collections.abc import Iterable, Iterator
from typing import TypeVar


T = TypeVar("T")


def progress(items: Iterable[T], desc: str | None = None) -> Iterator[T]:
    """Use tqdm when available, otherwise return a plain iterator."""
    try:
        from tqdm import tqdm
    except ImportError:
        return iter(items)

    return iter(tqdm(items, desc=desc))
