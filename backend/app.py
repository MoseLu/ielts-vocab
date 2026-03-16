from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
from config import Config
from models import db
from routes.auth import auth_bp, init_auth
from routes.progress import progress_bp
from routes.vocabulary import vocabulary_bp
from routes.speech import speech_bp
from routes.speech_socketio import register_socketio_events


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Initialize auth with app reference
    init_auth(app)

    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(progress_bp, url_prefix='/api/progress')
    app.register_blueprint(vocabulary_bp, url_prefix='/api/vocabulary')
    app.register_blueprint(speech_bp, url_prefix='/api/speech')

    # Create database tables
    with app.app_context():
        db.create_all()

    return app


# Create app instance
app = create_app()

# Initialize SocketIO with eventlet for better WebSocket support
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet', ping_timeout=60, ping_interval=25, logger=True, engineio_logger=True)

# Register Socket.IO events for speech recognition
register_socketio_events(socketio)


if __name__ == '__main__':
    print("=" * 50)
    print("IELTS Vocabulary Backend")
    print("=" * 50)
    print("Server running at: http://localhost:5000")
    print()
    print("API Endpoints:")
    print("  POST /api/auth/register - Register new user")
    print("  POST /api/auth/login    - Login")
    print("  POST /api/auth/logout   - Logout")
    print("  GET  /api/auth/me       - Get current user")
    print("  GET  /api/progress      - Get all progress")
    print("  POST /api/progress      - Save progress")
    print("  GET  /api/progress/<day> - Get day progress")
    print("  GET  /api/vocabulary    - Get all vocabulary")
    print("  GET  /api/vocabulary/day/<day> - Get day vocabulary")
    print()
    print("WebSocket Endpoints:")
    print("  /speech - Real-time speech recognition")
    print("=" * 50)

    socketio.run(app, debug=False, host='0.0.0.0', port=5002)
