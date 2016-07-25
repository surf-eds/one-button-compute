#!/usr/bin/env cwl-runner

cwlVersion: v1.0
class: CommandLineTool
doc: "Count number of chars, words and lines"
requirements:
- class: DockerRequirement
  dockerImageId: wca
  dockerFile:
    "$include": "Dockerfile"
inputs:
  input:
    type: File
    inputBinding:
      position: 1
  output:
    type: string
    inputBinding:
      position: 2
outputs:
  outputfile:
    type: File
    outputBinding:
      glob: $(inputs.output)
baseCommand: /bin/wca

