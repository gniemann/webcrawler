from flask import Flask, jsonify
from flask.views import  MethodView
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/')
def hello_world():
    return 'Hello World!'

class Crawler(MethodView):

    def post(self):
        dummy_data = {
            'status': 'success',
            'job_id': 2,
            'root': {
                'id': 1,
                'url': 'www.google.com',
                'favicon': 'www.google.com/favicon.ico',
                'parent': None
            }
        }

        return jsonify(dummy_data)

    def get(self, job_id):
        dummy_data = {
            'finished': True,
            'new_pages': [
                {
                    'id': 2,
                    'url': 'www.facebook.com',
                    'favicon': 'www.facebook.com/favicon.ico',
                    'parent': 1
                },
                {
                    'id': 3,
                    'url': 'www.twitter.com',
                    'favicon': 'www.twitter.com/favicon.ico',
                    'parent': 2
                }
            ]
        }

        return jsonify(dummy_data)

crawler_view = Crawler.as_view('crawler')
app.add_url_rule('/crawler/<int:job_id>', view_func=crawler_view, methods=['GET',])
app.add_url_rule('/crawler', view_func=crawler_view, methods=['POST',])


if __name__ == '__main__':
    app.run()
