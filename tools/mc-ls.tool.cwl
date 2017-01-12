cwlVersion: v1.0
class: CommandLineTool
label: mc ls
doc: List buckets and objects with mc client
requirements:
- class: InlineJavascriptRequirement
baseCommand: mc
arguments:
- ls
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
  target:
    type: string
    inputBinding:
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
          lines.pop(); // Remove trailing empty line
          return lines.map(function(d) {
            return JSON.parse(d);
          }).filter(function(d) {
            return d.type === 'file';
          }).map(function(d) {
            return d.key.replace(inputs.target, '').replace(/^[\/\\]/, '');
          });
        }
  folders:
    type: string[]
    outputBinding:
      glob: output.txt
      loadContents: true  # Watch out, will only load first 64Kb of stdout
      outputEval: |
        ${
          var lines = self[0].contents.split(/\r?\n/);
          lines.pop(); // Remove trailing empty line
          return lines.map(function(d) {
            return JSON.parse(d);
          }).filter(function(d) {
            return d.type === 'folder';
          }).map(function(d) {
            return d.key.replace(inputs.target, '').replace(/^[\/\\]/, '');
          });
        }
stdout: output.txt
