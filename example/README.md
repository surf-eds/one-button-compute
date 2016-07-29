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

1. Upload a text file and workflow file (cwa.tool.cwl) to the remote storage server configured in the settings.cfg file.
2. Create a output directory on remote storage server.
3. Submit in web application

* CWL workflow file: cwa.tool.cwl
* Input file:
* Output directory:

# Multiple files

Must use version >= v3.0.0 of one-button-compute repo.

## Run using cwl-runner

The job order file (cwa-files.job.yml) contains the list of input files and output filenames.

```
./example/cwa-files.tool.cwl cwa-files.job.yml
```

### Upload & run using Minio server

Requires a Minio server, see "S3 development server" section ../README.md for instructions.

With S3_ROOT of 'http://localhost:9000/mybucket/obc'
```
mc config host add myminio http://localhost:9000 *** ***
mc mb myminio/mybucket
mc cp cwa.tool.cwl myminio/mybucket/obc/run1/cwa.tool.cwl
mc cp README.md myminio/mybucket/obc/run1/input/file1.txt
mc cp cwa.tool.cwl myminio/mybucket/obc/run1/input/file2.txt
```

In the One Button Compute web interface fill form with

* Input directory = run1/input
* CWL workflow file = run1/cwa.tool.cwl
* Output directory = run1/output

# Multiple directories

Example outputs on file for each input directory.

## Local 

Setup with

```
mkdir dir1
cp README.md dir1
cp cwa.tool.cwl dir1
cp -r dir1 dir2
```

Run with

```
./tar-dirs.workflow.cwl tar-dirs.job.yml
```

