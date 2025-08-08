from app import configure_logger
from app import create_app
from waitress import serve

app = create_app()

configure_logger(app)

if __name__ == "__main__":
    app.run(host='172.16.0.160', port=8000, debug=True)
    #serve(app.run(host='172.16.0.160', port=8000))
