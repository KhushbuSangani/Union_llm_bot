from dotenv import load_dotenv
import os
load_dotenv()
SSL_SECURITY = os.environ.get("SSL_SECURITY", None)
ORACLE_USER = os.environ.get("ORACLE_USER", None)
ORACLE_PASSWORD = os.environ.get("ORACLE_PASSWORD", None)
DB_NAME = os.environ.get("DB_NAME", None)
ORACLE_IP = os.getenv("ORACLE_IP", None)
ORACLE_HOST = os.getenv("ORACLE_HOST", None)
ORACLE_PORT = os.environ.get("ORACLE_PORT", None)
ORACLE_DB = os.environ.get("ORACLE_DB", None)
BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:6002/")
PROD_URL = os.environ.get("PROD_URL", "http://127.0.0.1:6003/")
LOGIN_URL = os.environ.get("LOGIN_URL", None)
SECRET_KEY = os.environ.get("SECRET_KEY", None)
SESSION_TYPE = os.environ.get("SESSION_TYPE", None)
REDIS_URL = os.getenv("REDIS_URL", None)
MODEL_NAME=os.getenv("MODEL_NAME",None)
OLLAMA_URL=os.getenv("OLLAMA_URL",None)
QDRANT_HOST=os.getenv("QDRANT_HOST",None)

MODEL_LINK=os.getenv("MODEL_LINK",None)

TICKET_API_URL = os.environ.get(
    "TICKET_API_URL",
    None,
)
TICKET_API_USER = os.environ.get("TICKET_API_USER", None)
TICKET_API_CREDENTIAL = os.environ.get(
    "TICKET_API_CREDENTIAL", None
)
TICKET_API_PASSWORD = os.environ.get("TICKET_API_PASSWORD", None)
TICKET_API_TOKEN = os.environ.get(
    "TICKET_API_TOKEN",
    None
)
TICKET_API_SESSION = os.environ.get(
    "TICKET_API_SESSION", None
)
PROD_SOCKET_URI = os.environ.get("PROD_SOCKET_URI", None)
STAGING_SOCKET_URI = os.environ.get("STAGING_SOCKET_URI", None)
PROD_SOCKET_PATH = os.environ.get("PROD_SOCKET_PATH", None)
STAGING_SOCKET_PATH = os.environ.get("STAGING_SOCKET_PATH", None)
