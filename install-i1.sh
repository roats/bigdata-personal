#!/bin/bash
# 설치 날짜 기록
echo $(date) > /tmp/installDate

# EPEL 리포지토리 활성화 및 필수 패키지 설치
dnf install -y ansible
python3 -m pip install ansible-core

# dnf install -y java-1.8.0-openjdk-devel
# export JAVA_HOME=/usr/lib/jvm/java-1.8.0-openjdk
# echo 'export JAVA_HOME=/usr/lib/jvm/java-1.8.0-openjdk' >> /etc/profile
# echo 'export PATH=$JAVA_HOME/bin:$PATH' >> /etc/profile
# source /etc/profile

# .bashrc에 alias 추가
cat << 'EOF' >> /etc/bashrc
# Start all node
alias startAll='
stopAll
# HDFS 데몬 시작
ansible namenodes -i /df/ansible-hadoop/hosts -m shell -a "nohup hdfs --daemon start namenode &" -u root && \
ansible datanodes -i /df/ansible-hadoop/hosts -m shell -a "nohup hdfs --daemon start datanode &" -u root && \
# YARN 데몬 시작
ansible namenodes -i /df/ansible-hadoop/hosts -m shell -a "nohup yarn --daemon start resourcemanager &" -u root && \
ansible datanodes -i /df/ansible-hadoop/hosts -m shell -a "nohup yarn --daemon start nodemanager &" -u root && \
# MapReduce HistoryServer 시작 (선택 사항)
ansible namenodes -i /df/ansible-hadoop/hosts -m shell -a "nohup mapred --daemon start historyserver &" -u root && \
# Safe Mode off
ansible namenodes -i /df/ansible-hadoop/hosts -m shell -a "hdfs dfsadmin -safemode leave &" -u root --become
'

# Stop all node
alias stopAll='
# HDFS 데몬 종료
ansible namenodes -i /df/ansible-hadoop/hosts -m shell -a "hdfs --daemon stop namenode" -u root && \
ansible datanodes -i /df/ansible-hadoop/hosts -m shell -a "hdfs --daemon stop datanode" -u root && \
# YARN 데몬 종료
ansible namenodes -i /df/ansible-hadoop/hosts -m shell -a "yarn --daemon stop resourcemanager" -u root && \
ansible datanodes -i /df/ansible-hadoop/hosts -m shell -a "yarn --daemon stop nodemanager" -u root && \
# MapReduce HistoryServer 종료 (선택 사항)
ansible namenodes -i /df/ansible-hadoop/hosts -m shell -a "mapred --daemon stop historyserver" -u root
'
EOF
