"""Davlat xaridlaridagi xavf belgilarini (red flags) aniqlovchi PySpark qoidalari.

Har bir shartnoma darajasidagi qoida (contract_id, rule, detail) ustunli DataFrame qaytaradi.
Python UDF ishlatilmaydi - hammasi Spark SQL funksiyalari va window'lar orqali, shuning uchun klasterda ham tez ishlaydi.
"""
from __future__ import annotations

from pyspark.sql import DataFrame, Window
from pyspark.sql import functions as F

from audit import config as C

SECONDS_IN_DAY = 86_400


def _flag(df: DataFrame, rule: str, detail) -> DataFrame:
    return df.select("contract_id", F.lit(rule).alias("rule"), detail.alias("detail"))


def split_purchase(contracts: DataFrame) -> DataFrame:
    """Limitdan qochish uchun bitta xaridni bir necha kichik shartnomaga bo'lish.

    Bir tashkilot - bir yetkazib beruvchi - bir mahsulot bo'yicha +-N kun ichida
    har biri limitdan kichik, lekin jami limitdan oshadigan >= K ta shartnoma.
    """
    small = (contracts.where(F.col("amount") < C.DIRECT_PURCHASE_LIMIT_UZS)
                      .withColumn("ts", F.col("contract_date").cast("timestamp").cast("long")))
    w = (Window.partitionBy("org_inn", "supplier_inn", "product_code").orderBy("ts")
               .rangeBetween(-C.SPLIT_WINDOW_DAYS * SECONDS_IN_DAY, C.SPLIT_WINDOW_DAYS * SECONDS_IN_DAY))
    grouped = (small.withColumn("win_sum", F.sum("amount").over(w))
                    .withColumn("win_cnt", F.count("*").over(w)))
    hits = grouped.where((F.col("win_sum") >= C.DIRECT_PURCHASE_LIMIT_UZS) & (F.col("win_cnt") >= C.SPLIT_MIN_CONTRACTS))
    return _flag(hits, "SPLIT_PURCHASE",
                 F.format_string("%d ta shartnoma, jami %,.0f so'm", F.col("win_cnt"), F.col("win_sum")))


def price_outlier(contracts: DataFrame) -> DataFrame:
    """Birlik narxi shu mahsulotning mamlakat bo'yicha medianasidan keskin yuqori."""
    med = contracts.groupBy("product_code").agg(F.percentile_approx("unit_price", 0.5, 10_000).alias("median_price"))
    hits = (contracts.join(F.broadcast(med), "product_code")
                     .withColumn("ratio", F.col("unit_price") / F.col("median_price"))
                     .where(F.col("ratio") > C.PRICE_OUTLIER_RATIO))
    return _flag(hits, "PRICE_OUTLIER", F.format_string("narx medianadan %.1f barobar yuqori", F.col("ratio")))


def new_supplier_big_contract(contracts: DataFrame, suppliers: DataFrame) -> DataFrame:
    """Yaqinda ro'yxatdan o'tgan firma bilan katta summadagi shartnoma."""
    hits = (contracts.join(F.broadcast(suppliers), "supplier_inn")
                     .withColumn("age_days", F.datediff("contract_date", "registered_date"))
                     .where((F.col("age_days").between(0, C.NEW_SUPPLIER_DAYS))
                            & (F.col("amount") >= C.NEW_SUPPLIER_MIN_AMOUNT)))
    return _flag(hits, "NEW_SUPPLIER_BIG_CONTRACT",
                 F.format_string("firma %d kunlik, summa %,.0f so'm", F.col("age_days"), F.col("amount")))


def duplicate_payment(payments: DataFrame) -> DataFrame:
    """Bitta shartnoma bo'yicha bir xil summa qisqa vaqt ichida ikki marta to'langan.

    Bu qoida to'lov darajasida ishlaydi: (payment_id, contract_id, rule, detail) qaytaradi.
    """
    w = Window.partitionBy("contract_id", "supplier_inn", "amount").orderBy("pay_date", "payment_id")
    hits = (payments.withColumn("prev_date", F.lag("pay_date").over(w))
                    .withColumn("gap", F.datediff("pay_date", "prev_date"))
                    .where(F.col("gap").between(0, C.DUPLICATE_PAYMENT_DAYS)))
    return hits.select("payment_id", "contract_id", F.lit("DUPLICATE_PAYMENT").alias("rule"),
                       F.format_string("%,.0f so'm %d kun ichida qayta to'langan", F.col("amount"), F.col("gap")).alias("detail"))


def weekend_contract(contracts: DataFrame) -> DataFrame:
    """Dam olish kunida tuzilgan shartnoma (kuchsiz signal, boshqa belgilar bilan birga qaraladi)."""
    hits = contracts.where(F.dayofweek("contract_date").isin(1, 7))   # 1 = yakshanba, 7 = shanba
    return _flag(hits, "WEEKEND_CONTRACT", F.date_format("contract_date", "EEEE"))


def supplier_concentration(contracts: DataFrame) -> DataFrame:
    """Tashkilot darajasidagi qoida: xaridlarning g'ayritabiiy katta qismi bitta firmaga ketgan."""
    by_pair = contracts.groupBy("org_inn", "supplier_inn").agg(F.sum("amount").alias("spend"), F.count("*").alias("n"))
    w = Window.partitionBy("org_inn")
    shares = (by_pair.withColumn("share", F.col("spend") / F.sum("spend").over(w))
                     .withColumn("rnk", F.row_number().over(w.orderBy(F.desc("spend")))))
    return (shares.where((F.col("rnk") == 1) & (F.col("share") > C.CONCENTRATION_SHARE)
                         & (F.col("n") >= C.CONCENTRATION_MIN_CONTRACTS))
                  .select("org_inn", "supplier_inn", "share", "n", "spend"))
