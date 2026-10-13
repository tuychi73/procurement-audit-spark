"""Asosiy Spark job: qoidalar -> shartnoma risk bali -> tashkilot risk bali (qoidalar + ML)."""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from audit import config as C
from audit import ml, rules

log = logging.getLogger(__name__)
MAJOR_RISK = 25   # faqat jiddiy belgisi bor shartnomalar natijaga yoziladi


@dataclass
class JobResult:
    contracts_total: int
    flags_by_rule: dict
    flagged_contracts: pd.DataFrame
    flagged_payments: pd.DataFrame
    org_risk: pd.DataFrame
    evaluation: pd.DataFrame | None
    seconds: float


def _read(spark: SparkSession, data_dir: Path, name: str) -> DataFrame:
    path = data_dir / name
    if os.name != "nt" or os.getenv("HADOOP_HOME"):
        return spark.read.parquet(str(path))
    # Windows'da winutils/hadoop.dll bo'lmasa Spark lokal fayllarni o'qiy olmaydi:
    # fayl pyarrow bilan o'qilib, Arrow formatida Spark'ga uzatiladi (Python worker'larsiz).
    return spark.createDataFrame(pq.read_table(path))


def _save(pdf: pd.DataFrame, out_dir: Path, name: str) -> None:
    """Natijalar kichik (minglab qator), shuning uchun pandas orqali yoziladi.
    Klasterda buning o'rniga df.write.partitionBy(...).parquet(...) ishlatiladi
    (Windows'da Spark'ning o'zi yozishi uchun winutils.exe kerak bo'ladi)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf.to_parquet(out_dir / f"{name}.parquet", index=False)
    pdf.to_csv(out_dir / f"{name}.csv", index=False, encoding="utf-8-sig")


def run(spark: SparkSession, data_dir: Path, out_dir: Path | None = None) -> JobResult:
    t0 = time.time()
    data_dir = Path(data_dir)
    contracts = _read(spark, data_dir, "contracts").cache()
    suppliers = _read(spark, data_dir, "suppliers")
    payments = _read(spark, data_dir, "payments")
    orgs = _read(spark, data_dir, "organizations")
    total = contracts.count()
    log.info("contracts=%s", total)

    # 1. Shartnoma darajasidagi qoidalar
    pay_flags = rules.duplicate_payment(payments).cache()
    flags = (rules.split_purchase(contracts)
             .unionByName(rules.price_outlier(contracts))
             .unionByName(rules.new_supplier_big_contract(contracts, suppliers))
             .unionByName(rules.weekend_contract(contracts))
             .unionByName(pay_flags.select("contract_id", "rule", "detail"))
             .dropDuplicates(["contract_id", "rule"])
             .cache())
    flags_by_rule = {r["rule"]: r["count"] for r in flags.groupBy("rule").count().collect()}

    weights = F.create_map(*[x for k, v in C.WEIGHTS.items() for x in (F.lit(k), F.lit(v))])
    contract_risk = (flags.groupBy("contract_id")
                     .agg(F.sum(weights[F.col("rule")]).alias("risk_score"),
                          F.array_join(F.array_sort(F.collect_set("rule")), ", ").alias("rules"),
                          F.array_join(F.collect_list("detail"), " | ").alias("details")))

    # 2. Tashkilot darajasidagi belgilar (ML uchun feature'lar)
    conc = rules.supplier_concentration(contracts)
    top_share = (contracts.groupBy("org_inn", "supplier_inn").agg(F.sum("amount").alias("s"))
                 .groupBy("org_inn").agg((F.max("s") / F.sum("s")).alias("top_supplier_share"),
                                         F.count("*").alias("n_suppliers")))
    flagged_amount = (contracts.join(contract_risk.where(F.col("risk_score") >= MAJOR_RISK), "contract_id")
                      .groupBy("org_inn").agg(F.sum("amount").alias("flagged_amount"),
                                              F.count("*").alias("flagged_contracts")))
    features = (contracts.groupBy("org_inn").agg(
                    F.count("*").alias("n_contracts"),
                    F.sum("amount").alias("total_amount"),
                    F.avg("amount").alias("avg_amount"),
                    F.avg((F.col("method") == "direct").cast("int")).alias("direct_share"),
                    F.avg(F.dayofweek("contract_date").isin(1, 7).cast("int")).alias("weekend_share"),
                    F.avg(F.month("contract_date").isin(12).cast("int")).alias("december_share"))
                .join(top_share, "org_inn")
                .join(flagged_amount, "org_inn", "left")
                .join(orgs, "org_inn", "left")
                .join(conc.select("org_inn", F.lit(True).alias("concentration_flag")), "org_inn", "left")
                .fillna({"flagged_amount": 0.0, "flagged_contracts": 0, "concentration_flag": False}))
    org_pdf = features.toPandas()
    org_risk = ml.score_organizations(org_pdf)

    # 3. Natijalar: faqat jiddiy xavfli shartnomalar (kichik hajm) driver'ga olinadi
    flagged_contracts = (contract_risk.where(F.col("risk_score") >= MAJOR_RISK)
                         .join(contracts, "contract_id")
                         .select("contract_id", "org_inn", "supplier_inn", "product_code", "contract_date",
                                 "method", "amount", "risk_score", "rules", "details")
                         .orderBy(F.desc("risk_score"), F.desc("amount"))
                         .toPandas())
    flagged_payments = pay_flags.toPandas()

    evaluation = _evaluate(spark, data_dir, flags, pay_flags, org_risk)

    if out_dir is not None:
        _save(flagged_contracts, Path(out_dir), "flagged_contracts")
        _save(flagged_payments, Path(out_dir), "flagged_payments")
        _save(org_risk, Path(out_dir), "org_risk")
        if evaluation is not None:
            _save(evaluation, Path(out_dir), "evaluation")

    contracts.unpersist(); flags.unpersist(); pay_flags.unpersist()
    return JobResult(total, flags_by_rule, flagged_contracts, flagged_payments, org_risk, evaluation,
                     round(time.time() - t0, 1))


def _evaluate(spark, data_dir: Path, flags: DataFrame, pay_flags: DataFrame, org_risk: pd.DataFrame):
    """Sintetik ma'lumotga yashirilgan anomaliyalar bo'yicha precision / recall."""
    truth_dir = data_dir / "truth"
    if not truth_dir.exists():
        return None
    rows = []
    truth_c = _read(spark, data_dir, "truth/contracts.parquet")
    for rule in ["SPLIT_PURCHASE", "PRICE_OUTLIER", "NEW_SUPPLIER_BIG_CONTRACT"]:
        t = truth_c.where(F.col("anomaly") == rule).select("contract_id")
        f = flags.where(F.col("rule") == rule).select("contract_id")
        rows.append(_metrics(rule, t.count(), f.count(), t.join(f, "contract_id").count()))

    t = _read(spark, data_dir, "truth/payments.parquet").select("payment_id")
    f = pay_flags.select("payment_id")
    rows.append(_metrics("DUPLICATE_PAYMENT", t.count(), f.count(), t.join(f, "payment_id").count()))

    t_orgs = set(pd.read_parquet(truth_dir / "orgs.parquet")["org_inn"])
    f_orgs = set(org_risk.loc[org_risk["concentration_flag"], "org_inn"])
    rows.append(_metrics("SUPPLIER_CONCENTRATION", len(t_orgs), len(f_orgs), len(t_orgs & f_orgs)))
    ml_orgs = set(org_risk.loc[org_risk["ml_anomaly"], "org_inn"])
    rows.append(_metrics("ML_ISOLATION_FOREST (conc.)", len(t_orgs), len(ml_orgs), len(t_orgs & ml_orgs)))
    return pd.DataFrame(rows)


def _metrics(rule: str, truth: int, flagged: int, hit: int) -> dict:
    return {"rule": rule, "truth": truth, "flagged": flagged, "true_positive": hit,
            "precision": round(hit / flagged, 3) if flagged else None,
            "recall": round(hit / truth, 3) if truth else None}
