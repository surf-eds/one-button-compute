import logging
import os
import subprocess
import shutil
import tempfile
from urlparse import urlparse

from celery import Celery
from cwltool.load_tool import fetch_document, validate_document
from flask import Flask, render_template, request, redirect, jsonify, url_for
import easywebdav
import ruamel.yaml as yaml

app = Flask(__name__)
app.config.from_pyfile('settings.cfg')
app.config['CELERY_TRACK_STARTED'] = True
app.config['CELERY_TASK_SERIALIZER'] = 'json'
app.config['CELERY_ACCEPT_CONTENT'] = ['json']
app.config['CELERY_RESULT_SERIALIZER'] = 'json'

celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)


class WebDAV(object):
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

    def download(self, source, target):
        logging.warning(('Download', self.path + '/' + source, target))
        return self.client.download(self.path + '/' + source, target)

    def upload(self, source, target):
        return self.client.upload(source, self.path + '/' + target)

    def ls(self, path):
        """List files/directories in path

        Args:
            path (str):

        Returns:
            list: File name or directory (ends with /) relative to path
        """
        fpath = self.path + '/' + path
        listing = self.client.ls(fpath)
        return [d.name.replace(fpath + '/', '') for d in listing if d.name != fpath + '/']


def remote_storage_client(config):
    if config['REMOTE_STORAGE_TYPE'] is 'WEBDAV':
        return WebDAV(config['WEBDAV_ROOT'],
                      config['WEBDAV_USERNAME'],
                      config['WEBDAV_PASSWORD'],
                      )


def remote_url(config, path):
    if config['REMOTE_STORAGE_TYPE'] is 'WEBDAV':
        return config['WEBDAV_ROOT'] + '/' + path


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/jobs', methods=['POST'])
def submit_job():
    data = request.get_json()
    remote_input_dir = data['inputdir'].rstrip('/')
    remote_workflow_file = data['cwl_workflow']
    remote_output_dir = data['outputdir'].rstrip('/')
    # TODO validate extension, it should not contain dangerous chars, as it will be part of an argument of a system call
    output_extension = data['outputextension']

    job = perform_computation.delay(remote_workflow_file, remote_input_dir, remote_output_dir, output_extension)
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


def write_job_order(session_dir, input_dir, input_files, output_files, job_order_fn='job.yml'):
    abs_job_order_fn = session_dir + '/' + job_order_fn
    cwl_input_files = [{'class': 'File', 'path': input_dir + '/' + d} for d in input_files]
    data = {
        'input_files': cwl_input_files,
        'output_filenames': output_files,
    }

    logging.warning(data)

    with open(abs_job_order_fn, 'w') as f:
        yaml.dump(data, f, Dumper=yaml.SafeDumper)
    return job_order_fn


def write_workflow_wrapper(session_dir, workflow_file, workflow_wrapper_fn='workflow.wrapper.cwl'):
    abs_workflow_wrapper_fn = session_dir + '/' + workflow_wrapper_fn
    wrapper = {
        'class': 'Workflow',
        'cwlVersion': 'v1.0',
        'inputs': {
            'input_files': 'File[]',
            'output_filenames': 'string[]'
        },
        'outputs': {
            'output_files': {
                'outputSource': 'step1/outputfile',
                'type': 'File[]'
            }
        },
        'requirements': [{'class': 'ScatterFeatureRequirement'}],
        'steps': {
            'step1': {
                'in': {
                    'input': 'input_files',
                    'output': 'output_filenames'
                },
                'out': ['outputfile'],
                'run': workflow_file,
                'scatter': ['input', 'output'],
                'scatterMethod': 'dotproduct'
            }
        }
    }

    with open(abs_workflow_wrapper_fn, 'w') as f:
        yaml.dump(wrapper, f, Dumper=yaml.SafeDumper)
    return workflow_wrapper_fn


@celery.task(bind=True)
def perform_computation(self, remote_workflow_file, remote_input_dir, remote_output_dir, output_extension=''):
    self.update_state(state='PRESTAGING')
    remote_storage = remote_storage_client(app.config)
    input_dir = 'in'
    output_dir = 'out'
    local_input_dir, local_output_dir, session_dir = create_session_dir(input_dir, output_dir)
    workflow_file = fetch_workflow(remote_storage, session_dir, remote_workflow_file)
    input_files = fetch_input_files(remote_storage, local_input_dir, remote_input_dir)
    output_files = ['{0}{1}'.format(d, output_extension) for d in input_files]
    job_order_file = write_job_order(session_dir, input_dir, input_files, output_files)
    workflow_wrapper_file = write_workflow_wrapper(session_dir, workflow_file)

    self.update_state(state='RUNNING')
    result = run_cwl(workflow_wrapper_file, job_order_file, session_dir, output_dir)

    logging.warning(result)

    self.update_state(state='POSTSTAGING')
    upload_output_files(remote_storage, local_output_dir, output_files, remote_output_dir)
    shutil.rmtree(session_dir)

    result_url = remote_url(app.config, remote_output_dir)
    result['url'] = result_url
    return result


def create_session_dir(input_dir, output_dir):
    session_dir = tempfile.mkdtemp('-session', prefix='onebuttoncompute-')
    local_input_dir = session_dir + '/' + input_dir
    os.mkdir(local_input_dir)
    local_output_dir = session_dir + '/' + output_dir
    os.mkdir(local_output_dir)
    return local_input_dir, local_output_dir, session_dir


def upload_output_files(beehub, local_output_dir, output_files, remote_output_dir):
    # TODO update celery state with number of files copied vs total
    # TODO perform copy of files in parallel using Celery group
    for output_file in output_files:
        local_output_file = local_output_dir + '/' + output_file
        remote_output_file = remote_output_dir + '/' + output_file
        beehub.upload(local_output_file, remote_output_file)


def fetch_input_files(beehub, local_input_dir, remote_input_dir):
    # TODO update celery state with number of files copied vs total
    # TODO perform copy of files in parallel using Celery group
    input_files = []
    for input_file in beehub.ls(remote_input_dir):
        remote_input_file = remote_input_dir + '/' + input_file
        local_input_file = local_input_dir + '/' + input_file
        beehub.download(remote_input_file, local_input_file)
        input_files.append(input_file)
    return input_files


def fetch_workflow(beehub, local_input_dir, remote_workflow_file, workflow_file='workflow.cwl'):
    logging.warning('Downloading cwl')
    local_workflow_file = local_input_dir + '/' + workflow_file
    beehub.download(remote_workflow_file, local_workflow_file)
    logging.warning('Validating cwl')
    document_loader, workflowobj, uri = fetch_document(local_workflow_file)
    validate_document(document_loader, workflowobj, uri)
    return local_workflow_file


def run_cwl(workflow_file, job_order_file, session_dir, output_dir):

    logging.warning('Running cwl')

    args = 'cwl-runner --quiet --outdir {0} {1} {2}'.format(output_dir, workflow_file, job_order_file)

    logging.warning(args)

    p = subprocess.Popen(args,
                         shell=True,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         close_fds=False,
                         cwd=session_dir)
    (child_stdout, child_stderr) = p.communicate()
    exit_code = p.returncode

    logging.warning('Completed cwl run')
    output_object = yaml.load(child_stdout)

    return {'exit_code': exit_code, 'log': child_stderr, 'output_object': output_object}

if __name__ == '__main__':
    app.run(host='0.0.0.0', threaded=True)
