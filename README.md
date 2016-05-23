# One button compute

Web site to perform a calculation of a single input using a single command line call inside a docker container.

# Requirements

* Python2

# Run

```
pip install -r requirements.txt
cp settings.cfg-dist settings.cfg
```

Add Beehub credentials to settings.cfg and start web server with

```
python onebuttoncompute.py
```