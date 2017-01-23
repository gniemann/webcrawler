

from flask import Flask
from flask_cors import CORS
from flask.json import JSONEncoder

class CrawlerJSONEncoder(JSONEncoder):
    """Custom JSON encoder which calls object's jsonify() method (if it has one)
    Used to allow PageNode to jsonify itself"""

    def default(self, o):
        if hasattr(o, 'jsonify'):
            return o.jsonify()
        else:
            return JSONEncoder.default(self, o)

# set up the Flask application
app = Flask(__name__)

app.config.from_object('config')
CORS(app)
app.json_encoder = CrawlerJSONEncoder

import routes
