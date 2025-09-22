from flask import (
    render_template,
    request,
    session,
    redirect,
    Blueprint,
    Response,
    url_for,
)
# from utils.create_dataset import get_training_set
# from utils import rasa_wrapper as rasa_wrapper,config
from utils.db_connector import execute_query
from datetime import datetime, timedelta
from utils import db_handler
from controller.sso_login import get_latest_token, get_token
import pandas as pd
import threading
import shutil
import os,json,requests
from utils.logger import logger
from utils import config
from functools import wraps

event_logger = logger()

admin_details = Blueprint("admin", __name__)





#-----------------------------------LLM_ADMIN_DASHBOARD--------------------------#
def get_ollama_info():
    ollama_url = os.getenv("OLLAMA_URL")
    status_info = {}
    models = []

    try:
        tags_resp = requests.get(f"{ollama_url}/api/tags", timeout=5)
        if tags_resp.status_code == 200:
            status_info["models"] = [m["name"] for m in tags_resp.json().get("models", [])]
            status_info["status"] = "Running"
        else:
            status_info["models"] = []
            if "status" not in status_info:
                status_info["status"] = "unreachable"
    except Exception as e:
        event_logger.error(f"Error fetching Ollama models: {e}")
        status_info["models"] = []
        if "status" not in status_info:
            status_info["status"] = "unreachable"

    return status_info
    

@admin_details.route("/dashboard")
def dashboard():
    """
    Admin Dashboard
    :return: Admin DashBoard View
    """
    try:
        if session.get("islogin") != 1 and session.get("islogin") != "1":
            return redirect(
                url_for("auth.login", _external=True, _scheme=config.SSL_SECURITY)
            )
        session["status"] = "dashboard"

    except Exception as e:
        event_logger.error(e)
        return render_template("admin/401.html")
    if session.get("token") != get_latest_token(session.get("user_id")):
        return redirect(
            url_for("auth.login", _external=True, _scheme=config.SSL_SECURITY)
        )

    # Intent Details
    try:
        total_files = execute_query(
            "SELECT COUNT(*) AS total_files FROM uploaded_llm_files", 
            "select"
        )[0]["total_files"]
        pending_files = execute_query(
            "SELECT COUNT(*) AS pending_files FROM uploaded_llm_files WHERE file_status = 'pending'", 
            "select"
        )[0]["pending_files"]
        processed_files = execute_query(
            "SELECT COUNT(*) AS processed_files FROM uploaded_llm_files WHERE file_status = 'embedded'", 
            "select"
        )[0]["processed_files"]
        active_model=config.MODEL_NAME
        active_model_link=config.MODEL_LINK 
        active_user=execute_query(
            "SELECT COUNT(DISTINCT user_id) as active_user FROM conversation", 
            "select"
        )[0]["active_user"]
        admin_user=execute_query(
            "SELECT COUNT(DISTINCT user_id) as admin_user FROM admin_login", 
            "select"
        )[0]["admin_user"]
        daily_counts = db_handler.get_daily_query_counts()
        collection_counts = db_handler.get_collection_query_counts()
        ollama_info = get_ollama_info()
        available_models = ollama_info.get("models", [])
        ollama_status = ollama_info.get("status", {})
        event_logger.info(available_models)
        return render_template(
            "admin/dashboard.html",
            embedded_files=processed_files,
            pending_files=pending_files,
            total_files=total_files,
            data=[],
            active_model=active_model,
            available_models=available_models,
            active_model_link=active_model_link,
            active_user=active_user,
            daily_counts=json.dumps(daily_counts),
            collection_counts=json.dumps(collection_counts),
            total_admin_user=admin_user,
            ollama_status=ollama_status,
            prod_socket_uri=config.PROD_SOCKET_URI,
            prod_socket_path=config.PROD_SOCKET_PATH,
        )
    except Exception as e:
        print(e)
        event_logger.error(e)
        return render_template("admin/500.html")




