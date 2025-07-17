#!/usr/bin/env python3

# -------------------------------------------
# Compatibility shim for Python 3.12+ where the
# `distutils` module has been removed. Some third-
# party packages (e.g. eventlet) still import from
# `distutils`; here we transparently provide it by
# exposing `setuptools._distutils` under the original
# module name **before** those packages are imported.
# -------------------------------------------
import importlib
import sys

try:
    import distutils  # noqa: F401 – try real import first
except ModuleNotFoundError:  # pragma: no cover
    # Lazily load the replacement and register in sys.modules
    _distutils = importlib.import_module('setuptools._distutils')
    sys.modules['distutils'] = _distutils
    sys.modules['distutils.version'] = importlib.import_module('setuptools._distutils.version')

# Attempt to import and monkey-patch with eventlet for optimal WebSocket support.
# On Python 3.12+ eventlet <0.35 currently fails because the stdlib function
# `ssl.wrap_socket` has been removed.  If we detect a failure, or eventlet is
# simply not present, we gracefully fall back to the default "threading" async
# mode provided by Flask-SocketIO.  Long-polling will still work and WebSocket
# upgrade may be limited, but the server remains fully functional.

USE_EVENTLET = False

# Import eventlet only for Python < 3.12 where it is still compatible. Importing
# it under 3.12 can break the stdlib `ssl` module even if we catch the exception,
# because the import process patches `ssl` in-place *before* raising.  To be safe
# we skip the import entirely on 3.12+ and run Flask-SocketIO in its default
# "threading" mode.

if sys.version_info < (3, 12):  # pragma: no cover – skip on 3.12+
    try:
        import eventlet  # noqa: F401
        eventlet.monkey_patch()  # noqa: F401
        USE_EVENTLET = True
        print("✔ Using eventlet for async I/O ({})".format(sys.version.split()[0]))
    except Exception as _e:  # pragma: no cover – catch ALL problems
        print("⚠  Eventlet unavailable or incompatible ({}). Falling back to threading mode.".format(_e))

# Rest of the standard imports (after potential monkey-patching)
import os
import platform
from app import create_app, socketio

app = create_app()

if __name__ == '__main__':
    # Run the application
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '127.0.0.1')
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    print(f"🚀 Starting Skribly server...")
    print(f"   Host: {host}")
    print(f"   Port: {port}")
    print(f"   Debug: {debug}")
    print(f"   Mode: In-Memory Only (no database)")
    print(f"   Health check: http://{host}:{port}/health")
    
    socketio.run(app, host=host, port=port, debug=debug) 