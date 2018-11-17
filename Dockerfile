FROM ubuntu:16.04

RUN apt-get update  -y
RUN apt-get install -y software-properties-common
RUN add-apt-repository -y ppa:deadsnakes/ppa

RUN apt-get update  -y && \
    apt-get upgrade -y && \
    apt-get install -y

RUN apt-get install -y build-essential checkinstall && \
    apt-get install -y libreadline-gplv2-dev libncursesw5-dev && \
    apt-get install -y libssl-dev libsqlite3-dev tk-dev libgdbm-dev && \
    apt-get install -y libc6-dev libbz2-dev

RUN apt-get install -y python3.7 python3.7-dev python3.7-distutils

RUN apt-get update -y --fix-missing

RUN apt-get install -y curl git apt-transport-https &&\
    apt-get install -y redis-server

RUN curl https://bootstrap.pypa.io/get-pip.py | python3.7

RUN apt-get install -y mysql-client libmysqlclient-dev && \
    apt-get install -y nginx zip

RUN mkdir /var/www/pytigon && \
    git clone https://github.com/Splawik/pytigon.git /var/www/pytigon

WORKDIR /var/www/pytigon

RUN bash ./install_in_docker.sh

RUN mkdir /home/www-data && \
    mkdir /home/www-data/.pytigon && \
    mkdir /home/www-data/.pytigon/temp && \
    chown -R www-data:www-data /home/www-data && \
    usermod -d /home/www-data www-data && \
    ln -s /etc/nginx/sites-available/pytigon /etc/nginx/sites-enabled/pytigon && \
    rm /etc/nginx/sites-available/default && \
    rm /etc/nginx/sites-enabled/default

RUN pip3 install mysqlclient hypercorn --upgrade

EXPOSE 80
EXPOSE 443
EXPOSE 8000
EXPOSE 8001
EXPOSE 8002

CMD ["python3.7", "entrypoint-interface.py"]
