from app import configure_logger
from app import create_app
from waitress import serve
import os

app = create_app()

configure_logger(app)

if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    app.run(host="127.0.0.1", port=5000, debug=debug)
    #app.run(host='127.0.0.1', port=5000, debug=True, use_reloader=True)
    #serve(app,
    #      host='172.16.0.160',
    #        port=8000            
    #)
    # Detecta entorno
    

    # serve(app, host="172.16.0.160", port=8000)
