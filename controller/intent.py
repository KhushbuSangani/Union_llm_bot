from flask import (
    render_template,
    request,
    session,
    redirect,
    Blueprint,
    Response,
    url_for,
    jsonify,
    send_file,
    send_from_directory,
)
import os
import flask_paginate
from utils.db_connector import execute_query
from datetime import datetime, timedelta
from utils import fallback_handler
from controller.sso_login import get_latest_token
from utils import db_handler
from utils import ingest
from io import BytesIO
import pandas as pd
import yaml
import io
from utils.logger import logger
from utils import config
import json
import mimetypes
import re
import ast
import threading
import os
import threading
event_logger = logger()

intent_details = Blueprint("intent", __name__)

rows_per_page = 10

def is_date(string, format):
    try:
        datetime.strptime(string, format)
        return True
    except ValueError:
        return False

EXTENSION_TO_MIME = {
    '.pdf': 'application/pdf',
    '.txt': 'text/plain',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.gif': 'image/gif',
    '.html': 'text/html',
    '.css': 'text/css',
    '.js': 'application/javascript',
    '.json': 'application/json',
    '.csv': 'text/csv',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.xml': 'application/xml',
    '.zip': 'application/zip',
    '.rar': 'application/x-rar-compressed'
}
@intent_details.route("/bulk_intent")
def bulk_intent_page():
    """
    Add New Intent  - Add single Intent / Bulk Intent(Upload xslx)
    :return: Add Intent View / Intent list(list)/training Model List(List)
    """
    try:
        if session.get("islogin") != 1:
            return redirect(
                url_for("auth.login", _external=True, _scheme=config.SSL_SECURITY)
            )
        if session.get("token") != get_latest_token(session.get("user_id")):
            return redirect(
                url_for("auth.login", _external=True, _scheme=config.SSL_SECURITY)
            )
    except:
        event_logger.error(e)
        return render_template("admin/500.html")

    try:
        session["status"] = "add"
        # all_intents = db_handler.fetch_all_intents()
        # _all_intents = []
        # for idx, x in enumerate(all_intents):
        #     _all_intents.append(
        #         [
        #             idx + 1,
        #             x.get("intent"),
        #             x.get("response"),
        #             x.get("query"),
        #             x.get("entities"),
        #             x.get("timestamp"),
        #             x.get("user"),
        #             x.get("status"),
        #             x.get("nlu_id"),
        #         ]
        #     )
        # all_training = db_handler.fetch_training_model()
        # _all_training = []
        # for id_x, y in enumerate(all_training):
        #     _all_training.append(
        #         [
        #             id_x + 1,
        #             y.get("model_profile_name"),
        #             y.get("status"),
        #             y.get("timestamp"),
        #             y.get("trained_by"),
        #         ]
        #     )
        return render_template(
            "admin/bulk_intent.html", data=[], train_data=[]
        )
    except Exception as e:
        print(e)
        event_logger.error(e)
        return render_template("admin/500.html")

def fetch_files_with_limit_offset(
    limit,
    offset,
    file_name=None,
    file_format=None,
    created_by=None,
    file_status=None,
    file_size=None,  
    sort_by="upload_date",
    sort_order=None,
):
    # base_query = """
    #     SELECT files.*, admin_login.username AS created_by_username
    #     FROM uploaded_llm_files AS files
    #     LEFT JOIN admin_login ON files.created_by = admin_login.user_id
    #     WHERE 1=1
    #"""
    base_query = f"""SELECT files.* , admin_login.username  FROM uploaded_llm_files files LEFT JOIN admin_login ON files.created_by = admin_login.user_id WHERE files.file_status= '{file_status}' """
    dynamic_conditions = ""
    params = {}

    # Add conditions dynamically
    if file_name:
        base_query += " AND LOWER(files.file_name) LIKE LOWER(:file_name)"
        params["file_name"] = f"%{file_name.lower()}%"

    if file_format:
        base_query += " AND files.file_format = :file_format"
        params["file_format"] = file_format

    if created_by:
    
        if is_date(created_by, "%Y-%m-%d"):
            base_query += " AND TRUNC(files.upload_date) = TRUNC(TO_DATE(:created_date, 'YYYY-MM-DD'))"
            params["created_date"] = created_by
        else:
            base_query += "AND LOWER(admin_login.username) LIKE LOWER(:created_by)"
            params["created_by"] = f"%{created_by}%"
    if sort_order and sort_order.upper() in ['ASC', 'DESC']:
        order_by_clause = f"ORDER BY a.file_size {sort_order.upper()}"
    else:
        order_by_clause = "ORDER BY a.upload_date DESC, a.file_id DESC"

    # Final Pagination Query using ROW_NUMBER()
    paginated_query = f"""
    SELECT * FROM (
        SELECT a.*, ROW_NUMBER() OVER ({order_by_clause}) AS rnum
        FROM ({base_query}) a
    )
    WHERE rnum > :start_row AND rnum <= :end_row
    """

    # Pagination parameters
    params["end_row"] = offset + limit
    params["start_row"] = offset 
    
    
    try:
        results = execute_query(paginated_query, "select", params=params)
        return results

    except Exception as e:        
        event_logger.error(e)
    
@intent_details.route("/display_llm_files")
def display_llm_files():
    """
    Display file details with pagination, search, and filters.
    :return: Rendered template with file details
    """
    try:
        if session.get("islogin") != 1:
            return redirect(
                url_for("auth.login", _external=True, _scheme=config.SSL_SECURITY)
            )
    except Exception as e:
        event_logger.error(e)
        return render_template("admin/400.html")

    try:
        session["status"] = "llm_file"
        rows_per_page = request.args.get("limit", default=10, type=int)  # Dynamic limit
        page = request.args.get("page", type=int, default=1)
        file_name = request.args.get("search_file_name", default=None)
        file_format = request.args.get("file_format", default=None)
        file_size = request.args.get("search_size", default=None)
        created_by = request.args.get("search_created_by", default=None)
        sort_order = request.args.get("sort_order", default=None)
        offset = (page - 1) * rows_per_page
        all_files = fetch_files_with_limit_offset(
            limit=rows_per_page,
            offset=offset,
            file_name=file_name,
            file_format=file_format,
            file_size=file_size,
            created_by=created_by,
            file_status='pending',
            sort_by="upload_date",
            sort_order=sort_order,
        )
        file_details = []
        for idx, file in enumerate(all_files):
            try:
                user = db_handler.admin_user(file.get("created_by"))
            except:
                user = ""
            file_details.append(
                {
                    "id":  idx + 1+ offset,
                    "file_id":file.get("file_id"),
                    "name": file.get("file_name"),
                    "format": file.get("file_format"),
                    "size": file.get("file_size"),
                    "upload_date": file.get("upload_date"),
                    "created_by": user,
                    "status": file.get("file_status"),
                    "path": file.get("file_path"),
                    "comments": file.get("comments"),
                    "last_updated": file.get("last_updated"),
                    
                }
            )
        total_files_count = execute_query(
            "SELECT COUNT(*) AS total_files FROM uploaded_llm_files where file_status='pending'" , opration="select", fetch_one=True
        )[0]["total_files"]
        offset = (page - 1) * rows_per_page

        pagination = flask_paginate.Pagination(
            page=page,
            per_page=rows_per_page,
            offset=offset,
            total=total_files_count,
            record_name="file_details",
            css_framework="bootstrap5",
        )
        total_pages = (total_files_count + rows_per_page - 1) // rows_per_page  # Calculate total pages

        pagination_data = {
            "current_page": page,
            "total_pages": total_pages,
            "has_prev": page > 1,
            "has_next": page < total_pages,
            "prev_page": page - 1 if page > 1 else None,
            "next_page": page + 1 if page < total_pages else None,
            "page_numbers": list(range(1, total_pages + 1))
        }
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            rows_html = render_template(
                "admin/rows_llm_files.html",
                data=file_details,
                file_length=total_files_count,

            )
            return jsonify(
                {
                    "files":file_details,
                    "pagination":pagination_data
                }
            )
        else:           
            return render_template(
                "admin/llm_file_list.html",
                data=file_details,
                pagination=pagination_data,
                file_length=total_files_count
            )

    except Exception as e:
        print(e,33333333333333333333333333333333333333333333333333)
        event_logger.error(e)
        return render_template("admin/500.html")

