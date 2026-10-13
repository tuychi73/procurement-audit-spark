from __future__ import annotations

import os
import sys
from pathlib import Path

from pyspark.sql import SparkSession

ROOT = Path(__file__).resolve().parent.parent


def _ascii_tmp_dir() -> str:
    """Windows'da foydalanuvchi papkasi nomida lotin bo'lmagan harf bo'lsa (masalan C:\\Users\\а),
    Java vaqtinchalik fayl/socket yarata olmaydi. Shuning uchun loyiha ichidagi ASCII papka ishlatiladi."""
    tmp = Path(os.getenv("SPARK_TMP_DIR", ROOT / ".tmp"))
    tmp.mkdir(parents=True, exist_ok=True)
    return tmp.as_posix()


def get_spark(app_name: str = "procurement-audit", shuffle_partitions: int = 16) -> SparkSession:
    # Windows'da driver va worker bir xil Python'dan foydalanishi uchun
    os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
    os.environ.setdefault("PYSPARK_DRIVER_PYTHON", sys.executable)
    tmp = _ascii_tmp_dir()
    java_opts = f"-Djava.io.tmpdir={tmp} -Djdk.net.unixdomain.tmpdir={tmp}"
    return (SparkSession.builder
            .appName(app_name)
            .master(os.getenv("SPARK_MASTER", "local[*]"))
            .config("spark.sql.shuffle.partitions", shuffle_partitions)
            .config("spark.sql.adaptive.enabled", "true")
            .config("spark.driver.memory", os.getenv("SPARK_DRIVER_MEMORY", "4g"))
            .config("spark.driver.extraJavaOptions", java_opts)
            .config("spark.executor.extraJavaOptions", java_opts)
            .config("spark.local.dir", tmp)
            .config("spark.sql.session.timeZone", "UTC")
            .config("spark.sql.execution.arrow.pyspark.enabled", "true")
            .config("spark.sql.execution.arrow.pyspark.fallback.enabled", "false")
            .config("spark.ui.showConsoleProgress", "false")
            .getOrCreate())
