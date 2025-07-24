# bigdata-personal
> ABC 전문가 과정 - Data Track (Advanced) : Docker 개인 과제

## 1. Project Clone
```bash
git clone https://github.com/roats/bigdata-personal.git
```
---

## 2. Docker Compose 실행 및 i1 컨테이너 접속
```bash
cd bigdata-personal
docker-compose up --build -d
docker exec -it i1 bash
```
---

## 3. Ansible 사용하여 Hadoop, Spark, Kafka 설치 및 Hadoop 실행 (i1에서 실행)
```bash
cd /df
wget https://downloads.apache.org/hadoop/common/hadoop-3.3.6/hadoop-3.3.6.tar.gz
wget https://archive.apache.org/dist/spark/spark-3.4.4/spark-3.4.4-bin-hadoop3.tgz

ansible-playbook --flush-cache -i /df/ansible-hadoop/hosts /df/ansible-hadoop/hadoop_install.yml
ansible-playbook --flush-cache -i /df/ansible-spark/hosts /df/ansible-spark/spark_install.yml -e ansible_python_interpreter=/usr/bin/python3.12
ansible-playbook --flush-cache -i /df/ansible-kafka/hosts /df/ansible-kafka/kafka_install.yml -e ansible_python_interpreter=/usr/bin/python3.12
source /etc/bashrc

startAll
```
---

## 4. Spark, Kafka 실행 및 토픽 생성 (s1에서 실행)
```bash
$SPARK_HOME/sbin/start-all.sh
pip install -r /df/kafka-setting/requirements.txt
bash /df/kafka-setting/manage_kafka.sh start
bash /df/kafka-setting/manage_topics.sh create
bash /df/kafka-setting/manage_topics.sh list
jps
```
---

## 5. Producer 실행 (i1에서 실행)
```bash
tmux new-session -d -s producer 'python3 /df/kafka-producer/fms_producer.py'
```
---

## 6. Slack WebHook URL 환경 변수 등록 (s1에서 실행)
```bash
echo 'export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/XXXXX/XXXXX/XXXXXXXXXX"' >> /etc/bashrc
source /etc/bashrc
```
---

## 7. Consumer, Processor 실행 (s1에서 실행)
```bash
tmux new-session -d -s consumer 'bash -c "source /etc/bashrc && python3 /df/kafka-consumer/fms_consumer.py"'
tmux new-session -d -s processor 'spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.4 /df/spark-processor/fms_processor.py'
tmux new-session -d -s alert_consumer 'bash -c "source /etc/bashrc && python3 /df/kafka-consumer/fms_alert_consumer.py"'
```
---

## 8. Spark 처리 결과 확인 (s1에서 실행)
```bash
hdfs dfs -ls -R /fms/
spark-submit /df/spark-processor/fms_processing_result.py
```
---

## 9. Processor, Consumer, Kafka, Spark 종료 (s1에서 실행)
```bash
tmux kill-session -t alert_consumer
tmux kill-session -t processor
tmux kill-session -t consumer
bash /df/kafka-setting/manage_kafka.sh stop
$SPARK_HOME/sbin/stop-all.sh
```
---

## 10. Producer, Hadoop 종료 (i1에서 실행)
```bash
tmux kill-session -t producer
stopAll
```
---

## 11. Docker Compose 종료
```bash
docker-compose stop
```
---

## TO-DO List
### 1일차 (4H)
- 프로젝트 인프라 환경 구성
- 기존 Docker PreLab 팀 프로젝트 진행했던 내용과 동일하게 기능 구현
- Kafka Producer, Kafka Consumer, Spark Processor 구현

### 2일차 (4H)
- `fms_producer`, `fms_consumer.py`, `fms processor.py` 로직 고도화 및 정제
- `manage_kafka.sh` 필요 없는 토픽 제거 및 Slack 알람용 토픽 추가
- `fms_processor.py` 에서 Alert 데이터 Slack 알람용 Topic 전송 로직 구현
- Slack 알람용 Topic 수신하여 알람 발송하는 `fms_alert_consumer.py` 구현
- `fms_consumer.py` 수신 없으면 Slack 알람 발송하도록 개선

### 3일차 (4H)
- Airflow DAG & Spark Batch Job 사용하여 데이터 집계 구현
- Prometheus & Grafana 사용하여 실시간 모니터링 및 집계 데이터 Dashboard 등 구현

### 4일차 (4H)
- 각 폴더들에 대한 `README.md` 파일 생성
- 프로젝트 `README.md` 파일에 전체 아키텍쳐 Diagram 추가 및 실행 방법 업데이트
- 결과 보고 PPT 작성
