cwlVersion: v1.0
class: CommandLineTool
label: mc config host list
doc: List configured hosts of mc client
requirements:
- class: InlineJavascriptRequirement
baseCommand: mc
arguments:
- config
- host
- list
inputs:
  config-folder:
    type: Directory
    inputBinding:
      prefix: --config-folder
      position: -1
outputs:
  output:
    type: string
    outputBinding:
      loadContents: true
      outputEval: "$(self[0].contents)"
      glob: stdout.txt
stdout: stdout.txt
