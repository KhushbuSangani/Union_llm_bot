from flask import (
    render_template,
    request,
    session,
    redirect,
    Blueprint,
    Response,
    url_for,
    make_response,
)

admin_auth = Blueprint("auth", __name__)
from utils.logger import logger
from utils import config

event_logger = logger()


@admin_auth.route("/login")
def login():
    """
    Admin Login
    :return: Login Page View
    """
    try:
        return redirect(config.LOGIN_URL)
    except Exception as e:
        event_logger.error(e)
        return f"An error occurred: {str(e)}"


@admin_auth.route("/sign_out")
def sign_out():
    """
    User Logout
    :return: Redirect to Login View
    """
    session.clear()
    response = make_response("Logged out successfully")
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    return redirect(url_for("auth.login", _external=True, _scheme=config.SSL_SECURITY))