#--------------------------------RASA DASHBOARD CODE START--------------------------------------------------------#
# @admin_details.route("/author")
# def author_dashboard():
#     """
#     Admin Dashboard
#     :return: Admin DashBoard View
#     """
#     # try:
#     #     if session.get("islogin") != 1 and session.get("islogin") != "1":
#     #         return redirect(
#     #             url_for("auth.login", _external=True, _scheme=config.SSL_SECURITY)
#     #         )
#     #     session["status"] = "dashboard"

#     # except Exception as e:
#     #     event_logger.error(e)
#     #     return render_template("admin/401.html")
#     # if session.get("token") != get_latest_token(session.get("user_id")):
#     #     return redirect(
#     #         url_for("auth.login", _external=True, _scheme=config.SSL_SECURITY)
#     #     )

#     # Intent Details
#     try:
#         nlu_data_trained = execute_query(
#             "SELECT COUNT(*) AS nlu_data_trained FROM nlu_data WHERE status = '1'",
#             "select",
#         )[0]["nlu_data_trained"]
#         nlu_data_untrained = execute_query(
#             "SELECT COUNT(*) AS nlu_data_untrained FROM nlu_data WHERE status = '2'",
#             "select",
#         )[0]["nlu_data_untrained"]
#         nlu_data_total = execute_query(
#             "SELECT COUNT(*) AS nlu_data_total FROM nlu_data", "select"
#         )[0]["nlu_data_total"]
#         prod_count = ""
#         prod_name = ""
#         stag_count = ""
#         stag_name = ""
#         # Production modelau
#         prod_count_total = execute_query(
#             "SELECT COUNT(*) AS prod_count_total FROM train_data WHERE deploy = '1'",
#             "select",
#         )[0]["prod_count_total"]
#         prod_count_total_both = execute_query(
#             "SELECT COUNT(*) AS prod_count_total_both FROM train_data WHERE deploy = '3'",
#             "select",
#         )[0]["prod_count_total_both"]
#         if prod_count_total > 0:
#             prod_mod = execute_query(
#                 "SELECT * FROM train_data WHERE deploy = '1'", "select"
#             )
#             x = []
#             for i in prod_mod:
#                 x.append(i.get("model_profile_name"))
#                 x.append(i.get("intent_list"))
#             prod_count = str(len(x[1]))
#             prod_name = x[0]
#         elif prod_count_total_both > 0:
#             prod_mod = execute_query(
#                 "SELECT * FROM train_data WHERE deploy = '3'", "select"
#             )
#             x = []
#             for i in prod_mod:
#                 x.append(i.get("model_profile_name"))
#                 x.append(i.get("intent_list"))
#             prod_count = str(len(x[1]))
#             prod_name = x[0]
#         else:
#             prod_name = ""
#             prod_count = ""

