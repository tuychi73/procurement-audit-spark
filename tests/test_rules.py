from datetime import date

import pandas as pd
import pytest

from audit import config as C
from audit import rules
from audit.spark import get_spark


@pytest.fixture(scope="session")
def spark():
    s = get_spark("tests", shuffle_partitions=2)
    s.sparkContext.setLogLevel("ERROR")
    yield s
    s.stop()


def _df(spark, rows, cols):
    # pandas + Arrow orqali: Python worker jarayonlari kerak emas (Windows'da ham barqaror)
    return spark.createDataFrame(pd.DataFrame(rows, columns=cols))


def _contracts(spark, rows):
    cols = ["contract_id", "org_inn", "supplier_inn", "product_code", "unit_price", "amount", "contract_date"]
    return _df(spark, rows, cols)


def test_split_purchase_detects_cluster_but_not_spread_out(spark):
    lim = C.DIRECT_PURCHASE_LIMIT_UZS
    df = _contracts(spark, [
        # 3 ta shartnoma 10 kun ichida, har biri limitdan kichik, jami limitdan katta -> belgilanadi
        (1, "o1", "s1", "p", 1.0, lim * 0.9, date(2025, 3, 1)),
        (2, "o1", "s1", "p", 1.0, lim * 0.9, date(2025, 3, 5)),
        (3, "o1", "s1", "p", 1.0, lim * 0.9, date(2025, 3, 10)),
        # bir-biridan uzoq sanalar -> belgilanmaydi
        (4, "o2", "s1", "p", 1.0, lim * 0.9, date(2025, 1, 1)),
        (5, "o2", "s1", "p", 1.0, lim * 0.9, date(2025, 4, 1)),
        (6, "o2", "s1", "p", 1.0, lim * 0.9, date(2025, 7, 1)),
    ])
    ids = {r.contract_id for r in rules.split_purchase(df).collect()}
    assert ids == {1, 2, 3}


def test_price_outlier(spark):
    rows = [(i, "o", "s", "p", 100.0, 100.0, date(2025, 1, 1)) for i in range(1, 20)]
    rows.append((99, "o", "s", "p", 400.0, 400.0, date(2025, 1, 1)))
    ids = {r.contract_id for r in rules.price_outlier(_contracts(spark, rows)).collect()}
    assert ids == {99}


def test_new_supplier_big_contract(spark):
    big = C.NEW_SUPPLIER_MIN_AMOUNT * 2
    contracts = _contracts(spark, [(1, "o", "new", "p", 1.0, big, date(2025, 5, 10)),
                                   (2, "o", "old", "p", 1.0, big, date(2025, 5, 10)),
                                   (3, "o", "new", "p", 1.0, 1000.0, date(2025, 5, 10))])
    suppliers = _df(spark, [("new", date(2025, 5, 1)), ("old", date(2019, 1, 1))],
                    ["supplier_inn", "registered_date"])
    assert {r.contract_id for r in rules.new_supplier_big_contract(contracts, suppliers).collect()} == {1}


def test_duplicate_payment(spark):
    pay = _df(spark, [
        (1, 10, "s", 500.0, date(2025, 2, 1)),
        (2, 10, "s", 500.0, date(2025, 2, 2)),   # 1 kundan keyin aynan shu summa -> dublikat
        (3, 11, "s", 500.0, date(2025, 2, 1)),
        (4, 11, "s", 500.0, date(2025, 6, 1)),   # oylar o'tib - oddiy bo'lib to'lash
    ], ["payment_id", "contract_id", "supplier_inn", "amount", "pay_date"])
    assert {r.payment_id for r in rules.duplicate_payment(pay).collect()} == {2}


def test_supplier_concentration(spark):
    rows = [(i, "o1", "s1", "p", 1.0, 1000.0, date(2025, 1, 1)) for i in range(60)]
    rows += [(100 + i, "o1", f"x{i}", "p", 1.0, 1000.0, date(2025, 1, 1)) for i in range(40)]
    rows += [(200 + i, "o2", f"y{i}", "p", 1.0, 1000.0, date(2025, 1, 1)) for i in range(100)]
    res = rules.supplier_concentration(_contracts(spark, rows)).collect()
    assert [(r.org_inn, r.supplier_inn) for r in res] == [("o1", "s1")]
