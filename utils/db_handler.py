from utils.db_connector import execute_query
from utils.logger import logger
from datetime import datetime
import pandas as pd
import re, json,uuid
from flask import session
from werkzeug.utils import secure_filename
import os
from flask import Flask
from utils import ingest
import os
import shutil
from pathlib import Path
import zipfile


UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath("./hrbot")), "static/")

event_logger = logger()

source_folder='llm_files'

backup_folder='backup/backup_file'


if not os.path.exists(source_folder):
    os.makedirs(source_folder)
    print(f"Source folder '{source_folder}' created.")

# Check if backup folder exists, if not create it
if not os.path.exists(backup_folder):
    os.makedirs(backup_folder)
    print(f"Backup folder '{backup_folder}' created.")
    
    
def fetch_all_intents():
    query = """
        SELECT * 
        FROM nlu_data 
        WHERE status != 8 
        ORDER BY timestamp DESC
    """
    all_db_intents = execute_query(query=query, opration="select", params=None)
    return all_db_intents

def fetch_all_files():
    query = """
        SELECT * 
        FROM UPLOADED_LLM_FILES 
        ORDER BY timestamp DESC
    """
    all_db_files = execute_query(query=query, opration="select", params=None)
    return all_db_files


def fetch_intents_with_limit_offset(limit, offset):
    query = f"""
    SELECT * FROM (
        SELECT a.*, ROWNUM rnum
        FROM (
            SELECT * FROM nlu_data ORDER BY timestamp DESC
        ) a
        WHERE ROWNUM <= {offset + limit}
    )
    WHERE rnum > {offset}
    """
    return execute_query(query, "select")

def fetch_embedded_files_list(file_ids):
    query = """SELECT file_name ,file_id FROM UPLOADED_LLM_FILES WHERE file_status = 'embedded'and file_id IN ({})""".format(
        ",".join(f":id{i}" for i in range(len(file_ids)))
    )
    params = {f"id{i}": file_ids[i] for i in range(len(file_ids))}

    all_db_files = execute_query(query, opration="select",params=params)
    file_data = []
    for file in all_db_files:
        file_data.append(file["file_name"])
    return file_data
    

def count_all_intents():
    query = """
        SELECT COUNT(*) AS total FROM nlu_data
        """
    result = execute_query(query, "select", fetch_one=True)
    return result[0]["total"]


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


def upload_n_store_file(storage_folder, file):
    try:
        filename = secure_filename(file.filename)
        filepath = os.path.join(os.path.join(UPLOAD_FOLDER, storage_folder), filename)
        new_path = filepath.split("/static")[-1]
        new_path = "http://127.0.0.1:6001/static" + new_path
        file.save(filepath)
    except Exception as e:
        event_logger.error(e)
    return new_path



def background_task(paraphraser, query):
    paraphraser.generate_paraphrases(query)


def insert_single_intent(query_data):
    try:
        query_data_form = query_data.form
        query_data_files = query_data.files
        query_data_form = query_data_form.to_dict(flat=False)
        query_data_files = query_data_files.to_dict(flat=False)
        intent = query_data_form.pop("intent")[0].lower().replace(" ", "_")
        description = (
            query_data_form.pop("description")[0]
            if "description" in query_data_form
            else "testing"
        )
        title = query_data_form.pop("title")[0]
        responses_type = query_data_form.pop("responses_type")[0]
        if responses_type != "1":
            responses_text = query_data_form.pop("res_text")[0]
        response_payload = []
        response_text = []
        if responses_type == "1":
            response_type = "text"
            for res in range(30):
                try:
                    response_text.append(
                        query_data_form.pop("intentresponses_" + str(res))[0]
                    )
                except Exception as e:
                    break
            response_text = [item for item in response_text if item.strip() != ""][0]
        if responses_type == "2":
            response_type = "buttons"
            response_text = responses_text
            for res in range(30):
                try:
                    bt = []
                    intent_response_button = query_data_form.get(
                        "intentresponses_payload_button_" + str(res)
                    )[0]
                    query = """
                        SELECT title
                        FROM nlu_data
                        WHERE intent = :intent_response_button
                    """
                    intent_title = execute_query(
                        query,
                        opration="select",
                        params={"intent_response_button": intent_response_button},
                    )
                    nlu_data = ""
                    for nlu_ids in intent_title:
                        nlu_data = nlu_ids["title"]
                    bt.append(nlu_data)
                    bt.append(
                        query_data_form.pop(
                            "intentresponses_payload_button_" + str(res)
                        )[0]
                    )
                    response_payload.append(bt)
                except Exception as e:
                    event_logger.error(e)

        query = [value[0] for key, value in query_data_form.items() if key.startswith('mytext')]
        query = [item for item in query if item.strip() != ""]

        entities = get_entities(query)
        ct = datetime.now()
        ts = int(ct.timestamp()*1000)
        nlu_id = str(ts ^ (ts >> 3) ^ (ts >> 5))
        mydict = {
            "nlu_id": nlu_id,
            "intent": intent,
            "response_type": response_type,
            "response_text": json.dumps(response_text),
            "response_payload": json.dumps(response_payload),
            "title": title,
            "description": description,
            "status": "2",
            "p_status": "0",
            "s_status": "0",
            "entity": json.dumps(entities),
            "query": json.dumps(query),
            "timestamp": datetime.now().isoformat(),
            "user_id": session["user_id"],
        }
        query = """
            INSERT INTO nlu_data 
            (nlu_id, intent, response_type, response_text, response_payload, title, description, 
            status, p_status, s_status,entity, query, timestamp, user_id)
            VALUES (:nlu_id, :intent, :response_type, :response_text, :response_payload, :title, :description, 
            :status, :p_status, :s_status, :entity, :query, TO_TIMESTAMP(:timestamp, 'YYYY-MM-DD"T"HH24:MI:SS.FF6'), :user_id)
        """

        _id = execute_query(query, opration="insert", params=mydict)
        return str(_id)
    except Exception as e:
        event_logger.error(e)


