# Davlat xaridlari: avtomatlashtirilgan audit hisoboti

- Tahlil qilingan shartnomalar: **5 012 762**
- Jiddiy xavf belgisi bor shartnomalar: **11 928** (jami summa 9 204 987 539 900 so'm)
- Shubhali takroriy to'lovlar: **2 506**
- Hisoblash vaqti: 381.6 s

## Qoidalar bo'yicha topilmalar

| Qoida | Topildi |
|---|---:|
| Dam olish kunidagi shartnoma | 1 427 039 |
| Narxning keskin oshirilishi | 4 978 |
| Xaridni bo'lib-bo'lib qilish | 4 226 |
| Ikki marta to'lov | 2 506 |
| Yangi firma bilan katta shartnoma | 223 |

## Eng xavfli 10 ta shartnoma

| ID | Tashkilot INN | Yetkazib beruvchi INN | Summa (so'm) | Ball | Belgilar |
|---|---|---|---:|---:|---|
| 5001346 | 200000753 | 300006981 | 80 014 000 | 75 | DUPLICATE_PAYMENT, SPLIT_PURCHASE, WEEKEND_CONTRACT |
| 3544542 | 200001220 | 300000354 | 6 060 604 | 75 | DUPLICATE_PAYMENT, PRICE_OUTLIER |
| 2502834 | 200000712 | 300000979 | 960 141 | 75 | DUPLICATE_PAYMENT, PRICE_OUTLIER |
| 3262461 | 200000246 | 300010519 | 741 859 | 75 | DUPLICATE_PAYMENT, PRICE_OUTLIER |
| 5001774 | 200001429 | 390000043 | 1 772 447 702 | 65 | DUPLICATE_PAYMENT, NEW_SUPPLIER_BIG_CONTRACT |
| 2635868 | 200001774 | 300014416 | 16 474 113 725 | 45 | DUPLICATE_PAYMENT, WEEKEND_CONTRACT |
| 285855 | 200000834 | 300008151 | 15 078 280 455 | 45 | DUPLICATE_PAYMENT, WEEKEND_CONTRACT |
| 2388150 | 200000131 | 300006714 | 15 050 783 995 | 45 | DUPLICATE_PAYMENT, WEEKEND_CONTRACT |
| 3839950 | 200001386 | 300011943 | 14 349 292 870 | 45 | DUPLICATE_PAYMENT, WEEKEND_CONTRACT |
| 4283020 | 200000028 | 300011669 | 12 344 331 205 | 45 | DUPLICATE_PAYMENT, WEEKEND_CONTRACT |

## Birinchi navbatda tekshirilishi kerak bo'lgan 10 ta tashkilot

| INN | Hudud | Shartnomalar | Top yetkazib beruvchi ulushi | Belgilangan summa ulushi | ML ball | Yakuniy ball |
|---|---|---:|---:|---:|---:|---:|
| 200000819 | Surxondaryo | 2977 | 15.9% | 2.8% | 94.4 | **62.3** |
| 200001652 | Navoiy | 2958 | 20.6% | 3.1% | 93.2 | **62.2** |
| 200001413 | Toshkent vil. | 3047 | 21.0% | 0.4% | 100.0 | **60.6** |
| 200000008 | Jizzax | 3095 | 19.4% | 0.4% | 98.8 | **60.2** |
| 200000191 | Toshkent sh. | 2924 | 13.6% | 2.8% | 87.7 | **59.6** |
| 200001049 | Qoraqalpog'iston | 3100 | 18.1% | 0.5% | 95.9 | **59.2** |
| 200001913 | Samarqand | 2964 | 21.0% | 0.5% | 95.4 | **59.0** |
| 200000292 | Toshkent sh. | 2893 | 13.6% | 2.8% | 86.2 | **58.9** |
| 200001864 | Samarqand | 2950 | 18.4% | 0.4% | 95.7 | **58.9** |
| 200000667 | Surxondaryo | 3030 | 14.6% | 0.5% | 94.1 | **58.4** |

## Qoidalar sifati (sintetik ma'lumotdagi yashirilgan holatlar bo'yicha)

| Qoida | Haqiqiy | Topilgan | To'g'ri topilgan | Precision | Recall |
|---|---:|---:|---:|---:|---:|
| SPLIT_PURCHASE | 1613 | 4226 | 1613 | 0.382 | 1.0 |
| PRICE_OUTLIER | 5000 | 4978 | 4978 | 1.0 | 0.996 |
| NEW_SUPPLIER_BIG_CONTRACT | 223 | 223 | 223 | 1.0 | 1.0 |
| DUPLICATE_PAYMENT | 2506 | 2506 | 2506 | 1.0 | 1.0 |
| SUPPLIER_CONCENTRATION | 25 | 25 | 25 | 1.0 | 1.0 |
| ML_ISOLATION_FOREST (conc.) | 25 | 40 | 25 | 0.625 | 1.0 |
