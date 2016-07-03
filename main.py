import re
import time

from flask import Flask, jsonify
from flask.json import  dumps, JSONEncoder
from flask.views import  MethodView
from flask_cors import CORS
from flask_wtf import Form
from wtforms import StringField, IntegerField, validators
from google.appengine.api import memcache

from crawler import start_crawler, TerminationSentinal, JobModel, JobResultsModel

class CrawlerJSONEncoder(JSONEncoder):
    """Custom JSON encoder which calls object's jsonify() method (if it has one)
    Used to allow PageNode to jsonify itself"""
    def default(self, o):
        if hasattr(o, 'jsonify'):
            return o.jsonify()
        else:
            return JSONEncoder.default(self, o)

url_regex = re.compile(r'(https?://)?[a-z\-]*\.[a-z]*', re.IGNORECASE)

class CrawlerForm(Form):
    """This is the data submitted with the crawler POST request"""
    start_page = StringField('start_page', validators=[validators.regexp(url_regex)])
    depth = IntegerField('depth', default=5, validators=[validators.Optional()])
    end_phrase = StringField('end_phrase', validators=[validators.Optional()])
    search_type = StringField('search_type', default='BFS', validators=[validators.AnyOf(['DFS', 'BFS'])])

#set up the Flask application
app = Flask(__name__)
app.config['WTF_CSRF_ENABLED'] = False
CORS(app)
app.json_encoder = CrawlerJSONEncoder

class Crawler(MethodView):

    def post(self):
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
            else:
                return_data = {
                    'status': 'failure',
                    'errors': ['Invalid URL',]
                }
        else:
            return_data = {
                'status': 'failure',
                'errors': list(crawler_data.errors.values())
            }

        return jsonify(return_data)

    def get(self, job_id):
        job_key = JobModel.get_by_id(job_id)

        if job_key is None:

            # wait a second - poll might have started too early
            time.sleep(1)
            job_key = JobModel.get_by_id(job_id)
            if job_key is None:
                return "Job not scheduled", 404

        qry = JobResultsModel.query(ancestor=job_key.key)
        while qry.count() == 0:
            time.sleep(.5)
            qry = JobResultsModel.query(ancestor=job_key.key)

        new_nodes = []
        for row in qry.iter():
            new_nodes.extend(row.results)
            row.key.delete()

        # check for a termination sentinal
        finished = False
        for node in new_nodes:
            if isinstance(node, TerminationSentinal):
                finished = True
                new_nodes.remove(node)
                break

        return jsonify({'finished': finished, 'new_nodes': new_nodes})

crawler_view = Crawler.as_view('crawler')
app.add_url_rule('/crawler/<int:job_id>', view_func=crawler_view, methods=['GET',])
app.add_url_rule('/crawler', view_func=crawler_view, methods=['POST',])


if __name__ == '__main__':
    app.run()