def get_synonyms(word):
    """
    find the synonyms of the given word
    Args:
        word(str): input word to get synonyms
    Returns:
            synonyms(list): list of synonyms of the given word
    """
    synonyms = []
    # for syn in wordnet.synsets(word):
    #     for l in syn.lemmas():
    #         synonyms.append(l.name())
    # return list(set(synonyms))
    return synonyms


def create_multiple_query(data_up):
    new_data = []
    for x in data_up:
        tokens = x.split(" ")
        new_data.append(x)
        for i, t in enumerate(tokens):
            syno = get_synonyms(t)
            if syno:
                for s in syno:
                    rest = (
                        " ".join(tokens[0:i])
                        + " "
                        + s
                        + " "
                        + " ".join(tokens[(i + 1) : len(tokens)])
                    )
                    new_data.append(rest)

                    # my_collection.update_one({"nlu_id": "166728835731"}, {"$set": {"wordnet_queries": new_data}}, True)
    return new_data


def update_single_intent(query_data):
    try:
        query_data = query_data.to_dict(flat=False)
        intent = query_data.pop("intent")[0]
        response_payload = []
        responses_type = query_data.pop("responses_type")[0]
        if responses_type != "text":
            response_text = query_data.pop("res_text")[0]
        if responses_type == "text":
            response_text = []
            for res in range(30):
                try:
                    response_text.append(
                        query_data.pop("intentresponses_" + str(res))[0]
                    )
                except Exception as e:
                    event_logger.error(e)
            response_text = [item for item in response_text if item.strip() != ""][0]

        if responses_type == "buttons":
            x = []
            response_type = "buttons"
            response_text = response_text
            for res in range(30):
                try:
                    bt = []
                    intent_response_button = query_data.get(
                        "intentresponses_payload_button_" + str(res)
                    )[0]
                    query = """
                        SELECT title
                        FROM nlu_data
                        WHERE intent = :intent_response_button
                    """
                    intent_title = execute_query(
                        query,
                        opration="select",
                        params={"intent_response_button": intent_response_button},
                    )
                    nlu_data = ""
                    for nlu_ids in intent_title:
                        nlu_data = nlu_ids["title"]
                    bt.append(nlu_data)
                    bt.append(
                        query_data.pop("intentresponses_payload_button_" + str(res))[0]
                    )
                    x.append(bt)
                except Exception as e:
                    event_logger.error(e)
            response_payload = x

        description = query_data.pop("description")[0]
        nlu = query_data.pop("nlu_id")[0]
        query = [value[0] for key, value in query_data.items() if key.startswith('mytext')]
        query = [item for item in query if item.strip() != ""]
        updated_values = {
            "response_text": json.dumps(response_text),
            "response_payload": json.dumps(response_payload),
            "description": json.dumps(description),
            "query": json.dumps(query),
            "status": "2",
            "user_id": session.get("user_id"),
            "nlu_id": nlu,
            "timestamp": datetime.now().isoformat(),
        }

        sql_query = """ UPDATE nlu_data SET
            response_text = :response_text,response_payload = :response_payload,
            description = :description, query = :query,status = :status,user_id= :user_id ,timestamp= TO_TIMESTAMP(:timestamp, 'YYYY-MM-DD"T"HH24:MI:SS.FF6') WHERE nlu_id = :nlu_id"""

        update_response = execute_query(sql_query, "update", params=updated_values)

    except Exception as e:
        event_logger.error(e)


