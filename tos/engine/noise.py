"""Background interference: rare, location- and phrase-keyed ambient events.

Entries are sealed, so the data files stay readable while these stay surprising.
"""
from __future__ import annotations

import base64
import hashlib
import json

from .content import apply_effects

_SALT = bytes.fromhex("4a6a74e3e645c2abf7f6e2bca38c9c9e")
_TABLE = {
    "ac9e9d5470da49baca27": (
        "UDOLhgmZEEhMYYQo0/K6W69Sfoi6AiF0ObUfNoN+NlGG36gnrnvlpvwbnYsDrJa7NZWb1tZj"
        "xWvMZB8+MCrrr1e6LNnZKTU6ZeR3ufx5aHG7pIpyyyAsJ29w1L9nhwlTSS0kUBSMqpM56s0R"
        "Gm54hh1RgpShgKWTnB0VrmU2ioEofWnrtV9QhfbQstjjmMkjrVmUeXzCL+x187tNt531x9vE"
        "a5Znz82PK4iG3IJs/uMgxAHQFZL0Ponja4IglfoEve0WQzWX1vmH+Q99IP0nzhawlBEhWlcx"
        "gACFEwGPMsUOI92LwD+1RfonHMg12BPJEOQc/ZIYiUVafj3akqls4AA6Fd7++3kLICeGdlEu"
        "wbgXsVyXQmJ21gUTabdxVxNO6TIzrfyeIH3KxzncYCGsWWDpeT6Gh/J3mgIdoHFohBxiSD60"
        "25vz/hhclIcEVnEJVxgiON+f2o/xsUNCrIpwuIWcoAZTPtt+mZI4hvAEATF81Jk0y8is/pH9"
        "sKywA1dKognUpPEa5ElkC27BBIvAfQimmpfV2/LWuzjKbQ7wrSRM3nk1xr2jt6eU2scosj/k"
        "KZNMnfpbKz7o9qD18NANTxmec3aoDhkDczyHiAT3cFCHxMlG/9LqUrpv16imJbYORaW4eUje"
        "xDgY+BiIAdjH1bJdhhhIYma5NV/3eoB0yv+XRq0zQ2mYVxL3tevOc1zHJ3axuFD0xSEAgNOD"
        "7NdlAJZc0S2pHLsRvOyac/DVQ9G6rAwMjapmcCqOLRYrWH7eWcZ9AiQ0aC2ijJIFMfLfsfM4"
        "Xusr1NQt85rayJdry8eCEO+6jRp9Tfugy7q2S5QGpJIoCq125v96qaBdUDJqwYlAvNoChQIh"
        "BLJShIEk/+IzQ6+xafOSkMeFyC81+Wmhacx53i56hnaE7UIdlmOu87VWPqfOtU9qcsa19+TI"
        "mIwEV2rvtSEsMVS4iXjEVSxEtQ=="
    ),
    "49c4a2507e22d78affef": (
        "ggm5YuUl4UBm5tP9tpuOo9Gl2H20iQerGk5PCghf0zVhgghFKzywWOQ3Ysn89habYkxv8EY6"
        "f0BofFUN8Zoe6alNJFpIMTQxXsuPkPMCoZcHa1WqinTJu4c0MqlHE1ylaBnIK69cifBNrVmW"
        "ca2/6yoLJET8+oLZcDHCaRTL/3pW7SDoHp3Q3UwEG/qCFL4IuE0vjW6VNIT4vEXA+657bT0Y"
        "ciD0QdH08aXp9mYg+H/481c8lIcaYuTVuV+7WosSECDRAPojuTWZUfJjp8+Ybd0/j4Xmw9RK"
        "xeW6NHxI5L4frXkuzemXB9tKScy4T96+4aV6USOH031VIYeMaGMnPupBSJ7lLpNYWjSw0X0T"
        "B2C8P8ZSnfnLGke63hGg5SjRfMdYlFxD7I89ytm4q2Aj7BvkORgDGnMS1Hga/48xPawlUi+r"
        "ck/qKcQsFbdmqQFFHtVsuylyPqp/Gkx1RPnf"
    ),
}


def _key(*parts) -> bytes:
    return hashlib.sha256(_SALT + "|".join(map(str, parts)).encode()).digest()


def _open(k: bytes) -> dict | None:
    blob = _TABLE.get(hashlib.sha256(k).hexdigest()[:20])
    if blob is None:
        return None
    raw = base64.b64decode(blob)
    stream = b"".join(hashlib.sha256(k + i.to_bytes(4, "big")).digest() for i in range(len(raw) // 32 + 1))
    return json.loads(bytes(a ^ b for a, b in zip(raw, stream)))


def at(loc, x: int, y: int) -> list[tuple]:
    """Ambient events for standing on a tile. Usually nothing."""
    hit = _open(_key(loc.id, x, y))
    if not hit or hit.get("once") in loc.state.flags:
        return []
    if hit.get("once"):
        loc.state.flags.add(hit["once"])
    return apply_effects(hit.get("effects"), loc.state, loc.content)


def heard(word: str) -> dict | None:
    """A phrase typed at a terminal prompt that means something to the network. Usually nothing."""
    return _open(_key(word.strip().upper())) if word.strip() else None


def follow(state, content, hit: dict) -> list[tuple]:
    return apply_effects(hit.get("effects"), state, content) + ([("exit", hit["to"])] if hit.get("to") else [])
