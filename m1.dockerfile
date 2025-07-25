FROM oraclelinux:9

# 유틸 설치
RUN dnf install -y wget tar vim shadow-utils && \
    useradd -m -s /bin/bash grafana

# Prometheus 설치
RUN useradd -M -s /sbin/nologin prometheus && \
    mkdir -p /etc/prometheus /var/lib/prometheus && \
    cd /tmp && \
    wget https://github.com/prometheus/prometheus/releases/download/v2.52.0/prometheus-2.52.0.linux-amd64.tar.gz && \
    tar -xzf prometheus-2.52.0.linux-amd64.tar.gz && \
    cp prometheus-2.52.0.linux-amd64/prometheus /usr/local/bin/ && \
    cp prometheus-2.52.0.linux-amd64/promtool /usr/local/bin/ && \
    cp -r prometheus-2.52.0.linux-amd64/consoles /etc/prometheus/ && \
    cp -r prometheus-2.52.0.linux-amd64/console_libraries /etc/prometheus/
    # cp prometheus-2.52.0.linux-amd64/prometheus.yml /etc/prometheus/

# Grafana 설치
WORKDIR /opt
RUN wget https://dl.grafana.com/oss/release/grafana-10.4.2.linux-amd64.tar.gz && \
    tar -zxvf grafana-10.4.2.linux-amd64.tar.gz && \
    mv grafana-v10.4.2 grafana && \
    chown -R grafana:grafana /opt/grafana

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 9090 3000

CMD ["/entrypoint.sh"]