def insert_multiple_intent(intent_file, schedule_time):
    intent_file = intent_file.to_dict(flat=False)
    intent_file = intent_file.get("intent_file")[0]
    df = pd.read_excel(intent_file, header=[0])
    df["response_text"] = df["response_text"].str.strip()
    df["response_text"] = df["response_text"].str.replace("\n", "").str.strip()
    if "intent" in df:
        df = df.groupby(["intent"])
    else:
        return "error"
    bulk_intents = dict(list(df))
    all_intents = bulk_intents.keys()
    _multiple_intents = []
    ct = datetime.now()
    ts = int(ct.timestamp()*1000)
    nlu_time = ts ^ (ts >> 3) ^ (ts >> 5)
    error_intent = []
    error = []
    for _intent in all_intents:
        _intents = _intent.lower().replace(" ", "_")

        if (
            execute_query(
                "SELECT COUNT(*) as total FROM nlu_data WHERE intent =:intent",
                "select",
                params={"intent": _intents},
            )[0]["total"]
            > 0
        ):
            error_intent.append(_intent)
            error.append(
                "you need to adjust or remove the existing intent with this name as it already exists in our system."
            )

        execute_query(
            "DELETE FROM nlu_data WHERE intent = :intent",
            opration="delete",
            params={"intent": _intents},
        )

        _intents = _intent.lower().replace(" ", "_")
        ct = datetime.now()
        ts = int(ct.timestamp()*1000)
        nlu_time = ts ^ (ts >> 3) ^ (ts >> 5)
        nlu_id = str(nlu_time) 

        my_intent = bulk_intents.get(_intent)
        if "query" in my_intent:
            _queries = my_intent["query"].tolist()
        else:
            return "error"
        response_payload = []
        title = ""
        if "response_type" in my_intent:
            if my_intent["response_type"].unique() == "buttons":
                x = []
                response_type = "buttons"
                res_text = my_intent["response_text"].unique().tolist()
                response_text = res_text[0]
                button_pairs = (
                    my_intent[["button_title", "button_intent"]]
                    .dropna()
                    .values.tolist()
                )
                for res in range(30):
                    try:
                        button_title = my_intent["button_title"][res]
                        y = my_intent["button_intent"][res].split(",")
                        for i in y:
                            res_1 = execute_query(
                                "SELECT title FROM nlu_data WHERE intent = :1", (i,)
                            )
                            intent_title = res_1
                            bt = []
                            nlu_title = ""
                            for nlu_ids in intent_title:
                                nlu_title = nlu_ids["title"]
                            if not nlu_title:
                                nlu_title = button_title
                            bt.append(nlu_title)
                            bt.append(i)
                        x.append(bt)
                    except Exception as e:
                        event_logger.error(e)

                try:
                    title = my_intent["title"].unique().tolist()
                    title = "".join(title)
                except KeyError:
                    title = _intents

                response_payload = button_pairs
            elif my_intent["response_type"].unique() == "text":
                response_type = "text"
                try:
                    title = my_intent["title"].unique().tolist()
                    title = "".join(title)
                except KeyError:
                    title = _intents
                response_text = my_intent["response_text"].unique().tolist()[0]
        entities = get_entities("hi")

        _multiple_intents.append(
            {
                "nlu_id": nlu_id,
                "intent": _intents,
                "response_type": response_type,
                "response_text": json.dumps(response_text),
                "response_payload": json.dumps(response_payload),
                "title": title,
                "description": "testing",
                "status": "2",
                "p_status": "0",
                "s_status": "0",
                "entity": json.dumps(entities),
                "query": json.dumps(_queries),
                "timestamp": datetime.now().isoformat(),
                "user_id": session["user_id"],
            }
        )
    query = """
            INSERT INTO nlu_data 
            (nlu_id, intent, response_type, response_text, response_payload, title, description, 
            status, p_status, s_status,entity, query, timestamp, user_id)
            VALUES (:nlu_id, :intent, :response_type, :response_text, :response_payload, :title, :description, 
            :status, :p_status, :s_status, :entity, :query, TO_TIMESTAMP(:timestamp, 'YYYY-MM-DD"T"HH24:MI:SS.FF6'), :user_id)
        """
    print(execute_query(query, opration="insert", params=_multiple_intents))
    id = execute_query(query, opration="insert", params=_multiple_intents)
    if error_intent:
        session["current_intent"] = error_intent
        session["error"] = error
    # schedule training
    # training_collection.insert_one(
    #     {"training_time": schedule_time, "user": "neosoft"})
    return "pass"


def fetch_approved_model_data(
    model_name=None, model_trained_by=None, model_status=None
):
    base_query = """
    SELECT *
    FROM train_data
    WHERE deploy NOT IN ('1', '2', '3')
    """

    params = {}

    if model_name:
        base_query += " AND model_profile_name LIKE :model_name"
        params["model_name"] = f"%{model_name}%"

    if model_status:
        base_query += " AND status = :model_status"
        params["model_status"] = model_status

    if model_trained_by:
        base_query += " AND trained_by LIKE :model_trained_by"
        params["model_trained_by"] = f"%{model_trained_by}%"

    paginated_query = f"""
        SELECT * FROM (
            SELECT a.*, ROW_NUMBER() OVER (ORDER BY model_id DESC) as rnum
            FROM ({base_query}) a
        )
        WHERE rnum <= 10
    """
    all_db_intents = execute_query(paginated_query, "select", params)

    return all_db_intents


