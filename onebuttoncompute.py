import logging
import tempfile
from flask import Flask, render_template, request

app = Flask(__name__)
app.config.from_pyfile('settings.cfg')

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/compute', methods=['POST'])
def compute():
    logging.warn(request.form)
    inputdir = tempfile.TemporaryDirectory('in')
    outputdir = tempfile.TemporaryDirectory('out')

    # Download input file from beehub to inputdir

    # Run Docker

    # Upload content of output dir to Beehub

    inputdir.cleanup()
    outputdir.cleanup()

    result_url = app.config['BEEHUB_ROOT'] + request.form['outputdir']

    return render_template('result.html', result_url=result_url)

if __name__ == '__main__':
    app.run()