@intent_details.route("/embedded_file_list")
def embedded_file_list():
    """
    Display Embedded file details with pagination, search, and filters.
    :return: Rendered template with file details
    """
    try:
        if session.get("islogin") != 1:
            return redirect(
                url_for("auth.login", _external=True, _scheme=config.SSL_SECURITY)
            )
    except Exception as e:
        event_logger.error(e)
        return render_template("admin/400.html")
    try:        
        session["status"] = "embedded_file_list"
        rows_per_page = request.args.get("limit", default=10, type=int)  # Dynamic limit
        page = request.args.get("page", type=int, default=1)
        file_name = request.args.get("search_file_name", default=None)
        file_format = request.args.get("file_format", default=None)
        file_size = request.args.get("search_size", default=None)
        created_by = request.args.get("search_created_by", default=None)
        sort_order = request.args.get("sort_order", default=None)
        offset = (page - 1) * rows_per_page
        all_files = fetch_files_with_limit_offset(
            limit=rows_per_page,
            offset=offset,
            file_name=file_name,
            file_format=file_format,
            file_size=file_size,
            created_by=created_by,
            file_status='embedded',
            sort_by="upload_date",
            sort_order=sort_order,
        )
        file_details = []
        for idx, file in enumerate(all_files):
            try:
                user = db_handler.admin_user(file.get("created_by"))
            except:
                user = ""
            file_details.append(
                {
                    "id":  idx + 1+ offset,
                    "file_id":file.get("file_id"),
                    "name": file.get("file_name"),
                    "format": file.get("file_format"),
                    "size": file.get("file_size"),
                    "upload_date": file.get("upload_date"),
                    "created_by": user,
                    "status": file.get("file_status"),
                    "path": file.get("file_path"),
                    "comments": file.get("comments"),
                    "last_updated": file.get("last_updated"),
                    
                }
            )
        print(file_details)
        page = request.args.get(
            flask_paginate.get_page_parameter(), type=int, default=1
        )
        total_files_count = execute_query(
            "SELECT COUNT(*) AS total_files FROM uploaded_llm_files where file_status='embedded'", opration="select")[0]["total_files"]
        offset = (page - 1) * rows_per_page

        
        total_pages = (total_files_count + rows_per_page - 1) // rows_per_page  # Calculate total pages

        pagination_data = {
            "current_page": page,
            "total_pages": total_pages,
            "has_prev": page > 1,
            "has_next": page < total_pages,
            "prev_page": page - 1 if page > 1 else None,
            "next_page": page + 1 if page < total_pages else None,
            "page_numbers": list(range(1, total_pages + 1))
        }
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            rows_html = render_template(
                "admin/rows_llm_files.html",
                data=file_details,
                file_length=total_files_count,

            )
            return jsonify(
                {
                    "files":file_details,
                    "pagination":pagination_data
                }
            )
        else:           
            return render_template(
                "admin/embedded_file_list.html",
                data=file_details,
                pagination=pagination_data,
                file_length=total_files_count
            )
    except Exception as e:
        print(e,44444444444444444444444444444444444444444444444444444444444)
        event_logger.error(e)
        return render_template("admin/500.html")


@intent_details.route('/view_file/<id>')
def view_file(id):
    print(id)
    upload_folder = os.path.join("llm_files",)
    result = execute_query("select file_name from UPLOADED_LLM_FILES where file_id=:file_id", 'select', params={'file_id': id})
    file_name = result[0]['file_name']
    file_path = os.path.join(upload_folder, file_name)
   
    file_extension = os.path.splitext(file_name)[1].lower()
   
    mime_type = EXTENSION_TO_MIME.get(file_extension)
    if not mime_type:
        mime_type = 'application/octet-stream'
    return send_from_directory(upload_folder, file_name, as_attachment=False,mimetype=mime_type)

@intent_details.route("/delete_file", methods=["POST"])
def delete_file():
    """
    Delete Intent Data and Redirect to Intent List
    :return: Redirect to Intent List View
    
    """
    try:
        if session.get("islogin") != 1:
            return redirect(
                url_for("auth.login", _external=True, _scheme=config.SSL_SECURITY)
            )
    except Exception as e:
        event_logger.error(e)
        return render_template("admin/401.html")

    try:
        projectpath = request.form
        
        response = db_handler.delete_single_file(projectpath)
        print(response)
        return response

    except Exception as e:
        event_logger.error(e)
        return render_template("admin/500.html")

@intent_details.route("/download_sample_excel")
def download_sample_excel():
    """
    Download Sample Excel File with Only Column Names
    :return: Return Excel (Sample Data)
    """
    try:
        if session.get("islogin") != 1:
            return redirect(
                url_for("auth.login", _external=True, _scheme=config.SSL_SECURITY)
            )
    except Exception as e:
        event_logger.error(e)
        return render_template("admin/401.html")

    try:
        # Column names for the Excel file

        columns = [
            "title",
            "query",
            "response",
        ]

        df = pd.DataFrame(columns=columns)
        timestamp = str(datetime.now().replace(microsecond=0).isoformat("_"))

        # Create a BytesIO object to hold the Excel file
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Sheet1")
            workbook = writer.book
            worksheet = writer.sheets["Sheet1"]

            # Protect the worksheet
            for cell in worksheet[1]:
                cell.font = cell.font.copy(bold=True)

            # Protect the worksheet

        # Rewind the buffer
        output.seek(0)

        resp = Response(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-disposition": f"attachment; filename=sample_data.xlsx"},
        )
        return resp

    except Exception as e:
        event_logger.error(e)
        return render_template("admin/500.html")


@intent_details.route("/download_chats")
def download_chats():
    """
    Download All Intent In csv Format
    :return: Return CSV(All Intent List)
    """
    try:
        if session.get("islogin") != 1:
            return redirect(
                url_for("auth.login", _external=True, _scheme=config.SSL_SECURITY)
            )
    except Exception as e:
        event_logger.error(e)
        return render_template("admin/401.html")

    try:
        all_records = execute_query(
            "SELECT * FROM conversation", opration="select", fetch_one=False
        )
        df = pd.json_normalize(all_records)
        timestamp = str(datetime.now().replace(microsecond=0).isoformat("_"))
        csv_file = df.to_csv(
            encoding="utf-8",
            index=False,
        )
        resp = Response(
            csv_file,
            mimetype="text/csv",
            headers={
                "Content-disposition": f"attachment; filename=HRbot_Chats_History_{timestamp}.csv"
            },
        )
        return resp

    except Exception as e:
        event_logger.error(e)
        return render_template("admin/500.html")