def fetch_training_model():
    query = """
            SELECT *
            FROM (
                SELECT *
                FROM train_data
                WHERE (deploy IN ('1', '2', '3') OR status = '3')
                ORDER BY model_id DESC
            )
            WHERE ROWNUM <= 10

        """
    all_db_intents = execute_query(query=query, opration="select")
    return all_db_intents


def fetch_approved_model():
    my_collection = """
        SELECT *
            FROM (
                SELECT *
                FROM train_data
                WHERE (deploy IN ('1', '2', '3'))
                ORDER BY model_id, timestamp DESC
            )
            WHERE ROWNUM <= 10
    """
    all_db_intents = execute_query(my_collection, "select")
    return all_db_intents


def fetch_pending_model():
    query = """SELECT * FROM train_data WHERE approve_status = '2' and deploy = '2' ORDER BY model_id DESC FETCH FIRST 1 ROW ONLY"""
    all_pending_model = execute_query(query, opration="select", fetch_one=True)
    return all_pending_model


def fetch_nlu_id():
    query = """SELECT nlu_id FROM nlu_data WHERE status != '7'"""
    all_db_intents = execute_query(query, opration="select")
    nlu_data = []
    for nlu_ids in all_db_intents:
        nlu_data.append((nlu_ids["nlu_id"]))
    nlu_id = []
    for x in nlu_data:
        nlu_id.append(x)
    return nlu_id

def fetch_embedded_files():
    query = """SELECT file_id FROM UPLOADED_LLM_FILES WHERE file_status = 'embedded'"""
    all_db_files = execute_query(query, opration="select")
    file_data = []
    for file in all_db_files:
        file_data.append((file["file_id"]))
    
    return file_data

def fetch_untrained_intents():
    query = """SELECT nlu_id FROM nlu_data WHERE status = '2'"""
    all_db_intents = execute_query(query, opration="select")
    nlu_data = []
    for nlu_ids in all_db_intents:
        nlu_data.append((nlu_ids["nlu_id"]))
    nlu_id = []
    for x in nlu_data:
        nlu_id.append(x)
    return nlu_id


def fetch_untrained_files(file_ids):
    query = """SELECT file_name FROM UPLOADED_LLM_FILES WHERE file_status = 'pending'and file_id IN ({})""".format(
        ",".join(f":id{i}" for i in range(len(file_ids)))
    )
    params = {f"id{i}": file_ids[i] for i in range(len(file_ids))}

    all_db_files = execute_query(query, opration="select",params=params)
    file_data = []
    for file in all_db_files:
        file_data.append(file["file_name"])
    return file_data

def fetch_all_untrained_files(file_ids):
    query = """SELECT file_name FROM UPLOADED_LLM_FILES WHERE file_status = 'pending'"""

    all_db_files = execute_query(query, opration="select")
    file_data = []
    for file in all_db_files:
        file_data.append(file["file_name"])
    return file_data


def fetch_rejected_intents():
    query = """SELECT nlu_id FROM nlu_data WHERE status = '7'"""
    all_db_intents = execute_query(query, opration="select")
    nlu_data = []
    for nlu_ids in all_db_intents:
        nlu_data.append((nlu_ids["nlu_id"]))
    nlu_id = []
    for x in nlu_data:
        nlu_id.append(x)
    return nlu_id


def admin_user(id):
    """
    Fetch User Name Using user ID
    :param id: user id(str)
    :return: User Name(str)
    """
    query = "SELECT username FROM admin_login WHERE user_id = :admin_id"
    params = {"admin_id": id}
    result = execute_query(query, opration="select", params=params, fetch_one=True)[0][
        "username"
    ]
    return result

def emp_name(id):
    """
    Fetch User Name Using user ID
    :param id: user id(str)
    :return: User Name(str)
    """
    query = "SELECT EMP_NAME FROM user_master WHERE EMP_NUMBER = :emp_no"
    params = {"emp_no": id}
    result = execute_query(query, opration="select", params=params, fetch_one=True)[0]["emp_name"]
    return result

import math


