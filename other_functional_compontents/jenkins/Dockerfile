FROM jenkins/jenkins:2.289.2

USER root

ADD id_rsa /root/.ssh/id_rsa
ADD config.json /root/.docker/config.json
ADD docker /usr/bin/docker

RUN echo "    StrictHostKeyChecking no" >> /etc/ssh/ssh_config && \
    /bin/cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
    echo 'Asia/Shanghai' > /etc/timezone
