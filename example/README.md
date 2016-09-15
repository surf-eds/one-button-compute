Examples which can be used in One Button Compute application.

For more examples see https://github.com/surf-eds/cwl-examples

# Prerequisites

Install CWL runner.
```
pip install cwl-runner
```

# Word count example

Simple docker container that performs a word count.

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

## Run using cwl-runner with multiple files


The job order file (cwa-files.job.yml) contains the list of input files and output filenames.

```
./example/cwa-files.tool.cwl cwa-files.job.yml
```

### Run from web app with multiple files and using Minio server

Must use version >= v3.0.0 of one-button-compute repo.

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

The output can be cleared with
```
mc rm -r --force myminio/mybucket/obc/run1/output
```

### Use Swift storage

To run a cwl from Openstack Swift storage.

```
# Create a container for input
swift post -w $OS_USERNAME -r $OS_USERNAME eds
# Upload input file
swift upload --object-name pointcloud2images/input/rock-section.zip eds rock-section.zip
# Upload cwl
swift upload --object-name pointcloud2images/images2pointcloud.workflow.packed.cwl eds images2pointcloud.workflow.packed.cwl
```

In the One Button Compute web interface fill form with

* Input directory = pointcloud2images/input
* CWL workflow file = pointcloud2images/images2pointcloud.workflow.packed.cwl
* Output directory = pointcloud2images/output

The output can be cleared with
```
swift delete -p pointcloud2images/output eds
```

Use s3curl with s3sara alias in ~/.s3curl
```
# List bucket
s3curl.pl --id s3sara -- https://s3.swift.surfsara.nl/eds |xml_pp
# Download
s3curl.pl --id s3sara -- https://s3.swift.surfsara.nl/eds/pointcloud2images/input/rock-section.zip > rock-section.zip
# Upload
s3curl.pl --id s3sara --put=rr.zip -- https://s3.swift.surfsara.nl/eds/pointcloud2images/input/rr.zip
s3curl.pl --id s3sara --delete -- https://s3.swift.surfsara.nl/eds/pointcloud2images/input/rr.zip
```
