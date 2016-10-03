# One button compute

[![Build Status](https://travis-ci.org/surf-eds/one-button-compute.svg?branch=master)](https://travis-ci.org/surf-eds/one-button-compute)

Web site runs a workflow.

# Feature/Limitations

* Workflow is a single file in [Common Workflow format](http://www.commonwl.org/)
* Workflow must take single input file (--input option) and generates a single output file (--output option)
* Web application runs workflow on directory of input files
* The workflow, the directory with input files is downloaded from a remote storage server
* The directory with output files is uploaded to a remote storage server

The remote storage server can be WebDAV or S3 or Swift.

* The WebDAV server used for production is BeeHub (https://www.beehub.nl)
* The WebDAV server used for local development can be the Docker container `nlesc/xenon-webdav` (https://hub.docker.com/r/nlesc/xenon-webdav/)
* The S3 server used for local development is Minio (https://minio.io) instance, Minio is a single user S3 compliant server
* The Swift server used for production is a Openstack Swift (http://swift.openstack.org) instance

# Requirements

* Python2
* Docker
* Read/write access to a remote storage server. Can be a WebDAV or S3 or Swift server/account.

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

## S3 development server (optional)

A Minio server can be started with
```
mkdir -p minio/export
docker run -d --name obc-minio -p 9000:9000 -v $PWD/minio:/root minio/minio /root/export
docker logs obc-minio
```

The log output contains the credentials, urls and access instructions.

To use known credentials from settings.cfg start it with
```
docker run -d --name obc-minio -p 9000:9000 -v $PWD/minio:/root -e "MINIO_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE" \
  -e "MINIO_SECRET_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY" minio/minio /root/export
```

Use `mc` (https://docs.minio.io/docs/minio-client-quickstart-guide) as CLI client.

## WebDAV development server (optional)

A WebDAV server can be started with
```
docker run -d nlesc/xenon-webdav
```

Read/write can be done in `~/xenon/uploads` path with xenon:javagat credentials.

Use `cadaver` (http://www.webdav.org/cadaver/) as CLI client.

## Reverse proxy (optional)

Configure Nginx as reverse proxy for the flask app port 5000.

```
location / {
  proxy_pass http://localhost:5000;
}
```

## Auto start (optional)

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

# Automatic deployment

Use ansible playbook to setup server

Create a host group called `obc`.
Add a host to the group.
Add the following vars:

* obc_web_user
* obc_web_pw
* obc_domain
* domain_email

Create a local one-button-compute config file called `settings.cfg` (it will be copied to deployment machine)
Create a local Openstack Swift config file called `keystonerc` (it will be sourced before deamons stats)

Run playbook with something like:

```
ansible-playbook -v -i ansible.hosts -b -u ubuntu ansible-playbook.yml
```
