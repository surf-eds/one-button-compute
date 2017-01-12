cwlVersion: v1.0
class: CommandLineTool
label: mc cp <remote> <local>
doc: Download file on remote storage to local file using mc client
baseCommand: mc
arguments:
- cp
- --json
inputs:
  config-folder:
    type: Directory
    inputBinding:
      prefix: --config-folder
      position: -1
  recursive:
    type: boolean
    default: false
    inputBinding:
      prefix: --recursive
      position: 1
  source:
    type: File
    inputBinding:
      position: 2
  target:
    type: string
    inputBinding:
      position: 3
outputs: []
