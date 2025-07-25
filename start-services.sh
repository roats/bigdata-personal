#!/bin/bash

echo "▶️ hostname 확인 중..."
hostname

if [ "$(hostname)" = "i1" ]; then
  echo "🔧 i1: SSH 초기 설정 중 (setup-ssh.sh 실행)..."
  /root/setup-ssh.sh
fi

echo "🔓 SSHD 시작..."
/usr/sbin/sshd

echo "📊 node_exporter 시작..."
nohup node_exporter --web.listen-address=:9100 &

if [ "$(hostname)" = "s1" ]; then
  echo "Starting Exporter..."
  if [ -f /df/exporter/exporter.py ]; then
    nohup python3 /df/exporter/exporter.py > /df/exporter/exporter.log 2>&1 &
  else
    echo "[entrypoint] exporter.py not found at /df/exporter/exporter.py"
  fi
fi

echo "✅ 모든 서비스 기동 완료. 대기 중..."
tail -f /dev/null
