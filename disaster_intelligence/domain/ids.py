from __future__ import annotations

import os
import time

_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def ulid() -> str:
    """Crockford ULID (26 chars) without extra dependencies."""
    ms = int(time.time() * 1000)
    time_chars = []
    t = ms
    for _ in range(10):
        time_chars.append(_CROCKFORD[t & 31])
        t >>= 5
    rand = os.urandom(10)
    rand_int = int.from_bytes(rand, "big")
    rand_chars = []
    for _ in range(16):
        rand_chars.append(_CROCKFORD[rand_int & 31])
        rand_int >>= 5
    return "".join(reversed(time_chars)) + "".join(reversed(rand_chars))
