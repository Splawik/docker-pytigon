FROM python:3.7

RUN apt-get update -y

RUN apt-get install -y curl git apt-transport-https &&\
    apt-get install -y redis-server

RUN apt-get install -y default-mysql-client default-libmysqlclient-dev && \
    apt-get install -y nginx zip

RUN mkdir -p /home/www-data/pytigon/ext_prg
RUN mkdir -p /home/www-data/.pytigon/temp

ADD ./entrypoint-interface.py /home/www-data/pytigon/entrypoint-interface.py
ADD ./entrypoint-interface-scheduler.sh /home/www-data/pytigon/entrypoint-interface-scheduler.sh

WORKDIR /home/www-data/pytigon

RUN chown -R www-data:www-data /home/www-data && \
    usermod -d /home/www-data www-data && \
    ln -s /etc/nginx/sites-available/pytigon /etc/nginx/sites-enabled/pytigon && \
    rm /etc/nginx/sites-available/default && \
    rm /etc/nginx/sites-enabled/default

RUN apt-get -y install postgresql-client postgresql-client-common libpq-dev

RUN pip3 install django-filer
RUN pip3 install git+https://github.com/Splawik/pytigon.git
RUN pip3 uninstall pytigon-lib -y
RUN pip3 install git+https://github.com/Splawik/pytigon-lib.git 

RUN pip3 install psycopg2-binary psycopg2 channels_redis graphviz gunicorn hypercorn --upgrade
RUN pip3 install "uvicorn<0.12"

RUN pip3 install https://github.com/groveco/django-sql-explorer/tarball/master#egg=package-1.0 --upgrade
RUN pip3 install https://github.com/OmenApps/django-polymorphic/tarball/master --upgrade

EXPOSE 80
EXPOSE 443

CMD ["python3.7", "entrypoint-interface.py"]

