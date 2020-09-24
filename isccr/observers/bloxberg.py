# -*- coding: utf-8 -*-
from isccr import standalone
import time
from django.db import InterfaceError, OperationalError, connection
from datetime import datetime
import pytz
import sys
import iscc
from more_itertools import chunked
from loguru import logger as log
from isccr.core.models import Chain, IsccID
from web3 import Web3
import json

from isccr.utils import build_iscc_id


CHAIN_ID_BLOXBERG = 2
ISCC_ID_HEADER_BLOXBERG = 0b0100_0010 .to_bytes(1, "big", signed=False)
W3_CLIENT = None
W3_URL = "wss://websockets.bloxberg.org"
W3_CONTRACT = "0x4945d63B509e137b0293Bd958cf97B61996c0fB9"
W3_ABI = json.loads(
    '[{"type":"event","name":"ISCC","inputs":[{"type":"address","name":"actor",'
    '"internalType":"address","indexed":true},{"type":"bytes","name":"iscc",'
    '"internalType":"bytes","indexed":false},{"type":"bytes","name":"tophash",'
    '"internalType":"bytes","indexed":false}],"anonymous":false},{"type":"function",'
    '"stateMutability":"nonpayable","outputs":[],"name":"declare","inputs":[{"type":'
    '"bytes","name":"iscc","internalType":"bytes"},{"type":"bytes","name":"tophash",'
    '"internalType":"bytes"}]}]'
)
EXPLORER_TPL = "https://blockexplorer.bloxberg.org/tx/{}/internal_transactions/"


def w3_client():
    """Return cached web3 connection."""
    global W3_CLIENT
    if not W3_CLIENT:
        W3_CLIENT = Web3(Web3.WebsocketProvider(W3_URL))
        if W3_CLIENT.isConnected():
            log.debug(f"Connected to {W3_URL}")
        else:
            log.error("Connection failed")
            log.error(f"Connection failed to {W3_URL}.")
            sys.exit()
    return W3_CLIENT


def update(chain_obj: Chain):

    last = (
        IsccID.objects.filter(src_chain__id=CHAIN_ID_BLOXBERG)
        .order_by("-src_chain_idx")
        .first()
    )
    if last is None:
        start_height = 0
    else:
        start_height = last.src_chain_idx + 1

    w3 = w3_client()
    co = w3.eth.contract(W3_CONTRACT, abi=W3_ABI)
    event_filter = co.events.ISCC.createFilter(fromBlock=start_height)
    log.info(f"Observing bloxberg: start_height={start_height}")
    for event in event_filter.get_all_entries():
        txhash = event.transactionHash.hex()
        if IsccID.objects.filter(src_tx_hash=txhash).exists():
            log.warning(f"Already processed: {txhash}")
            continue

        iscc_code = "-".join([iscc.encode(co) for co in chunked(event.args.iscc, 9)])
        actor = event.args.actor
        ts = w3.eth.getBlock(event.blockNumber)["timestamp"]
        declaration = dict(
            iscc_code=iscc_code,
            actor=actor,
            src_chain=chain_obj,
            src_chain_idx=event.blockNumber,
            src_block_hash=event.blockHash.hex(),
            src_tx_hash=txhash,
            src_time=datetime.fromtimestamp(ts, tz=pytz.utc),
        )
        counter = 0
        while True:
            iscc_id = build_iscc_id(ISCC_ID_HEADER_BLOXBERG, iscc_code, counter)
            try:
                iscc_id_obj = IsccID.objects.get(iscc_id=iscc_id)
            except IsccID.DoesNotExist:
                iscc_id_obj = IsccID.objects.create(iscc_id=iscc_id, **declaration)
                log.debug(f"created {iscc_id_obj}")
                break
            # Update exsting ISCC-ID if from same actor for same ISCC-CODE
            if iscc_id_obj.actor == actor and iscc_id_obj.iscc_code == iscc_code:
                for key in declaration:
                    setattr(iscc_id_obj, key, declaration[key])
                iscc_id_obj.revision += 1
                iscc_id_obj.save()
                log.info(f"updated {iscc_id}")
                break
            counter += 1


def observe():
    log.info("Start observing bloxberg")
    chain_obj, created = Chain.objects.get_or_create(
        id=CHAIN_ID_BLOXBERG,
        defaults=dict(
            slug="bloxberg",
            url_template=EXPLORER_TPL,
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
        time.sleep(3)


if __name__ == "__main__":
    observe()
