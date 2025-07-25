#!/bin/bash

echo "[entrypoint] Starting Prometheus..."
nohup /usr/local/bin/prometheus \
  --config.file=/etc/prometheus/prometheus.yml \
  --web.listen-address=":9090" &

echo "[entrypoint] Starting Grafana..."
/opt/grafana/bin/grafana-server \
  --homepath=/opt/grafana \
  --config=/opt/grafana/conf/defaults.ini \
  --packaging=docker
