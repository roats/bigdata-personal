#!/usr/bin/env python3
from flask import Flask, Response
from prometheus_client import Gauge, generate_latest, CollectorRegistry, CONTENT_TYPE_LATEST
import json
import os

app = Flask(__name__)
registry = CollectorRegistry()

# 각 센서 및 모터 값에 대한 Gauge 정의
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

@app.route("/metrics")
def metrics_exporter():
    json_path = "/df/exporter/latest_data.json"
    if not os.path.exists(json_path):
        return Response("# No data found", mimetype="text/plain")

    try:
        with open(json_path, "r") as f:
            data = json.load(f)

        for row in data:
            device = str(row["DeviceId"])
            for key in metrics:
                if key in row:
                    metrics[key].labels(device=device).set(float(row[key]))

        return Response(generate_latest(registry), mimetype=CONTENT_TYPE_LATEST)

    except Exception as e:
        return Response(f"# Exporter Error: {e}", mimetype="text/plain")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
