"""Audit qoidalari parametrlari. Qiymatlar shartli - real auditda me'yoriy hujjatlar asosida belgilanadi."""

YEAR = 2025

# To'g'ridan-to'g'ri xarid uchun shartli limit (so'm)
DIRECT_PURCHASE_LIMIT_UZS = 100_000_000
SPLIT_WINDOW_DAYS = 30           # +- shuncha kun ichidagi xaridlar bitta guruh hisoblanadi
SPLIT_MIN_CONTRACTS = 3

PRICE_OUTLIER_RATIO = 2.5        # narx shu mahsulot medianasidan necha marta yuqori bo'lsa

NEW_SUPPLIER_DAYS = 60           # firma ro'yxatdan o'tganiga shuncha kun bo'lmagan bo'lsa
NEW_SUPPLIER_MIN_AMOUNT = 500_000_000

DUPLICATE_PAYMENT_DAYS = 3

CONCENTRATION_SHARE = 0.05       # bitta yetkazib beruvchining tashkilot xarajatidagi ulushi
CONCENTRATION_MIN_CONTRACTS = 50

# Shartnoma darajasidagi risk ballari
WEIGHTS = {
    "SPLIT_PURCHASE": 30,
    "PRICE_OUTLIER": 35,
    "NEW_SUPPLIER_BIG_CONTRACT": 25,
    "DUPLICATE_PAYMENT": 40,
    "WEEKEND_CONTRACT": 5,
}
