# -*- coding: utf-8 -*-
import textwrap
import iscc
import uvarint


ISCC_COMPONENT_CODES = {
    "CC",
    "CT",
    "Ct",
    "CY",
    "Ci",
    "CA",
    "Ca",
    "CV",
    "Cv",
    "CM",
    "Cm",
    "CD",
    "CR",
}


def iscc_verify(i):
    i = iscc_clean(i)
    for c in i:
        if c not in iscc.SYMBOLS:
            raise ValueError('Illegal character "{}" in ISCC Code'.format(c))
    for component_code in iscc_split(i):
        iscc_verify_component(component_code)
    return True


def iscc_verify_component(component_code):

    if not len(component_code) == 13:
        raise ValueError(
            "Illegal component length {} for {}".format(
                len(component_code), component_code
            )
        )

    header_code = component_code[:2]
    if header_code not in ISCC_COMPONENT_CODES:
        raise ValueError("Illegal component header {}".format(header_code))


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
    return iscc.encode(ledger_id + iscc_id_body + uvarint.encode(counter))
