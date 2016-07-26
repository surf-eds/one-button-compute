import logging
import os
import shutil
import tempfile
import uuid
from urlparse import urlparse
from flask import Flask, render_template, request, redirect, jsonify, url_for
from celery import Celery
import easywebdav
import subprocess
from cwltool.load_tool import fetch_document, validate_document, make_tool
from cwltool.workflow import defaultMakeTool
from cwltool.main import load_job_order
from docker import Client as DockerClient


app = Flask(__name__)
app.config.from_pyfile('settings.cfg')
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'
app.config['CELERY_TRACK_STARTED'] = True
app.config['CELERY_TASK_SERIALIZER'] = 'json'
app.config['CELERY_ACCEPT_CONTENT'] = ['json']
app.config['CELERY_RESULT_SERIALIZER'] = 'json'

celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)


class BeeHub(object):
    def __init__(self, root, username, password):
        o = urlparse(root)
        logging.warning(o)
        logging.warning(o.path)
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


@app.route('/jobs', methods=['POST'])
def submit_job():
    data = request.get_json()
    remote_input_file = data['inputfile']
    remote_workflow_file = data['cwl_workflow']
    remote_output_dir = data['outputdir']

    job = perform_computation.delay(remote_workflow_file, remote_input_file, remote_output_dir)
    return redirect("/jobs/{0}".format(job.id))


@app.route('/jobs/<job_id>', methods=['GET'])
def status_job(job_id):
    job = perform_computation.AsyncResult(job_id)
    response = {
        'id': url_for('status_job', job_id=job_id),
        'state': job.state,
    }
    if job.successful():
        response['result'] = job.result
    elif job.failed():
        # result is an exception
        response['result'] = str(job.result)
    return jsonify(response)


@celery.task(bind=True)
def perform_computation(self, remote_workflow_file, remote_input_file, remote_output_dir):
    self.update_state(state='PRESTAGING')
    session_dir = tempfile.mkdtemp('-session', prefix='onebuttoncompute-')
    local_input_dir = session_dir + '/in'
    os.mkdir(local_input_dir)
    local_output_dir = session_dir + '/out'
    os.mkdir(local_output_dir)

    logging.warning('Downloading input file and workflow')
    # Download input file from beehub to inputdir
    input_file = 'input'
    beehub = BeeHub.from_config(app.config)
    local_input_file = local_input_dir + '/' + input_file
    beehub.download(remote_input_file, local_input_file)
    workflow_file = 'workflow.cwl'
    local_workflow_file = local_input_dir + '/' + workflow_file
    beehub.download(remote_workflow_file, local_workflow_file)
    output_file = 'output'

    self.update_state(state='RUNNING')
    exit_code, log = run_cwl(local_workflow_file, input_file, local_input_dir, local_output_dir, output_file)

    self.update_state(state='POSTSTAGING')
    logging.warning('Uploading output file')
    # Upload content of output dir to Beehub
    remote_output_file = remote_output_dir + '/' + output_file
    abs_output_file = local_output_dir + '/' + output_file
    beehub.upload(abs_output_file, remote_output_file)

    # logging.warning('Clear session')
    shutil.rmtree(session_dir)

    result_url = app.config['BEEHUB_ROOT'] + '/' + remote_output_dir

    return exit_code, log, result_url


def run_cwl(workflow_file, input_file, local_input_dir, local_output_dir, output_file):

    logging.warning('Validating cwl')
    document_loader, workflowobj, uri = fetch_document(workflow_file)
    document_loader, avsc_names, processobj, metadata, uri = validate_document(document_loader, workflowobj, uri)
    # tool = make_tool(document_loader, avsc_names, metadata, uri,
    #                  defaultMakeTool, {})
    # job_order_object = load_job_order(args, tool, stdin,
    #                                   print_input_deps=args.print_input_deps,
    #                                   relative_deps=args.relative_deps,
    #                                   stdout=stdout)

    logging.warning('Running cwl')
    # logging.warning('Starting xenon')

    # import xenon
    # with xenon.Xenon() as xe:
    #     job_api = xe.jobs()
    #     scheduler = job_api.newScheduler('local', 'localhost', None, None)
    #     desc = xenon.jobs.JobDescription()
    #     desc.setExecutable('cwl-runner')
    #     desc.setArguments(workflow_file, input_file, output_file)
    #     cwl_stdout = local_output_dir + 'stdout.txt'
    #     desc.setStdout(cwl_stdout)
    #     cwl_stderr = local_output_dir + 'stderr.txt'
    #     desc.setStderr(cwl_stderr)
    #
    #     job = job_api.submitJob(scheduler, desc)
    #     job_api.waitUntilDone(job, 1000)
    #
    #     job_status = job_api.getJobStatus(job)
    #     exit_code = job_status.getExitCode()
    #
    # log = ['STDERR:\n']
    # with open(cwl_stderr) as f:
    #     log += f.readlines()
    # log.append('STDOUT:\n')
    # with open(cwl_stdout) as f:
    #     log += f.readlines()

    args = 'cwl-runner {0} --input {1}/{2} --output {3}'.format(workflow_file, local_input_dir, input_file, output_file)

    logging.warning(args)

    p = subprocess.Popen(args,
                         shell=True,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         close_fds=False,
                         cwd=local_output_dir)
    (child_stdout, child_stderr) = p.communicate()
    exit_code = p.returncode
    log = ['STDERR:\n', child_stderr, 'STDOUT:\n', child_stdout]

    logging.warning('Completed cwl run')

    return exit_code, ''.join(log)


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
    app.run(host='0.0.0.0', threaded=True)
