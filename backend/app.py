
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO

from routes import api

app = Flask(__name__)
CORS(app)

socketio = SocketIO(app, cors_allowed_origins="*")

app.register_blueprint(api)


if __name__ == "__main__":
    socketio.run(app, debug=True, port=5000)