def delete_single_intent(query_data):
    query_data = query_data.to_dict(flat=False)
    nlu_id = query_data.pop("id")[0]
    all_records = execute_query(
        "SELECT * FROM nlu_data", opration="select", fetch_one=False
    )
    intent_data = execute_query(
        f"SELECT * FROM nlu_data WHERE nlu_id = {nlu_id}",
        opration="select",
        fetch_one=True,
    )
    intent_name = intent_data[0].get("intent") if intent_data else None
    all_responses = []
    for rec in all_records:
        response_type = rec.get("response_type")
        response = rec.get("response_text")
        response_payload = rec.get("response_payload")
        all_responses.append([response_type, response, response_payload])
    for response in all_responses:
        if not response:
            continue
        if any(isinstance(elem, float) and math.isnan(elem) for elem in response):
            continue
        intent_list = response[-1]
        if isinstance(intent_list, list):
            intent_present = any(str(intent_name) in intent for intent in intent_list)
            if intent_present:
                return f"{intent_name} is not deleted"
        else:

            if intent_name in response:
                return f"{intent_name} is not deleted"

    result = execute_query(
        "DELETE FROM nlu_data WHERE nlu_id = :id",
        opration="delete",
        params={"id": nlu_id},
    )
    try:
        sql_query = (
            "UPDATE maintain_status SET status = :status,id = :id WHERE name = :name"
        )
        update_response = execute_query(
            sql_query,
            "update",
            params={"status": "1", "id": "3", "name": "intent_status"},
        )

    except:
        sql_query = (
            "INSERT INTO maintain_status (name,id,status) VALUES(:name,:id,:status)"
        )
        update_response = execute_query(
            sql_query,
            "insert",
            params={"status": "1", "id": "2", "name": "intent_status"},
        )
    return "file is deleted"

def delete_single_file(query_data):
    query_data = query_data.to_dict(flat=False)
    id = query_data.pop("id")[0]
    category=query_data.pop("category")[0]
    try:
        # Step 1: Fetch file details from the database
        result = execute_query("SELECT file_name FROM UPLOADED_LLM_FILES WHERE file_id=:file_id", 
                                'select', params={'file_id': id})
        file_name = result[0]['file_name']
        if not result:
            return  "File not found"
        if category == 'embedded':
            collection_name=os.path.splitext(file_name)[0]
            ingest.qdrant_client.delete_collection(
                collection_name=collection_name)
            execute_query("""UPDATE UPLOADED_LLM_FILES  SET FILE_STATUS='pending' where file_id=:file_id """,'update',params={'file_id': id})
            delete_from_cache_question(collection_name)
        else:
            backup_and_merge_files(file_name, source_folder, backup_folder)

            execute_query("DELETE FROM UPLOADED_LLM_FILES WHERE file_id=:file_id", 
                        'delete', params={'file_id': id})
        return {"message":"File deleted successfully","files":file_name}

    except Exception as e:
        print(e,88888888888888888888888888888888888888)
        return str(e)
    
    
def delete_from_cache_question(collection_name):
    query = """
        SELECT query,id
        FROM CONVERSATION
        WHERE JSON_VALUE(METADATA, '$.collection_name') = :collection_name
        """
    result=execute_query(query,'select',params={"collection_name":collection_name})
    if result:
        for x in result:
            delete_chat(x.get('id'))
            try:
                ingest.remove_cache_question(x.get("query"))
            except:
                pass
    return None

def delete_all_intent():
    result = execute_query("DELETE FROM nlu_data ", opration="delete", params={})
    # if result.deleted_count > 0:
    #     print("Deleted", result.deleted_count, "documents from nlu_data collection")
    # else:
    #     print("No documents found in nlu_data collection")

    try:
        sql_query = "UPDATE maintain_status SET status = :status WHERE name = :name"
        update_response = execute_query(
            sql_query, "update", params={"status": "1", "name": "intent_status"}
        )

    except Exception as e:
        sql_query = "INSERT INTO maintain_status (name,status) VALUES(:name,:status)"
        update_response = execute_query(
            sql_query, "update", params={"status": "1", "name": "intent_status"}
        )

    return update_response

def backup_and_merge_files(file_name, source_folder, backup_folder):
    file_path = os.path.join(source_folder, file_name)
    destination_path = os.path.join(backup_folder, file_name)

    if os.path.exists(file_path):
        if os.path.exists(destination_path):
            with open(destination_path, 'r') as dest_file:
                existing_content = dest_file.read()

            with open(file_path, 'r') as src_file:
                new_content = src_file.read()

            merged_content = existing_content + "\n" + new_content

            with open(destination_path, 'w') as dest_file:
                dest_file.write(merged_content)
        else:
            shutil.move(file_path, destination_path)
        
    else:
        print(f"File '{file_name}' does not exist in '{source_folder}'.")
        
        
        
def delete_all_files(selected_files):
    llm_files_dir = "llm_files"

    if selected_files:
        untrained_files = fetch_untrained_files(selected_files)
    for file_name in untrained_files:
        file_path = os.path.join(llm_files_dir, file_name)
        if os.path.isfile(file_path) and file_name in untrained_files:        
            file_path = os.path.join(llm_files_dir, file_name)
            destination_path = os.path.join(backup_folder)
            backup_and_merge_files(file_name, source_folder, destination_path)
        execute_query("DELETE FROM UPLOADED_LLM_FILES WHERE file_name=:file_name",'delete', params={'file_name': file_name})
    # move_files_to_zip_folder()
    # result = execute_query("DELETE FROM uploaded_llm_files where file_status='pending' ", opration="delete", params={})
    # try:
    #     sql_query = "UPDATE maintain_status SET status = :status WHERE name = :name"
    #     update_response = execute_query(
    #         sql_query, "update", params={"status": "1", "name": "intent_status"}
    #     )

    
    return {"message":"all files deleted sucessfully"}

