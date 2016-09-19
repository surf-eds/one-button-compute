import logging
import os
import re
import subprocess
import shutil
import tempfile
from urlparse import urlparse, urldefrag

from celery import Celery
from cwltool.load_tool import fetch_document, validate_document
from flask import Flask, render_template, request, redirect, jsonify, url_for
import easywebdav
import magic
import minio
import ruamel.yaml as yaml
from swiftclient.service import SwiftService, SwiftUploadObject

app = Flask(__name__)
app.config.from_pyfile('settings.cfg')
app.config['CELERY_TRACK_STARTED'] = True
app.config['CELERY_TASK_SERIALIZER'] = 'json'
app.config['CELERY_ACCEPT_CONTENT'] = ['json']
app.config['CELERY_RESULT_SERIALIZER'] = 'json'

celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

logger = logging.getLogger('onebuttoncompute')


class WebDAVClient(object):
    def __init__(self, root, username, password):
        self.root = root
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

    def url(self, path=''):
        return self.root + '/' + path


class S3Client(object):
    def __init__(self, root, access_key, secret_key):
        self.root = root
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

    def ls(self, path):
        fpath = self.prefix + '/' + path + '/'
        listing = self.client.list_objects(self.bucket, prefix=fpath)
        return [d.object_name.replace(fpath, '') for d in listing]

    def url(self, path=''):
        return self.root + '/' + path


class SwiftClient(object):
    """Client for Swift object/blob store of Openstack

    See http://swift.openstack.org

    Swift requires environment variables (OS_*) for the authentication and configuration"""

    def __init__(self, container, prefix=''):
        self.container = container
        self.prefix = prefix
        self.client = SwiftService()

    def download(self, source, target):
        objects = [self.prefix + '/' + source]
        options = {'out_file': target}
        return list(self.client.download(self.container, objects, options))

    def upload(self, source, target):
        object_name = self.prefix + '/' + target
        objects = [SwiftUploadObject(source, object_name=object_name)]
        return list(self.client.upload(self.container, objects))

    def ls(self, path):
        fpath = self.prefix + '/' + path + '/'
        clisting = self.client.list(self.container, {'prefix': fpath})
        listing = list(clisting)[0]['listing']
        result = [d['name'].replace(fpath, '') for d in listing]
        return result

    def url(self, path=''):
        return self.container + '/' + self.prefix + '/' + path


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
    elif config['REMOTE_STORAGE_TYPE'] is 'SWIFT':
        return SwiftClient(config['SWIFT_CONTAINER'],
                           config['SWIFT_PREFIX'],
                           )


@app.route('/', methods=['GET'])
def index():
    remote_storage = remote_storage_client(app.config)
    remote_storage_url = remote_storage.url()
    return render_template('index.html', remote_storage_url=remote_storage_url)


@app.route('/jobs', methods=['POST'])
def submit_job():
    data = request.get_json()
    remote_input_dir = data['inputdir'].rstrip('/')
    remote_workflow_file = data['cwl_workflow']
    remote_output_dir = data['outputdir'].rstrip('/')
    if re.compile('[^a-zA-Z0-9-_.]').search(data['outputextension']):
        raise ValueError('outputextension can only contain alphanumeric or -_.')
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
        # result is an exception, with str(exception) set, but other exception attributes are missing.
        response['result'] = {'log': str(job.result)}
    try:
        if response['result']['exit_code'] != 0:
            response['state'] = 'FAILURE'
    except (TypeError, KeyError) as ex:
        pass

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


def write_workflow_wrapper(session_dir, workflow_file, workflow_wrapper_fn='workflow.wrapper.cwl', fragment=''):
    abs_workflow_wrapper_fn = session_dir + '/' + workflow_wrapper_fn
    workflow_file_frag = workflow_file
    if fragment is not '':
        workflow_file_frag = workflow_file + '#' + fragment
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
        'requirements': [
            {'class': 'ScatterFeatureRequirement'},
            {'class': 'SubworkflowFeatureRequirement'},
        ],
        'steps': {
            'step1': {
                'in': {
                    'input': 'input_files',
                    'output': 'output_filenames'
                },
                'out': ['outputfile'],
                'run': workflow_file_frag,
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
    logging.warning(session_dir)
    remote_workflow_file, fragment = urldefrag(remote_workflow_file)
    workflow_file = fetch_workflow(remote_storage, session_dir, remote_workflow_file)
    input_files = fetch_input_files(remote_storage, local_input_dir, remote_input_dir)
    output_files = ['{0}{1}'.format(d, output_extension) for d in input_files]
    job_order_file = write_job_order(session_dir, input_dir, input_files, output_files)
    workflow_wrapper_file = write_workflow_wrapper(session_dir, workflow_file, fragment=fragment)

    self.update_state(state='RUNNING')
    result = run_cwl(workflow_wrapper_file, job_order_file, session_dir, output_dir)

    logging.warning(result)

    if result['exit_code'] == 0:
        self.update_state(state='POSTSTAGING')
        upload_output_files(remote_storage, local_output_dir, output_files, remote_output_dir)
        result_url = remote_storage.url()
        result['url'] = result_url

    self.update_state(state='FINISHING')
    shutil.rmtree(session_dir)

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', threaded=True)
