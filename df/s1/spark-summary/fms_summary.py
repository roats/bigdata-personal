from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, sum, when, lit
import sys
import os
import json

# ✅ 1. 인자 처리 (YYYYMMDDHH)
if len(sys.argv) != 2:
    print("Usage: spark-submit device_error_summary_optimized.py <YYYYMMDDHH>")
    sys.exit(1)

partition_hour_str = sys.argv[1]

try:
    year = partition_hour_str[0:4]
    month = partition_hour_str[4:6]
    day = partition_hour_str[6:8]
    hour = partition_hour_str[8:10]
except Exception as e:
    print(f"[ERROR] Invalid time format: {e}")
    sys.exit(1)

# ✅ 2. SparkSession 생성 (리소스 최소화 + 부하 방지 설정)
spark = SparkSession.builder \
    .appName("Device Error Summary (Optimized)") \
    .master("local[1]") \
    .config("spark.executor.cores", "1") \
    .config("spark.executor.memory", "1g") \
    .config("spark.driver.memory", "1g") \
    .config("spark.sql.shuffle.partitions", "1") \
    .config("spark.default.parallelism", "1") \
    .config("spark.sql.sources.partitionOverwriteMode", "dynamic") \
    .getOrCreate()

# ✅ 3. 필요한 컬럼만 선택하여 읽기
input_path = f"hdfs://s1:9000/fms/processed/*/year={year}/month={month}/day={day}/hour={hour}"

try:
    df = spark.read.parquet(input_path) \
        .select("DeviceId", "status") \
        .filter(col("DeviceId").isNotNull())
except Exception as e:
    print(f"[INFO] Skipping processing because no data was found: {e}")
    spark.stop()
    sys.exit(0)

# ✅ 4. groupBy를 통한 오류 집계
summary = df.groupBy("DeviceId").agg(
    count("*").alias("total_count"),
    sum(when(col("status") == "ALERT", 1).otherwise(0)).alias("error_count")
).withColumn(
    "error_rate", (col("error_count") / col("total_count")) * 100
).withColumn("year", lit(year)) \
 .withColumn("month", lit(month)) \
 .withColumn("day", lit(day)) \
 .withColumn("hour", lit(hour))

# ✅ 5. 저장- HDFS
output_path = "hdfs://s1:9000/fms/summary/errors"

try:
    summary.write \
        .mode("overwrite") \
        .partitionBy("year", "month", "day", "hour") \
        .parquet(output_path)
    print("[INFO] Summary saved successfully.")
except Exception as e:
    print(f"[ERROR] Failed to write summary: {e}")

# ✅ 6. summary.json 저장 (exporter 용)
try:
    # Pandas로 변환
    pandas_df = summary.toPandas()

    # dict 구조로 재정리
    result = {
        row['DeviceId']: {
            "total_count": int(row['total_count']),
            "error_count": int(row['error_count']),
            "error_rate": round(float(row['error_rate']), 2)
        }
        for _, row in pandas_df.iterrows()
    }

    # 저장 경로 설정
    output_json_path = "/df/exporter/summary.json"
    os.makedirs(os.path.dirname(output_json_path), exist_ok=True)

    with open(output_json_path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"[INFO] summary.json saved to {output_json_path}")

except Exception as e:
    print(f"[ERROR] Failed to write summary.json: {e}")

# ✅ 7. 명시적 종료
spark.stop()