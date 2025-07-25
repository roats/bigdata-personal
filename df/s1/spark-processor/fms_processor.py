#!/usr/bin/env python3

import time
import json
import requests
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *

# SparkSession 생성
spark = SparkSession.builder \
    .appName("FMS Data Processing") \
    .master("local[1]") \
    .config("spark.executor.cores", "1") \
    .config("spark.executor.memory", "1g") \
    .config("spark.driver.memory", "1g") \
    .config("spark.sql.shuffle.partitions", "1") \
    .config("spark.default.parallelism", "1") \
    .getOrCreate()

spark.sparkContext.setLogLevel("ERROR")

# 스키마 정의 (raw 데이터 구조 반영)
schema = StructType([
    StructField("time", StringType()),
    StructField("DeviceId", LongType()),
    StructField("sensor1", DoubleType()),
    StructField("sensor2", DoubleType()),
    StructField("sensor3", DoubleType()),
    StructField("motor1", LongType()),
    StructField("motor2", LongType()),
    StructField("motor3", LongType()),
    StructField("isFail", BooleanType()),
    StructField("collected_at", StringType()),
])

# 데이터 로드
raw_df = spark.readStream \
    .format("parquet") \
    .schema(schema) \
    .option("recursiveFileLookup", "true") \
    .option("maxFilesPerTrigger", 50) \
    .load("hdfs://s1:9000/fms/raw/")

# 결측 기본값 처리 및 파싱
filled_df = raw_df.fillna({
    "motor1": 0, "motor2": 0, "motor3": 0, "isFail": False
})
converted_df = filled_df \
    .withColumn("timestamp", to_timestamp(col("time"), "yyyy-MM-dd'T'HH:mm:ssX"))

# 파생 컬럼 추가
processed_df = converted_df \
    .withColumn("sensor_avg", (col("sensor1") + col("sensor2") + col("sensor3")) / 3.0) \
    .withColumn("motor_total", col("motor1") + col("motor2") + col("motor3")) \
    .withColumn("processed_at", current_timestamp()) \
    .withColumn("year", year("timestamp")) \
    .withColumn("month", format_string("%02d", month("timestamp"))) \
    .withColumn("day", format_string("%02d", dayofmonth("timestamp"))) \
    .withColumn("hour", format_string("%02d", hour("timestamp"))) \
    .withColumn("minute", format_string("%02d", minute("timestamp")))

# 유효성 검증
validated_df = processed_df \
    .withColumn("valid_device", col("DeviceId").between(1, 100)) \
    .withColumn("valid_time", col("timestamp").isNotNull()) \
    .withColumn("valid_isFail", col("isFail").isin(True, False)) \
    .withColumn("valid_s1", col("sensor1").between(0, 100)) \
    .withColumn("valid_s2", col("sensor2").between(0, 100)) \
    .withColumn("valid_s3", col("sensor3").between(0, 150)) \
    .withColumn("valid_m1", col("motor1").between(0, 2000)) \
    .withColumn("valid_m2", col("motor2").between(0, 1500)) \
    .withColumn("valid_m3", col("motor3").between(0, 1800))

# 상태 분류 로직
status_df = validated_df.withColumn(
    "status",
    when(~(col("valid_device") & col("valid_time") & col("valid_isFail")), "CHECK")
    .when(col("isFail") == True, "ALERT")
    .when(~(col("valid_s1") & col("valid_s2") & col("valid_s3") &
            col("valid_m1") & col("valid_m2") & col("valid_m3")), "ALERT")
    .otherwise("NORMAL")
)

# 분기 필터링
normal_data = status_df.filter(col("status") == "NORMAL")
alert_data = status_df.filter(col("status") == "ALERT")
check_data = status_df.filter(col("status") == "CHECK")

# HDFS 저장 함수 (시간 단위 파티셔닝 포함)
def write_query(df, base_path, checkpoint, name):
    query = df.writeStream \
        .queryName(name) \
        .outputMode("append") \
        .format("parquet") \
        .option("path", base_path) \
        .option("checkpointLocation", checkpoint) \
        .partitionBy("year", "month", "day", "hour", "minute") \
        .trigger(processingTime="10 seconds") \
        .start()

    print(f"[HDFS] Write to {base_path}, Active: {query.isActive}, Status: {query.status}")
    return query

# ALERT 데이터 Kafka 전송 함수
def write_to_kafka(df, topic, checkpoint, name):
    kafka_df = df \
        .withColumn("key", col("DeviceId").cast("string")) \
        .withColumn(
            "value",
            to_json(struct(
                col("DeviceId"),
                col("sensor1"),
                col("sensor2"),
                col("sensor3"),
                col("motor1"),
                col("motor2"),
                col("motor3"),
                col("isFail"),
                col("time"),
                current_timestamp().alias("event_time")
            ))
        ) \
        .select("key", "value")

    query = kafka_df.writeStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", "s1:9092,s2:9092,s3:9092") \
        .option("topic", topic) \
        .option("checkpointLocation", checkpoint) \
        .outputMode("append") \
        .trigger(processingTime="10 seconds") \
        .queryName(name) \
        .start()

    print(f"[Kafka] Write to topic {topic}, Active: {query.isActive}")
    print(json.dumps(query.status, indent=2))  # JSON 형태 상태 출력

    return query

def write_latest_to_single_json(df):
    from pyspark.sql.functions import to_json, struct
    import os

    def batch_writer(batch_df, batch_id):
        if batch_df.isEmpty():
            return
        json_data = batch_df.select(
                "DeviceId","sensor1", "sensor2", "sensor3",
                "motor1", "motor2", "motor3",
                "sensor_avg", "motor_total", "isFail", "time"
        ).orderBy("time").toJSON().collect()

        json_path = "/df/exporter/latest_data.json"
        with open(json_path, "w") as f:
            f.write("[\n" + ",\n".join(json_data) + "\n]")

    return df.writeStream \
        .foreachBatch(batch_writer) \
        .outputMode("append") \
        .trigger(processingTime="10 seconds") \
        .queryName("latest_json") \
        .start()

queries = []

# HDFS 쿼리
try:
    queries.append(write_query(normal_data,
        "hdfs://s1:9000/fms/processed/normal",
        "hdfs://s1:9000/tmp/checkpoints/fms/normal",
        "normal"))

    queries.append(write_query(check_data,
        "hdfs://s1:9000/fms/processed/check",
        "hdfs://s1:9000/tmp/checkpoints/fms/check",
        "check"))

    queries.append(write_query(alert_data,
        "hdfs://s1:9000/fms/processed/alert",
        "hdfs://s1:9000/tmp/checkpoints/fms/alert",
        "alert"))

except Exception as e:
    print("[ERROR] HDFS 쿼리 실패:", e)

# Kafka 전송 추가
try:
    queries.append(write_to_kafka(alert_data,
        "fms-alert-data",
        "hdfs://s1:9000/tmp/checkpoints/fms/alert_kafka",
        "alert_kafka"))

except Exception as e:
    print("[ERROR] Kafka 쿼리 실패:", e)

# Exporter
try:
    queries.append(write_latest_to_single_json(status_df))
except Exception as e:
    print("[ERROR] JSON Export 쿼리 실패:", e)

# 모든 쿼리 종료 대기
try:
    while any([q.isActive for q in queries]):
        time.sleep(10)
except KeyboardInterrupt:
    print("종료 신호 수신, 모든 쿼리 종료")
    for q in queries:
        q.stop()
finally:
    for q in queries:
        if q.isActive:
            q.stop()