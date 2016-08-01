import logging
import os
import re
import subprocess
import shutil
import tempfile
from urlparse import urlparse

from celery import Celery
from cwltool.load_tool import fetch_document, validate_document
from flask import Flask, render_template, request, redirect, jsonify, url_for
import easywebdav
import magic
import minio
import ruamel.yaml as yaml

app = Flask(__name__)
app.config.from_pyfile('settings.cfg')
app.config['CELERY_TRACK_STARTED'] = True
app.config['CELERY_TASK_SERIALIZER'] = 'json'
app.config['CELERY_ACCEPT_CONTENT'] = ['json']
app.config['CELERY_RESULT_SERIALIZER'] = 'json'

celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)


class WebDAVClient(object):
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
        return self.client.download(self.path + '/' + source, target)

    def upload(self, source, target):
        return self.client.upload(source, self.path + '/' + target)

    def ls(self, path, recursive=False, relative=None):
        """List files in path

        Args:
            path (str): The path
            recursive (bool): Whether to do ls -R or ls
            relative (str): The return files name should be relative to this, if None then set to path

        Returns:
            list: File names
        """
        fpath = self.path + '/' + path
        if relative is None:
            relative = fpath + '/'
        listing = self.client.ls(fpath)
        files = []
        for item in listing:
            if item.name == fpath + '/':
                # skip self
                continue
            if item.name.endswith('/'):
                # is directory
                if recursive:
                    files += self.ls(item.name.lstrip(self.path + '/').rstrip('/'), recursive=recursive, relative=fpath)
            else:
                files.append(item.name.lstrip(relative))

        return files

    def mkdirs(self, path):
        fpath = self.path + '/' + path
        self.client.mkdirs(fpath)


class S3Client(object):
    def __init__(self, root, access_key, secret_key):
        o = urlparse(root)
        endpoint = o.netloc
        if o.scheme == 'https':
            secure = True
        elif o.scheme == 'http':
            secure = False
        else:
            raise ValueError('Scheme "{0}" not supported'.format(o.scheme))
        paths = o.path.strip('/').split('/')
        self.bucket = paths.pop(0)
        self.prefix = '/'.join(paths)
        self.client = minio.Minio(endpoint=endpoint, access_key=access_key, secret_key=secret_key, secure=secure)

    def download(self, source, target):
        return self.client.fget_object(self.bucket, self.prefix + '/' + source, target)

    def upload(self, source, target):
        content_type = magic.from_file(source, mime=True)
        return self.client.fput_object(self.bucket, self.prefix + '/' + target, source, content_type)

    def ls(self, path, recursive=False):
        fpath = self.prefix + '/' + path + '/'
        listing = self.client.list_objects(self.bucket, prefix=fpath, recursive=recursive)
        return [d.object_name.replace(fpath, '') for d in listing]

    def mkdirs(self, path):
        # S3 has know directories
        pass


def remote_storage_client(config):
    if config['REMOTE_STORAGE_TYPE'] is 'WEBDAV':
        return WebDAVClient(config['WEBDAV_ROOT'],
                            config['WEBDAV_USERNAME'],
                            config['WEBDAV_PASSWORD'],
                            )
    elif config['REMOTE_STORAGE_TYPE'] is 'S3':
        return S3Client(config['S3_ROOT'],
                        config['S3_ACCESS_KEY'],
                        config['S3_SECRET_KEY'],
                        )


def remote_url(config, path):
    if config['REMOTE_STORAGE_TYPE'] is 'WEBDAV':
        return config['WEBDAV_ROOT'] + '/' + path
    elif config['REMOTE_STORAGE_TYPE'] is 'S3':
        return config['S3_ROOT'] + '/' + path


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/jobs', methods=['POST'])
def submit_job():
    data = request.get_json()
    remote_input_dir = data['inputdir'].rstrip('/')
    input_item_type = data.get('inputitemtype', 'file')
    remote_workflow_file = data['cwl_workflow']
    remote_output_dir = data['outputdir'].rstrip('/')
    output_extension = data.get('outputextension', '')
    if re.compile('[^a-zA-Z0-9-_.]').search(output_extension):
        raise ValueError('outputextension can only contain alphanumeric or -_.')

    job = perform_computation.delay(remote_workflow_file, remote_input_dir, input_item_type, remote_output_dir, output_extension)
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


def write_job_order_on_files(session_dir, input_dir, input_files, output_files, job_order_fn='job.yml'):
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


def write_workflow_wrapper_on_files(session_dir, workflow_file, workflow_wrapper_fn='workflow.wrapper.cwl'):
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
def perform_computation(self,
                        remote_workflow_file,
                        remote_input_dir,
                        input_item_type,
                        remote_output_dir,
                        output_extension):
    if input_item_type is 'file':
        return perform_computation_on_files(self,
                                     remote_workflow_file,
                                     remote_input_dir,
                                     remote_output_dir,
                                     output_extension)
    elif input_item_type is 'dir':
        return perform_computation_on_dirs(self,
                                    remote_workflow_file,
                                    remote_input_dir,
                                    remote_output_dir)
    else:
        raise ValueError('Invalid inputitemtype, must be file or dir')


