FROM nowage/i1s3:oraclelinux9

# 추가 설치 스크립트 복사 및 실행
COPY install-i1.sh /root/install-i1.sh
RUN chmod +x /root/install-i1.sh && /root/install-i1.sh

# SSH 설정 스크립트 복사
COPY setup-ssh.sh /root/setup-ssh.sh
RUN chmod +x /root/setup-ssh.sh

# SSH 설정 및 실행
# CMD ["/bin/bash", "-c", "/root/setup-ssh.sh && sleep infinity"]
# CMD ["/bin/bash", "-c", "/root/setup-ssh.sh && /usr/sbin/sshd -D"]

# node-exporter 설치
RUN cd /opt && \
    curl -LO https://github.com/prometheus/node_exporter/releases/download/v1.8.0/node_exporter-1.8.0.linux-amd64.tar.gz && \
    tar -xzf node_exporter-1.8.0.linux-amd64.tar.gz && \
    mv node_exporter-1.8.0.linux-amd64/node_exporter /usr/local/bin && \
    rm -rf node_exporter-*

# 서비스 실행 스크립트 복사
COPY start-services.sh /root/start-services.sh
RUN chmod +x /root/start-services.sh

# 포트 노출
EXPOSE 22 9100

# 엔트리포인트 실행
CMD ["/root/start-services.sh"]
