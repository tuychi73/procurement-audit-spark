"""Auditor uchun qisqa Markdown hisobot."""
from __future__ import annotations

from pathlib import Path

from audit.job import JobResult

RULE_NAMES = {
    "SPLIT_PURCHASE": "Xaridni bo'lib-bo'lib qilish",
    "PRICE_OUTLIER": "Narxning keskin oshirilishi",
    "NEW_SUPPLIER_BIG_CONTRACT": "Yangi firma bilan katta shartnoma",
    "DUPLICATE_PAYMENT": "Ikki marta to'lov",
    "WEEKEND_CONTRACT": "Dam olish kunidagi shartnoma",
}


def _fmt(x: float) -> str:
    return f"{x:,.0f}".replace(",", " ")


def write_report(res: JobResult, path: Path) -> None:
    fc, orgs = res.flagged_contracts, res.org_risk
    lines = [
        "# Davlat xaridlari: avtomatlashtirilgan audit hisoboti\n",
        f"- Tahlil qilingan shartnomalar: **{_fmt(res.contracts_total)}**",
        f"- Jiddiy xavf belgisi bor shartnomalar: **{_fmt(len(fc))}** "
        f"(jami summa {_fmt(fc['amount'].sum())} so'm)",
        f"- Shubhali takroriy to'lovlar: **{_fmt(len(res.flagged_payments))}**",
        f"- Hisoblash vaqti: {res.seconds} s\n",
        "## Qoidalar bo'yicha topilmalar\n",
        "| Qoida | Topildi |", "|---|---:|",
        *[f"| {RULE_NAMES.get(k, k)} | {_fmt(v)} |" for k, v in sorted(res.flags_by_rule.items(), key=lambda kv: -kv[1])],
        "\n## Eng xavfli 10 ta shartnoma\n",
        "| ID | Tashkilot INN | Yetkazib beruvchi INN | Summa (so'm) | Ball | Belgilar |", "|---|---|---|---:|---:|---|",
        *[f"| {r.contract_id} | {r.org_inn} | {r.supplier_inn} | {_fmt(r.amount)} | {r.risk_score} | {r.rules} |"
          for r in fc.head(10).itertuples()],
        "\n## Birinchi navbatda tekshirilishi kerak bo'lgan 10 ta tashkilot\n",
        "| INN | Hudud | Shartnomalar | Top yetkazib beruvchi ulushi | Belgilangan summa ulushi | ML ball | Yakuniy ball |",
        "|---|---|---:|---:|---:|---:|---:|",
        *[f"| {r.org_inn} | {r.region} | {r.n_contracts} | {r.top_supplier_share:.1%} | {r.flagged_share:.1%} "
          f"| {r.ml_anomaly_score} | **{r.org_risk_score}** |" for r in orgs.head(10).itertuples()],
    ]
    if res.evaluation is not None:
        lines += ["\n## Qoidalar sifati (sintetik ma'lumotdagi yashirilgan holatlar bo'yicha)\n",
                  "| Qoida | Haqiqiy | Topilgan | To'g'ri topilgan | Precision | Recall |", "|---|---:|---:|---:|---:|---:|",
                  *[f"| {r.rule} | {r.truth} | {r.flagged} | {r.true_positive} | {r.precision} | {r.recall} |"
                    for r in res.evaluation.itertuples()]]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
