"""Shared token-based search clause builder.

The old search did ``field ILIKE '%whole query%'`` on each column separately,
so a multi-word query like "Hasanova Yorqinoy" never matched — "Hasanova" is
the last_name and "Yorqinoy" is the first_name, and no single field contains
the whole phrase.

`token_search_clause` splits the query into words and requires EACH word to
match at least one of the given columns, AND-ing the words together. So the
two words can land in different fields, in any order.
"""

from __future__ import annotations

from typing import Sequence

from sqlalchemy import and_, or_
from sqlalchemy.sql.elements import ColumnElement


def token_search_clause(
    query: str,
    text_columns: Sequence[ColumnElement],
    *,
    phone_columns: Sequence[ColumnElement] | None = None,
) -> ColumnElement | None:
    """Build an AND-of-ORs search clause.

    - `text_columns`: each word is matched with ILIKE '%word%' against these.
    - `phone_columns`: additionally matched against a digits-only form of the
      word (so "+998 90" and "99890" both work), when the word has ≥3 digits.

    Returns None if the query is blank.
    """
    tokens = [t for t in (query or "").split() if t]
    if not tokens:
        return None

    per_token: list[ColumnElement] = []
    for tok in tokens:
        like = f"%{tok}%"
        ors: list[ColumnElement] = [c.ilike(like) for c in text_columns]
        if phone_columns:
            digits = "".join(ch for ch in tok if ch.isdigit())
            if len(digits) >= 3:
                plike = f"%{digits}%"
                ors.extend(c.ilike(plike) for c in phone_columns)
        per_token.append(or_(*ors))

    return and_(*per_token)
