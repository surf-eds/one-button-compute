# One button compute

[![Build Status](https://travis-ci.org/surf-eds/one-button-compute.svg?branch=master)](https://travis-ci.org/surf-eds/one-button-compute)

Web site runs a workflow.
 
# Feature/Limitations

* Workflow is a single file in [Common Workflow format](http://www.commonwl.org/)
* Workflow must take single input file (--input option) and generates a single output file (--output option)
* The workflow, input file are downloaded from a webdav server
* The output file is uploaded to a webdav server

# Requirements

* Python2

# Install

1. Configure Nginx as reverse proxy for the flask app port 5000.
```
location / {
  proxy_pass http://localhost:5000
}
```
2. Install docker
```
curl -fsSL https://get.docker.com/ | sh
```

Install app:
```
cd /opt
git clone https://github.com/surf-eds/one-button-compute.git
cd one-button-compute/
pip install -r requirements.txt
# Create settings.cfg
```

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

3. Start redis server

```
docker run -d -p 6379:6379 redis
```

# Run

```
pip install -r requirements.txt
cp settings.cfg-dist settings.cfg
```

Add Beehub credentials to settings.cfg and start web server with

```
celery worker -A onebuttoncompute.celery &
python onebuttoncompute.py
```