def perform_computation_on_files(self,
                                 remote_workflow_file,
                                 remote_input_dir,
                                 remote_output_dir,
                                 output_extension=''):
    self.update_state(state='PRESTAGING')
    remote_storage = remote_storage_client(app.config)
    input_dir = 'in'
    output_dir = 'out'
    local_input_dir, local_output_dir, session_dir = create_session_dir(input_dir, output_dir)
    workflow_file = fetch_workflow(remote_storage, session_dir, remote_workflow_file)

    input_files = fetch_input_files(remote_storage, local_input_dir, remote_input_dir)
    output_files = ['{0}{1}'.format(d, output_extension) for d in input_files]
    job_order_file = write_job_order_on_files(session_dir, input_dir, input_files, output_files)
    workflow_wrapper_file = write_workflow_wrapper_on_files(session_dir, workflow_file)

    self.update_state(state='RUNNING')
    result = run_cwl(workflow_wrapper_file, job_order_file, session_dir, output_dir)

    logging.warning(result)

    self.update_state(state='POSTSTAGING')
    upload_output_files(remote_storage, local_output_dir, output_files, remote_output_dir)
    shutil.rmtree(session_dir)

    result_url = remote_url(app.config, remote_output_dir)
    result['url'] = result_url
    return result


def perform_computation_on_dirs(self, remote_workflow_file, remote_input_dir, remote_output_dir):
    self.update_state(state='PRESTAGING')
    remote_storage = remote_storage_client(app.config)
    input_dir = 'in'
    output_dir = 'out'
    local_input_dir, local_output_dir, session_dir = create_session_dir(input_dir, output_dir)
    workflow_file = fetch_workflow(remote_storage, session_dir, remote_workflow_file)

    input_dirs = fetch_input_dirs(remote_storage, local_input_dir, remote_input_dir)
    job_order_file = write_job_order_on_dirs(session_dir, input_dirs)
    workflow_wrapper_file = write_workflow_wrapper_on_dirs(session_dir, workflow_file)

    self.update_state(state='RUNNING')
    result = run_cwl(workflow_wrapper_file, job_order_file, session_dir, output_dir)

    self.update_state(state='POSTSTAGING')

    upload_output_dir(remote_storage, local_output_dir, remote_output_dir)
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


def upload_output_files(remote_storage, local_output_dir, output_files, remote_output_dir):
    # TODO update celery state with number of files copied vs total
    # TODO perform copy of files in parallel using Celery group
    for output_file in output_files:
        local_output_file = local_output_dir + '/' + output_file
        remote_output_file = remote_output_dir + '/' + output_file
        logging.info('Uploading "' + local_output_file + '" to "' + remote_output_file + '"')
        remote_storage.upload(local_output_file, remote_output_file)


def fetch_input_files(remote_storage, local_input_dir, remote_input_dir):
    # TODO update celery state with number of files copied vs total
    # TODO perform copy of files in parallel using Celery group
    input_files = []
    for input_file in remote_storage.ls(remote_input_dir):
        remote_input_file = remote_input_dir + '/' + input_file
        local_input_file = local_input_dir + '/' + input_file
        logging.info('Downloading "' + remote_input_file + '" to "' + local_input_file + '"')
        remote_storage.download(remote_input_file, local_input_file)
        input_files.append(input_file)
    return input_files


def fetch_workflow(remote_storage, local_input_dir, remote_workflow_file, workflow_file='workflow.cwl'):
    logging.warning('Downloading cwl')
    local_workflow_file = local_input_dir + '/' + workflow_file
    remote_storage.download(remote_workflow_file, local_workflow_file)
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


def fetch_input_dirs(remote_storage, local_input_dir, remote_input_dir):
    # recursively download files from remote_input_dir to local_input_dir
    subdirs = set()
    for input_file in remote_storage.ls(remote_input_dir, recursive=True):
        remote_input_file = remote_input_dir + '/' + input_file
        local_input_file = local_input_dir + '/' + input_file
        dirname = os.path.dirname(local_input_file)
        if dirname:
            os.makedirs(dirname)
            if '/' not in dirname:
                subdirs.add(dirname)

        logging.info('Downloading "' + remote_input_file + '" to "' + local_input_file + '"')
        remote_storage.download(remote_input_file, local_input_file)

    return subdirs


def write_job_order_on_dirs(session_dir, input_dirs):
    # TODO write a job order file
    raise NotImplementedError()


def write_workflow_wrapper_on_dirs(session_dir, workflow_file, workflow_wrapper_fn='workflow.wrapper.cwl'):
    # TODO write a workflow wrapper
    raise NotImplementedError()


def upload_output_dir(remote_storage, local_output_dir, remote_output_dir):
    for root, dirs, files in os.walk(local_output_dir):
        remote_storage.mkdir(remote_output_dir + '/' + root)
        for output_file in files:
            local_output_file = local_output_dir + '/' + output_file
            remote_output_file = remote_output_dir + '/' + output_file
            logging.info('Uploading "' + local_output_file + '" to "' + remote_output_file + '"')
            remote_storage.upload(local_output_file, remote_output_file)


if __name__ == '__main__':
    app.run(host='0.0.0.0', threaded=True)
