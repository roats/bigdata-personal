#!/usr/bin/env python3
from flask import Flask, Response
from prometheus_client import Gauge, generate_latest, CollectorRegistry, CONTENT_TYPE_LATEST
import json
import os

app = Flask(__name__)
registry = CollectorRegistry()

# 실시간 측정값 메트릭
metrics = {
    "sensor1": Gauge("fms_sensor1", "Sensor 1", ["device"], registry=registry),
    "sensor2": Gauge("fms_sensor2", "Sensor 2", ["device"], registry=registry),
    "sensor3": Gauge("fms_sensor3", "Sensor 3", ["device"], registry=registry),
    "motor1":  Gauge("fms_motor1",  "Motor 1",  ["device"], registry=registry),
    "motor2":  Gauge("fms_motor2",  "Motor 2",  ["device"], registry=registry),
    "motor3":  Gauge("fms_motor3",  "Motor 3",  ["device"], registry=registry),
    "isFail":  Gauge("fms_is_fail", "Failure Status", ["device"], registry=registry),
    "sensor_avg": Gauge("fms_sensor_avg", "Sensor Average", ["device"], registry=registry),
    "motor_total": Gauge("fms_motor_total", "Motor Total Load", ["device"], registry=registry),
}

# summary.json 기반 메트릭
summary_metrics = {
    "error_rate": Gauge("fms_error_rate_summary", "Error Rate Summary (%)", ["device"], registry=registry),
    "error_count": Gauge("fms_error_count_summary", "Error Count Summary", ["device"], registry=registry),
    "total_count": Gauge("fms_total_count_summary", "Total Count Summary", ["device"], registry=registry),
}

@app.route("/metrics")
def metrics_exporter():
    latest_path = "/df/exporter/latest_data.json"
    summary_path = "/df/exporter/summary.json"

    # 실시간 데이터 처리
    if os.path.exists(latest_path):
        try:
            with open(latest_path, "r") as f:
                latest_data = json.load(f)

            for row in latest_data:
                device = str(row["DeviceId"])
                for key in metrics:
                    if key in row:
                        metrics[key].labels(device=device).set(float(row[key]))
        except Exception as e:
            return Response(f"# Error loading latest_data.json: {e}", mimetype="text/plain")

    # summary 데이터 처리
    if os.path.exists(summary_path):
        try:
            with open(summary_path, "r") as f:
                summary_data = json.load(f)

            for device, values in summary_data.items():
                for key in summary_metrics:
                    if key in values:
                        summary_metrics[key].labels(device=device).set(float(values[key]))
        except Exception as e:
            return Response(f"# Error loading summary.json: {e}", mimetype="text/plain")

    return Response(generate_latest(registry), mimetype=CONTENT_TYPE_LATEST)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
