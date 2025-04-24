from utils.db_connector import execute_query
from utils.logger import logger
from datetime import datetime
import pandas as pd
import re,time,json
import random
from flask import session
import threading
event_logger = logger()


def get_user_details(user_id):
    query = "SELECT * FROM user_master WHERE user_id = :user_id "
    user = execute_query(
        query, opration="select", params={"user_id": user_id}, fetch_one=True
    )
    if user:
        return user
    else:
        return {"error": user}


def get_user_roles_permissions(role_id):
    query = "SELECT access_list FROM ADMIN_ROLE WHERE ROLE_ID = :role_id"
    result = execute_query(
        query, opration="select", params={"role_id": role_id}, fetch_one=True
    )
    return result


def get_entities(input):
    all_entities = []
    for x in input:
        extracted_data = re.findall(r"\[+([[a-zA-z0-9@'.]+)]+\(([a-zA-Z]+)\)", x)
        entities = [
            all_entities.append(x[1])
            for x in extracted_data
            if x[1] not in all_entities
        ]

    return all_entities


def save_conversation(msg, response,user_id,model_name,metadata,feedback_action=None, feedback_msg=None):
    excluded_msgs = {"hi", "hello", "hey", "how are you"}
    if msg.strip().lower() in excluded_msgs:
        print(f"Ignoring message: {msg}")
        return '1'

    # Check for duplicate messages
    duplicate_check_query = """
        SELECT COUNT(*) AS total
        FROM CONVERSATION
        WHERE QUERY = :msg AND USER_ID = :user_id
    """
    duplicate_count = execute_query(duplicate_check_query, "select", params={"msg": msg, "user_id": user_id})[0]["total"]
    if duplicate_count> 0:
        fetch_query = """
        SELECT ID 
        FROM CONVERSATION
        WHERE QUERY = :msg AND USER_ID = :user_id
        """
        inserted_id = execute_query(fetch_query, "select", params={"msg": msg, "user_id": user_id})

        # Directly return the inserted ID without conditionals
        inserted_id_value = inserted_id[0]["id"]
        print(f"Duplicate message detected: {msg}")
        return inserted_id_value  # Skip insertion for duplicate messages
    ct = datetime.now()
    ts = ct.timestamp()
    id = str(int(ts))
    sql_query = """INSERT INTO CONVERSATION (ID, QUERY, RESPONSE_TEXT, USER_ID,USER_ACTION ,FEEDBACK_MSG,TIMESTAMP,MODEL_USED,METADATA)
        VALUES (:id, :msg, :response, :user_id, :user_action, :feedback_msg,TO_TIMESTAMP(:timestamp, 'YYYY-MM-DD"T"HH24:MI:SS.FF6'),:model_used,:metadata)
        """
    data = {
        "id": id,
        "msg": msg,
        "response": response,
        "user_id": user_id,
        "user_action": feedback_action,
        "feedback_msg": feedback_msg,
        "timestamp":datetime.now().isoformat(),
        "model_used":model_name,
        "metadata":json.dumps(metadata)
    }
    result=execute_query(sql_query, "insert", params=data)
    fetch_query = """
        SELECT ID 
        FROM CONVERSATION
        WHERE ID = :id
    """
    inserted_id = execute_query(fetch_query, "select", params={"id": id})

    # Directly return the inserted ID without conditionals
    inserted_id_value = inserted_id[0]["id"]
    rows = execute_query("SELECT * FROM conversation", "select")
    if len(list(rows)) > 499:
        deletion_query = """
                            DELETE FROM conversation
                                    WHERE id IN (
                                        SELECT id
                                        FROM (
                                            SELECT id, ROW_NUMBER() OVER (ORDER BY id DESC) AS row_num
                                            FROM conversation
                                        )
                                        WHERE row_num > 499
                            )

                        """
        execute_query(deletion_query, "delete")
    # time.sleep(0.5)
    # fetch_query = """
    #     SELECT ID 
    #     FROM CONVERSATION
    #     WHERE ID = :id
    # """
    # inserted_id = execute_query(fetch_query, "select", params={"id": id})
    # if inserted_id:
    #     return inserted_id[0]['id'] if inserted_id[0]['id'] else None
    # else:
    #     # Handle the error or log the failure to insert the record
    #     print("Error: No record found")
    return inserted_id_value
    



def delete_old_tickets():
    deletion_query = """
        DELETE FROM TICKET_GENERATION
        WHERE id IN (
            SELECT id
            FROM (
                SELECT id, ROW_NUMBER() OVER (ORDER BY id DESC) AS row_num
                FROM TICKET_GENERATION
            )
            WHERE row_num > 100000
        )
    """
    execute_query(deletion_query, "delete")


def insert_ticket_record(b1_value, token_data):
    try:
        sql_query = """
            INSERT INTO TICKET_GENERATION 
                (id, module_name, token_number, emp_number, type_of_query, subject, description, priority, mobile_num,file_data) 
            VALUES 
                (:id, :module_name, :token_number, :emp_number, :type_of_query, :subject, :description, :priority, :mobile_num,:file_data)
        """
        params = {
            "id": int(datetime.now().timestamp()),
            "module_name": token_data["p_grvc_module_name"],
            "token_number": b1_value,
            "emp_number": token_data["p_grvc_emp_number"],
            "type_of_query": token_data["p_grvc_type_of_query"],
            "subject": token_data["p_grvc_subject"],
            "description": token_data["p_grvc_description"],
            "priority": token_data["p_grvc_priority"],
            "mobile_num": token_data["p_grvc_mob_number"],
            "file_data":token_data["p_grvc_file"],
        }
        result=execute_query(sql_query, "insert", params=params)
        return result
    except Exception as e:
        event_logger.error(e)
