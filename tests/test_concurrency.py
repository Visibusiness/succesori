"""089: two threads feeding Pipeline.receive (what the API's sync endpoint does in its thread pool) lose no document.
Before Pipeline.lock, scripts/scala_race.py lost 7-9% of them (083)."""
import sys
import threading

from scripts.scala_logic import Pipeline, build_bank, docs_for


def test_two_threads_lose_no_document():
    n = 300
    pipe = Pipeline(build_bank(n))
    errors: list[str] = []

    def feed(k: int) -> None:
        for i in range(n):
            try:
                pipe.receive(docs_for(i)[k])
            except Exception as e:  # noqa: BLE001
                errors.append(repr(e))

    old = sys.getswitchinterval()
    sys.setswitchinterval(1e-6)   # makes the rare interleaving frequent (without the lock: dozens of losses at n=300)
    try:
        ts = [threading.Thread(target=feed, args=(k,)) for k in (0, 1)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
    finally:
        sys.setswitchinterval(old)
    assert errors == []
    assert sum(len(c.documents) for c in pipe.cases.values()) == 2 * n
    assert len(pipe.cases) == n and len({c.cif for c in pipe.cases.values()}) == n


def test_the_lock_is_reentrant_for_the_api():
    pipe = Pipeline(build_bank(1))
    with pipe.lock:   # agent/api.py holds it around receive + trace
        assert pipe.receive(docs_for(0)[0])["case_id"]


def test_indexes_give_the_same_answer_as_the_scans():
    """089: Bank.find_customer and Pipeline._case_for use indexes; changes made from outside (reset, scripts adding
    customers, a CNP changed in place) give the same answer as the old linear scans."""
    from agent.core_mock import Bank
    from agent.demo_documents import DOCUMENTS
    bank = Bank()
    assert bank.find_customer("2XXXXXXXXXXXX")["cif"] == "RC1001" and bank.find_customer("nu") is None
    bank.customers["RX1"] = {**bank.customers["RC2002"], "cif": "RX1", "cnp": "9000000000001"}   # added from outside
    assert bank.find_customer("9000000000001")["cif"] == "RX1"
    bank.customers["RX1"]["cnp"] = "9000000000002"                                              # changed in place
    assert bank.find_customer("9000000000001") is None and bank.find_customer("9000000000002")["cif"] == "RX1"
    bank.reset()
    assert bank.find_customer("9000000000002") is None and bank.find_customer("1XXXXXXXXXXX7")["cif"] == "RC2002"

    pipe = Pipeline(Bank())
    first = pipe.receive(DOCUMENTS[0])["case_id"]
    assert pipe.receive(DOCUMENTS[1])["case_id"] == first
    pipe.cases.clear()                                    # what POST /demo/reset does
    assert pipe.receive(DOCUMENTS[0])["case_id"] == "SC-2026-0001" and len(pipe.cases) == 1
