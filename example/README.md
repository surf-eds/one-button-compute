Simple docker container that performs a word count.

# Run from command line

It takes 2 arguments:
1. Input text file
2. Output text file

Create a input file and run with input and output volumes mounted.
```
echo Lorem ipsum dolor sit amet > input
docker run -ti --rm -u $UID -v $PWD:/input -v $PWD:/output wca /input/input /output/output
cat output
```

# Run from web app

1. Upload a text file to a BeeHub (https://www.beehub.nl).
2. Create a output directory on Beehub.
3. Submit in webapplication

* input:
* outputdir:
* image: wca

# Build

Run:
```
docker build -t wca .
```

# Run tool as cwl

Install CWL runner.
```
pip install cwl-runner
```

```
cwl-runner --debug example/cwa.tool.cwl --input README.md --output README.wc
```
This will execute cwa script inside Docker container using cwl-runner.


