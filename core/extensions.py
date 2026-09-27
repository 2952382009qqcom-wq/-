"""Application extensions shared by feature blueprints."""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from flask_socketio import SocketIO


migrate = Migrate(compare_type=True)
limiter = Limiter(key_func=get_remote_address, default_limits=[])
socketio = SocketIO(async_mode="threading", manage_session=False)
