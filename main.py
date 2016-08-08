"""
main app code
This file contains all the Flask code to run the front-facing web service
"""
import datetime
import logging
import io
import re
import time

from flask import Flask, jsonify, send_file
from flask.json import JSONEncoder
from flask.views import MethodView
from flask_cors import CORS
from flask_wtf import Form
from wtforms import StringField, IntegerField, validators

from crawler import start_crawler, TerminationSentinal
from models import JobModel
from site_utils import read_file


class CrawlerJSONEncoder(JSONEncoder):
    """Custom JSON encoder which calls object's jsonify() method (if it has one)
    Used to allow PageNode to jsonify itself"""

    def default(self, o):
        if hasattr(o, 'jsonify'):
            return o.jsonify()
        else:
            return JSONEncoder.default(self, o)


url_regex = re.compile(r'''(https?://)?([a-z0-9\-]+\.){1,}[a-z0-9]+((\?|/)[^'" ]*)?''', re.IGNORECASE)


class CrawlerForm(Form):
    """This is the data submitted with the crawler POST request"""
    start_page = StringField('start_page', validators=[validators.regexp(url_regex)])
    depth = IntegerField('depth', default=1)
    end_phrase = StringField('end_phrase', validators=[validators.Optional()])
    search_type = StringField('search_type', default='BFS', validators=[validators.AnyOf(['DFS', 'BFS'])])


# set up the Flask application
app = Flask(__name__)
app.config['WTF_CSRF_ENABLED'] = False
CORS(app)
app.json_encoder = CrawlerJSONEncoder


class Crawler(MethodView):
    """
    API methods for the crawler
    route is /crawler/<optional ID>
    on POST (without <ID>), attempt to start a new job
    on GET (with <ID>), return results since the last GET returned
    """

    def post(self):
        """
        Attempts to start a new crawler job.
        :return: Returns a JSON object
        On success, 'status' is set to 'success' and 'job_id' is the ID of the newly created crawl job. Also,
            'root' is a PageNode of the root URL
        On failure, 'status' is set to 'failure' and 'errors' is a list of error strings why the crawl failed to start
        """
        crawler_data = CrawlerForm(csrf_enabled=False)
        if crawler_data.validate_on_submit():
            root, job_id = start_crawler(crawler_data.start_page.data, crawler_data.search_type.data,
                                         crawler_data.depth.data, crawler_data.end_phrase.data)

            if root:
                return_data = {
                    'status': 'success',
                    'job_id': job_id,
                    'root': root
                }
                logging.info("Starting job {}, root is {}".format(job_id, root.url))
            else:
                return_data = {
                    'status': 'failure',
                    'errors': ['Invalid URL', ]
                }
                logging.info("Invalid URL: {}".format(crawler_data.start_page.data))
        else:
            return_data = {
                'status': 'failure',
                'errors': list(crawler_data.errors.values())
            }
            logging.info("Errors on form validation")

        return jsonify(return_data)

    def get(self, job_id):
        """
        Returns new results from the crawl job
        :param job_id: the ID of the crawl job
        :return:
        If no job with the ID is running, returns status 404
        Otherwise, returns a JSON list of JSONified PageNode objects
        """
        job = JobModel.get_by_id(job_id)

        if job is None:
            # wait a second - poll might have started too early
            time.sleep(1)
            job = JobModel.get_by_id(job_id)
            if job is None:
                return "Job not scheduled", 404

        new_nodes = job.get_unreturned_results()
        timeout_len = .5
        timeout_time = 0

        while not new_nodes and timeout_time < 20:
            timeout_time += timeout_len
            time.sleep(timeout_len)
            new_nodes = job.get_unreturned_results()

        finished = False

        # if we got new nodes before the timeout, process them and return
        # otherwise, we will just return not finished and an empty list
        if new_nodes:
            # check for a termination sentinal
            for node in new_nodes:
                if isinstance(node, TerminationSentinal):
                    finished = True
                    new_nodes.remove(node)

                    # delete the job
                    job.delete()
                    break

            new_nodes.sort(key=lambda n: n.id)

        return jsonify({'finished': finished, 'new_nodes': new_nodes})


crawler_view = Crawler.as_view('crawler')
app.add_url_rule('/crawler/<int:job_id>', view_func=crawler_view, methods=['GET', ])
app.add_url_rule('/crawler', view_func=crawler_view, methods=['POST', ])


@app.route('/favicons/<filename>')
def retrieve_favicon(filename):
    """
    Route which returns one of the saved favicons (identified by the filename)
    :param filename: favicon file to return
    :return: returns the favicon
    """
    icon = io.BytesIO(read_file(filename))
    if icon:
        return send_file(icon, mimetype='image/x-icon')
    else:
        logging.warning("Favicon {} does not exist.".format(filename))
        return send_file('/images/sunburst.png')


@app.route('/admin/cron/cleanup')
def cleanup():
    """
    Clears out from the Datastore jobs which are more than 4 hours old
    :return: No return
    """
    delta = datetime.timedelta(hours=4)
    qry = JobModel.query().filter(JobModel.start_time < (datetime.datetime.now() - delta))
    logging.info("Cleaning up {} stale jobs".format(qry.count()))
    qry.map(JobModel.delete)

    return 'OK', 200


@app.route('/')
def index():
    return send_file('index.html')


if __name__ == '__main__':
    app.run()
