import logging
import os
import shutil
import tempfile
import uuid
from urlparse import urlparse
from flask import Flask, render_template, request
import easywebdav
from docker import Client as DockerClient

app = Flask(__name__)
app.config.from_pyfile('settings.cfg')


class BeeHub(object):
    def __init__(self, root, username, password):
        o = urlparse(root)
        self.path = o.path
        self.client = easywebdav.connect(
            host=o.netloc,
            protocol=o.scheme,
            username=username,
            password=password,
        )
        self.username = username
        self.password = password

    @classmethod
    def from_config(cls, config):
        return BeeHub(config['BEEHUB_ROOT'],
                      config['BEEHUB_USERNAME'],
                      config['BEEHUB_PASSWORD'],
                      )

    def download(self, source, target):
        logging.warning(('Download', self.path + '/' + source, target))
        return self.client.download(self.path + '/' + source, target)

    def upload(self, source, target):
        return self.client.upload(source, self.path + '/' + target)


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/compute', methods=['POST'])
def compute():
    remote_input_file = request.form['inputfile']
    image = request.form['dockerimage']
    remote_output_dir = request.form['outputdir']

    exit_code, log, result_url = perform_computation(image, remote_input_file, remote_output_dir)

    return render_template('result.html', result_url=result_url, exit_code=exit_code, log=log)


def perform_computation(image, remote_input_file, remote_output_dir):
    session_dir = tempfile.mkdtemp('session', prefix='onebuttoncompute')
    local_input_dir = session_dir + '/in'
    os.mkdir(local_input_dir)
    local_output_dir = session_dir + '/out'
    os.mkdir(local_output_dir)

    # Download input file from beehub to inputdir
    input_file = 'input'
    beehub = BeeHub.from_config(app.config)
    local_input_file = local_input_dir + '/' + input_file
    beehub.download(remote_input_file, local_input_file)
    # Run Docker
    output_file = 'output'

    exit_code, log = run_docker(image, input_file, local_input_dir, local_output_dir, output_file)

    # Upload content of output dir to Beehub
    remote_output_file = remote_output_dir + '/' + output_file
    abs_output_file = local_output_dir + '/' + output_file
    beehub.upload(abs_output_file, remote_output_file)

    shutil.rmtree(session_dir)

    result_url = app.config['BEEHUB_ROOT'] + '/' + request.form['outputdir']
    return exit_code, log, result_url


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
    volumes = [docker_input_dir, docker_output_dir]
    binds = [
        local_input_dir + ':' + docker_input_dir,
        local_output_dir + ':' + docker_output_dir,
    ]
    docker_client = DockerClient()
    if docker_client.images(image):
        docker_client.pull(image)
    uniq_name = str(uuid.uuid4())
    host_config = docker_client.create_host_config(binds=binds)
    container = docker_client.create_container(image, command,
                                               user=uid,
                                               volumes=volumes,
                                               host_config=host_config,
                                               name=uniq_name)
    logging.warning(container)
    docker_client.start(container)
    exit_code = docker_client.wait(container)
    log = docker_client.logs(container)
    # docker_client.remove_container(container)
    logging.warning(exit_code)
    logging.warning(log)
    return exit_code, log


if __name__ == '__main__':
    app.run()
