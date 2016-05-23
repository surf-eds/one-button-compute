# One button compute

Web site to perform a calculation of a single input using a single command line call inside a docker container.

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
# Create settings.cfs
```

Automaticly start one-button-compute on boot with upstart file

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

```
pip install -r requirements.txt
cp settings.cfg-dist settings.cfg
```

Add Beehub credentials to settings.cfg and start web server with

```
python onebuttoncompute.py
```