def delete_chat(id):
    query = """
        SELECT QUERY
        FROM conversation
        WHERE ID = :conversation_id
    """
    params = {"conversation_id":id}
    result = execute_query(query, "select", params=params)
    if result:
        ingest.remove_cache_question(result[0]['query'])
    result = execute_query("DELETE FROM conversation WHERE ID= :id", opration="delete", params={"id":id})
    return result

def delete_single_user_feedback(id,ticket_id):

    fetch_query = "SELECT metadata FROM conversation WHERE ID = :id"
    metadata_result = execute_query(fetch_query, "select", params={"id": id})

    if metadata_result and metadata_result[0].get("metadata"):
        metadata = metadata_result[0]["metadata"]  # Convert JSON string to Python dict
        metadata.pop("ticket_id", None)
    update_query = """
        UPDATE conversation 
        SET USER_ACTION = '', 
            metadata = :metadata 
        WHERE ID = :id
    """
    params = {"metadata": json.dumps(metadata), "id": id}
    execute_query(update_query, "update", params=params)
    result = execute_query("DELETE FROM GP_USER_QUERY WHERE REQUESTID= :ticket_id", opration="delete", params={"ticket_id":ticket_id})

    return result


def delete_user_feedback():
   # Step 1: Fetch all conversation records where user_action is 'like' or 'unlike'
    fetch_query = """
        SELECT ID, metadata FROM conversation 
        WHERE USER_ACTION IN ('like', 'dislike')
    """
    feedback_records = execute_query(fetch_query, "select")

    # Extract ticket_ids if they exist in metadata
    ticket_ids = []
    conversation_ids = []

    for record in feedback_records:
        conversation_ids.append(record["id"])
        metadata = record["metadata"] if record["metadata"] else {}
        ticket_id = metadata.pop("ticket_id", None)
        if ticket_id:
            ticket_ids.append(ticket_id)
        
        # Update metadata (remove ticket_id)
        update_query = """
            UPDATE conversation 
            SET metadata = :metadata, USER_ACTION = '' 
            WHERE ID = :id
        """
        execute_query(update_query, "update", params={"metadata": json.dumps(metadata), "id": record["id"]})

    # Step 2: Delete from GP_USER_QUERY where ticket_id exists
    if ticket_ids:
        delete_tickets_query = "DELETE FROM GP_USER_QUERY WHERE REQUESTID IN :ticket_ids"
        execute_query(delete_tickets_query, "delete", params={"ticket_ids": tuple(ticket_ids)})

   
    return {"message": "Bulk feedback deleted successfully", "deleted_feedback": len(conversation_ids), "deleted_tickets": len(ticket_ids)}
def delete_all_chats():
    result = execute_query("TRUNCATE TABLE conversation", opration="delete", params={})
    ingest.qdrant_client.delete_collection(collection_name='cache_question')
    return result



from werkzeug.datastructures import ImmutableMultiDict
import os
from datetime import date, timedelta
def format_file_size(size_in_bytes):
    if size_in_bytes < 1024:
        return f"{size_in_bytes} B"
    elif size_in_bytes < 1024**2:
        return f"{size_in_bytes / 1024:.2f} KB"
    elif size_in_bytes < 1024**3:
        return f"{size_in_bytes / 1024**2:.2f} MB"
    else:
        return f"{size_in_bytes / 1024**3:.2f} GB"
if not os.path.isdir(source_folder):
    os.mkdir(source_folder)
