# One button compute

[![Build Status](https://travis-ci.org/surf-eds/one-button-compute.svg?branch=master)](https://travis-ci.org/surf-eds/one-button-compute)

Web site runs a workflow.
 
# Feature/Limitations

* Workflow is a single file in [Common Workflow format](http://www.commonwl.org/)
* Workflow must take single input file (--input option) and generates a single output file (--output option)
* The workflow, input file are downloaded from a WebDAV server
* The output file is uploaded to a WebDAV server

The WebDAV server used for production is BeeHub (https://www.beehub.nl). 
The WebDAV server used for local development can be the Docker image nlesc/xenon-webdav (https://hub.docker.com/r/nlesc/xenon-webdav/).

# Requirements

* Python2
* Docker
* Read/write access to a remote storage server. Can be a WebDAV server.

# Install

## 1. Redis server

Redis server is used to perform computation asynchronous from http request.

Use Docker to start a redis server

```
docker run -d -p 6379:6379 redis
```

Note!: When Celery workers are going to be run on different machines make sure they can connect to the redis server. 

## 2. Install dependencies

Install the Python dependencies with
```
pip install -r requirements.txt
```

## 3. Configure the application

```
cp settings.cfg-dist settings.cfg
```

Configure remote storage type, location and credentials in settings.cfg.

## 4. Reverse proxy (optional)

Configure Nginx as reverse proxy for the flask app port 5000.

```
location / {
  proxy_pass http://localhost:5000
}
```

## 5. Auto start (optional)

Automatically start one-button-compute on boot with upstart file

```
cat /etc/init/onebuttoncompute.conf
# Running on port 5000

description "One button compute"

start on filesystem or runlevel [2345]
stop on runlevel [!2345]

script
  cd /opt/one-button-compute
  python onebuttoncompute.py
end script
```

# Run

Start Celery worker and web server with
```
celery worker -A onebuttoncompute.celery &
python onebuttoncompute.py
```

# Usage

Add a CWL workflow and input files to remote storage. 
See `example/` sub-directory for an example workflow.

Go to http://localhost:5000/ (or http://&lt;server-name&gt;/ when reverse proxy is setup) to submit a computation.