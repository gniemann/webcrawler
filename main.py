import re

from flask import Flask, jsonify
from flask.json import  dumps, JSONEncoder
from flask.views import  MethodView
from flask_cors import CORS
from flask_wtf import Form
from wtforms import StringField, IntegerField, validators

from crawler import PageNode, get_page

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
            root, _ = get_page(crawler_data.start_page.data, 0)

            return_data = {
                'status': 'success',
                'job_id': 2,
                'root': root
            }
        else:
            return_data = {
                'status': 'failure',
                'errors': crawler_data.errors
            }

        return jsonify(return_data)

    def get(self, job_id):
        dummy_data = {
            'finished': True,
            'new_pages': [PageNode(2, 'www.facebook.com', 'www.facebook.com/favicon.ico', 1),
                          PageNode(3, 'www.twitter.com', 'www.twitter.com/favicon.ico', 2)]
        }

        return jsonify(dummy_data)

crawler_view = Crawler.as_view('crawler')
app.add_url_rule('/crawler/<int:job_id>', view_func=crawler_view, methods=['GET',])
app.add_url_rule('/crawler', view_func=crawler_view, methods=['POST',])


if __name__ == '__main__':
    app.run()
