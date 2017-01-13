#!/usr/bin/env cwl-runner
cwlVersion: v1.0
class: Workflow
label: Download input file from S3, run workflow, upload output file to S3
doc: |
  1. download input file
  2. runs user workflow
  3. upload output file to output_dir

  Below is an example using CLI commands.

  input_dir=mine/eds/run1/input
  (mine=a mc client alias for a S3 server,
  eds=a bucket on the S3 server)
  input_file=file1
  output_dir=mine/eds/run1/output
  output_extension=.wc

  mc cp mine/eds/run1/input/file1 file1
  cwl-runner cwa.tool.cwl --input file1 --output file1.wc
  mc cp file1.wc mine/eds/run1/output/file1.wc
requirements:
  - class: SubworkflowFeatureRequirement
  - class: StepInputExpressionRequirement
inputs:
  input_dir: string
  input_file: string
  output_dir: string
  output_extension: string
  # Storage specific inputs
  config-folder: Directory
outputs: []  # TODO uploaded output filename
steps:
  download_input_file:
    in:
      source:
        source:
        - input_dir
        - input_file
        valueFrom: $(self.join('/'))
      target: input_file
      config-folder: config-folder
    out:
    - target
    run: ../tools/mc-download.tool.cwl
  run_user_workflow:
    in:
      input: download_input_file/target
      output:
        source:
        - input_file
        - output_extension
        valueFrom: $(self.join(''))
    out:
    - outputfile
    run: cwa.tool.cwl  # Workflow of user
  upload_output_file:
    run: ../tools/mc-upload.tool.cwl
    in:
      source: run_user_workflow/outputfile
      target:
        source:
        - output_dir
        - input_file
        - output_extension
        valueFrom: $(self[0] + '/' + self[1] + self[2])
      config-folder: config-folder
    out: []