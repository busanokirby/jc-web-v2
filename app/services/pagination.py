from math import ceil
from types import SimpleNamespace
from flask import request

DEFAULT_PER_PAGE = 20
MAX_PER_PAGE = 200


class Pagination(SimpleNamespace):
    """Lightweight pagination object compatible with Flask-SQLAlchemy's Pagination

    Attributes expected by templates:
      - items, page, per_page, total, pages, has_prev, has_next,
        prev_num, next_num, iter_pages()
    """

    def __init__(self, items, page: int, per_page: int, total: int):
        pages = ceil(total / per_page) if per_page else 0
        has_prev = page > 1
        has_next = page < pages
        super().__init__(items=items, page=page, per_page=per_page, total=total, pages=pages,
                         has_prev=has_prev, has_next=has_next,
                         prev_num=(page - 1) if has_prev else None,
                         next_num=(page + 1) if has_next else None)

    def iter_pages(self, left_edge=2, left_current=2, right_current=5, right_edge=2):
        last = 0
        for num in range(1, (self.pages or 1) + 1):
            if (
                num <= left_edge
                or (num > self.page - left_current - 1 and num < self.page + right_current)
                or num > self.pages - right_edge
            ):
                if last + 1 != num:
                    yield None
                yield num
                last = num


def get_page_args(default_per_page: int = DEFAULT_PER_PAGE, max_per_page: int = MAX_PER_PAGE):
    """Safely read page and per_page from request args with validation."""
    try:
        page = int(request.args.get('page', 1))
    except Exception:
        page = 1
    try:
        per_page = int(request.args.get('per_page', default_per_page))
    except Exception:
        per_page = default_per_page

    if page < 1:
        page = 1
    if per_page < 1:
        per_page = default_per_page
    if per_page > max_per_page:
        per_page = max_per_page

    return page, per_page


def paginate_sequence(seq, page: int, per_page: int):
    """Paginate an in-memory sequence and return a Pagination-like object.

    Use when the source is already a list (e.g., merged results). This avoids
    forcing caller templates to handle sequences differently from DB query
    pagination objects.
    """
    total = len(seq)
    if per_page <= 0:
        per_page = DEFAULT_PER_PAGE
    start = (page - 1) * per_page
    end = start + per_page
    items = seq[start:end]
    return Pagination(items=items, page=page, per_page=per_page, total=total)
