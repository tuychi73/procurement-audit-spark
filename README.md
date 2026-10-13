# procurement-audit-spark — davlat xaridlarida xavf belgilarini aniqlash (PySpark + ML)

**5 milliondan ortiq** shartnoma va to'lovni Apache Spark'da tahlil qilib, davlat auditida
qo'llaniladigan xavf belgilarini (red flags) avtomatik topadigan, har bir shartnoma va tashkilotga
**risk bali** beradigan hamda qoidalarga tushmagan g'ayrioddiy holatlarni **Isolation Forest** (ML)
bilan aniqlaydigan loyiha.

## Qoidalar

| Qoida | Mantiq | Spark texnikasi |
|---|---|---|
| **Xaridni bo'lib-bo'lib qilish** | Bir tashkilot–firma–mahsulot bo'yicha ±30 kun ichida har biri limitdan kichik, jami limitdan katta ≥3 shartnoma | `Window.rangeBetween` (vaqt oynasi) |
| **Narxning keskin oshirilishi** | Birlik narxi mahsulot medianasidan 2.5 barobardan yuqori | `percentile_approx` + `broadcast` join |
| **Yangi firma – katta shartnoma** | Ro'yxatdan o'tganiga 60 kun bo'lmagan firma bilan ≥500 mln so'mlik shartnoma | `datediff`, broadcast join |
| **Ikki marta to'lov** | Bir shartnoma bo'yicha aynan shu summa 3 kun ichida qayta to'langan | `lag` window |
| **Yetkazib beruvchiga bog'lanib qolish** | Tashkilot xarajatida bitta firmaning ulushi g'ayritabiiy yuqori | ikki bosqichli agregatsiya + `row_number` |
| **Dam olish kunidagi shartnoma** | Kuchsiz signal — faqat boshqa belgilar bilan birga ballga ta'sir qiladi | `dayofweek` |

Python UDF ishlatilmagan — barcha mantiq Spark'ning ichki funksiyalarida, shuning uchun klasterda ham chiziqli masshtablanadi.

**ML qismi:** har bir tashkilot uchun 8 ta belgi (shartnomalar soni, o'rtacha summa, to'g'ridan-to'g'ri xarid ulushi,
dam olish kuni ulushi, dekabr ulushi, top firma ulushi, firmalar xilma-xilligi, belgilangan summa ulushi) →
`RobustScaler` → `IsolationForest`. Yakuniy tashkilot bali = qoidalar (60%) + ML (40%).

## Natija (haqiqiy run, lokal kompyuter)

```
Tayyor: 5,012,762 shartnoma 381.6 s da tahlil qilindi.
Jiddiy xavfli shartnomalar: 11,928
```

Sintetik ma'lumotga ataylab yashirilgan holatlar bo'yicha qoidalar sifati:

| Qoida | Yashirilgan | Topilgan | To'g'ri | Precision | Recall |
|---|---:|---:|---:|---:|---:|
| SPLIT_PURCHASE | 1 613 | 4 226 | 1 613 | 0.382* | 1.000 |
| PRICE_OUTLIER | 5 000 | 4 978 | 4 978 | 1.000 | 0.996 |
| NEW_SUPPLIER_BIG_CONTRACT | 223 | 223 | 223 | 1.000 | 1.000 |
| DUPLICATE_PAYMENT | 2 506 | 2 506 | 2 506 | 1.000 | 1.000 |
| SUPPLIER_CONCENTRATION (tashkilot) | 25 | 25 | 25 | 1.000 | 1.000 |
| ML Isolation Forest (tashkilot) | 25 | 40 | 25 | 0.625 | 1.000 |

\* "Ortiqcha" topilgan 2 613 ta shartnomadan **2 611 tasi** bitta firmaga bog'lanib qolgan tashkilotlarga tegishli:
ular bir firmadan bir xil mahsulotni qayta-qayta, limitdan kichik summalarda xarid qilgan — bu ham aynan
"bo'lib xarid qilish" belgisi. Ya'ni qoida xato qilmagan, ikki xil qoidabuzarlik bir-birini kesib o'tgan.
Narx qoidasida o'tkazib yuborilgan 22 ta holat — narxi medianadan atigi 2.15–2.5 barobar yuqori bo'lganlar (chegara: 2.5 dan katta).

To'liq hisobot: [`output/report.md`](output/report.md), natija jadvallari: `output/*.csv`.

## Ishga tushirish

Talablar: Python 3.10+, Java 17 yoki 21.

```bat
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
python -m audit generate --rows 5000000   # ~230 MB Parquet, ~20 s
python -m audit run                       # Spark tahlili + output/report.md
pytest                                    # qoidalar uchun unit testlar
```

**Windows haqida:** Spark lokal fayllarni o'qishi uchun odatda `winutils.exe`/`hadoop.dll` kerak.
`HADOOP_HOME` o'rnatilmagan bo'lsa, `job._read()` Parquet'ni pyarrow bilan o'qib, Arrow orqali Spark'ga uzatadi.
Linux / klasterda esa to'g'ridan-to'g'ri `spark.read.parquet` ishlaydi. Foydalanuvchi papkasi nomida kirill
harfi bo'lsa ham ishlashi uchun Spark vaqtinchalik fayllari loyiha ichidagi `.tmp/` ga yo'naltirilgan.

## Tuzilma

```
audit/generate.py   sintetik ma'lumot + yashirilgan anomaliyalar (truth/)
audit/rules.py      PySpark qoidalari
audit/job.py        orkestratsiya, risk ballari, baholash (precision/recall)
audit/ml.py         Isolation Forest
audit/report.py     Markdown hisobot
audit/config.py     chegaralar va vaznlar (shartli qiymatlar)
tests/              har bir qoida uchun unit test
```

> Barcha ma'lumotlar sintetik. Chegaralar (limit, 2.5×, 60 kun va h.k.) shartli — real auditda me'yoriy hujjatlar asosida belgilanadi.
