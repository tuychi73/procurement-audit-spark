"""Tashkilotlar xulq-atvoridagi g'ayrioddiylikni Isolation Forest bilan aniqlash.

Qoidalar "ma'lum" sxemalarni topadi; ML esa qoidaga tushmagan, lekin
boshqa tashkilotlardan keskin farq qiladigan holatlarni auditor e'tiboriga chiqaradi.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import RobustScaler

FEATURES = ["log_n_contracts", "log_avg_amount", "direct_share", "weekend_share", "december_share",
            "top_supplier_share", "supplier_diversity", "flagged_share"]


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    f = pd.DataFrame(index=df.index)
    f["log_n_contracts"] = np.log1p(df["n_contracts"])
    f["log_avg_amount"] = np.log1p(df["avg_amount"])
    f["direct_share"] = df["direct_share"]
    f["weekend_share"] = df["weekend_share"]
    f["december_share"] = df["december_share"]
    f["top_supplier_share"] = df["top_supplier_share"]
    f["supplier_diversity"] = df["n_suppliers"] / df["n_contracts"]
    f["flagged_share"] = df["flagged_amount"] / df["total_amount"]
    return f[FEATURES]


def score_organizations(df: pd.DataFrame, contamination: float = 0.02, seed: int = 0) -> pd.DataFrame:
    out = df.copy()
    x = RobustScaler().fit_transform(build_features(out))
    model = IsolationForest(n_estimators=300, contamination=contamination, random_state=seed).fit(x)
    # score_samples: kichikroq = g'ayrioddiyroq. 0..100 shkalaga o'tkazamiz.
    raw = -model.score_samples(x)
    out["ml_anomaly_score"] = np.round(100 * (raw - raw.min()) / (raw.max() - raw.min() + 1e-12), 1)
    out["ml_anomaly"] = model.predict(x) == -1

    out["flagged_share"] = out["flagged_amount"] / out["total_amount"]
    # Yakuniy ball: qoidalar (60%) + ML (40%). Auditorlar ro'yxatni shu bo'yicha saralaydi.
    rule_part = np.clip(out["flagged_share"] * 4, 0, 1) * 40 + out["concentration_flag"].astype(int) * 20
    out["org_risk_score"] = np.round(rule_part + out["ml_anomaly_score"] * 0.4, 1)
    cols = ["org_inn", "region", "n_contracts", "total_amount", "top_supplier_share", "direct_share",
            "flagged_contracts", "flagged_share", "concentration_flag", "ml_anomaly", "ml_anomaly_score", "org_risk_score"]
    return out[cols].sort_values("org_risk_score", ascending=False).reset_index(drop=True)
