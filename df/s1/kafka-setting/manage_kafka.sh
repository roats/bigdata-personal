#!/bin/bash
# Kafka 클러스터 관리 스크립트

start_kafka_cluster() {
    echo "Starting Kafka cluster..."

    # s1에서 Zookeeper 시작
    echo "Starting Zookeeper on s1..."
    tmux new-session -d -s zookeeper 'zookeeper-server-start.sh /opt/kafka/config/zookeeper.properties'
    sleep 5

    # Kafka 브로커들 시작
    echo "Starting Kafka brokers..."
    tmux new-session -d -s kafka 'kafka-server-start.sh /opt/kafka/config/server.properties'
    ssh s2 "tmux new-session -d -s kafka 'kafka-server-start.sh /opt/kafka/config/server.properties'"
    ssh s3 "tmux new-session -d -s kafka 'kafka-server-start.sh /opt/kafka/config/server.properties'"

    echo "Kafka cluster started successfully"
}

stop_kafka_cluster() {
    echo "Stopping Kafka cluster..."

    # Kafka 브로커들 중지
    tmux kill-session -t kafka 2>/dev/null
    ssh s2 "tmux kill-session -t kafka" 2>/dev/null
    ssh s3 "tmux kill-session -t kafka" 2>/dev/null

    # Zookeeper 중지
    tmux kill-session -t zookeeper 2>/dev/null

    echo "Kafka cluster stopped"
}

check_kafka_status() {
    echo "Checking Kafka cluster status..."
    kafka-topics.sh --list --bootstrap-server s1:9092,s2:9092,s3:9092
}

# 사용법
case "$1" in
    start)
        start_kafka_cluster
        ;;
    stop)
        stop_kafka_cluster
        ;;
    status)
        check_kafka_status
        ;;
    *)
        echo "Usage: $0 {start|stop|status}"
        exit 1
        ;;
esac