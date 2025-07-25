FROM nowage/i1s3:oraclelinux9

# 추가 설치 스크립트 복사 및 실행
COPY install-s.sh /root/install-s.sh
RUN chmod +x /root/install-s.sh && /root/install-s.sh

# Python 설치
RUN dnf install -y python3-pip && \
    pip3 install flask prometheus_client

# 포트 22 노출
# EXPOSE 22

# SSHD 실행
# CMD ["/usr/sbin/sshd", "-D"]

# # SSHD 실행
# CMD ssh-keygen -A && [ -f /etc/ssh/ssh_host_rsa_key ] && [ -f /etc/ssh/ssh_host_ecdsa_key ] && [ -f /etc/ssh/ssh_host_ed25519_key ] && /usr/sbin/sshd -D || (echo "Host keys not found!" && exit 1)

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