@intent_details.route("/download_caches_questions")
def download_caches_questions():
    """
    Download All Intent In csv Format
    :return: Return CSV(All Intent List)
    """
    try:
        if session.get("islogin") != 1:
            return redirect(
                url_for("auth.login", _external=True, _scheme=config.SSL_SECURITY)
            )
    except Exception as e:
        event_logger.error(e)
        return render_template("admin/401.html")

    try:
        all_records = execute_query(
            "SELECT * FROM conversation where admin_action='like'", opration="select", fetch_one=False
        )
        df = pd.json_normalize(all_records)
        timestamp = str(datetime.now().replace(microsecond=0).isoformat("_"))
        csv_file = df.to_csv(
            encoding="utf-8",
            index=False,
        )
        resp = Response(
            csv_file,
            mimetype="text/csv",
            headers={
                "Content-disposition": f"attachment; filename=HRbot_Cache_Questions_{timestamp}.csv"
            },
        )
        return resp

    except Exception as e:
        event_logger.error(e)
        return render_template("admin/500.html")


@intent_details.route("/chat_list")
def chat_list():
    try:
        if session.get("islogin") != 1:
            return redirect(
                url_for("auth.login", _external=True, _scheme=config.SSL_SECURITY)
            )
    except Exception as e:
        event_logger.error(e)
        return render_template("admin/404.html")
    if session.get("token") != get_latest_token(session.get("user_id")):
        return redirect(
            url_for("auth.login", _external=True, _scheme=config.SSL_SECURITY)
        )

    try:
        session["status"] = "chat_list"
        all_data = fallback_handler.fetch_chats()
        
        data = []
        for idx, x in enumerate(all_data):
            try:
                user = db_handler.emp_name(x.get("user_id"))
            except:
                user = "Unknown user"
            data.append(
                [
                    idx + 1,
                    x.get("query"),
                    x.get("response_text"),
                    x.get("admin_action"),
                    x.get("feedback_msg"),
                    x.get("id"),
                    user,
                    x.get("timestamp")
                ]
            )

        page = request.args.get(
            flask_paginate.get_page_parameter(), type=int, default=1
        )
        offset = (page - 1) * rows_per_page
        x = (int(page) - 1) * rows_per_page
        y = int(page) * rows_per_page
        chat_data = data[x:y]
        pagination = flask_paginate.Pagination(
            page=page,
            per_page=rows_per_page,
            offset=offset,
            total=len(data),
            record_name="chat_list",
            css_framework="bootstrap5",
        )
        return render_template(
            "admin/chat_list.html", data=chat_data, pagination=pagination
        )
    except Exception as e:
        print(e,55555555555555555555555555555555555555555555555555555555)
        event_logger.error(e)
        return render_template("admin/500.html")

@intent_details.route("/delete_all_files", methods=["POST"])
def delete_all_files():
    """
    Delete All Intent Data and Redirect to Intent List
    :return: Redirect to Intent List View-
    """
    try:
        data = request.get_json()
        selected_files = data.get('files', [])
        response=db_handler.delete_all_files(selected_files)
        return response
    except Exception as e:
        event_logger.error(e)
        return render_template("admin/500.html")
    
    
@intent_details.route("/delete_all_embedded_files", methods=["POST"])
def delete_all_embedded_files():
    """
    Delete All Intent Data and Redirect to Intent List
    :return: Redirect to Intent List View-
    """
    try:
        data = request.get_json()
        selected_files = data.get('files', [])
        all_files = db_handler.fetch_embedded_files_list(selected_files)
        file_details = []
        print(all_files)
        for file_name in all_files:
            if file_name:  # Ensure file_name is not None
                name_without_ext = os.path.splitext(file_name)[0]  # Remove extension
                file_details.append(name_without_ext)
                try:
                    db_handler.delete_from_cache_question(name_without_ext)
                except:
                    pass
            print(file_name)
            execute_query(f"""UPDATE UPLOADED_LLM_FILES set FILE_STATUS='pending' WHERE FILE_STATUS='embedded' and FILE_NAME='{file_name}' """,'update')
        ingest.delete_all_embedded_files(file_details)
        
        return redirect(
            url_for(
                "intent.display_llm_files"
            )
        )
    except Exception as e:
        print(e,444444444444444444444444444444)
        event_logger.error(e)
        return render_template("admin/500.html")

@intent_details.route("/delete_chat", methods=["POST"])
def delete_chat():
    """
    Delete All Intent Data and Redirect to Intent List
    :return: Redirect to Intent List View-
    """
    try:
        query_data = request.form
        query_data = query_data.to_dict(flat=False)
        id = query_data.pop("id")[0]
        db_handler.delete_chat(id)
        return redirect(
            url_for(
                "intent.display_llm_files", _external=True, _scheme=config.SSL_SECURITY
            )
        )
    except Exception as e:
        event_logger.error(e)
        return render_template("admin/500.html")

@intent_details.route("/delete_all_chats", methods=["POST"])
def delete_all_chats():
    """
    Delete All Intent Data and Redirect to Intent List
    :return: Redirect to Intent List View-
    """
    try:
        db_handler.delete_all_chats()
        return redirect(
            url_for(
                "intent.display_llm_files", _external=True, _scheme=config.SSL_SECURITY
            )
        )
    except Exception as e:
        event_logger.error(e)
        return render_template("admin/500.html")

@intent_details.route("/add_files_for_llm", methods=["POST"])
def add_files_for_llm():
    """
    :Input: XLSX File
    Add Bulk Intent and redirect to Add Form
    :return: Redirect to Add Form View
    """
    try:
        if session.get("islogin") != 1:
            return redirect(
                url_for("auth.login", _external=True, _scheme=config.SSL_SECURITY)
            )
        if session.get("token") != get_latest_token(session.get("user_id")):
            return redirect(
                url_for("auth.login", _external=True, _scheme=config.SSL_SECURITY)
            )
    except:
        event_logger.error(e)
        return render_template("admin/500.html")
    try:
        
        form_data = request.form.to_dict(flat=False)
        now = datetime.now()
        schedule_time = now + timedelta(minutes=5)
        if form_data.get("schedule_training") == "schedule":
            schedule_time = form_data.get("train_schedule_date")
        intent_file = request.files
        response = db_handler.insert_llm_files(intent_file, schedule_time)
       
        return response
    except Exception as e:
        print(e,222222222222222222222222)
        event_logger.error(e)
        return render_template("admin/500.html")
    

