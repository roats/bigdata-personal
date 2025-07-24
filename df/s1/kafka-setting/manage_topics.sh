#!/bin/bash
# Kafka 토픽 관리 스크립트

BROKERS="s1:9092,s2:9092,s3:9092"

create_topics() {
    echo "Creating Kafka topics..."

    # FMS 실제 데이터용 토픽
    kafka-topics.sh --create --topic fms-sensor-data \
        --partitions 5 --replication-factor 2 \
        --if-not-exists \
        --config retention.ms=604800000 \
        --config compression.type=gzip \
        --bootstrap-server $BROKERS

    # FMS 알림 데이터용 토픽
    kafka-topics.sh --create --topic fms-alert-data \
        --partitions 3 --replication-factor 2 \
        --if-not-exists \
        --config retention.ms=604800000 \
        --config compression.type=gzip \
        --bootstrap-server $BROKERS

    # 기본 테스트 토픽들
    # kafka-topics.sh --create --topic test-topic --bootstrap-server $BROKERS
    # kafka-topics.sh --create --topic input-topic --bootstrap-server $BROKERS
    # kafka-topics.sh --create --topic filtered-topic --bootstrap-server $BROKERS

    # 고가용성 테스트용 토픽
    # kafka-topics.sh --create --topic replicated-topic \
    #     --partitions 3 --replication-factor 2 \
    #     --if-not-exists \
    #     --config retention.ms=604800000 \
    #     --config compression.type=gzip \
    #     --bootstrap-server $BROKERS

    # 센서 데이터용 토픽
    # kafka-topics.sh --create --topic sensor-data \
    #     --partitions 5 --replication-factor 2 \
    #     --if-not-exists \
    #     --config retention.ms=604800000 \
    #     --config compression.type=gzip \
    #     --bootstrap-server $BROKERS

    echo "Topics created successfully"
}

list_topics() {
    echo "Listing all topics..."
    kafka-topics.sh --list --bootstrap-server $BROKERS
}

describe_topic() {
    local topic=$1
    echo "Describing topic: $topic"
    kafka-topics.sh --describe --topic $topic --bootstrap-server $BROKERS
}

delete_topic() {
    local topic=$1
    echo "Deleting topic: $topic"
    kafka-topics.sh --delete --topic $topic --bootstrap-server $BROKERS
}

# 사용법
case "$1" in
    create)
        create_topics
        ;;
    list)
        list_topics
        ;;
    describe)
        describe_topic $2
        ;;
    delete)
        delete_topic $2
        ;;
    *)
        echo "Usage: $0 {create|list|describe|delete} [topic-name]"
        exit 1
        ;;
esac