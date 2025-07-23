#!/usr/bin/env python3
"""
FMS Spark Streaming Processor (정책 완전 적용 버전)
/fms/raw → 전처리 및 집계 → HDFS 대상 경로 분기 저장
정상: /fms/processed/main
장애: /fms/processed/alert
비정상: /fms/processed/quarantine
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *

# SparkSession 생성
spark = SparkSession.builder \
    .appName("FMS Data Processing") \
    .getOrCreate()

# 스키마 정의
schema = StructType([
    StructField("time", StringType()),
    StructField("DeviceId", LongType()),
    StructField("sensor1", DoubleType()),
    StructField("sensor2", DoubleType()),
    StructField("sensor3", DoubleType()),
    StructField("motor1", LongType()),
    StructField("motor2", LongType()),
    StructField("motor3", LongType()),
    StructField("isFail", BooleanType())
])

# 데이터 로드
raw_df = spark.readStream \
    .format("parquet") \
    .schema(schema) \
    .option("recursiveFileLookup", "true") \
    .load("hdfs://s1:9000/fms/raw/")

# 결측 기본값 처리
filled_df = raw_df.fillna({"motor1": 0, "motor2": 0, "motor3": 0, "isFail": False})
converted_df = filled_df.withColumn("timestamp", to_timestamp(col("time"), "yyyy-MM-dd'T'HH:mm:ssX"))

# 파생 컬럼 추가
processed_df = converted_df \
    .withColumn("converted_df", (col("sensor1") + col("sensor2") + col("sensor3")) / 3.0) \
    .withColumn("motor_total", col("motor1") + col("motor2") + col("motor3")) \
    .withColumn("processed_at", current_timestamp())

# 유효성 검증 컬럼 생성
validated_df = processed_df \
    .withColumn("now", current_timestamp()) \
    .withColumn("valid_device", col("DeviceId").between(1, 5)) \
    .withColumn("valid_s1", col("sensor1").between(0, 100)) \
    .withColumn("valid_s2", col("sensor2").between(0, 100)) \
    .withColumn("valid_s3", col("sensor3").between(0, 150)) \
    .withColumn("valid_m1", col("motor1").between(0, 2000)) \
    .withColumn("valid_m2", col("motor2").between(0, 1500)) \
    .withColumn("valid_m3", col("motor3").between(0, 1800)) \
    .withColumn("valid_isFail", col("isFail").isin(True, False))

# 상태 분류
status_df = validated_df.withColumn(
    "status",
    when(~(col("valid_device") & col("timestamp").isNotNull() & col("DeviceId").isNotNull()), "BAD_DATA")
    .when(~(col("valid_s1") & col("valid_s2") & col("valid_s3") & col("valid_m1") & col("valid_m2") & col("valid_m3") & col("valid_isFail")), "CHECK")
    .when(col("isFail") == True, "ALERT")
    .otherwise("NORMAL")
)

# 분기 저장
main_data = status_df.filter(col("status") == "NORMAL")
alert_data = status_df.filter(col("status") == "ALERT")
quarantine_data = status_df.filter(col("status").isin("CHECK", "BAD_DATA"))

# 저장 함수
def write_query(df, path, checkpoint):
    return df.writeStream \
        .outputMode("append") \
        .format("parquet") \
        .option("path", path) \
        .option("checkpointLocation", checkpoint) \
        .trigger(processingTime="10 seconds") \
        .start()

# 실행
main_query = write_query(main_data, "hdfs://s1:9000/fms/processed/main", "/tmp/checkpoints/fms/main")
alert_query = write_query(alert_data, "hdfs://s1:9000/fms/processed/alert", "/tmp/checkpoints/fms/alert")
quarantine_query = write_query(quarantine_data, "hdfs://s1:9000/fms/processed/quarantine", "/tmp/checkpoints/fms/quarantine")

main_query.awaitTermination()
alert_query.awaitTermination()
quarantine_query.awaitTermination()