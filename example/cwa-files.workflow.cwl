#!/usr/bin/env cwl-runner
cwlVersion: v1.0
class: Workflow
doc: |
  Input and output are list of files.
  Loop over files and call tool as input-file -> tool -> output-file
inputs:
  input_files: File[]
  output_filenames: string[]
outputs:
  output_files:
    type: File[]
    outputSource: step1/outputfile
requirements:
  - class: ScatterFeatureRequirement
steps:
  step1:
    run: cwa.tool.cwl
    in:
      input: input_files
      output: output_filenames
    out:
    - outputfile
    scatter:
    - input
    - output
    scatterMethod: dotproduct