@intent_details.route('/submit_feedback_admin', methods=['POST'])
def submit_feedback_admin():
    """Handles admin feedback submission (like, dislike, or comment)."""
    try:
        feedback_data = request.get_json()
        action = feedback_data.get('action')
        text = feedback_data.get('text')
        conversation_id = feedback_data.get('conversation_id')
        user_id = feedback_data.get('emp_no', '')
        event_logger.info(f"Received feedback from user_id: {user_id}, action: {action}, conversation_id: {conversation_id}")
        
        # Ensure required parameters exist
        if not conversation_id or not action:
            event_logger.error("Missing required parameters: conversation_id or action")
            return jsonify({"status": "error", "message": "Missing required parameters"}), 400
        
        admin_id = session.get('user_id') if session else None
        timestamp = datetime.now().isoformat()
        
        if not user_id:
            try:
                if action == 'comment':
                    update_query = """
                        UPDATE conversation
                        SET feedback_msg = :text, ADMIN_ID = :admin_id, TIMESTAMP = TO_TIMESTAMP(:timestamp, 'YYYY-MM-DD"T"HH24:MI:SS.FF6')
                        WHERE ID = :conversation_id
                    """
                    params = {
                        "conversation_id": conversation_id,
                        "admin_id": admin_id,
                        "timestamp": timestamp,
                        "text": text  
                    }
                    event_logger.info(f"Executing query to update comment feedback: {params}")
                    execute_query(update_query, "update", params=params)
                
                elif action in ['like', 'dislike']:
                    update_query = """
                        UPDATE conversation
                        SET ADMIN_ACTION = :feedback_action, ADMIN_ID = :admin_id, TIMESTAMP = TO_TIMESTAMP(:timestamp, 'YYYY-MM-DD"T"HH24:MI:SS.FF6')
                        WHERE ID = :conversation_id
                    """
                    params = {
                        "conversation_id": conversation_id,
                        "admin_id": admin_id,
                        "timestamp": timestamp,
                        "feedback_action": action,
                    }
                    event_logger.info(f"Executing query to update like/dislike feedback: {params}")
                    execute_query(update_query, "update", params=params)
                    
                    # Fetch related questions and answers from Oracle database
                    try:
                        db_handler.fetch_questions_and_answers_from_oracle(conversation_id, action)
                    except Exception as db_error:
                        event_logger.error(f"Error fetching data from Oracle: {db_error}")
                
                return jsonify({
                    "status": "success",
                    "action": action,
                    "message": "Feedback saved successfully"
                })
            
            except Exception as query_error:
                event_logger.error(f"Database query execution error: {query_error}")
                return jsonify({"status": "error", "message": "Database update failed"}), 500
        
    except Exception as e:
        event_logger.error(f"Unexpected error while processing feedback: {e}")
        return jsonify({"status": "error", "message": "An error occurred while saving the feedback"}), 500


def process_files(selected_files, selected_status):
    """
    Function to process files, extract text, index them, and update statuses.
    This is meant to run in a background thread.
    """
    try:
        llm_files_dir = "llm_files"
        files = os.listdir(llm_files_dir)
        
        # Fetch list of files to be processed based on selected_files and status.
        if selected_files and selected_status == 'false':
            untrained_files = db_handler.fetch_untrained_files(selected_files)
        else:
            untrained_files = db_handler.fetch_all_untrained_files(selected_files)
        
        for file_name in files:
            file_path = os.path.join(llm_files_dir, file_name)
            if os.path.isfile(file_path) and file_name in untrained_files:
                event_logger.info(f"Processing file: {file_name}")
                
                file_extension = file_name.split(".")[-1].lower()
                text_chunks = []
                
                # Extract text based on file format
                if file_extension == "pdf":
                    raw_text = ingest.extract_text_from_pdf([file_path])
                    text_chunks = ingest.chunk_text(raw_text)
                elif file_extension == "csv":
                    text_chunks = ingest.extract_text_from_csv(file_path)
                elif file_extension == "xlsx":
                    text_chunks = ingest.extract_data_from_excel(file_path)
                elif file_extension =='docs':
                    text_chunks=ingest.extract_text_from_docx(file_path)
                else:
                    event_logger.error(f"Unsupported file type: {file_extension}")
                    continue
                
                # Index extracted content in Qdrant
                ingest.indexing(text_chunks, file_name)
                
                # Update file status in the database
                update_sql = """
                    UPDATE uploaded_llm_files 
                    SET file_status = :file_status 
                    WHERE file_name = :file_name
                """
                execute_query(update_sql, 'update', params={"file_status": "embedded", "file_name": file_name})
    except Exception as e:
        print(e,88888888888888888888888888)
        event_logger.error(f"Error in process_files: {e}")
    
@intent_details.route("/embedding_llm_files", methods=["POST"])
def embedding_llm_files():
    """
    Endpoint to initiate embedding of LLM files in a separate thread.
    """
    try:
        data = request.get_json()
        selected_files = data.get('files', [])
        selected_status = data.get('select_all_status', None)
        
       
        # Start the file processing in a new background thread.
        processing_thread = threading.Thread(target=process_files, args=(selected_files, selected_status))
        processing_thread.daemon = True  # Optional: Ensures the thread exits when the main program does.
        processing_thread.start()
        
        # Immediately redirect the user (or return a message) without waiting for the processing to complete.
        return redirect(url_for("intent.embedded_file_list"))
    
    except Exception as e:
        event_logger.error(f"Error in embedding_llm_files: {e}")
        return redirect(url_for("intent.display_llm_files"))

@intent_details.route("/cache_questions")    
def cache_questions():
    try:
        if session.get("islogin") != 1:
            return redirect(
                url_for("auth.login", _external=True, _scheme=config.SSL_SECURITY)
            )
    except Exception as e:
        event_logger.error(e)
        return render_template("admin/400.html")
    try:
        session["status"] = "cache_questions"
        rows_per_page = request.args.get("limit", default=10, type=int)
        page = request.args.get("page", default=1, type=int)
        offset = (page - 1) * rows_per_page

        # Filters
        search_query = request.args.get("search_query", "").lower()
        search_response = request.args.get("search_response", "").lower()
        search_file_name = request.args.get("search_file_name", "").lower()
        search_created_by = request.args.get("search_created_by", "").lower()
        print(search_query,search_response,search_file_name,search_created_by)
        # Fetch all cached questions
        all_data = fallback_handler.fetch_cache_questions(
            limit=rows_per_page,
            offset=offset,
            collection_name=search_file_name, 
            created_by=search_created_by, 
            query_text=search_query,
            response_text=search_response
        )

        data = []
        for idx, x in enumerate(all_data):
            try:
                user = db_handler.emp_name(x.get("user_id"))
            except:
                user = "Unknown user"
            metadata_raw = x.get("metadata", {})
            try:
                collection_name = metadata_raw.get("collection_name", "N/A")
            except Exception:
                collection_name = "Invalid JSON"

            data.append({
                "id":  idx + 1+ offset,
                "cache_id": x.get("id"),
                "query": x.get("query"),
                "response": x.get("response_text"),
                "file_name": collection_name,
                "created_by": user,
                "send_date": x.get("timestamp"),
                "comment": x.get("feedback_msg"),
            })
        print(data)
        total_count = execute_query(
            "SELECT COUNT(*) AS total_ques FROM conversation where admin_action='like'" , opration="select", fetch_one=True
        )[0]["total_ques"]
        paginated_data = data[offset:offset + rows_per_page]

        total_pages = (total_count + rows_per_page - 1) // rows_per_page
        pagination_data = {
            "current_page": page,
            "total_pages": total_pages,
            "has_prev": page > 1,
            "has_next": page < total_pages,
            "prev_page": page - 1 if page > 1 else None,
            "next_page": page + 1 if page < total_pages else None,
            "page_numbers": list(range(1, total_pages + 1))
        }

        # Return JSON if it's an AJAX request
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({
                "data": data,
                "pagination": pagination_data
            })

        # Else return full HTML page
        return render_template(
            "admin/cache_questions.html",
            data=data,
            pagination=pagination_data,
            file_length=total_count
        )

    except Exception as e:
        print(e, 555555555555555555555555555)
        event_logger.error(e)
        return render_template("admin/500.html")
