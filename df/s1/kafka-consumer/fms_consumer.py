#!/usr/bin/env python3
"""
FMS Consumer for Real Data Processing
실제 FMS 센서 데이터를 수신하여 처리 및 HDFS 저장
"""
import json
import os
from confluent_kafka import Consumer, KafkaError
import logging
from datetime import datetime
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import subprocess
from collections import defaultdict
import time
import requests

# Kafka 설정
BROKER = "s1:9092,s2:9092,s3:9092"
TOPIC = "fms-sensor-data"
GROUP_ID = "fms-data-processor"

# HDFS 저장 경로
HDFS_BASE_PATH = "/fms/raw"

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DEVICE_IDS = [1, 2, 3, 4, 5]

class FMSDataConsumer:
    def __init__(self):
        self.consumer = Consumer({
            'bootstrap.servers': BROKER,
            'group.id': GROUP_ID,
            'auto.offset.reset': 'latest'
        })
        self.batch_buffer = defaultdict(list)
        self.batch_interval = 5  # 5초마다 묶어서 저장
        self.last_receive_time = time.time()
        self.alert_interval = 30  # 30초 이상 수신 없을 경우 슬랙 알림
        self.last_alert_sent = 0  # 중복 알림 방지

    def validate_data(self, data):
        """데이터 필수 유효성 검사"""
        required_fields = [
            'time', 'DeviceId'
        ]

        # 1. 필수 필드 존재 여부
        if not all(field in data for field in required_fields):
            logger.warning("⚠️ 누락된 필드 있음 → 건너뜀")
            return False

        # 2. time → ISO8601 형식 검사
        try:
            datetime.fromisoformat(data['time'])
        except Exception:
            logger.warning(f"⚠️ 잘못된 timestamp 형식: {data['time']}")
            return False

        # # 3. DeviceId 값 형변환 가능 여부
        try:
            data['DeviceId'] = int(data['DeviceId'])
        except Exception:
            logger.warning(f"⚠️ DeviceId 형변환 실패: {data['DeviceId']}")
            return False

        # 4. 센서 값 형변환 가능 여부
        for key in ['sensor1', 'sensor2', 'sensor3']:
            try:
                data[key] = float(data[key])
            except Exception:
                logger.warning(f"⚠️ {key} 값 형변환 실패: {data[key]}")
                return False

        # 5. 모터 값 형변환 가능 여부
        for key in ['motor1', 'motor2', 'motor3']:
            try:
                data[key] = int(data[key])
            except Exception:
                logger.warning(f"⚠️ {key} 값 형변환 실패: {data[key]}")
                return False

        return True

    def run(self):
        logger.info("FMS Data Consumer 시작...")
        logger.info(f"구독 토픽: {TOPIC}")

        self.consumer.subscribe([TOPIC])

        last_flush_time = time.time()

        try:
            while True:
                msgs = self.consumer.consume(num_messages=100, timeout=1.0)
                if msgs:
                    for msg in msgs:
                        if msg is None:
                            continue
                        elif msg.error():
                            if msg.error().code() != KafkaError._PARTITION_EOF:
                                logger.error(f"Consumer error: {msg.error()}")
                                break
                        else:
                            data = json.loads(msg.value().decode('utf-8'))
                            self.last_receive_time = time.time()
                            if self.validate_data(data):
                                ts_key = datetime.fromisoformat(data['time']).strftime('%Y%m%d%H%M%S')
                                self.batch_buffer[ts_key].append(data)

                now = time.time()
                if now - last_flush_time >= self.batch_interval:
                    self.flush_batches()
                    last_flush_time = now

                # Kafka로부터 너무 오랫동안 메시지를 못 받았을 경우 Slack 알림
                now = time.time()
                if now - self.last_receive_time > self.alert_interval:
                    if now - self.last_alert_sent > self.alert_interval:
                        self.send_slack_alert("⚠️ FMS Kafka 토픽에서 30초 이상 데이터 수신 없음")
                        self.last_alert_sent = now

        except KeyboardInterrupt:
            logger.info("사용자에 의해 중단됨")
        finally:
            self.consumer.close()
            logger.info("Consumer 종료")

    def flush_batches(self):
        try:
            for ts_key, records in self.batch_buffer.items():
                if records:
                    ts = datetime.fromisoformat(records[0]['time'])
                    hdfs_path = f"{HDFS_BASE_PATH}/year={ts.year}/month={ts.month:02d}/day={ts.day:02d}/hour={ts.hour:02d}/minute={ts.minute:02d}"
                    now_str = datetime.now().strftime("%Y%m%d%H%M%S")
                    file_name = f"{ts_key}_{now_str}.parquet"
                    local_tmp_file = f"/tmp/{file_name}"

                    df = pd.DataFrame(records)
                    table = pa.Table.from_pandas(df)
                    pq.write_table(table, local_tmp_file, compression='snappy')

                    subprocess.run(["hdfs", "dfs", "-mkdir", "-p", hdfs_path], check=True)
                    subprocess.run(["hdfs", "dfs", "-put", "-f", local_tmp_file, f"{hdfs_path}/{file_name}"], check=True)
                    os.remove(local_tmp_file)

                    logger.info(f"✅ {len(records)}개 → HDFS 저장 완료: {hdfs_path}/{file_name}")

            self.batch_buffer.clear()
        except Exception as e:
            logger.error(f"HDFS 저장 실패: {e}")

    def send_slack_alert(self, message):
        webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
        if not webhook_url:
            logger.warning("Slack Webhook URL이 설정되어 있지 않음")
            return
        payload = {
            "text": message
        }
        try:
            requests.post(webhook_url, json=payload)
            logger.info("📢 Slack 알림 전송됨")
        except Exception as e:
            logger.error(f"Slack 알림 전송 실패: {e}")

if __name__ == "__main__":
    consumer = FMSDataConsumer()
    consumer.run()