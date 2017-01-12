cwlVersion: v1.0
class: CommandLineTool
label: mc config host add
doc: Configure hosts for mc client
baseCommand: mc
arguments:
- config
- host
- add
inputs:
  config-folder:
    type: Directory
    inputBinding:
      prefix: --config-folder
      position: -1
  alias:
    type: string
    inputBinding:
      position: 1
  endpoint:
    type: string
    inputBinding:
      position: 1
  access:
    type: string
    inputBinding:
      position: 1
  secret:
    type: string
    inputBinding:
      position: 1
  signature:
    type: string
    default: S3v4
    inputBinding:
      position: 1
outputs: []