@intent_details.route("/download_embedded_files")
def download_embedded_files():
    """
    Download All Intent In csv Format
    :return: Return CSV(All Intent List)
    """
    try:
        if session.get("islogin") != 1:
            return redirect(
                url_for("auth.login", _external=True, _scheme=config.SSL_SECURITY)
            )
    except Exception as e:
        event_logger.error(e)
        return render_template("admin/401.html")

    try:
        all_records = execute_query(
            "SELECT * FROM uploaded_llm_files WHERE file_status='embedded'", opration="select", fetch_one=False
        )
        df = pd.json_normalize(all_records)
        timestamp = str(datetime.now().replace(microsecond=0).isoformat("_"))
        csv_file = df.to_csv(
            encoding="utf-8",
            index=False,
        )
        resp = Response(
            csv_file,
            mimetype="text/csv",
            headers={
                "Content-disposition": f"attachment; filename=LLM_EMBEDDED_FILES_{timestamp}.csv"
            },
        )
        return resp

    except Exception as e:
        event_logger.error(e)
        return render_template("admin/500.html")


@intent_details.route("/download_user_feedback")
def download_user_feedback():
    try:
        if session.get("islogin") != 1:
            return redirect(
                url_for("auth.login", _external=True, _scheme=config.SSL_SECURITY)
            )
    except Exception as e:
        event_logger.error(e)
        return render_template("admin/401.html")

    try:
        all_data = fallback_handler.fetch_user_feedback_and_tickets()
        df = pd.json_normalize(all_data)
        timestamp = str(datetime.now().replace(microsecond=0).isoformat("_"))
        csv_file = df.to_csv(
            encoding="utf-8",
            index=False,
        )
        resp = Response(
            csv_file,
            mimetype="text/csv",
            headers={
                "Content-disposition": f"attachment; filename=USER_FEEDBACK_{timestamp}.csv"
            },
        )
        return resp

    except Exception as e:
        event_logger.error(e)
        return render_template("admin/500.html")
@intent_details.route("/user_feedback_list")
def user_feedback_list():
    
    try:
        if session.get("islogin") != 1:
            return redirect(
                url_for("auth.login", _external=True, _scheme=config.SSL_SECURITY)
            )
    except Exception as e:
        event_logger.error(e)
        return render_template("admin/401.html")
    
    try:
        session["status"] = "user_feedback_list"
        all_data = fallback_handler.fetch_user_feedback_and_tickets()
        print(all_data)
        data = []
        for idx, x in enumerate(all_data):
            try:
                user = db_handler.emp_name(x.get("user_id"))
            except:
                user = "Unknown user"
            data.append(
                [
                    idx + 1,
                    x.get("query"),
                    x.get("response_text"),
                    x.get("user_action"),
                    x.get("description"),
                    x.get("id"),
                    user,
                    x.get("timestamp"),
                    x.get("status"),
                    x.get("ticket_id")
                    
                ]
            )
        page = request.args.get(
            flask_paginate.get_page_parameter(), type=int, default=1
        )
        offset = (page - 1) * rows_per_page
        x = (int(page) - 1) * rows_per_page
        y = int(page) * rows_per_page
        chat_data = data[x:y]
        pagination = flask_paginate.Pagination(
            page=page,
            per_page=rows_per_page,
            offset=offset,
            total=len(data),
            record_name="user_feedback_list",
            css_framework="bootstrap5",
        )
        return render_template(
            "admin/user_feedback_list.html", data=chat_data, pagination=pagination
        )
    except Exception as e:
        print(e,55555555555555555555555555555555555555555555555555555555)
        event_logger.error(e)
        return render_template("admin/500.html")
    
@intent_details.route("/delete_single_user_feedback", methods=['POST'])
def delete_single_user_feedback():
    try:
        if session.get("islogin") != 1:
            return redirect(
                url_for("auth.login", _external=True, _scheme=config.SSL_SECURITY)
            )
    except Exception as e:
        event_logger.error(e)
        return render_template("admin/401.html")

    try:
        query_data = request.form
        query_data = query_data.to_dict(flat=False)
        id = query_data.pop("id")[0]
        ticket_id = query_data.pop("ticket_id")[0]

        r=db_handler.delete_single_user_feedback(id,ticket_id)
        
        return r

    except Exception as e:
        event_logger.error(e)
        return render_template("admin/500.html")
@intent_details.route("/delete_user_feedback", methods=['POST'])
def delete_user_feedback():
    try:
        if session.get("islogin") != 1:
            return redirect(
                url_for("auth.login", _external=True, _scheme=config.SSL_SECURITY)
            )
    except Exception as e:
        event_logger.error(e)
        return render_template("admin/401.html")

    try:

        r=db_handler.delete_user_feedback()
        
        return r

    except Exception as e:
        event_logger.error(e)
        return render_template("admin/500.html")
@intent_details.route("/dashboard_test", methods=["GET"])
def deshboard_test():
    session["status"] = "dashboard_test"
    try:
        session["status"] = "dashboard_test"
        return render_template("admin/add_intent.html")
    except Exception as e:
        event_logger.error(e)
        return render_template("admin/500.html")



@intent_details.route("/download_intents")
def download_intents():
    """
    Download All Intent In csv Format
    :return: Return CSV(All Intent List)
    """
    try:
        if session.get("islogin") != 1:
            return redirect(
                url_for("auth.login", _external=True, _scheme=config.SSL_SECURITY)
            )
    except Exception as e:
        event_logger.error(e)
        return render_template("admin/401.html")

    try:
        all_records = execute_query(
            "SELECT * FROM uploaded_llm_files WHERE file_status='pending'", opration="select", fetch_one=False
        )
        df = pd.json_normalize(all_records)
        timestamp = str(datetime.now().replace(microsecond=0).isoformat("_"))
        csv_file = df.to_csv(
            encoding="utf-8",
            index=False,
        )
        resp = Response(
            csv_file,
            mimetype="text/csv",
            headers={
                "Content-disposition": f"attachment; filename=LLM_PENDING_FILE_{timestamp}.csv"
            },
        )
        return resp

    except Exception as e:
        event_logger.error(e)
        return render_template("admin/500.html")


@intent_details.route("/download_tickets")
def download_tickets():
    """
    Download All Intent In csv Format
    :return: Return EXCEl(All Intent List)
    """
    try:
        if session.get("islogin") != 1:
            return redirect(
                url_for("auth.login", _external=True, _scheme=config.SSL_SECURITY)
            )
    except Exception as e:
        event_logger.error(e)
        return render_template("admin/401.html")

    try:
        query = """
                SELECT REQUESTID, TYPEOFQUERY, SUBJECT, PRIORITY, DESCRIPTION, STATUS, CREATEDBY, CREATEDDATE,
                    MODIFIEDBY, MODIFIEDDATE, RESOLVEDBY, REQUIREDDAYS, MODULE_ID, MOBILE_NUMBER FROM GP_USER_QUERY
                WHERE STATUS != 'Resolved' AND TYPEOFQUERY = 'Process Issue'
            """


        all_records = execute_query(query, "select", fetch_one=False)
        df = pd.json_normalize(all_records)

        # Create a timestamp for the file name
        timestamp = datetime.now().replace(microsecond=0).isoformat("_")

        # Use BytesIO to write the DataFrame to an Excel file in memory
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Sheet1")
            workbook = writer.book
            worksheet = writer.sheets["Sheet1"]

        # Seek to the beginning of the BytesIO object
        output.seek(0)

        # Create a Response object to return the Excel file
        resp = Response(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-disposition": f"attachment; filename=HRbot_Tickets_{timestamp}.xlsx"
            },
        )
        return resp

    except Exception as e:
        event_logger.error(e)
        return render_template("admin/500.html")


