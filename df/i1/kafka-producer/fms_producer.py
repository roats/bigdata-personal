#!/usr/bin/env python3
"""
FMS Real Data Producer (멀티스레드 버전)
실제 API에서 FMS 센서 데이터를 병렬로 수집하여 Kafka로 전송
"""

import json
import time
import requests
import threading
from confluent_kafka import Producer
from datetime import datetime
import logging

# Kafka 설정
BROKER = "s1:9092,s2:9092,s3:9092"
TOPIC = "fms-sensor-data"

# FMS API 설정
API_BASE_URL = "http://finfra.iptime.org:9872"
DEVICE_IDS = [1, 2, 3, 4, 5]
FETCH_INTERVAL = 10  # 수집 주기 (초)

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FMSDataProducer:
    def __init__(self):
        self.producer = Producer({
            'bootstrap.servers': BROKER,
            'compression.type': 'gzip',
            'batch.size': 16384,
            'linger.ms': 10
        })

    def fetch_device_data(self, device_id, retries=3, delay=1):
        """특정 장비의 데이터를 API에서 가져오기 (재시도 포함)"""
        for attempt in range(1, retries + 1):
            try:
                url = f"{API_BASE_URL}/{device_id}/"
                response = requests.get(url, timeout=5)

                if response.status_code == 200:
                    data = response.json()
                    data['collected_at'] = datetime.now().isoformat()
                    return data
                else:
                    logger.warning(f"Device {device_id}: HTTP {response.status_code} (시도 {attempt}/{retries})")

            except requests.exceptions.RequestException as e:
                logger.warning(f"Device {device_id}: API 요청 실패 (시도 {attempt}/{retries}) - {e}")

        logger.error(f"Device {device_id}: 모든 API 요청 실패")
        return None

    def send_to_kafka(self, data):
        """Kafka로 데이터 전송"""
        try:
            key = str(data['DeviceId'])
            value = json.dumps(data, ensure_ascii=False)

            self.producer.produce(
                topic=TOPIC,
                key=key,
                value=value,
                callback=self.delivery_callback
            )
            self.producer.poll(0)

        except Exception as e:
            logger.error(f"Kafka send error: {e}")

    def delivery_callback(self, err, msg):
        """메시지 전송 결과 콜백"""
        if err:
            logger.error(f'Message delivery failed: {err}')
        else:
            logger.info(f'Message delivered to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}')

    def collect_and_send(self, device_id):
        """단일 장비에 대한 데이터 수집 및 전송"""
        data = self.fetch_device_data(device_id)

        if data:
            self.send_to_kafka(data)
            logger.info(f"Device {device_id}: 데이터 전송 완료")
        else:
            logger.warning(f"Device {device_id}: 데이터 수집 실패")

    def run_continuous(self):
        """멀티스레드로 연속 데이터 수집 및 전송"""
        logger.info("FMS Data Producer (멀티스레드 모드) 시작...")
        logger.info(f"수집 대상: 장비 {DEVICE_IDS}")
        logger.info(f"수집 주기: {FETCH_INTERVAL}초")

        try:
            while True:
                start_time = time.time()
                threads = []

                for device_id in DEVICE_IDS:
                    t = threading.Thread(target=self.collect_and_send, args=(device_id,))
                    t.start()
                    threads.append(t)

                for t in threads:
                    t.join()

                self.producer.flush()

                elapsed = time.time() - start_time
                sleep_time = max(0, FETCH_INTERVAL - elapsed)
                if sleep_time > 0:
                    logger.info(f"다음 수집까지 {sleep_time:.1f}초 대기...")
                    time.sleep(sleep_time)
                else:
                    logger.warning(f"수집 시간이 {elapsed:.1f}초로 설정된 주기를 초과했습니다.")

        except KeyboardInterrupt:
            logger.info("사용자에 의해 중단됨")
        except Exception as e:
            logger.error(f"예상치 못한 오류: {e}")
        finally:
            self.producer.flush()
            logger.info("Producer 종료")

    def run_once(self):
        """한 번만 데이터 수집 (테스트용)"""
        logger.info("FMS Data Producer 테스트 실행...")

        for device_id in DEVICE_IDS:
            data = self.fetch_device_data(device_id)

            if data:
                print(f"\n=== Device {device_id} ===")
                print(json.dumps(data, indent=2, ensure_ascii=False))

                if self.validate_data(data):
                    self.send_to_kafka(data)
                    print("✅ Kafka 전송 완료")
                else:
                    print("❌ 데이터 유효성 검사 실패")
            else:
                print(f"❌ Device {device_id}: 데이터 수집 실패")

        self.producer.flush()

def main():
    import sys
    producer = FMSDataProducer()

    if len(sys.argv) > 1 and sys.argv[1] == "test":
        producer.run_once()
    else:
        producer.run_continuous()

if __name__ == "__main__":
    main()