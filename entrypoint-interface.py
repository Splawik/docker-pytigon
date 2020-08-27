#!/usr/bin/env python3.7

import subprocess
import os
import sys
import pwd
from os import environ


if __name__ == "__main__":
    from pytigon_lib.schtools.tools import get_executable
    from pytigon_lib.schtools.main_paths import get_main_paths

    import pytigon

    environ["START_PATH"] = os.path.abspath(os.getcwd())

    access_logfile = "--access-logfile /var/log/pytigon-access.log"
    access_log = access_logfile.replace("logfile", "log")
    log_file = "--log-file /var/log/pytigon-worker-err.log"
    error_logfile = "--error-logfile /var/log/pytigon-worker-err.log"

    paths = get_main_paths()

    PYTIGON_PATH = os.path.abspath(os.path.dirname(pytigon.__file__))
    STATIC_PATH = paths["STATIC_PATH"]
    DATA_PATH = paths["DATA_PATH"]
    PRJ_PATH = paths["PRJ_PATH"]
    PRJ_PATH_ALT = paths["PRJ_PATH_ALT"]
    BASE_APPS_PATH = paths["PRJ_PATH"]
    LOCAL_IP = "http://127.0.0.1"
    sys.path.append(BASE_APPS_PATH)

    uid, gid = pwd.getpwnam("www-data").pw_uid, pwd.getpwnam("www-data").pw_uid

    os.chown(DATA_PATH, uid, gid)
    os.chown("/var/log", uid, gid)

    if not os.path.exists("/var/log/nginx"):
        os.makedirs("/var/log/nginx")

    if not os.path.exists(BASE_APPS_PATH):
        os.makedirs(BASE_APPS_PATH)
        os.chown(BASE_APPS_PATH, uid, gid)

    if not os.path.exists("/home/www-data/.pytigon/static"):
        os.makedirs("/home/www-data/.pytigon/static")

    # hack:
    subprocess.Popen("chmod -R 777 /home/www-data/.pytigon/static", shell=True)

    subprocess.Popen(
        "chmod -R 777 /usr/local/lib/python3.7/dist-packages/pytigon/static", shell=True
    )
    # hack end

    if "VIRTUAL_HOST" in environ:
        VIRTUAL_HOST = str(environ["VIRTUAL_HOST"])
    else:
        VIRTUAL_HOST = "localhost"

    if "VIRTUAL_PORT" in environ:
        VIRTUAL_PORT = str(environ["VIRTUAL_PORT"])
    else:
        if "CERT" in environ:
            VIRTUAL_PORT = "443"
        else:
            VIRTUAL_PORT = "80"

    if "VIRTUAL_PORT_80" in environ:
        VIRTUAL_PORT_80 = str(environ["VIRTUAL_PORT_80"])
    else:
        VIRTUAL_PORT_80 = "80"

    if "PORT_80_REDIRECT" in environ:
        PORT_80_REDIRECT = environ["PORT_80_REDIRECT"]
    else:
        PORT_80_REDIRECT = None

    if "CERT" in environ:
        x = environ["CERT"].split(";")
        CRT = "ssl_certificate " + x[0] + ";"
        KEY = "ssl_certificate_key " + x[1] + ";"
        VIRTUAL_PORT += " ssl http2"
    else:
        CRT = ""
        KEY = ""

    if "NGINX_INCLUDE" in environ:
        NGINX_INCLUDE = environ["NGINX_INCLUDE"]
    else:
        NGINX_INCLUDE = None

    # NUMBER_OF_WORKER_PROCESSES struct:
    # 1. NUMBER_FOR_MAIN_APP, for example: 4
    # 2. NUMBER_FOR_MAIN_APP:NUMBER_FOR_ADDITIONAL_APP, for example: 4:1
    # 3. NAME_OF_SPECIFIC_APP:NUMBER_FOR_SPECIFIC_APP,*, for example:  schportal:4,schdevtools:2

    NOWP = {}
    if "NUMBER_OF_WORKER_PROCESSES" in environ:
        nowp = environ["NUMBER_OF_WORKER_PROCESSES"]
        if ":" in nowp:
            if "," in nowp or ";" in nowp:
                for pos in nowp.replace(",", ";").split(";"):
                    if ":" in pos:
                        x = pos.split(":")
                        NOWP[x[0]] = x[1]
                    else:
                        NOWP[x] = 1
            else:
                x = nowp.split(":")
                NOWP["default-main"] = int(x[0])
                NOWP["default-additional"] = int(x[1])
        else:
            NOWP["default-main"] = int(nowp)
            NOWP["default-additional"] = 1
    else:
        NOWP["default-main"] = 4
        NOWP["default-additional"] = 1

    if "TIMEOUT" in environ:
        TIMEOUT = environ["TIMEOUT"]
    else:
        TIMEOUT = "30"

    if "WEBSOCKET_TIMEOUT" in environ:
        WEBSOCKET_TIMEOUT = environ["WEBSOCKET_TIMEOUT"]
    else:
        WEBSOCKET_TIMEOUT = "30"

    # ASGI_SERVER_NAME:
    # 1. daphne
    # 2. gunicorn
    # 3. hypercorn
    ASGI_SERVER_ID = 0
    if "ASGI_SERVER_NAME" in environ:
        if "gunicorn" in environ["ASGI_SERVER_NAME"]:
            ASGI_SERVER_ID = 1
        elif "dapne" in environ["ASGI_SERVER_NAME"]:
            ASGI_SERVER_ID = 2

    START_CLIENT_PORT = 8000
    PRJS = []
    PRJ_FOLDERS = []
    MAIN_PRJ = None
    NO_ASGI = []

    if PORT_80_REDIRECT:
        CFG_OLD = f"""server {{
           listen         {VIRTUAL_PORT_80};
           server_name    {VIRTUAL_HOST} www.{VIRTUAL_HOST};
           return         301 {PORT_80_REDIRECT}$request_uri;
    }}

    """

    if CRT:
        CFG_START = f"""
    server {{
        listen {VIRTUAL_PORT};
        client_max_body_size 50M;
        server_name www.{VIRTUAL_HOST};
        charset utf-8;

        {CRT}
        {KEY}

        return 301 {PORT_80_REDIRECT}$request_uri;
    }}"""
    else:
        CFG_START = ""

    CFG_START += f"""

    map $http_upgrade $connection_upgrade {{
        default upgrade;
        ''      close;
    }}

    server {{
        listen {VIRTUAL_PORT};
        client_max_body_size 50M;
        server_name {VIRTUAL_HOST};
        charset utf-8;

        {CRT}
        {KEY}

        location /static/ {{
            alias {STATIC_PATH}/$PRJ/;
            autoindex on;
        }}

    """
    CFG_ELEM = f"""
        location /$PRJ/static/ {{
            alias {STATIC_PATH}/$PRJ/;
            autoindex on;
        }}
        location /$PRJ/site_media/ {{
            alias {DATA_PATH}/$PRJ/media/;
            autoindex on;
        }}
        location /$PRJ/site_media_protected/ {{
            internal;
            alias {DATA_PATH}/$PRJ/media_protected/;
        }}
        location ~ /$PRJ(.*)/channel/$ {{
            proxy_http_version 1.1;

            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_pass {LOCAL_IP}:$PORT/$PRJ$1/channel/;
            proxy_connect_timeout       {WEBSOCKET_TIMEOUT};
            proxy_send_timeout          {WEBSOCKET_TIMEOUT};
            proxy_read_timeout          {WEBSOCKET_TIMEOUT};
            send_timeout                {WEBSOCKET_TIMEOUT};
        }}
        location /$PRJ {{
            proxy_pass {LOCAL_IP}:$PORT/$PRJ;

            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $remote_addr;

            proxy_set_header X-Forwarded-Host $host;
            proxy_set_header X-Forwarded-Proto https;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection $connection_upgrade;

            proxy_connect_timeout       {TIMEOUT};
            proxy_send_timeout          {TIMEOUT};
            proxy_read_timeout          {TIMEOUT};
            send_timeout                {TIMEOUT};
        }}
    """
    CFG_END = f"""
        location ~ (.*)/channel/$ {{
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_pass {LOCAL_IP}:$PORT$1/channel/;
            proxy_connect_timeout       {WEBSOCKET_TIMEOUT};
            proxy_send_timeout          {WEBSOCKET_TIMEOUT};
            proxy_read_timeout          {WEBSOCKET_TIMEOUT};
            send_timeout                {WEBSOCKET_TIMEOUT};
        }}

        location / {{
            proxy_pass {LOCAL_IP}:$PORT;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $remote_addr;
            proxy_connect_timeout       {TIMEOUT};
            proxy_send_timeout          {TIMEOUT};
            proxy_read_timeout          {TIMEOUT};
            send_timeout                {TIMEOUT};
        }}
    }}
    """

    def create_sym_links(source_path, dest_path):
        if os.path.exists(source_path) and os.path.exists(dest_path):
            x = os.listdir(source_path)
            for pos in x:
                s_path = os.path.join(source_path, pos)
                d_path = os.path.join(dest_path, pos)
                if not os.path.exists(d_path):
                    os.symlink(s_path, d_path)

    for ff in os.listdir(BASE_APPS_PATH):
        if os.path.isdir(os.path.join(BASE_APPS_PATH, ff)):
            if not ff.startswith("_"):
                PRJ_FOLDERS.append(ff)

    for prj in PRJ_FOLDERS:
        base_apps_pack2 = os.path.join(BASE_APPS_PATH, prj)
        try:
            x = __import__(prj + ".apps")
        except:
            continue
        if hasattr(x.apps, "NO_ASGI") and x.apps.NO_ASGI:
            NO_ASGI.append(prj)

        if hasattr(x.apps, "PUBLIC") and x.apps.PUBLIC:
            if hasattr(x.apps, "MAIN_PRJ") and x.apps.MAIN_PRJ:
                MAIN_PRJ = prj
            else:
                PRJS.append(prj)

    if "INCLUDE_SETUP" in environ:
        PRJS.append("schsetup")
    if "INCLUDE_DEVTOOLS" in environ:
        PRJS.append("schdevtools")
    if "INCLUDE_PORTAL" in environ:
        PRJS.append("schportal")
    if "MAIN_PRJ" in environ:
        MAIN_PRJ = environ["MAIN_PRJ"]

    if not MAIN_PRJ and len(PRJS) == 1:
        MAIN_PRJ = PRJS[0]
        PRJS = []

    with open("/etc/nginx/sites-available/pytigon", "wt") as conf:
        if PORT_80_REDIRECT:
            conf.write(CFG_OLD)

        conf.write(CFG_START.replace("$PRJ", MAIN_PRJ))

        port = START_CLIENT_PORT
        for prj in PRJS:

            path = f"{PRJ_PATH}/{prj}/static/{prj}"
            if not os.path.exists(path):
                path = f"{PRJ_PATH_ALT}/{prj}/static/{prj}"

            conf.write(CFG_ELEM.replace("$PRJ", prj).replace("$PORT", str(port)))
            port += 1
        if MAIN_PRJ:
            if NGINX_INCLUDE:
                conf.write("    include %s;\n\n" % NGINX_INCLUDE)
            conf.write(CFG_END.replace("$PORT", str(port)))

    if MAIN_PRJ and not MAIN_PRJ in PRJS:
        PRJS.append(MAIN_PRJ)

    port = START_CLIENT_PORT
    ret_tab = []

    for prj in PRJS:

        static_path = os.path.join(DATA_PATH, "static", prj)
        if not os.path.exists(static_path):
            os.makedirs(static_path)
            os.chown(static_path, uid, gid)

        cmd = (
            f"cd /var/www/pytigon && su - www-data -s /bin/sh -c 'cd /var/www/pytigon; exec %s -m pytigon.ptig manage_{prj} collectstatic --noinput'"
            % get_executable()
        )

        collectstatic = subprocess.Popen(cmd, shell=True)
        collectstatic.wait()

        if prj in NOWP:
            count = NOWP[prj]
        else:
            count = (
                NOWP["default-main"] if prj == MAIN_PRJ else NOWP["default-additional"]
            )

        if prj in NO_ASGI:
            server = f"gunicorn -b 0.0.0.0:{port} --user www-data -w {count} {access_logfile} {error_logfile} wsgi -t {TIMEOUT}"
        else:
            server1 = f"hypercorn -b 0.0.0.0:{port} --user www-data -w {count} {access_logfile} {error_logfile} asgi:application"
            server2 = f"gunicorn -b 0.0.0.0:{port} --user www-data -w {count} -k uvicorn.workers.UvicornWorker {access_logfile} {error_logfile} asgi:application -t {TIMEOUT}"
            server3 = f"daphne -b 0.0.0.0 -p {port} --proxy-headers {access_log} asgi:application"

            server = (server1, server2, server3)[ASGI_SERVER_ID]

        path = f"/home/www-data/.pytigon/prj/{prj}"
        if not os.path.exists(path):
            path = f"/usr/local/lib/python3.7/dist-packages/pytigon/prj/{prj}"

        cmd = f"cd {path} && exec {server}"

        port += 1
        print(cmd)
        ret_tab.append(subprocess.Popen(cmd, shell=True))

    if not "NO_EXECUTE_TASKS" in environ:
        for prj in PRJS:
            cmd = (
                "cd /home/www-data/.pytigon && su - www-data -s /bin/sh -c 'exec python3.7 -m pytigon.pytigon_task %s'"
                % (get_executable(), prj)
            )
            print(cmd)
            ret_tab.append(subprocess.Popen(cmd, shell=False))

    restart = subprocess.Popen("nginx -g 'daemon off;'", shell=True)
    restart.wait()

    for pos in ret_tab:
        pos.wait()