#         # Staging Model
#         stag_count_total = execute_query(
#             "SELECT COUNT(*) AS stag_count_total FROM train_data WHERE deploy = '2'",
#             "select",
#         )[0]["stag_count_total"]
#         stag_count_total_both = execute_query(
#             "SELECT COUNT(*) AS stag_count_total_both FROM train_data WHERE deploy = '3'",
#             "select",
#         )[0]["stag_count_total_both"]
#         if stag_count_total > 0:
#             stag_mod = execute_query(
#                 "SELECT * FROM train_data WHERE deploy = '2'", "select"
#             )
#             y = []
#             for j in stag_mod:
#                 y.append(j.get("model_profile_name"))
#                 y.append(j.get("intent_list"))
#             stag_count = str(len(y[1]))
#             stag_name = y[0]
#         elif stag_count_total_both > 0:
#             stag_mod = execute_query(
#                 "SELECT * FROM train_data WHERE deploy = '3'", "select"
#             )
#             y = []
#             for j in stag_mod:
#                 y.append(j.get("model_profile_name"))
#                 y.append(j.get("intent_list"))
#             stag_count = str(len(y[1]))
#             stag_name = y[0]
#         else:
#             stag_name = ""
#             stag_count = ""
#         # Pending List
#         all_intents = db_handler.fetch_pending_model()
#         _all_intents = []
#         if all_intents:
#             for idx, x in enumerate(all_intents):
#                 _all_intents.append(
#                     [
#                         idx + 1,
#                         x.get("model_profile_name"),
#                         x.get("status"),
#                         pd.to_datetime(x.get("timestamp")),
#                         x.get("trained_by"),
#                         x.get("model_name"),
#                         x.get("deploy"),
#                         x.get("_id"),
#                         active_count_test_pend(x.get("model_id"), "1", "stage"),
#                         active_count_test_pend(x.get("model_id"), "0", "stage"),
#                         active_count_test_pend(x.get("model_id"), "1", "prod"),
#                         active_count_test_pend(x.get("model_id"), "0", "prod"),
#                         x.get("model_id"),
#                         x.get("approve_status"),
#                     ]
#                 )
#         return render_template(
#             "admin/author_dashboard.html",
#             nlu_data_trained=nlu_data_trained,
#             nlu_data_untrained=nlu_data_untrained,
#             nlu_data_total=nlu_data_total,
#             data=_all_intents,
#             prod_name=prod_name,
#             prod_count=prod_count,
#             stag_name=stag_name,
#             stag_count=stag_count,
#             prod_socket_uri=config.PROD_SOCKET_URI,
#             prod_socket_path=config.PROD_SOCKET_PATH,
#         )
#     except Exception as e:
#         event_logger.error(e)
#         return render_template("admin/500.html")
    

# @admin_details.route("/admin/testing")
# def testing():
#     """
#     Admin Dashboard
#     :return: Admin DashBoard View
#     """
#     try:
#         if session.get("islogin") != 1 or session.get("islogin") != "1":
#             return redirect(
#                 url_for("auth.login", _external=True, _scheme=config.SSL_SECURITY)
#             )
#     except Exception as e:
#         event_logger.error(e)
#         return render_template("admin/401.html")
#     session["status"] = "testing"
#     return render_template(
#         "super_admin/testing.html",
#         prod_socket_uri=config.PROD_SOCKET_URI,
#         prod_socket_path=config.PROD_SOCKET_PATH,
#     )





# @admin_details.route("/active_count_test_pend")
# def active_count_test_pend(model_id, status, evn):
#     try:
#         all_db_intents = execute_query(
#             """SELECT intent_list FROM train_data WHERE model_id = :model_id""",
#             "select",
#             params={"model_id": model_id},
#         )
#         all_intents = []
#         nlu_data = ""
#         if not all_db_intents[0]["intent_list"]:
#             intent_list = []
#         else:
#             for x in all_db_intents:
#                 all_intents.append(x["intent_list"])
#             intent_list = all_intents[0]
#             intent_list = ",".join(["'" + str(nlu_id) + "'" for nlu_id in intent_list])
#             if status == "1" and evn == "stage":
#                 nlu_data = execute_query(
#                     f"SELECT COUNT(*)  as count FROM nlu_data WHERE s_status = '1' AND nlu_id IN ({intent_list})",
#                     "select",
#                 )[0]["count"]
#             elif status == "0" and evn == "stage":
#                 nlu_data = execute_query(
#                     f"SELECT COUNT(*)  as count FROM nlu_data WHERE s_status = '0' AND nlu_id IN ({intent_list})",
#                     "select",
#                 )[0]["count"]
#             elif status == "1" and evn == "prod":
#                 nlu_data = execute_query(
#                     f"SELECT COUNT(*)  as count FROM nlu_data WHERE p_status = '1' AND nlu_id IN ({intent_list})",
#                     "select",
#                 )[0]["count"]
#             elif status == "0" and evn == "prod":
#                 nlu_data = execute_query(
#                     f"SELECT COUNT(*)  as count FROM nlu_data WHERE p_status = '0' AND nlu_id IN ({intent_list})",
#                     "select",
#                 )[0]["count"]
#         return str(nlu_data)
#     except Exception as e:
#         event_logger.error(e)
#         return render_template("admin/500.html")



