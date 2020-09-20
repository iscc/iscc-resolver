# -*- coding: utf-8 -*-
from isccr import standalone
from django.conf import settings
import sys
import time
from loguru import logger as log
from datetime import datetime
import pytz
from django.db import InterfaceError, OperationalError, connection
from mcrpc.exceptions import RpcError
from isccr.core.models import Chain, IsccID
from isccr.utils import build_iscc_id
import mcrpc


CHAIN_ID_COBLO = 1
ISCC_ID_HEADER_COBLO = 0b0100_0001 .to_bytes(1, "big")


class LazyStream:
    """A 'paginatable' wrapper for MultiChain Streams"""

    def __init__(self, name, descending=False):
        self.name = name
        self.descending = descending
        self.api = mcrpc.RpcClient(
            settings.CHAIN_COBLO_HOST,
            settings.CHAIN_COBLO_PORT,
            settings.CHAIN_COBLO_USER,
            settings.CHAIN_COBLO_PWD,
        )

    def __len__(self):
        try:
            return int(self.api.liststreams(self.name)[0]["items"])
        except (RpcError, IndexError):
            return 0

    def __getitem__(self, item):
        if self.descending:
            return self._get_descending(item)
        else:
            return self._get_ascending(item)

    def _get_ascending(self, item):
        """From oldest to latest"""
        if isinstance(item, slice):
            count = item.stop - item.start
            try:
                result = self.api.liststreamitems(
                    self.name,
                    verbose=True,
                    count=count,
                    start=item.start,
                    local_ordering=False,
                )
                result = [dict(e, stream=self.name) for e in result]
            except RpcError:
                return []
            return result

        elif isinstance(item, int):
            try:
                result = self.api.liststreamitems(
                    self.name, verbose=True, count=1, start=item, local_ordering=False
                )[0]
                result["stream"] = self.name
            except (RpcError, IndexError):
                return {}
            return result

    def _get_descending(self, item):
        """From latest to oldest entry"""
        if isinstance(item, slice):
            count = item.stop - item.start
            try:
                result = self.api.liststreamitems(
                    self.name,
                    verbose=True,
                    count=count,
                    start=-(item.start + count),
                    local_ordering=False,
                )
                result = [dict(e, stream=self.name) for e in result]
            except RpcError:
                return []
            return list(reversed(result))

        elif isinstance(item, int):
            try:
                result = self.api.liststreamitems(
                    self.name,
                    verbose=True,
                    count=1,
                    start=-(item + 1),
                    local_ordering=False,
                )[0]
                result["stream"] = self.name
            except (RpcError, IndexError):
                return {}
            return result


def update(chain_obj: Chain, batch_size: int = 1000):
    """Process next 'batch_size' ISCC declerations"""
    iscc_stream = LazyStream("iscc")
    last = (
        IsccID.objects.filter(src_chain__id=CHAIN_ID_COBLO)
        .order_by("-src_chain_idx")
        .first()
    )
    if last is None:
        start_height = 0
    else:
        start_height = last.src_chain_idx + 1
    log.info(f"Updateing coblo: start_height={start_height}, batch_size={batch_size}")

    for lidx, entry in enumerate(iscc_stream[start_height : start_height + batch_size]):
        log.debug(entry)
        iscc_code = "-".join(entry["keys"])
        actor = entry["publishers"][0]
        decleration = dict(
            iscc_code=iscc_code,
            actor=actor,
            src_chain=chain_obj,
            src_chain_idx=start_height + lidx,
            src_block_hash=entry["blockhash"],
            src_tx_hash=entry["txid"],
            src_tx_out_idx=entry["vout"],
            src_time=datetime.fromtimestamp(entry["time"], tz=pytz.utc),
        )

        data = entry["data"].get("json")
        if data:
            if data.get("tophash"):
                decleration["iscc_tophash"] = data["tophash"]
            if data.get("title"):
                decleration["iscc_seed_title"] = data["title"]
            if data.get("extra"):
                decleration["iscc_seed_extra"] = data["extra"]
            if data.get("meta"):
                decleration["iscc_mutable_metadata"] = data["meta"]

        counter = 0
        while True:
            iscc_id = build_iscc_id(ISCC_ID_HEADER_COBLO, iscc_code, counter)
            try:
                iscc_id_obj = IsccID.objects.get(iscc_id=iscc_id)
            except IsccID.DoesNotExist:
                iscc_id_obj = IsccID.objects.create(iscc_id=iscc_id, **decleration)
                log.debug(f"created {iscc_id_obj}")
                break
            # Update exsting ISCC-ID if from same actor for same ISCC-CODE
            if iscc_id_obj.actor == actor and iscc_id_obj.iscc_code == iscc_code:
                for key in decleration:
                    setattr(iscc_id_obj, key, decleration[key])
                iscc_id_obj.revision += 1
                iscc_id_obj.save()
                log.info(f"updated {iscc_id}")
                break
            counter += 1


def observe():
    log.info("Start observing coblo")

    chain_obj, created = Chain.objects.get_or_create(
        id=CHAIN_ID_COBLO,
        defaults=dict(
            slug="coblo", url_template="https://explorer.coblo.net/stream/iscc/{}:{}/"
        ),
    )
    if created:
        log.info(f"Created {repr(chain_obj)} in DB.")
    else:
        log.info(f"Using {repr(chain_obj)}")

    while True:
        try:
            update(chain_obj)
        except (InterfaceError, OperationalError) as e:
            log.warning(repr(e))
            log.info("Trying to gracefully reconnect to DB")
            try:
                connection.connect()
                log.info("Reconnection success")
            except Exception as e:
                log.warning("Reconnection failed")
                time.sleep(10)


if __name__ == "__main__":
    log.remove()
    log.add(sys.stderr, level="INFO")
    try:
        observe()
    except KeyboardInterrupt:
        log.debug("Stop observing coblo")
        sys.exit()
