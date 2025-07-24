#!/usr/bin/env python3

from pyspark.sql import SparkSession
from pyspark.sql.types import StructType
from pyspark.sql.functions import col
from datetime import datetime, timedelta
import sys

# ====== [1] 입력 파라미터 확인 ======
if len(sys.argv) == 2:
    try:
        target_hour = sys.argv[1]  # 예: 2025-07-24-13
        year, month, day, hour = map(int, target_hour.split("-"))
    except:
        print("입력 형식 오류: YYYY-MM-DD-HH 형식으로 입력해주세요.")
        sys.exit(1)
else:
    now = datetime.now()
    one_hour_ago = now - timedelta(hours=1)
    year = one_hour_ago.year
    month = one_hour_ago.month
    day = one_hour_ago.day
    hour = one_hour_ago.hour
    target_hour = one_hour_ago.strftime("%Y-%m-%d-%H")
    print(f"[INFO] 파라미터가 없어 기본값 사용: {target_hour}")

# ====== [2] SparkSession 생성 ======
spark = SparkSession.builder \
    .appName("Read Processed FMS Data") \
    .master("local[1]") \
    .config("spark.executor.cores", "1") \
    .config("spark.executor.memory", "1g") \
    .config("spark.driver.memory", "1g") \
    .config("spark.sql.shuffle.partitions", "1") \
    .config("spark.default.parallelism", "1") \
    .getOrCreate()

spark.sparkContext.setLogLevel("ERROR")

# ====== [3] 데이터 경로 설정 ======
paths = {
    "NORMAL": "hdfs://s1:9000/fms/processed/normal/",
    "ALERT": "hdfs://s1:9000/fms/processed/alert/",
    "CHECK": "hdfs://s1:9000/fms/processed/check/",
}

empty_schema = StructType([])

# ====== [4] 안전하게 Parquet 읽기 ======
def safe_read_parquet(path, label):
    print(f"\n[INFO] 시도하는 경로: {path}")
    try:
        df = spark.read.parquet(path)
        df_filtered = df.filter(
            (col("year") == year) &
            (col("month") == month) &
            (col("day") == day) &
            (col("hour") == hour)
        )
        count = df_filtered.count()
        if count == 0:
            print(f"[FAIL] {label} 데이터 로드 실패 (총 0건)")
        else:
            print(f"[SUCCESS] {label} 데이터 로드 완료 (총 {count}건)")
            df_filtered.printSchema()
            df_filtered.orderBy("year", "month", "day", "hour", "minute").show(truncate=False)
        return df_filtered
    except Exception as e:
        print(f"[FAIL] {label} 데이터 로드 실패: {e}")
        return spark.createDataFrame([], empty_schema)

# ====== [5] 각 상태별 데이터 출력 ======
for label, path in paths.items():
    safe_read_parquet(path, label)

# ====== [6] 종료 ======
spark.stop()