# @admin_details.route("/approver")
# def approver_dashboard():
#     """
#     Admin Dashboard
#     :return: Admin DashBoard View
#     """
#     try:
#         if session.get("islogin") != 1:
#             return redirect(
#                 url_for("auth.login", _external=True, _scheme=config["SSL_SECURITY"])
#             )
#     except Exception as e:
#         event_logger.error(e)
#         return render_template("admin/401.html")
#     if session.get("token") != get_latest_token(session.get("user_id")):
#         return redirect(
#             url_for("auth.login", _external=True, _scheme=config.SSL_SECURITY)
#         )
#     else:
#         session["status"] = "dashboard"

#     try:
#         session["status"] = "dashboard"
#         # Intent Details
#         nlu_data_trained = execute_query(
#             "SELECT COUNT(*) AS nlu_data_trained FROM nlu_data WHERE status = '1'",
#             "select",
#         )[0]["nlu_data_trained"]
#         nlu_data_untrained = execute_query(
#             "SELECT COUNT(*) AS nlu_data_untrained FROM nlu_data WHERE status = '2'",
#             "select",
#         )[0]["nlu_data_untrained"]
#         nlu_data_total = execute_query(
#             "SELECT COUNT(*) AS nlu_data_total FROM nlu_data", "select"
#         )[0]["nlu_data_total"]
#         prod_count = ""
#         prod_name = ""
#         stag_count = ""
#         stag_name = ""
#         # Production model
#         prod_count_total = execute_query(
#             "SELECT COUNT(*) AS prod_count_total FROM train_data WHERE deploy = '1'",
#             "select",
#         )[0]["prod_count_total"]
#         prod_count_total_both = execute_query(
#             "SELECT COUNT(*) AS prod_count_total_both FROM train_data WHERE deploy = '3'",
#             "select",
#         )[0]["prod_count_total_both"]
#         if prod_count_total > 0:
#             prod_mod = execute_query(
#                 "SELECT * FROM train_data WHERE deploy = '1'", "select"
#             )
#             x = []
#             for i in prod_mod:
#                 x.append(i.get("model_profile_name"))
#                 x.append(i.get("intent_list"))
#             prod_count = str(len(x[1]))
#             prod_name = x[0]
#         elif prod_count_total_both > 0:
#             prod_mod = execute_query(
#                 "SELECT * FROM train_data WHERE deploy = '3'", "select"
#             )
#             x = []
#             for i in prod_mod:
#                 x.append(i.get("model_profile_name"))
#                 x.append(i.get("intent_list"))
#             prod_count = str(len(x[1]))
#             prod_name = x[0]
#         else:
#             prod_name = ""
#             prod_count = ""