EXPECTED_HEADERS = {"title", "query", "response"}
def insert_llm_files(intent_file, schedule_time):
    failed_files = []  
    uploaded_files = []  
    for uploaded_file in intent_file.getlist('llm_file'): 
        file_name = uploaded_file.filename
        file_extension = file_name.split(".")[-1].lower()
        
        try:
            if file_extension in {"csv", "xlsx"}:
                uploaded_file.seek(0)  # Reset pointer before reading
                if file_extension == "csv":
                    df = pd.read_csv(uploaded_file, nrows=1)  # Read only the header
                else:
                    df = pd.read_excel(uploaded_file, nrows=1)
                file_headers = set(df.columns.str.strip()) 
                print(file_headers,99999999999999999999999999999999999)
                # Get the actual column names
                if not EXPECTED_HEADERS.issubset(file_headers):  # Check if required headers exist
                    failed_files.append(file_name)
                    event_logger.error(f"File '{file_name}' is missing required headers {EXPECTED_HEADERS}. Please ensure the first row contains 'title, query, response'.")
                    continue  # Skip this file
                uploaded_file.seek(0)  # Reset file pointer after reading size


        except Exception as e:
            failed_files.append(file_name)
            event_logger.error(f"Error reading file '{file_name}': {str(e)}. Please upload a valid structured file.")
            continue  # Skip this file

        file_path = os.path.join(source_folder, file_name)
        file_size = format_file_size(len(uploaded_file.read()))  # Get file size in bytes
        uploaded_file.seek(0)  # Reset file pointer after reading size
        created_by = session.get("user_id")  # Replace with actual user info
        file_status = "pending"  # Status set to pending
        upload_date = datetime.now()
        file_id = str(uuid.uuid4())

        try:
            # Check if file with the same name already exists
            check_sql = """SELECT file_id FROM uploaded_llm_files WHERE file_name = :file_name"""
            existing_file = execute_query(check_sql, 'select', params={'file_name': file_name})
            if existing_file:  # Update details if the file exists
                print(f"File '{file_name}' already exists. Updating details...")
                update_sql = """
                    UPDATE uploaded_llm_files 
                    SET file_format = :file_format, 
                        file_size = :file_size, 
                        upload_date = :upload_date,
                        created_by = :created_by,
                        file_status = :file_status, 
                        file_path = :file_path
                    WHERE file_id = :file_id
                """
                params = {
                    "file_id": existing_file[0]['file_id'],
                    "file_format": file_extension,
                    "file_size": file_size,
                    "upload_date": upload_date,
                    "created_by": created_by,
                    "file_status": file_status,
                    "file_path": file_path,
                }
                execute_query(update_sql, 'update', params=params)
            else:  # Insert a new record
                print(f"Inserting new file '{file_name}' into database...")
                insert_sql = """
                    INSERT INTO uploaded_llm_files 
                    (file_id, file_name, file_format, file_size, upload_date, created_by, file_status, file_path) 
                    VALUES (:file_id, :file_name, :file_format, :file_size, :upload_date, :created_by, :file_status, :file_path)
                """
                params = {
                    "file_id": file_id,
                    "file_name": file_name,
                    "file_format": file_extension,
                    "file_size": file_size,
                    "upload_date": upload_date,
                    "created_by": created_by,
                    "file_status": file_status,
                    "file_path": file_path,
                }
                execute_query(insert_sql, 'insert', params=params)

            # Write the file to the filesystem
            with open(file_path, "wb") as output_file:
                output_file.write(uploaded_file.read())

            uploaded_files.append(file_name)  # Add to successful uploads
            event_logger.info(f"File '{file_name}' uploaded successfully with status '{file_status}'!")
        except Exception as e:
            print(e,777777777777777777777777777777777777777777)
            event_logger.error(f"Error uploading file '{file_name}': {str(e)}")
            failed_files.append(file_name)  # Add to failed uploads

    # Return the response
    if failed_files:
        return {
        "status": "failed",
        "failed_files": failed_files,
        "message": "Some files are missing required headers. Ensure the first row contains 'title, query, response' or convert them to .txt."
         }
    else:
        return {"status": "success", "uploaded_files": uploaded_files}
