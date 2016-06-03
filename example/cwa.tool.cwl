#!/usr/bin/env cwl-runner

cwlVersion: draft-3
class: CommandLineTool
description: "Count number of chars, words and lines"
requirements:
- class: DockerRequirement
  dockerImageId: wca
  dockerFile:
    "$include": "Dockerfile"
inputs:
  - id: input
    type: File
    inputBinding:
      position: 1
  - id: output
    type: string
    inputBinding:
      position: 2
outputs:
  - id: outputfile
    type: File
    outputBinding:
      glob: $(inputs.output)
baseCommand: /bin/wca

