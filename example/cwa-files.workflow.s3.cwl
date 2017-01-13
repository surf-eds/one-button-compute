#!/usr/bin/env cwl-runner
cwlVersion: v1.0
class: Workflow
label: Run workflow on each file in a directory on S3 and upload each output file to S3
doc: |
  Foreach file in input_dir run cwa-file.workflow.s3.cwl

  Below is an example using CLI commands.

  input_dir=mine/eds/run1/input
  (mine=a mc client alias for a S3 server,
  eds=a bucket on the S3 server)

  mc ls mine/eds/run1/input
  # loop over output = [file1]
  cwl-runner cwa-file.workflow.s3.cwl --input_file file1 <inputs of this workflow>

inputs:
  input_dir: string
  output_dir: string
  output_extension: string
  # Storage specific inputs
  config-folder: Directory
outputs: []  # TODO list of files uploaded to output_dir
requirements:
  - class: ScatterFeatureRequirement
  - class: SubworkflowFeatureRequirement
steps:
  list_input_dir:
    run: ../tools/mc-ls.tool.cwl
    in:
      target: input_dir
      config-folder: config-folder
    out:
    - objects
  loop_input_files:
    in:
      input_dir: input_dir
      input_file: list_input_dir/objects
      output_dir: output_dir
      output_extension: output_extension
      config-folder: config-folder
    out: []
    scatter:
    - input_file
    scatterMethod: dotproduct
    run: cwa-file.workflow.s3.cwl