def process_file_for_qdrant(file_name):
    try:
        file_path = os.path.join(source_folder, file_name)
        if not os.path.exists(file_path):
            print(f"File '{file_name}' does not exist in the system.")
            return

        # Determine file extension
        file_extension = file_name.split(".")[-1].lower()

        # Process the file for indexing
        print(f"Processing file '{file_name}' for Qdrant...")
        text_chunks = []
        if file_extension == "pdf":
            raw_text = ingest.extract_text_from_pdf([file_path])
            text_chunks = ingest.chunk_text(raw_text)
        elif file_extension == "csv":
            text_chunks = ingest.extract_text_from_csv(file_path)
        elif file_extension == "xlsx":
            text_chunks = ingest.extract_data_from_excel(file_path)
        else:
            print(f"Unsupported file type: {file_extension}")
            return

        # Index the content in Qdrant
        ingest.indexing(text_chunks, file_name)

        # Update the file status to 'active'
        update_sql = """
            UPDATE uploaded_llm_files 
            SET file_status = :file_status 
            WHERE file_name = :file_name
        """
        execute_query(update_sql, 'update', params={"file_status": "active", "file_name": file_name})

        print(f"File '{file_name}' successfully processed and added to Qdrant!")
    except Exception as e:
        print(f"Error processing file '{file_name}' for Qdrant: {str(e)}")
    # for uploaded_file in intent_file.getlist('llm_file'):  # Use .getlist to handle multiple files
    #     file_name = uploaded_file.filename
    #     file_extension = file_name.split(".")[-1].lower()
    #     file_path = os.path.join("llm_files", file_name)
    #     file_size = len(uploaded_file.read())  # Get file size in bytes
    #     uploaded_file.seek(0)  # Reset file pointer after reading size
    #     created_by = "author"  # Replace with actual user info
    #     file_status = "active"
    #     comments = None
    #     upload_date = datetime.now()
    #     file_id = str(uuid.uuid4())

    #     try:
    #         # Check if file with the same name already exists
    #         check_sql = """SELECT file_id FROM uploaded_llm_files WHERE file_name = :file_name"""
    #         existing_file = execute_query(check_sql, 'select', params={'file_name': file_name})
    #         print(existing_file)
    #         if existing_file:  # If a file with the same name exists, update its details
    #             print(f"File '{file_name}' already exists. Updating details...")
    #             update_sql = """
    #                 UPDATE uploaded_llm_files 
    #                 SET file_format = :file_format, 
    #                     file_size = :file_size, 
    #                     upload_date = :upload_date,
    #                     created_by = :created_by,
    #                     file_status = :file_status, 
    #                     file_path = :file_path,
    #                     comments = :comments
    #                 WHERE file_id = :file_id
    #             """
    #             params = {
    #                 "file_id": existing_file[0]['file_id'],
    #                 "file_format": file_extension,
    #                 "file_size": file_size,
    #                 "upload_date": upload_date,
    #                 "created_by": created_by,
    #                 "file_status": file_status,
    #                 "file_path": file_path,
    #                 "comments": comments,
    #             }
    #             execute_query(update_sql, 'update', params=params)
    #         else:  # Insert a new file record if it doesn't exist
    #             print(f"Inserting new file '{file_name}' into database...")
    #             insert_sql = """
    #                 INSERT INTO uploaded_llm_files 
    #                 (file_id, file_name, file_format, file_size, upload_date, created_by, file_status, file_path, comments) 
    #                 VALUES (:file_id, :file_name, :file_format, :file_size, :upload_date, :created_by, :file_status, :file_path, :comments)
    #             """
    #             params = {
    #                 "file_id": file_id,
    #                 "file_name": file_name,
    #                 "file_format": file_extension,
    #                 "file_size": file_size,
    #                 "upload_date": upload_date,
    #                 "created_by": created_by,
    #                 "file_status": file_status,
    #                 "file_path": file_path,
    #                 "comments": comments,
    #             }
    #             execute_query(insert_sql, 'insert', params=params)

    #         # Write the uploaded file to the filesystem
    #         existing_content = ""
    #         if os.path.exists(file_path):
    #             with open(file_path, "r", encoding="utf-8") as existing_file:
    #                 existing_content = existing_file.read()

    #         with open(file_path, "wb") as output_file:
    #             output_file.write(uploaded_file.read())

    #         if existing_content:
    #             print(f"Merging content for '{file_name}'")
    #             with open(file_path, "a", encoding="utf-8") as output_file:  
    #                 output_file.write("\n" + existing_content)

    #         # Process the file for indexing
    #         print(f"Processing file '{file_name}'")
    #         text_chunks = []
    #         if file_extension == "pdf":
    #             raw_text = extract_text_from_pdf([file_path]) 
    #             text_chunks = chunk_text(raw_text)
    #         elif file_extension == "csv":
    #             text_chunks = extract_text_from_csv(file_path)  
    #         elif file_extension == "xlsx":
    #             text_chunks = extract_data_from_excel(file_path) 
    #         else:
    #             print(f"Unsupported file type: {file_extension}")
    #             continue 

    #         indexing(text_chunks, file_name)
    #         print(f"File '{file_name}' processed successfully!")

    #     except Exception as e:
    #         print(f"Error processing file '{file_name}': {str(e)}")
            
def fetch_questions_and_answers_from_oracle(conversation_id,action):
    query = """
        SELECT ID, QUERY, RESPONSE_TEXT
        FROM conversation
        WHERE ADMIN_ACTION = :action and ID = :conversation_id
    """
    params = {"action": action,"conversation_id":conversation_id}
    result = execute_query(query, "select", params=params)
    if action == "like":
        ingest.cache_qestions(result)
    elif action == "dislike":
        ingest.remove_cache_question(result[0]['query'])
    return result  # List of dictionaries with 'question' and 'answer' keys



def get_daily_query_counts():
    """
    Dummy function to simulate fetching daily query counts.
    In production, you might run a query like:
    """
    query="""SELECT TO_CHAR(TIMESTAMP, 'YYYY-MM-DD') AS day, COUNT(*) AS count
    FROM CONVERSATION
    GROUP BY TO_CHAR(TIMESTAMP, 'YYYY-MM-DD')
    ORDER BY day
    """
    data = execute_query(query,'select')
    return data

def get_collection_query_counts():
    """
    Dummy function to simulate fetching query counts by collection.
    In production, if METADATA stores JSON data, you might use:
    """ 
    
    query="""SELECT JSON_VALUE(METADATA, '$.collection_name') AS collection, COUNT(*) AS count
    FROM CONVERSATION
    GROUP BY JSON_VALUE(METADATA, '$.collection_name')
    """
    data = execute_query(query,'select')
    print(data)
    return data