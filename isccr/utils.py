# -*- coding: utf-8 -*-
import textwrap
import iscc
import uvarint


def iscc_clean(i):
    """Remove leading scheme and dashes"""
    return i.split(":")[-1].strip().replace("-", "")


def iscc_split(i):
    return textwrap.wrap(iscc_clean(i), 13)


def iscc_decode(code) -> bytes:
    return b"".join(iscc.decode(c) for c in iscc_split(code))


def build_iscc_id(ledger_id, iscc_code, counter: int):
    """Create ISCC-ID from full ISCC for given ledger with a given counter"""
    components = iscc_split(iscc_code)
    # First 7 bytes (including header) of all but Instance-ID
    digests = [iscc.decode(c)[:7] for c in components if not c.startswith("CR")]
    iscc_id_body = iscc.similarity_hash(digests)
    # cid = digest[10:13]
    # did = digest[20:22]
    # iid = digest[29:31]
    return iscc.encode(ledger_id + iscc_id_body + uvarint.encode(counter))