#--------------------------------------------------RASA CODE-----------------------------------#


# def combine_response(intent):
#     response_type = intent.get("response_type")
#     response_text = intent.get("response_text")
#     response_payload = intent.get("response_payload")

#     if response_type == "text":
#         return response_text
#     elif response_type == "buttons":
#         # Assuming response_payload is a JSON array
#         return f"['{response_type}','{response_text}',{response_payload}]"
#     else:
#         return "Unknown Response Type"


# def fetch_intents_with_limit_offset(
#     limit,
#     offset,
#     intent=None,
#     status=None,
#     created_by=None,
#     query=None,
#     sort_by="timestamp",
#     sort_order="DESC",
# ):

#     base_query = """
#         SELECT nlu_data.*, admin_login.username FROM nlu_data 
#         LEFT JOIN admin_login ON nlu_data.user_id = admin_login.user_id 
#         WHERE 1=1
#     """
#     params = {}

#     if intent:
#         base_query += (
#             " AND (nlu_data.intent LIKE :intent OR nlu_data.title LIKE :intent)"
#         )
#         params["intent"] = f"%{intent}%"

#     if status:
#         base_query += " AND nlu_data.status = :status"
#         params["status"] = status

#     if created_by:

#         if is_date(created_by, "%Y-%m-%d"):
#             base_query += " AND TRUNC(nlu_data.timestamp) = TRUNC(TO_DATE(:created_date, 'YYYY-MM-DD'))"
#             params["created_date"] = created_by
#         else:
#             base_query += "AND LOWER(admin_login.username) LIKE LOWER(:created_by)"
#             params["created_by"] = f"%{created_by}%"

#     if query:
#         base_query += " AND nlu_data.query LIKE :query"
#         params["query"] = f"%{query}%"
#     base_query += " ORDER BY nlu_data.timestamp DESC"
#     paginated_query = f"""
#     SELECT * FROM (
#         SELECT a.*, ROWNUM rnum
#         FROM ({base_query}) a
#         WHERE ROWNUM <= :end_row
#     )
#     WHERE rnum > :start_row ORDER BY timestamp DESC
#     """
#     params["end_row"] = offset + limit
#     params["start_row"] = offset
#     results = execute_query(paginated_query, "select", params)
#     return results


# @intent_details.route("/display_intents")
# def display_intents():
#     """
#     List of all Intents
#     :return: Edit Intent View with
#         data: Intent List(list)
#         train: Count of Untrained Intents(string)
#     """
#     try:
#         if session.get("islogin") != 1:
#             return redirect(
#                 url_for("auth.login", _external=True, _scheme=config.SSL_SECURITY)
#             )
#     except Exception as e:
#         event_logger.error(e)
#         return render_template("admin/400.html")

#     try:
#         if session.get("token") != get_latest_token(session.get("user_id")):
#             return redirect(
#                 url_for("auth.login", _external=True, _scheme=config.SSL_SECURITY)
#             )
#     except Exception as e:
#         event_logger.error(e)
#         return render_template("admin/400.html")
#     try:
#         rows_per_page = 10
#         page = request.args.get("page", type=int, default=1)
#         intent = request.args.get("search_intent", default=None)
#         status = request.args.get("status", default=None)
#         created_by = request.args.get("search_created_by", default=None)
#         query = request.args.get("search_query", default=None)
#         sort_order = request.args.get("sort_order", default="asc")
#         offset = (page - 1) * rows_per_page
#         session["status"] = "intent"

#         offset = (page - 1) * rows_per_page

#         session["status"] = "intent"
#         # all_intents = db_handler.fetch_intents_with_limit_offset(limit=rows_per_page, offset=offset)
#         all_intents = fetch_intents_with_limit_offset(
#             limit=rows_per_page,
#             offset=offset,
#             intent=intent,
#             status=status,
#             created_by=created_by,
#             query=query,
#             sort_by="timestamp",
#             sort_order="asc",
#         )
#         # all_intents = db_handler.fetch_all_intents()
#         _all_intents = []
#         for idx, x in enumerate(all_intents):
#             response = combine_response(x)
#             try:
#                 user = db_handler.admin_user(x.get("user_id"))
#             except:
#                 user = ""

#             _all_intents.append(
#                 [
#                     offset + idx + 1,
#                     x.get("intent"),
#                     response,
#                     x.get("query"),
#                     x.get("entities"),
#                     x.get("timestamp"),
#                     user,
#                     x.get("status"),
#                     x.get("nlu_id"),
#                 ]
#             )

#         status_data = execute_query(
#             "SELECT COUNT(*) AS status_data FROM nlu_data WHERE status = '2'",
#             opration="select",
#             fetch_one=True,
#         )[0]["status_data"]
#         intent_status = execute_query(
#             "SELECT COUNT(*) AS intent_status FROM maintain_status WHERE name = 'intent_status' AND status = '1'",
#             opration="select",
#             fetch_one=True,
#         )[0]["intent_status"]
#         staging_data_count = execute_query(
#             "SELECT COUNT(*) AS staging_data_count FROM train_data",
#             opration="select",
#             fetch_one=True,
#         )[0]["staging_data_count"]

#     except Exception as e:
#         event_logger.error(e)
#         return render_template("admin/404.html")

#     try:
#         if staging_data_count == 0:
#             can_open = 1
#         else:
#             staging_data = execute_query(
#                 "SELECT * FROM train_data ORDER BY model_id DESC FETCH FIRST 1 ROW ONLY",
#                 opration="select",
#             )
#             all_intents = []
#             for x in staging_data:
#                 all_intents.append(x["approve_status"])
#                 all_intents.append(x["deploy"])
#             if all_intents[1] == "1" or all_intents[1] == "3":
#                 can_open = 1
#             else:
#                 if (
#                     all_intents[0] == "1"
#                     or all_intents[0] == "4"
#                     or all_intents[0] == "5"
#                 ):
#                     can_open = 1
#                 else:
#                     can_open = 0
#         page = request.args.get(
#             flask_paginate.get_page_parameter(), type=int, default=1
#         )
#         offset = (page - 1) * rows_per_page
#         x = (int(page) - 1) * rows_per_page
#         y = int(page) * rows_per_page
#         intents = _all_intents
#         total_intents_count = db_handler.count_all_intents()
#         pagination = flask_paginate.Pagination(
#             page=page,
#             per_page=rows_per_page,
#             offset=offset,
#             total=total_intents_count,
#             record_name="_all_intents",
#             css_framework="bootstrap5",
#         )
#         if request.headers.get("X-Requested-With") == "XMLHttpRequest":
#             rows_html = render_template(
#                 "admin/rows.html",
#                 data=intents,
#                 train=status_data,
#                 can_open=can_open,
#                 intent_status=intent_status,
#                 pagination=pagination,
#             )
#             # If the request is AJAX, return JSON with the necessary fragments
#             return jsonify(
#                 {
#                     "rows_html": rows_html,
#                 }
#             )
#         else:
#             # If the request is a regular page load, render the full template
#             return render_template(
#                 "admin/intent_list.html",
#                 data=intents,
#                 train=status_data,
#                 can_open=can_open,
#                 intent_status=intent_status,
#                 pagination=pagination,
#             )
#     except Exception as e:
#         event_logger.error(e)
#         return render_template("admin/500.html")


