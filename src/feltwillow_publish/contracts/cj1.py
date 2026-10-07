"""Feltwillow canonical-json-v1, constrained profile (handoff-contract draft H1).

PROPOSED CONTRACT. The serializer is byte-for-byte the v2 `canonical_bytes`
(the v2 blueprint's tools/validate_blueprint.py): json.dumps(sort_keys=True,
separators=(",", ":"), ensure_ascii=False, allow_nan=False) encoded as UTF-8.
H1 adds an explicit *value domain* (the "safe domain") that every producer and
consumer enforces before hashing. Inside that domain the bytes are identical
to RFC 8785 (JCS) output and to the JavaScript reference in cj1.mjs.

Domain (each violation has a stable error code):
  CJ_INVALID_UTF8      input bytes are not well-formed UTF-8
  CJ_BOM               input starts with U+FEFF
  CJ_SYNTAX            not RFC 8259 JSON (incl. NaN/Infinity tokens, trailing data)
  CJ_DUPLICATE_KEY     an object repeats a member name
  CJ_KEY_NOT_ASCII     a member name contains a code point outside U+0020..U+007E
  CJ_FLOAT             a number has a fraction or exponent part (1.0, 1e2, 0.1, -0.0)
  CJ_INT_RANGE         an integer is outside -(2**53-1) .. 2**53-1
  CJ_LONE_SURROGATE    a string contains an unpaired surrogate (only reachable via \\uD8xx escapes)
  CJ_UNASSIGNED_CODEPOINT a string contains a code point unassigned (category Cn) in the
                       Unicode version of the authoritative validator (Python 3.12: 15.0.0).
                       This makes the NFC verdict version-stable: Unicode normalization
                       stability guarantees verdicts for ASSIGNED characters never change.
  CJ_NOT_NFC           a string value is not in Unicode Normalization Form C
  CJ_DEPTH             nesting deeper than MAX_DEPTH
Only the standard library is used. No network, no subprocess.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata

ALGORITHM_ID = "feltwillow-canonical-json-v1"
MAX_SAFE_INT = 2**53 - 1
MAX_DEPTH = 64
_KEY_RE = re.compile(r"^[\x20-\x7e]*$")


class CanonicalError(ValueError):
    def __init__(self, code: str, detail: str = ""):
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code


def _reject_float(text: str):
    raise CanonicalError("CJ_FLOAT", text)


def _check_int(text: str) -> int:
    if len(text.lstrip("-")) > 16:  # > 2**53-1 for sure; also avoids Python's int-digit limit (CJ_SYNTAX)
        raise CanonicalError("CJ_INT_RANGE", text[:24] + ("..." if len(text) > 24 else ""))
    value = int(text)
    if not -MAX_SAFE_INT <= value <= MAX_SAFE_INT:
        raise CanonicalError("CJ_INT_RANGE", text)
    return value


def _reject_constant(text: str):
    raise CanonicalError("CJ_SYNTAX", "non-JSON constant " + text)


def _pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise CanonicalError("CJ_DUPLICATE_KEY", repr(key))
        out[key] = value
    return out


def check_domain(value, depth: int = 0) -> None:
    """Raise CanonicalError if an already-parsed value is outside the safe domain."""
    if depth > MAX_DEPTH:
        raise CanonicalError("CJ_DEPTH")
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, int):
        if not -MAX_SAFE_INT <= value <= MAX_SAFE_INT:
            raise CanonicalError("CJ_INT_RANGE", str(value))
        return
    if isinstance(value, float):
        raise CanonicalError("CJ_FLOAT", repr(value))
    if isinstance(value, str):
        _check_string(value)
        return
    if isinstance(value, list):
        for item in value:
            check_domain(item, depth + 1)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise CanonicalError("CJ_KEY_NOT_ASCII", "non-string key")
            if any(0xD800 <= ord(c) <= 0xDFFF for c in key):
                raise CanonicalError("CJ_LONE_SURROGATE", "in key")
            if not _KEY_RE.match(key):
                raise CanonicalError("CJ_KEY_NOT_ASCII", repr(key))
            check_domain(item, depth + 1)
        return
    raise CanonicalError("CJ_SYNTAX", "unsupported type " + type(value).__name__)


def _check_string(s: str) -> None:
    if any(0xD800 <= ord(c) <= 0xDFFF for c in s):
        raise CanonicalError("CJ_LONE_SURROGATE")
    if any(unicodedata.category(c) == "Cn" for c in s):
        raise CanonicalError("CJ_UNASSIGNED_CODEPOINT", "Unicode " + unicodedata.unidata_version)
    if not unicodedata.is_normalized("NFC", s):
        raise CanonicalError("CJ_NOT_NFC", repr(s[:40]))


def loads_strict(data: bytes):
    """Parse UTF-8 JSON bytes into a value of the safe domain (or raise CanonicalError)."""
    if data.startswith(b"\xef\xbb\xbf"):
        raise CanonicalError("CJ_BOM")
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise CanonicalError("CJ_INVALID_UTF8", str(exc)) from None
    try:
        value = json.loads(text, object_pairs_hook=_pairs, parse_float=_reject_float,
                           parse_int=_check_int, parse_constant=_reject_constant)
    except CanonicalError:
        raise
    except RecursionError:
        raise CanonicalError("CJ_DEPTH") from None
    except ValueError as exc:
        raise CanonicalError("CJ_SYNTAX", str(exc)) from None
    check_domain(value)
    return value


def canonical_bytes(value) -> bytes:
    """v2 canonical-json-v1 bytes, after enforcing the H1 safe domain."""
    check_domain(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def v2_canonical_bytes_unconstrained(value) -> bytes:
    """The v2 function exactly as shipped (finite floats and big ints allowed), for the audit."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")
