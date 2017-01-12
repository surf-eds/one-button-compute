cwlVersion: v1.0
class: CommandLineTool
label: mc cp <local> <remote>
doc: Upload local file to remote storage using mc client
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
    type: string
    inputBinding:
      position: 2
  target:
    type: string
    inputBinding:
      position: 3
outputs:
  target:
    type: File
    outputBinding:
      glob: $(inputs.target)

