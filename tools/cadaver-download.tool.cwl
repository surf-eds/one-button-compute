cwlVersion: v1.0
class: CommandLineTool
label: cadaver get <remote> <local>
doc: Download file from WebDav server with cadaver client
requirements:
- class: InlineJavascriptRequirement
- class: EnvVarRequirement
  envDef:
    CADAVER_MACHINE: $(inputs.machine)
    CADAVER_LOGIN: $(inputs.login)
    CADAVER_PASSWORD: $(inputs.password)
- class: DockerRequirement
  dockerImageId: cadaver
  dockerFile: |
    FROM alpine
    # cadaver fetches credentials from ~/.netrc or interactivly,
    # create a cadaver wrapper which generates a .netrc from environment vars
    RUN apk add --no-cache cadaver && \
    echo -e '#!/bin/ash\necho "machine $CADAVER_MACHINE login $CADAVER_LOGIN password $CADAVER_PASSWORD" > ~/.netrc\ncadaver $*' > /usr/bin/cadaver.sh && \
    chmod +x /usr/bin/cadaver.sh
    CMD ["cadaver.sh"]
- class: InitialWorkDirRequirement
  listing:
    - entryname: cadaver.cmds
      entry: $('get ' + inputs.source + ' ' + inputs.target)
baseCommand: cadaver.sh
# TODO cadaver expects the commands from the stdin,
# to do this in CWL we create a file with the commands with InitialWorkDirRequirement
# the generated file is then used as stdin
# a cwl-runner bug (https://github.com/common-workflow-language/cwltool/issues/195) blocks current approach
stdin: cadaver.cmds
inputs:
  machine: string
  login: string
  password: string
  path:
    type: string
    inputBinding:
      position: 1
  source:
    type: string
  target:
    type: string
outputs:
  target:
    type: File
    outputBinding:
      glob: $(inputs.target)