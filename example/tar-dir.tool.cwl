class: CommandLineTool
cwlVersion: v1.0
doc: "Compresses content of directory in gzipped tarball"
requirements:
  - class: ShellCommandRequirement
inputs:
  input: Directory
  output:
    type: string
    default: tarball.tar.gz
outputs:
  tarball:
    type: File
    outputBinding:
      glob: "$(inputs.output)"
arguments:
- sleep
- "5"
- {shellQuote: false, valueFrom: "&&"}
- tar
- "-jchf"
- "$(inputs.output)"
- "-C"
- "$(inputs.input.path)"
- "."