#!/usr/bin/env cwl-runner

cwlVersion: v1.0
class: CommandLineTool
doc: "Count number of chars, words and lines"
requirements:
- class: DockerRequirement
  dockerImageId: wca
  dockerFile: |
    FROM alpine
    RUN echo -e '#!/bin/sh\nsleep 10\nwc $1 > $2\necho Something to stdout\n(>&2 echo "Something to stderr")' > /bin/wca && chmod +x /bin/wca
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