@intent_details.route("/add_single_intent", methods=["POST"])
def add_single_intent():
    """
    Add Single Intent and redirect to Add Form
    :return: Redirect to Add Form View
    """
    try:
        x = db_handler.insert_single_intent(request)
        return redirect(
            url_for(
                "intent.bulk_intent_page", _external=True, _scheme=config.SSL_SECURITY
            )
        )
    except Exception as e:
        event_logger.error(e)
        return render_template("admin/500.html")


# @intent_details.route("/add_multiple_intents", methods=["POST"])
# def add_multiple_intents():
#     """
#     :Input: XLSX File
#     Add Bulk Intent and redirect to Add Form
#     :return: Redirect to Add Form View
#     """
#     try:
#         intent_file = request.files["intent_file"]

#         form_data = request.form.to_dict(flat=False)
#         now = datetime.now()
#         schedule_time = now + timedelta(minutes=1)
#         if form_data.get("schedule_training") == "schedule":
#             schedule_time = form_data.get("train_schedule_date")
#         intent_file = request.files
#         data = db_handler.insert_multiple_intent(intent_file, schedule_time)
#         if "current_intent" in session:
#             error_intent = "present"
#         else:
#             error_intent = "absent"
#         if error_intent == "present":
#             response_data = {"status": "error_occured", "message": "Error occurred"}
#         else:
#             response_data = {
#                 "status": "success",
#                 "message": "Intent added successfully",
#             }

#         return jsonify(response_data)

#     except Exception as e:
#         event_logger.error(e)
#         return jsonify({"status": "error", "message": "Internal server error"})




@intent_details.route("/download_error_file")
def download_error_file():
    if "current_intent" in session:
        error_intent = session["current_intent"]
        error = session["error"]
        df = pd.DataFrame({"session_data": error_intent, "session_error": error})
        # Save the DataFrame to an Excel file
        excel_filename = io.BytesIO()
        df.to_excel(excel_filename, index=False)
        timestamp = str(datetime.now().replace(microsecond=0).isoformat("_"))
        excel_filename.seek(0)
        # Clear the session data
        session.pop("current_intent", None)
        session.pop("error", None)
        # Provide the error file for download
        # return send_file(excel_filename, as_attachment=True)
        resp = Response(
            excel_filename,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-disposition": f"attachment; filename=BulkIntent_error_{timestamp}.xlsx"
            },
        )
        return redirect(
            url_for(
                "intent.display_llm_files", _external=True, _scheme=config.SSL_SECURITY
            )
        )

    return redirect(
        url_for("intent.display_llm_files", _external=True, _scheme=config.SSL_SECURITY)
    )







# @intent_details.route("/replace_intent")
# def edit_intent():
#     """
#     Edit Intent details
#     :id: Intent Object Id
#     :return: Edit Intent View with
#         data: Intent Details
#         x_data: Intent Example List
#     """
#     try:
#         if session.get("islogin") != 1:
#             return redirect(
#                 url_for("auth.login", _external=True, _scheme=config.SSL_SECURITY)
#             )
#     except Exception as e:
#         event_logger.error(e)
#         return render_template("admin/400.html")
#     try:
#         if session.get("token") != get_latest_token(session.get("user_id")):
#             return redirect(
#                 url_for("auth.login", _external=True, _scheme=config.SSL_SECURITY)
#             )
#     except Exception as e:
#         event_logger.error(e)
#         return render_template("admin/401.html")

#     try:
#         session["status"] = "intent"
#         id_ = request.args.get("id")
#         all_db_intents = execute_query(
#             "SELECT * FROM NLU_DATA WHERE NLU_id = :id",
#             opration="select",
#             params={"id": id_},
#             fetch_one=False,
#         )
#         all_intents = []
#         res_data = execute_query(
#             "SELECT response_type,response_text,response_payload FROM NLU_DATA WHERE NLU_id = :id",
#             opration="select",
#             params={"id": id_},
#             fetch_one=False,
#         )
#         r_data = []

#         if res_data:
#             if res_data[0]["response_type"] == "text":
#                 data = res_data[0]["response_text"]
#                 # r_data=res_data[0]['response_text']
#                 if not isinstance(data, list):
#                     r_data.append(res_data[0]["response_text"])
#                     len_res_data = str(len(r_data) - 1)
#                 else:
#                     r_data = res_data[0]["response_text"]
#                     len_res_data = str(len(res_data[0]["response_text"]) - 1)
#             else:
#                 r_data.append(res_data[0]["response_type"])
#                 r_data.append(res_data[0]["response_text"])
#                 r_data.append(res_data[0]["response_payload"])
#                 len_res_data = str(len(r_data[2]) - 1)

#         for x in all_db_intents:
#             all_intents.append(x["intent"])
#             all_intents.append(x["response_type"])
#             query_data = x["query"]

#             all_intents.append(query_data[0])
#             all_intents.append(x.get("description", False))

#             all_intents.append(x["nlu_id"])

#             if not all_intents.append(x["title"]):
#                 x["title"] = ""
#             else:
#                 all_intents.append(x["title"])
#         x_data = query_data

#         len_query_data = str(len(x_data) - 1)
#         return render_template(
#             "admin/edit_intent_new.html",
#             data=all_intents,
#             x_data=x_data,
#             r_data=r_data,
#             len_query_data=len_query_data,
#             len_res_data=len_res_data,
#         )
#     except Exception as e:
#         event_logger.error(e)
#         return render_template("admin/500.html")


# @intent_details.route("/update_intent", methods=["POST"])
# def update_intent():
#     """
#     Update Intent Data and Redirect to Intent List
#     :return: Redirect to Intent List View
#     """
#     try:
#         projectpath = request.form
#         db_handler.update_single_intent(projectpath)
#         return redirect(
#             url_for(
#                 "intent.display_intents", _external=True, _scheme=config.SSL_SECURITY
#             )
#         )
#     except Exception as e:
#         event_logger.error(e)
#         return render_template("admin/500.html")


# @intent_details.route("/check_intent", methods=["POST"])
# def check_intent():
#     """
#     Validation function Check Intent is present or not(Unique)
#     :return: Intent Count String
#     """
#     try:
#         projectpath = request.form
#         query_data = projectpath.to_dict(flat=False)
#         intent = query_data.pop("answer1")[0]
#         title = query_data.pop("answer4")[0]
#         query_intent_count = "SELECT COUNT(*) FROM nlu_data WHERE intent = :intent"
#         query_title_count = "SELECT COUNT(*) FROM nlu_data WHERE title = :title"

#         intent_count = execute_query(
#             query_intent_count,
#             opration="select",
#             params={"intent": intent},
#             fetch_one=True,
#         )[0]
#         title_count = execute_query(
#             query_title_count,
#             opration="select",
#             params={"title": title},
#             fetch_one=True,
#         )[0]

#         data = {"answer1": intent_count["count(*)"], "answer4": title_count["count(*)"]}
#         return data
#     except Exception as e:
#         event_logger.error(e)
#         return render_template("admin/500.html")


# @intent_details.route("/check_intent_duplicat", methods=["POST"])
# def check_intent_duplicat():
#     """
#     Validation function Check Intent is present or not(Unique)
#     :return: Intent Count String
#     """
#     try:
#         projectpath = request.form
#         query_data = projectpath.to_dict(flat=False)
#         intent = query_data.pop("answer1")[0]
#         title = query_data.pop("answer4")[0]
#         query_intent_count = "SELECT COUNT(*) FROM nlu_data WHERE intent = :intent"
#         query_title_count = "SELECT COUNT(*) FROM nlu_data WHERE title = :title"

