"""Katta hajmdagi sintetik davlat xaridlari ma'lumotlarini yaratish (millionlab qator).

Ichiga ma'lum turdagi qoidabuzarliklar ataylab "yashiriladi" va ular alohida
`truth/` papkasiga yoziladi. Shu orqali audit qoidalarining aniqligini
(precision / recall) o'lchash mumkin bo'ladi.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from audit.config import DIRECT_PURCHASE_LIMIT_UZS, YEAR

REGIONS = np.array(["Toshkent sh.", "Toshkent vil.", "Samarqand", "Buxoro", "Farg'ona", "Andijon", "Namangan",
                    "Qashqadaryo", "Surxondaryo", "Xorazm", "Navoiy", "Jizzax", "Sirdaryo", "Qoraqalpog'iston"])
# (mahsulot kodi, bazaviy narx so'mda)
PRODUCTS = np.array([("30.02.11", 9_500_000), ("30.02.12", 2_800_000), ("30.02.15", 3_200_000),
                     ("17.12.14", 55_000), ("31.01.11", 1_900_000), ("31.01.12", 1_400_000),
                     ("28.25.12", 6_700_000), ("19.20.21", 11_000), ("62.01.11", 4_500_000),
                     ("43.21.10", 25_000_000), ("21.20.13", 180_000), ("10.71.11", 7_000)], dtype=object)
QTY_CHOICES = np.array([1, 1, 2, 3, 5, 10, 20, 50, 100, 500])
METHODS = np.array(["tender", "direct", "e-shop"])

N_ORGS, N_SUPPLIERS = 2_000, 15_000
YEAR_START = np.datetime64(f"{YEAR}-01-01")


def _write(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pandas(df, preserve_index=False), path, compression="snappy")


def generate(out_dir: Path, rows: int = 5_000_000, chunk: int = 1_000_000, seed: int = 2025) -> dict:
    out_dir = Path(out_dir)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    rng = np.random.default_rng(seed)

    org_inn = np.arange(200_000_001, 200_000_001 + N_ORGS).astype(str)
    org_region = rng.choice(REGIONS, N_ORGS)
    sup_inn = np.arange(300_000_001, 300_000_001 + N_SUPPLIERS).astype(str)
    sup_reg = YEAR_START - rng.integers(400, 4000, N_SUPPLIERS).astype("timedelta64[D]")
    _write(pd.DataFrame({"org_inn": org_inn, "region": org_region}), out_dir / "organizations" / "part-0.parquet")

    truth_contracts: list[pd.DataFrame] = []
    next_id = 1

    # ---------- 1. Oddiy (normal) shartnomalar ----------
    for part, start in enumerate(range(0, rows, chunk)):
        n = min(chunk, rows - start)
        ids = np.arange(next_id, next_id + n)
        next_id += n
        oi = rng.integers(0, N_ORGS, n)
        prod = rng.integers(0, len(PRODUCTS), n)
        base = PRODUCTS[prod, 1].astype(float)
        qty = rng.choice(QTY_CHOICES, n)
        price = np.round(base * rng.lognormal(0, 0.12, n), 2)
        df = pd.DataFrame({
            "contract_id": ids,
            "org_inn": org_inn[oi],
            "supplier_inn": sup_inn[rng.integers(0, N_SUPPLIERS, n)],
            "product_code": PRODUCTS[prod, 0].astype(str),
            "quantity": qty,
            "unit_price": price,
            "contract_date": YEAR_START + rng.integers(0, 365, n).astype("timedelta64[D]"),
            "method": rng.choice(METHODS, n, p=[0.35, 0.25, 0.40]),
        })
        # Narxni sun'iy oshirish (0.1%)
        idx = rng.choice(n, n // 1000, replace=False)
        df.loc[idx, "unit_price"] = np.round(df.loc[idx, "unit_price"] * rng.uniform(3, 6, len(idx)), 2)
        truth_contracts.append(pd.DataFrame({"contract_id": df.loc[idx, "contract_id"], "anomaly": "PRICE_OUTLIER"}))
        df["amount"] = np.round(df["quantity"] * df["unit_price"], 2)
        _write(df, out_dir / "contracts" / f"part-{part:04d}.parquet")

    # ---------- 2. Xaridni bo'lib-bo'lib qilish (limitdan qochish) ----------
    groups = 400
    rows_split = []
    for g in range(groups):
        o, s = org_inn[rng.integers(N_ORGS)], sup_inn[rng.integers(N_SUPPLIERS)]
        code, base = PRODUCTS[rng.integers(len(PRODUCTS))]
        day0 = int(rng.integers(0, 330))
        k = int(rng.integers(3, 6))
        for j in range(k):
            amount = DIRECT_PURCHASE_LIMIT_UZS * rng.uniform(0.75, 0.97)
            qty = max(1, int(amount // base))
            rows_split.append((next_id, o, s, code, qty, round(amount / qty, 2),
                               YEAR_START + np.timedelta64(day0 + int(rng.integers(0, 25)), "D"), "direct"))
            next_id += 1
    split = pd.DataFrame(rows_split, columns=["contract_id", "org_inn", "supplier_inn", "product_code", "quantity",
                                              "unit_price", "contract_date", "method"])
    split["amount"] = np.round(split["quantity"] * split["unit_price"], 2)
    truth_contracts.append(pd.DataFrame({"contract_id": split["contract_id"], "anomaly": "SPLIT_PURCHASE"}))

    # ---------- 3. Yangi ochilgan firma - katta shartnoma ----------
    n_new = 60
    new_inn = np.arange(390_000_001, 390_000_001 + n_new).astype(str)
    new_reg = np.empty(n_new, dtype="datetime64[D]")
    rows_new = []
    for i in range(n_new):
        reg = YEAR_START + np.timedelta64(int(rng.integers(10, 330)), "D")
        new_reg[i] = reg
        for _ in range(int(rng.integers(2, 6))):
            rows_new.append((next_id, org_inn[rng.integers(N_ORGS)], new_inn[i], "43.21.10", int(rng.integers(30, 80)),
                             round(25_000_000 * rng.uniform(0.9, 1.1), 2),
                             reg + np.timedelta64(int(rng.integers(1, 25)), "D"), "tender"))
            next_id += 1
    newco = pd.DataFrame(rows_new, columns=split.columns[:-1])
    newco["amount"] = np.round(newco["quantity"] * newco["unit_price"], 2)
    truth_contracts.append(pd.DataFrame({"contract_id": newco["contract_id"], "anomaly": "NEW_SUPPLIER_BIG_CONTRACT"}))

    # ---------- 4. Bitta yetkazib beruvchiga bog'lanib qolgan tashkilotlar ----------
    captured = rng.choice(org_inn, 25, replace=False)
    rows_cap = []
    for o in captured:
        s = sup_inn[rng.integers(N_SUPPLIERS)]
        for _ in range(int(rng.integers(300, 600))):
            code, base = PRODUCTS[rng.integers(len(PRODUCTS))]
            qty = int(rng.choice(QTY_CHOICES))
            rows_cap.append((next_id, o, s, code, qty, round(base * rng.lognormal(0, 0.12), 2),
                             YEAR_START + np.timedelta64(int(rng.integers(0, 365)), "D"), "direct"))
            next_id += 1
    cap = pd.DataFrame(rows_cap, columns=split.columns[:-1])
    cap["amount"] = np.round(cap["quantity"] * cap["unit_price"], 2)
    _write(pd.concat([split, newco, cap], ignore_index=True), out_dir / "contracts" / "part-9999.parquet")

    suppliers = pd.DataFrame({"supplier_inn": np.concatenate([sup_inn, new_inn]),
                              "registered_date": np.concatenate([sup_reg, new_reg])})
    _write(suppliers, out_dir / "suppliers" / "part-0.parquet")

    # ---------- 5. To'lovlar va ikki marta to'lash ----------
    pay_parts = sorted((out_dir / "contracts").glob("*.parquet"))
    next_pay = 1
    dup_truth = []
    for i, p in enumerate(pay_parts):
        c = pq.read_table(p, columns=["contract_id", "supplier_inn", "amount", "contract_date"]).to_pandas()
        n = len(c)
        pay = pd.DataFrame({
            "payment_id": np.arange(next_pay, next_pay + n),
            "contract_id": c["contract_id"].to_numpy(),
            "supplier_inn": c["supplier_inn"].to_numpy(),
            "amount": c["amount"].to_numpy(),
            "pay_date": c["contract_date"].to_numpy() + rng.integers(5, 40, n).astype("timedelta64[D]"),
        })
        next_pay += n
        idx = rng.choice(n, max(1, n // 2000), replace=False)
        dup = pay.iloc[idx].copy()
        dup["payment_id"] = np.arange(next_pay, next_pay + len(dup))
        dup["pay_date"] = dup["pay_date"] + rng.integers(0, 4, len(dup)).astype("timedelta64[D]")
        next_pay += len(dup)
        dup_truth.append(pd.DataFrame({"payment_id": dup["payment_id"], "anomaly": "DUPLICATE_PAYMENT"}))
        pay = pd.concat([pay, dup], ignore_index=True)
        pay["invoice_no"] = "INV-" + pay["payment_id"].astype(str)
        _write(pay, out_dir / "payments" / f"part-{i:04d}.parquet")

    _write(pd.concat(truth_contracts, ignore_index=True), out_dir / "truth" / "contracts.parquet")
    _write(pd.concat(dup_truth, ignore_index=True), out_dir / "truth" / "payments.parquet")
    _write(pd.DataFrame({"org_inn": captured, "anomaly": "SUPPLIER_CONCENTRATION"}), out_dir / "truth" / "orgs.parquet")

    return {"contracts": next_id - 1, "payments": next_pay - 1, "path": str(out_dir)}
