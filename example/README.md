Simple docker container that performs a word count.

# Prerequisites

Build Docker image
Run:
```
docker build -t wca .
```

Install CWL runner.
```
pip install cwl-runner
```

# Single file

## Run using Docker

It takes 2 arguments:
1. Input text file
2. Output text file

Create a input file and run with input and output volumes mounted.
```
echo Lorem ipsum dolor sit amet > input
docker run -ti --rm -u $UID -v $PWD:/input -v $PWD:/output wca /input/input /output/output
cat output
```

## Run using cwl-runner

```
./example/cwa.tool.cwl --input README.md --output README.wc
```
This will execute cwa script inside Docker container using cwl-runner.

## Run from web app

Must use version >= v2.0.0 and < 3.0.0 of one-button-compute repo.

1. Upload a text file and workflow file (cwa.tool.cwl) to a BeeHub (https://www.beehub.nl).
2. Create a output directory on Beehub.
3. Submit in web application

* CWL workflow file: cwa.tool.cwl
* Input file:
* Output directory:

# Multiple files

## Run using cwl-runner

The job order file (cwa-files.job.yml) contains the list of input files and output filenames.

```
./example/cwa-files.tool.cwl cwa-files.job.yml
```
