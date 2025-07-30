#!/usr/bin/env python3
from pyspark.sql import SparkSession
import sys

if len(sys.argv) != 2:
    print("Usage: spark-submit fms_summary_result.py <YYYYMMDDHH>")
    sys.exit(1)

partition_hour = sys.argv[1]

try:
    year = partition_hour[0:4]
    month = partition_hour[4:6]
    day = partition_hour[6:8]
    hour = partition_hour[8:10]
except Exception as e:
    print(f"[ERROR] Invalid partition_hour format: {e}")
    sys.exit(1)

spark = SparkSession.builder \
    .appName("Error Summary Result") \
    .master("local[1]") \
    .config("spark.executor.cores", "1") \
    .config("spark.executor.memory", "1g") \
    .config("spark.driver.memory", "1g") \
    .config("spark.sql.shuffle.partitions", "1") \
    .config("spark.default.parallelism", "1") \
    .getOrCreate()

try:
    path = f"hdfs://s1:9000/fms/summary/errors/year={year}/month={month}/day={day}/hour={hour}"
    print(f"[INFO] Reading from: {path}")
    df = spark.read.parquet(path)
    df.show()
except Exception as e:
    print(f"[ERROR] Failed to read or show data: {e}")

spark.stop()
