from app import app
from utils.logger import logger

if __name__ == "__main__":
    event_logger = logger()
    event_logger.info("Loading bot app.")
    app.run(debug=True)

    # app.run(debug=True,ssl_context=context)