#         # Staging Model
#         stag_count_total = execute_query(
#             "SELECT COUNT(*) AS stag_count_total FROM train_data WHERE deploy = '2'",
#             "select",
#         )[0]["stag_count_total"]
#         stag_count_total_both = execute_query(
#             "SELECT COUNT(*) AS stag_count_total_both FROM train_data WHERE deploy = '3'",
#             "select",
#         )[0]["stag_count_total_both"]
#         if stag_count_total > 0:
#             stag_mod = execute_query(
#                 "SELECT * FROM train_data WHERE deploy = '2'", "select"
#             )
#             y = []
#             for j in stag_mod:
#                 y.append(j.get("model_profile_name"))
#                 y.append(j.get("intent_list"))
#             stag_count = str(len(y[1]))
#             stag_name = y[0]
#         elif stag_count_total_both > 0:
#             stag_mod = execute_query(
#                 "SELECT * FROM train_data WHERE deploy = '3'", "select"
#             )
#             y = []
#             for j in stag_mod:
#                 y.append(j.get("model_profile_name"))
#                 y.append(j.get("intent_list"))
#             stag_count = str(len(y[1]))
#             stag_name = y[0]
#         else:
#             stag_name = ""
#             stag_count = ""
#         # Pending List
#         all_intents = db_handler.fetch_pending_model()
#         _all_intents = []
#         if all_intents:
#             for idx, x in enumerate(all_intents):
#                 _all_intents.append(
#                     [
#                         idx + 1,
#                         x.get("model_profile_name"),
#                         x.get("status"),
#                         pd.to_datetime(x.get("timestamp")),
#                         x.get("trained_by"),
#                         x.get("model_name"),
#                         x.get("deploy"),
#                         x.get("_id"),
#                         active_count_test_pend(x.get("model_id"), "1", "stage"),
#                         active_count_test_pend(x.get("model_id"), "0", "stage"),
#                         active_count_test_pend(x.get("model_id"), "1", "prod"),
#                         active_count_test_pend(x.get("model_id"), "0", "prod"),
#                         x.get("model_id"),
#                         x.get("approve_status"),
#                     ]
#                 )
#         else:
#             _all_intents = []
#         return render_template(
#             "admin/approver_dashboard.html",
#             nlu_data_trained=nlu_data_trained,
#             nlu_data_untrained=nlu_data_untrained,
#             nlu_data_total=nlu_data_total,
#             data=_all_intents,
#             prod_name=prod_name,
#             prod_count=prod_count,
#             stag_name=stag_name,
#             stag_count=stag_count,
#             prod_socket_uri=config.PROD_SOCKET_URI,
#             prod_socket_path=config.PROD_SOCKET_PATH,
#         )
#     except Exception as e:
#         event_logger.error(e)
#         return render_template("admin/500.html")


# @admin_details.route("/check_username", methods=["POST"])
# def check_username():
#     """
#     Validation function Check Intent is present or not(Unique)
#     :return: admin username Count String
#     """
#     try:
#         projectpath = request.form
#         query_data = projectpath.to_dict(flat=False)
#         admin = query_data.pop("answer2")[0]
#         admin_count = execute_query(
#             """SELECT COUNT(*) as admin_count FROM admin_login WHERE username = :admin""",
#             "select",
#             params={"admin": admin},
#         )[0]["admin_count"]
#         return str(admin_count)
#     except Exception as e:
#         event_logger.error(e)
#         return render_template("admin/500.html")


# @admin_details.route("/check_email", methods=["POST"])
# def check_email():
#     """
#     Validation function Check Intent is present or not(Unique)
#     :return: admin email Count String
#     """
#     try:
#         projectpath = request.form
#         query_data = projectpath.to_dict(flat=False)
#         admin = query_data.pop("answer3")[0]
#         admin_count = execute_query(
#             """SELECT COUNT(*) as admin_count FROM admin_login WHERE email = :email""",
#             "select",
#             params={"email": admin},
#         )[0]["admin_count"]
#         return str(admin_count)

#     except Exception as e:
#         event_logger.error(e)
#         return render_template("admin/500.html")


# @admin_details.route("/download_admin")
# def download_admin():
#     """
#     Download All Intent In csv Format
#     :return: Return CSV(All Admin List)
#     """
#     try:
#         if session.get("islogin") != 1:
#             return redirect(
#                 url_for("auth.login", _external=True, _scheme=config["SSL_SECURITY"])
#             )
#     except Exception as e:
#         event_logger.error(e)
#         return render_template("admin/401.html")
#     try:
#         cursor = execute_query("SELECT * FROM admin_login", "select")
#         df = pd.json_normalize(cursor)
#         timestamp = str(datetime.now().replace(microsecond=0).isoformat("_"))
#         csv_file = df.to_csv(
#             encoding="utf-8",
#             index=False,
#         )
#         resp = Response(
#             csv_file,
#             mimetype="text/csv",
#             headers={
#                 "Content-disposition": f"attachment; filename=Chat_user_{timestamp}.csv"
#             },
#         )
#         return resp
#     except Exception as e:
#         event_logger.error(e)
#         return render_template("admin/500.html")
