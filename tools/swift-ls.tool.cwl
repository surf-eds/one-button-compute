cwlVersion: v1.0
class: CommandLineTool
label: swift list
doc: List objects on OpenStack Swift server
requirements:
- class: InlineJavascriptRequirement
- class: EnvVarRequirement
  envDef:
    OS_AUTH_URL: $(inputs.keystone.OS_AUTH_URL)
    OS_IDENTITY_API_VERSION: $(inputs.keystone.OS_IDENTITY_API_VERSION)
    OS_AUTH_VERSION: $(inputs.keystone.OS_AUTH_VERSION)
    OS_REGION_NAME: $(inputs.keystone.OS_REGION_NAME)
    OS_PROJECT_DOMAIN_ID: $(inputs.keystone.OS_PROJECT_DOMAIN_ID)
    OS_USER_DOMAIN_ID: $(inputs.keystone.OS_USER_DOMAIN_ID)
    OS_PROJECT_NAME: $(inputs.keystone.OS_PROJECT_NAME)
    OS_TENANT_NAME: $(inputs.keystone.OS_TENANT_NAME)
    OS_USERNAME: $(inputs.keystone.OS_USERNAME)
    OS_PASSWORD: $(inputs.keystone.OS_PASSWORD)
- class: DockerRequirement
  dockerImageId: openstack-swift
  dockerFile: |
    FROM python:3
    RUN pip install python-swiftclient python-keystoneclient
    CMD ["ash"]
baseCommand: swift
arguments:
- list
inputs:
  keystone:
    type:
      type: record
      fields:
        OS_AUTH_URL:
          type: string
        OS_IDENTITY_API_VERSION:
          type: string
        OS_AUTH_VERSION:
          type: string
        OS_REGION_NAME:
          type: string
        OS_PROJECT_DOMAIN_ID:
          type: string
        OS_USER_DOMAIN_ID:
          type: string
        OS_PROJECT_NAME:
          type: string
        OS_TENANT_NAME:
          type: string
        OS_USERNAME:
          type: string
        OS_PASSWORD:
          type: string
  container:
    type: string
    inputBinding:
      position: 1
  prefix:
    type: string
    inputBinding:
      prefix: --prefix
      position: 2
outputs:
  objects:
    type: string[]
    outputBinding:
      glob: output.txt
      loadContents: true  # Watch out, will only load first 64Kb of stdout
      outputEval: |
        ${
          var lines = self[0].contents.split(/\r?\n/);
          lines.pop();
          return lines;
        }
stdout: output.txt
