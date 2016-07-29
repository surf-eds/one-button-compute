#!/usr/bin/env cwl-runner
cwlVersion: v1.0
class: Workflow
doc: |
  Input and output are list of files.
  Loop over files and call tool as input-file -> tool -> output-file
inputs:
  input_dirs: Directory[]
  output_filenames: string[]
outputs:
  output_files:
    type: File[]
    outputSource: step1/tarball
requirements:
  - class: ScatterFeatureRequirement
  - class: StepInputExpressionRequirement
steps:
  step1:
    run: tar-dir.tool.cwl
    in:
      input: input_dirs
      output: output_filenames
    out:
    - tarball
    scatter:
    - input
    - output
    scatterMethod: dotproduct
#  step2:
#    doc: Moves all files and directories from step1 to output_dir
#    out:
#    - output
# TODO implement rest of step2
