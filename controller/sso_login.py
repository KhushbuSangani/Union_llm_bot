from flask import (
    render_template,
    request,
    session,
    redirect,
    Blueprint,
    Response,
    url_for,
    jsonify,
)
from utils.db_connector import db_connection
from datetime import datetime
import random
import requests
import json
from utils.db_connector import create_connection, execute_query
import oracledb as cx_Oracle

sso_auth = Blueprint("sso", __name__)
from utils.logger import logger
from utils import config
from utils.db_response import get_user_details, get_user_roles_permissions

event_logger = logger()


def get_latest_token(emp_no):
    connection = create_connection()
    cursor = connection.cursor()
    if config.LOGIN_URL == "https://150.242.12.189/union-bank-new/login":
        var_token = cursor.var(cx_Oracle.CURSOR)
        params = [emp_no, var_token]
        cursor.callproc("USP_GETLATESTTOKEN", params)
        result = var_token.getvalue().fetchall()
        result = result[0][0]
    else:
        var_token = cursor.var(cx_Oracle.STRING)
        params = [emp_no, var_token]
        result = cursor.callproc("USP_GETLATESTTOKEN", params)
        result = result[1]
    # var_token = cursor.var(cx_Oracle.CURSOR)
    # params = [emp_no, var_token]
    # cursor.callproc("USP_GETLATESTTOKEN", params)
    # result = var_token.getvalue().fetchall()
    # result = result[0][0]
    cursor.close()
    connection.close()

    # Assuming 'var_Token' is the name of the output parameter
    latest_token = result

    return latest_token


def get_token(emp_no):
    user_token = execute_query(
        "SELECT token FROM admin_login WHERE user_id = :emp_no",
        "select",
        params={"emp_no": emp_no},
    )[0]["token"]
    return user_token