#         intent_count = execute_query(
#             query_intent_count,
#             opration="select",
#             params={"intent": intent},
#             fetch_one=True,
#         )[0]
#         title_count = execute_query(
#             query_title_count,
#             opration="select",
#             params={"title": title},
#             fetch_one=True,
#         )[0]

#         data = {"answer1": intent_count["count(*)"], "answer4": title_count["count(*)"]}
#         return data
#     except Exception as e:
#         event_logger.error(e)
#         return render_template("admin/404.html")




# @intent_details.route("/intent")
# def intents():
#     """
#     List of all Intents
#     :return: Edit Intent View with
#         data: Intent List(list)
#         train: Count of Untrained Intents(string)
#     """
#     try:
#         if session.get("islogin") != 1:
#             return redirect(
#                 url_for("auth.login", _external=True, _scheme=config.SSL_SECURITY)
#             )
#     except Exception as e:
#         return render_template("admin/401.html")

#     try:
#         session["status"] = "intent"
#         all_intents = db_handler.fetch_all_intents()
#         _all_intents = []
#         for idx, x in enumerate(all_intents):
#             _all_intents.append(
#                 [
#                     idx + 1,
#                     x.get("intent"),
#                     x.get("response"),
#                     x.get("query"),
#                     x.get("entities"),
#                     x.get("timestamp"),
#                     db_handler.admin_user(x.get("user")),
#                     x.get("status"),
#                     x.get("_id"),
#                     x.get("nlu_id"),
#                 ]
#             )
#         query = """
#         SELECT count(*)
#         FROM nlu_data 
#         WHERE status = 2 
#         ORDER BY nlu_id DESC """
#         status_data = execute_query(query=query, opration="select")[0]["count(*)"]
#         return render_template(
#             "admin/intent.html", data=_all_intents, train=status_data
#         )
#     except Exception as e:
#         event_logger.error(e)
#         return render_template("admin/500.html")






# @intent_details.route("/all_chats")
# def all_chats():
#     # try:
#     #     if session.get("islogin") != 1:
#     #         return redirect(
#     #             url_for("auth.login", _external=True, _scheme=config.SSL_SECURITY)
#     #         )
#     # except Exception as e:
#     #     event_logger.error(e)
#     #     return render_template("admin/400.html")
#     # try:
#     #     if "5" not in session.get("access"):
#     #         return redirect(
#     #             url_for("auth.login", _external=True, _scheme=config.SSL_SECURITY)
#     #         )
#     # except Exception as e:
#     #     event_logger.error(e)
#     #     return render_template("admin/401.html")

#     try:
#         session["status"] = "intent_mapping"
#         all_intents = db_handler.fetch_mismatch_intent()
#         intents_list = db_handler.fetch_all_intents()
#         _all_intents = []
#         for idx, x in enumerate(all_intents):
#             _all_intents.append([idx + 1, x.get("query"), x.get("q_id")])
#         intents_data = []
#         for idx, y in enumerate(intents_list):
#             intents_data.append(
#                 [
#                     str(y.get("intent")),
#                     str(y.get("nlu_id")),
#                 ]
#             )
#         return render_template(
#             "admin/intent_mapping.html", data=_all_intents, x_data=intents_data
#         )
#     except Exception as e:
#         event_logger.error(e)
#         return render_template("admin/500.html")


# @intent_details.route("/intent_map_list")
# def intent_map_list():
#     try:
#         fallback_handler.fetch_mismatch_chats()
#         return redirect(
#             url_for(
#                 "intent.intent_mapping", _external=True, _scheme=config.SSL_SECURITY
#             )
#         )
#     except Exception as e:
#         event_logger.error(e)
#         return render_template("admin/404.html")




# @intent_details.route("/model_intent_list", methods=["POST"])
# def model_intent_list():
#     try:
#         projectpath = request.form
#         query_data = projectpath.to_dict(flat=False)
#         model_id = query_data.get("model_id")[0]
#         model_name = query_data.get("name")[0]

#         all_db_intents = execute_query(
#             """SELECT newly_train_intents FROM train_data WHERE model_id = :model_id""",
#             "select",
#             params={"model_id": model_id},
#         )[0]["newly_train_intents"]
#         all_intents = []
#         if not all_db_intents:
#             newly_train_intents = []
#         else:
#             for x in all_db_intents:
#                 all_intents.append(x["newly_train_intents"])
#             newly_train_intents = all_intents[0]

#         newly_train_intents = ",".join(
#             ["'" + str(nlu_id) + "'" for nlu_id in newly_train_intents]
#         )
#         nlu_details = execute_query(
#             f"SELECT * FROM nlu_data WHERE  nlu_id IN ({newly_train_intents})", "select"
#         )
#         _nlu_intents = []
#         for idx, x in enumerate(nlu_details):
#             _nlu_intents.append(
#                 [
#                     idx + 1,
#                     x.get("intent"),
#                     x.get("nlu_id"),
#                 ]
#             )
#         return render_template(
#             "admin/intent_rejection.html",
#             data=_nlu_intents,
#             model_name=model_name,
#             model_id=model_id,
#         )
#     except Exception as e:
#         event_logger.error(e)
#         return render_template("admin/500.html")

# #@csrf.exempt
# @intent_details.route("/delete_intent", methods=["POST"])
# def delete_intent():
#     """
#     Delete Intent Data and Redirect to Intent List
#     :return: Redirect to Intent List View
#     """
#     try:
#         projectpath = request.form

#         response = db_handler.delete_single_intent(projectpath)

#         return response

#     except Exception as e:
#         event_logger.error(e)
#         return render_template("admin/500.html")


# @intent_details.route("/delete_all_intent", methods=["POST"])
# def delete_all_intent():
#     """
#     Delete All Intent Data and Redirect to Intent List
#     :return: Redirect to Intent List View-
#     """
#     try:
#         db_handler.delete_all_intent()
#         return redirect(
#             url_for(
#                 "intent.display_intents", _external=True, _scheme=config.SSL_SECURITY
#             )
#         )
#     except Exception as e:
#         event_logger.error(e)
#         return render_template("admin/500.html")
    


# @intent_details.route("/update_res", methods=["POST"])
# def update_res():
#     projectpath = request.form
#     query_data = projectpath.to_dict(flat=False)
#     res_type = query_data.pop("res_type")[0]
#     res_data = query_data.pop("res_data")[0]
#     res_data = ast.literal_eval(res_data)
#     _all_intents = []
#     if res_type == "2":
#         all_intents = db_handler.fetch_all_intents()
#         for idx, x in enumerate(all_intents):
#             _all_intents.append(
#                 [
#                     idx + 1,
#                     x.get("intent"),
#                 ]
#             )
#         res_data = res_data[2]
#     return render_template(
#         "user_input/update_res.html",
#         data=res_type,
#         data_button=_all_intents,
#         res_data=res_data,
#     )

# #@csrf.exempt
# @intent_details.route("/intent_res", methods=["POST"])
# def intent_res():
#     projectpath = request.form
#     query_data = projectpath.to_dict(flat=False)
#     res_type = query_data.pop("res_type")[0]
#     _all_intents = []
#     if res_type == "2":
#         all_intents = db_handler.fetch_all_intents()
#         for idx, x in enumerate(all_intents):
#             _all_intents.append(
#                 [
#                     idx + 1,
#                     x.get("intent"),
#                 ]
#             )
#     return render_template(
#         "user_input/text_res.html", data=res_type, data_button=_all_intents
#     )





