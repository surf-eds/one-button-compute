import logging
import os
import tempfile
from urllib.parse import urlparse
from flask import Flask, render_template, request
import webdav.client.Client as WebDAVClient
from docker import Client as DockerClient

app = Flask(__name__)
app.config.from_pyfile('settings.cfg')


class BeeHub(object):
    def __init(self, root, username, password):
        o = urlparse(root)
        self.path = o.path
        self.client = WebDAVClient({
            'webdav_hostname': o.scheme + '://' + o.netloc,
            'webdav_login': username,
            'webdav_password': password,
        })
        self.username = username
        self.password = password

    @classmethod
    def from_config(cls, config):
        return BeeHub(config['BEEHUB_ROOT'],
                      config['BEEHUB_USERNAME'],
                      config['BEEHUB_PASSWORD'],
                      )

    def download(self, source, target):
        return self.client.download_sync(remote_path=self.path + '/' + source, local_path=target)

    def upload(self, source, target):
        return self.client.upload_sync(local_path=source, remote_path=self.path + '/' + target)


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/compute', methods=['POST'])
def compute():
    remote_input_file = request.form['inputfile']
    image = request.form['dockerimage']
    remote_output_dir = request.form['outputdir']

    local_input_dir = tempfile.TemporaryDirectory('in')
    local_output_dir = tempfile.TemporaryDirectory('out')

    # Download input file from beehub to inputdir
    input_file = 'input'
    beehub = BeeHub.from_config(app.config)
    local_input_file = local_input_dir.name + '/' + input_file
    beehub.download(remote_input_file, local_input_file)

    # Run Docker
    output_file = 'output'
    exit_code, log = run_docker(image, input_file, local_input_dir, local_output_dir, output_file)

    # Upload content of output dir to Beehub
    remote_output_file = remote_output_dir + '/' + output_file
    abs_output_file = local_output_dir.name + '/' + output_file
    beehub.upload(abs_output_file,  remote_output_file)

    local_input_dir.cleanup()
    local_output_dir.cleanup()

    result_url = app.config['BEEHUB_ROOT'] + request.form['outputdir']

    return render_template('result.html', result_url=result_url, exit_code=exit_code, log=log)


def run_docker(image, input_file, local_input_dir, local_output_dir, output_file):
    docker_input_dir = '/input'
    docker_output_dir = '/output'
    docker_input_file = docker_input_dir + '/' + input_file
    docker_output_file = docker_output_dir + '/' + output_file
    command = [
        docker_input_file,
        docker_output_file,
    ]
    uid = os.geteuid()
    volumes = [
        local_input_dir.name + ':' + docker_input_dir,
        local_output_dir.name + ':' + docker_output_dir,
    ]
    docker_client = DockerClient()
    container = docker_client.create_container(image, command, user=uid, volumes=volumes)
    docker_client.start(container)
    exit_code = docker_client.wait(container)
    log = docker_client.logs(container)
    docker_client.remove_container(container)
    return exit_code, log


if __name__ == '__main__':
    app.run()