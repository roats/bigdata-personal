#!/usr/bin/env python3

from kafka import KafkaConsumer
import os
import json
import requests
import time

# Kafka 설정
TOPIC_NAME = "fms-alert-data"
BOOTSTRAP_SERVERS = ["s1:9092", "s2:9092", "s3:9092"]

# Slack Webhook URL
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")
if not SLACK_WEBHOOK_URL:
    raise ValueError("SLACK_WEBHOOK_URL 환경 변수가 설정되지 않았습니다.")

# Kafka Consumer 생성
consumer = KafkaConsumer(
    TOPIC_NAME,
    bootstrap_servers=BOOTSTRAP_SERVERS,
    auto_offset_reset='latest',
    enable_auto_commit=True,
    group_id='fms-alert-slack-group',
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

def send_slack_alert(data):
    try:
        device_id = data.get("DeviceId", "Unknown")
        sensors = [data.get(f"sensor{i}", "N/A") for i in range(1, 4)]
        motors = [data.get(f"motor{i}", "N/A") for i in range(1, 4)]
        is_fail = data.get("isFail", False)
        time_str = data.get("time", "unknown")

        msg = (
            f":rotating_light: *FMS ALERT 감지*\n"
            f"> *장비 ID:* `{device_id}`\n"
            f"> *센서값:* {sensors}\n"
            f"> *모터값:* {motors}\n"
            f"> *isFail:* `{is_fail}`\n"
            f"> *수집 시각:* `{time_str}`"
        )

        response = requests.post(SLACK_WEBHOOK_URL, json={"text": msg})
        if response.status_code != 200:
            print(f"[Slack Error] Status: {response.status_code}, Body: {response.text}")

    except Exception as e:
        print(f"[Slack Alert Error] {e}")

print("✅ Kafka 소비자 시작됨 - Slack 알림 대기 중...")

for message in consumer:
    value = message.value
    print(f"[Kafka] 받은 메시지: {value}")
    send_slack_alert(value)
    time.sleep(0.5)  # Slack API 요청 간격 제한 고려
