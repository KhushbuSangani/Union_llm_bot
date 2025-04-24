from flask import (
    render_template,
    request,
    session,
    redirect,
    Blueprint,
    jsonify,
    Response,
    url_for,
)
from utils.create_dataset import get_training_set
from utils import logger, rasa_wrapper as rasa_wrapper,ingest
from utils.db_connector import execute_query
from datetime import datetime, timedelta
from utils import db_handler
from controller.sso_login import get_latest_token
import pandas as pd
import threading
import shutil
import os,json
from utils import config

training_details = Blueprint("training", __name__)
event_logger = logger.logger()

import asyncio

@training_details.route("/training_status")
def training_status(): 
    try:
        if session.get("islogin") != 1:
            return redirect(url_for("auth.login", _external=True, _scheme=config.SSL_SECURITY))
    except Exception as e:
        event_logger.error(e)
        return render_template("admin/400.html")
    if session.get("token")!=get_latest_token(session.get("user_id")):
        return redirect(url_for("auth.login", _external=True, _scheme= config.SSL_SECURITY))

    session["status"] = "training"
   
    try: 
        model_name = request.args.get('search_model', '')
        model_trained_by=request.args.get('search_trained_by', '')
        model_status = request.args.get('search_status', '')  
        all_intents = db_handler.fetch_training_model()
        _all_intents = []

        for idx, x in enumerate(all_intents):
            _all_intents.append(
                [
                    idx + 1,
                    x.get("model_profile_name"),
                    x.get("status"),
                    pd.to_datetime(x.get("timestamp")),
                    x.get("trained_by"),
                    x.get("model_name"),
                    x.get("deploy"),
                    x.get("model_id"),
                    active_count_test(x.get("model_id"), "1", "stage"),
                    active_count_test(x.get("model_id"), "0", "stage"),
                    active_count_test(x.get("model_id"), "1", "prod"),
                    active_count_test(x.get("model_id"), "0", "prod"),
                    x.get("model_id"),
                    x.get("approve_status"),
                ]
            )

        all_intents_approved = db_handler.fetch_approved_model_data(model_name=model_name,model_trained_by=model_trained_by,model_status=model_status)
        _all_intents_approved = []
        for idx, y in enumerate(all_intents_approved):
            _all_intents_approved.append(
                [
                    idx + 1,
                    y.get("model_profile_name"),
                    y.get("status"),
                    pd.to_datetime(y.get("timestamp")),
                    y.get("trained_by"),
                    y.get("model_name"),
                    y.get("deploy"),
                    y.get("model_id"),
                    active_count_test(y.get("model_id"), "1", "stage"),
                    active_count_test(y.get("model_id"), "0", "stage"),
                    active_count_test(y.get("model_id"), "1", "prod"),
                    active_count_test(y.get("model_id"), "0", "prod"),
                    y.get("model_id"),
                    y.get("approve_status"),
                ]
            )
        stag_model_count = execute_query("SELECT COUNT(*) as count FROM train_data WHERE deploy = '2'",'select')[0]['count']
        both_model_count = execute_query("SELECT COUNT(*) as count FROM train_data WHERE deploy = '3'",'select')[0]['count']
        total = stag_model_count + both_model_count
        if  request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            rows_html = render_template('admin/raw_model.html', data=_all_intents,stag_model_count=total,approve_data=_all_intents_approved)
                # If the request is AJAX, return JSON with the necessary fragments
            return jsonify({
                "rows_html": rows_html,
            })
        else:
            return render_template(
                "admin/training.html",
                data=_all_intents,
                stag_model_count=total,
                approve_data=_all_intents_approved,
            )
        
    except Exception as e:
        event_logger.error(e)
        return render_template("admin/500.html")


@training_details.route("/pending_list")
def pending_list():
    try:
        if session.get("islogin") != 1:
            return redirect(url_for("auth.login", _external=True, _scheme=config.SSL_SECURITY))
    except Exception as e:
        event_logger.error(e)
        return render_template("admin/400.html")
    try:
        if 4 not in session.get("access"):
            return redirect(url_for("auth.login", _external=True, _scheme=config.SSL_SECURITY))
    except Exception as e:
        return render_template("admin/401.html")
    try:
        session["status"] = "pending"
        all_intents = db_handler.fetch_pending_model()
        _all_intents = []
        for idx, x in enumerate(all_intents):
            _all_intents.append(
                [
                    idx + 1,
                    x.get("model_profile_name"),
                    x.get("status"),
                    pd.to_datetime(x.get("timestamp")),
                    x.get("trained_by"),
                    x.get("model_name"),
                    x.get("deploy"),
                    x.get("_id"),
                    active_count_test(x.get("model_id"), "1", "stage"),
                    active_count_test(x.get("model_id"), "0", "stage"),
                    active_count_test(x.get("model_id"), "1", "prod"),
                    active_count_test(x.get("model_id"), "0", "prod"),
                    x.get("model_id"),
                    x.get("approve_status"),
                ]
            )
        return render_template("admin/pending_training.html", data=_all_intents)
    except Exception as e:
        event_logger.error(e)
        return render_template("admin/500.html")

import asyncio

@training_details.route("/model/train", methods=["POST"])
def train_model():
    """
    -- Check User Session
    -- Generate Model Id
    -- If Training Start Now
        -- Before Thread Start
            -- Update All intents those status is Untrained/Failed(2,3) to InProgress
            -- Create Document New Model Name without File
            -- Fetch Intent list and pass to view
        -- After Thread will Start
            -- Fetch all intents data from db
            -- Pass data to rasa for training
                -- if get status is success
                    -- move model file to anther folder(for run multiple rasa)
                    -- Update all Intent Status to Trained(1)
                    -- Update Model documents with New Generated model file and all Intent list
                -- else get status is failure
                    -- Changes the status of Untrained/Failed(2,3) Intents to TrainingFailed(4)
                    -- Delete Already created Document form database
    -- Else Training Scheduled
        -- Create New Model without File
        -- Add data in schedular collection with date
        -- Fetch Intent list and pass to view
    :return: Training View
    """
    try:
        if session.get("islogin") != 1:
            return redirect(url_for("auth.login", external=True, scheme=config.SSL_SECURITY))
    except Exception as e:
        event_logger.error(e)
        return render_template("admin/400.html")

    projectpath = request.form
    query_data = projectpath.to_dict(flat=False)
   
    user_model_name = query_data.pop("model_name")[0]
    r_status = query_data.pop("r_status")[0]
    s_date = query_data.pop("s_date")[0]
   
    
    result = {}
    result["status"] = "0"
    status_collection = "SELECT COUNT(*) as status_count FROM maintain_status WHERE name = 'stag_training_status' AND status = '1'"
    evn_status =execute_query(status_collection,opration='select',fetch_one=True)[0]['status_count']
   
    try:
       
        model_profile = user_model_name
        ct = datetime.now()
        ts = ct.timestamp()
        model_id = str(int(ts))
        untrained_intents = db_handler.fetch_untrained_intents()
        rejected_intents = db_handler.fetch_rejected_intents()
        if r_status == "1":
            mydict_in = {
                "model_name": "",
                "model_profile_name": model_profile,
                "timestamp":datetime.now().isoformat(),
                "model_id": model_id,
                "status": "3",
                "deploy": "5",
                "prod_active_count": "",
                "prod_inactive_count": "",
                "active_count": "",
                "inactive_count": "",
                "intent_list": json.dumps([]),
                "newly_train_intents": json.dumps([]),
                "approve_status": "0",
                "trained_by":"",
            }
            query="""INSERT INTO train_data (model_name,model_profile_name, timestamp, model_id, status, deploy, prod_active_count,prod_inactive_count,active_count,inactive_count,intent_list,newly_train_intents,approve_status,trained_by)
                VALUES ( :model_name, :model_profile_name, TO_TIMESTAMP(:timestamp, 'YYYY-MM-DD"T"HH24:MI:SS.FF6'), :model_id, :status, :deploy, :prod_active_count, :prod_inactive_count, :active_count, :inactive_count, :intent_list ,:newly_train_intents,:approve_status,:trained_by)
            """
            
            execute_query(query,opration='insert',params=mydict_in)
           
            def long_running_task(**kwargs):
                user_id=kwargs.get("user_id")
                user_name=execute_query("SELECT username from admin_login where user_id=:user_id",'select',params={'user_id':user_id})[0]['username']
               
                event_logger.error(
                    "===================================================="
                )
                training_data = get_training_set()
                try:
                    execute_query("UPDATE maintain_status SET status = '1' WHERE name = 'stag_training_status'",opration="update")
                except:
                    status_collection=execute_query("INSERT INTO maintain_status (id,name, status) VALUES ('1','stag_training_status', '1')",opration="insert")

                
                with rasa_wrapper.RasaAPIWarapper() as rasaApi:
                    status, model_name = rasaApi.train(data=training_data)
                    event_logger.error(status)
                    if status == True:
                        flag = "1"
                        src = os.getcwd() + "/bot/models/" + model_name
                        dst = os.getcwd() + "/bot/prod_models/" + model_name
                        shutil.copyfile(src, dst)
                        shutil.copy(src, dst)
                        nlu_ids = db_handler.fetch_nlu_id()

                        prod_active_count =execute_query("SELECT COUNT(*) as p_status FROM nlu_data WHERE p_status = '1'",opration='select')[0]['p_status']
                        prod_inactive_count = execute_query("SELECT COUNT(*) as p_status FROM nlu_data WHERE p_status = '0'",opration='select')[0]['p_status']
                        active_count = execute_query("SELECT COUNT(*) as s_status FROM nlu_data WHERE s_status = '1'",opration='select')[0]['s_status']
                        inactive_count = execute_query("SELECT COUNT(*) as s_status FROM nlu_data WHERE s_status = '0'",opration='select')[0]['s_status']
                        mydict = {
                                "model_name": str(model_name),
                                "model_profile_name": model_profile,
                                "intent_list": json.dumps(nlu_ids),
                                "newly_train_intents": json.dumps(untrained_intents),
                                "status": flag,
                                "timestamp":datetime.now().isoformat(),
                                "deploy": "0",
                                "prod_active_count": prod_active_count,
                                "prod_inactive_count": prod_inactive_count,
                                "active_count": active_count,
                                "inactive_count": inactive_count,
                                "approve_status": "0",
                                "model_id": model_id,
                                "trained_by":user_name,
                        }
                        update_query = """UPDATE train_data SET model_name = :model_name, model_profile_name = :model_profile_name, intent_list = :intent_list, newly_train_intents = :newly_train_intents, status = :status,timestamp=TO_TIMESTAMP(:timestamp, 'YYYY-MM-DD"T"HH24:MI:SS.FF6'), deploy = :deploy, prod_active_count = :prod_active_count, prod_inactive_count = :prod_inactive_count, active_count = :active_count, inactive_count = :inactive_count, approve_status = :approve_status,trained_by=:trained_by WHERE model_id = :model_id """
                        _id=execute_query(update_query,opration='update',params=mydict)
                        list=','.join(["'" + str(nlu_id) + "'" for nlu_id in nlu_ids])
                        query = """UPDATE nlu_data SET status = :flag WHERE nlu_id IN ({})""".format(list)
                        bind_values = {'flag': flag}  
                        _id=execute_query(query,opration='update',params=bind_values)
                        deploy_log = {
                            "model_name": model_name,
                            "model_id": model_id,
                            "timestamp":datetime.now().isoformat(),
                            "status": "1",
                            "user_name": user_name,
                        }
                        _id = execute_query(
                            """INSERT INTO training_log (model_name, model_id, timestamp, status, user_name)
                            VALUES (:model_name, :model_id, TO_TIMESTAMP(:timestamp, 'YYYY-MM-DD"T"HH24:MI:SS.FF6'), :status, :user_name)""",'insert',params=deploy_log)
                        s_id = deploy_stag(model_id)
                    else:
                        query="""SELECT nlu_id
                            FROM nlu_data
                            WHERE status IN ('2', '3', '5')"""
                        active_count = execute_query(query,opration='select')
                        all_intents = []
                        for x in active_count:
                            all_intents.append(x["nlu_id"])
                        untrained_intent_list = all_intents
                        flag = "2"
                        query = """UPDATE nlu_data
                            SET s_status = "2"
                            WHERE nlu_id IN ({0})
                        """.format(','.join("'{0}'".format(id) for id in untrained_intent_list))

                        up_intent_collection= execute_query(query,opration='update')
                        model_id_data = {"model_id": model_id}
                        execute_query("DELETE FROM train_data WHERE model_id = :model_id",opration='delete',params=model_id_data)
                        deploy_log = {
                            "model_name": model_name,
                            "model_id": model_id,
                            "timestamp":datetime.now().isoformat(),
                            "status": "2",
                            "user_name": user_name,
                        }
                        _id = execute_query(
                            """INSERT INTO training_log (model_name, model_id, timestamp, status, user_name)
                            VALUES (:model_name, :model_id, TO_TIMESTAMP(:timestamp, 'YYYY-MM-DD"T"HH24:MI:SS.FF6'), :status, :user_name)""",opration='insert',params=deploy_log)
                    execute_query("UPDATE maintain_status SET status = '0' WHERE name = 'stag_training_status'",opration='update')
                    execute_query("UPDATE maintain_status SET status = '0' WHERE name = 'intent_status'",opration='update')

            thread = threading.Thread(
                target=long_running_task, kwargs={"post_data": projectpath,"user_id":session.get('user_id')}
            )
            thread.start()
            
          
            myquery_old = """UPDATE nlu_data
                    SET status = '3'
                    WHERE status = '2'"""
            execute_query(myquery_old,opration='update')
            
            all_intents = db_handler.fetch_all_intents()
            _all_intents = []

            for idx, x in enumerate(all_intents):
                _all_intents.append(
                    [
                        idx + 1,
                        x.get("intent"),
                        x.get("response"),
                        x.get("query"),
                        x.get("entities"),
                        x.get("timestamp"),
                        x.get("user"),
                        x.get("status"),
                        x.get("nlu_id"),
                    ]
                )
            return render_template("admin/intent_table.html", data=_all_intents)
        else:
            mydict = {
                "model_name": "",
                "model_profile_name": model_profile,
                "timestamp":datetime.now().isoformat(),
                "model_id": model_id,
                "status": "3",
                "deploy": "0",
                "prod_active_count": "",
                "prod_inactive_count": "",
                "active_count": "",
                "inactive_count": "",
                "intent_list": [],
                "newly_train_intents": [],
                "approve_status": "0",
            }
            query="""INSERT INTO my_collection (model_profile_name, timestamp, model_id, status, deploy, approve_status)
                VALUES (:model_profile_name, TO_TIMESTAMP(:timestamp, 'YYYY-MM-DD"T"HH24:MI:SS'), :model_id, :status, :deploy, :approve_status)
            """
            _id = execute_query(query,opration='insert',params=mydict)
            schedule_training = {
                "model_name": "",
                "model_profile_name": model_profile,
                "timestamp":datetime.now().isoformat(),
                "schedule_time": s_date,
                "model_id": model_id,
                "status": "1",
            }
            query = "INSERT INTO training_schedule(model_name, model_profile_name, timestamp, schedule_time, model_id, status) VALUES ( :model_name, :model_profile_name, TO_TIMESTAMP(:timestamp, 'YYYY-MM-DD\"T\"HH24:MI:SS.FF6'), TO_TIMESTAMP(:schedule_time, 'YYYY-MM-DD\"T\"HH24:MI:SS.FF6'), :model_id, :status)"

            _id = execute_query(query, opration='insert',params=schedule_training)
            query = "UPDATE nlu_data SET status = :new_status"
            params = {"new_status": "4"}
            
            _id = execute_query(query,opration='update', params=params)
            all_intents = db_handler.fetch_all_intents()
            _all_intents = []
            for idx, x in enumerate(all_intents):
                _all_intents.append(
                    [
                        idx + 1,
                        x.get("intent"),
                        x.get("response"),
                        x.get("query"),
                        x.get("entities"),
                        x.get("timestamp"),
                        x.get("user"),
                        x.get("status"),
                        x.get("_id"),
                    ]
                )
            return render_template("admin/intent_table.html", data=_all_intents)
    except Exception as e:
        event_logger.error(e)
        return redirect(
            url_for("intent.display_intents", external=True, scheme=config.SSL_SECURITY)
        )




def deploy_stag(_model_id):
    try:
        
        id_ = _model_id
        all_db_intents = execute_query("SELECT * FROM train_data WHERE model_id = :id",opration='select',params={'id':id_})
        all_intents = []
        for x in all_db_intents:
            all_intents.append(x["model_name"])
            all_intents.append(x["deploy"])
            all_intents.append(x["intent_list"])
        model_name = all_intents[0]
        deploy = all_intents[1]
        intent_list = all_intents[2]
        with rasa_wrapper.RasaAPIWarapper() as rasaApi:
            status = rasaApi.replace_model(model_file=model_name)
            if status == True:
                if deploy == "1":
                    status = "3"
                else:
                    status = "2"
                my_collection_old = """UPDATE train_data SET deploy = '1' WHERE deploy = '3'"""
                _id = execute_query(my_collection_old,opration='update')

                update_nlu_data = {
                        "new_s_status": "0"  
                }
                _id =execute_query("UPDATE nlu_data SET s_status = :new_s_status",opration='update',params=update_nlu_data)
                update_query = """
                    UPDATE nlu_data
                    SET s_status = '1'
                    WHERE nlu_id IN ({})
                """.format(','.join("'{0}'".format(id) for id in intent_list))
                nlu_collection=execute_query(update_query,'update')

                
                update_nlu_count="""UPDATE train_data
                    SET active_count = (SELECT COUNT(*) FROM nlu_data WHERE s_status = '1'),
                    inactive_count = (SELECT COUNT(*) FROM nlu_data WHERE s_status = '0') where model_id= :model_id"""
                nlu_obj = {"model_id": id_}
                _id = execute_query(update_nlu_count,opration='update',params=nlu_obj)

                update_old_data ="""UPDATE train_data SET deploy = '0' WHERE deploy = '2'"""
                _id = execute_query(update_old_data,opration='update')

                update_intent_data = {
                    
                        "deploy": status,
                        "model_name": model_name,
                        "timestamp":datetime.now().isoformat()
                    
                }
                my_collection = """UPDATE train_data SET deploy = :deploy,timestamp = TO_TIMESTAMP(:timestamp, 'YYYY-MM-DD"T"HH24:MI:SS.FF6') WHERE model_name = :model_name"""
                _id = execute_query(my_collection,opration='update',params=update_intent_data)

                deploy_log = {
                    "model_name": model_name,
                    "timestamp":datetime.now().isoformat(),
                    "status": "1",
                    "environment": "staging",
                    "user_name": "neosoft",
                }
                query="""INSERT INTO deploy_log (model_name, timestamp, status, environment, user_name)
                    VALUES (:model_name, TO_TIMESTAMP(:timestamp, 'YYYY-MM-DD"T"HH24:MI:SS.FF6'), :status, :environment, :user_name)"""
                _id = execute_query(query,opration='insert',params=deploy_log)
            else:

                myquery_run = {"model_name": model_name}
                update_query = """UPDATE train_data SET deploy = "5" WHERE model_name = :model_name"""
                _id = execute_query(update_query,opration='update',params=myquery_run)
                deploy_log = {
                    "model_name": model_name,
                    "timestamp":datetime.now().isoformat(),
                    "status": "2",
                    "environment": "staging",
                    "user": "neosoft",
                }
                query="""INSERT INTO deploy_log (model_name, timestamp, status, environment, user_name)
                    VALUES (:model_name, TO_TIMESTAMP(:timestamp, 'YYYY-MM-DD"T"HH24:MI:SS.FF6'), :status, :environment, :user_name)"""
                _id = execute_query(query,opration='insert',params=deploy_log)
        return _id
    except Exception as e:
        event_logger.error(e)
        return render_template("admin/500.html")


@training_details.route("/replace/stag")
def replace_stag():
    try:
        if session.get("islogin") != 1:
            return redirect(url_for("auth.login", _external=True, _scheme=config.SSL_SECURITY))
    except Exception as e:
        event_logger.error(e)
        return render_template("admin/400.html")

    result = {}
    result["status"] = "0"
    try:
        evn_status = execute_query("SELECT COUNT(*) as evn_status FROM maintain_status WHERE name = 'stag_training_status' AND status = '1'",'select')[0]['evn_status']
    except Exception as e:
        event_logger.error(e)
        return render_template("admin/400.html")
    if evn_status > 1:
        result["status"] = "1"
        return result
    id_ = request.args.get("id")
    all_db_intents = execute_query("SELECT * FROM train_data WHERE model_id = :id",opration='select',params={'id':id_})
    all_intents = []
    for x in all_db_intents:
        all_intents.append(x["model_name"])
        all_intents.append(x["deploy"])
        all_intents.append(x["intent_list"])
    model_name = all_intents[0]
    deploy = all_intents[1]
    intent_list = all_intents[2]
    try:

        def long_running_task(**kwargs):
            try:
                execute_query("UPDATE maintain_status SET status = '1' WHERE name = 'stag_training_status'",opration="update")
            except:
                status_collection=execute_query("INSERT INTO maintain_status (id,name, status) VALUES ('1','stag_training_status', '1')",opration="insert")

            query="""MERGE INTO maintain_status tgt
                    USING (SELECT 'stag_training_status' AS name FROM dual) src
                    ON (tgt.name = src.name)
                    WHEN MATCHED THEN
                        UPDATE SET tgt.status = '1'
                    WHEN NOT MATCHED THEN
                        INSERT (name, status) VALUES ('stag_training_status', '1')"""
            execute_query(query,'insert')
           
            with rasa_wrapper.RasaAPIWarapper() as rasaApi:
                status = rasaApi.replace_model(model_file=model_name)
                if status == True:
                    if deploy == "1":
                        status = "3"
                    else:
                        status = "2"                    
                    my_collection_old = """UPDATE train_data SET deploy = '1' WHERE deploy = '3'"""
                    execute_query(my_collection_old,opration='update')

                    update_nlu_data = {
                            "new_s_status": "0"  
                    }
                    execute_query("UPDATE nlu_data SET s_status = :new_s_status",opration='update',params=update_nlu_data)
                    update_query = """
                        UPDATE nlu_data
                        SET s_status = '1'
                        WHERE nlu_id IN ({})
                    """.format(','.join("'{0}'".format(id) for id in intent_list))
                    execute_query(update_query,'update')

                    
                    update_nlu_count="""UPDATE train_data
                        SET active_count = (SELECT COUNT(*) FROM nlu_data WHERE s_status = '1'),
                        inactive_count = (SELECT COUNT(*) FROM nlu_data WHERE s_status = '0') where model_id= :model_id"""
                    nlu_obj = {"model_id": id_}
                    _id = execute_query(update_nlu_count,opration='update',params=nlu_obj)

                    update_old_data ="""UPDATE train_data SET deploy = '0' WHERE deploy = '2'"""
                    _id = execute_query(update_old_data,opration='update')
                    update_intent_data = {
                    
                        "deploy": status,
                        "model_name": model_name,
                        "timestamp":datetime.now().isoformat()
                    
                    }
                    my_collection = """UPDATE train_data SET deploy = :deploy,timestamp = TO_TIMESTAMP(:timestamp, 'YYYY-MM-DD"T"HH24:MI:SS.FF6') WHERE model_name = :model_name"""
                    _id = execute_query(my_collection,opration='update',params=update_intent_data)

                    deploy_log = {
                        "model_name": model_name,
                        "timestamp":datetime.now().isoformat(),
                        "status": "1",
                        "environment": "staging",
                        "user_name": "neosoft",
                    }
                    query="""INSERT INTO deploy_log (model_name, timestamp, status, environment, user_name)
                        VALUES (:model_name, TO_TIMESTAMP(:timestamp, 'YYYY-MM-DD"T"HH24:MI:SS.FF6'), :status, :environment, :user_name)"""
                    execute_query(query,opration='insert',params=deploy_log)
                        
                        
                else:
                    myquery_run = {"model_name": model_name}
                    update_query = """UPDATE train_data SET deploy = "5" WHERE model_name = :model_name"""
                    _id = execute_query(update_query,opration='update',params=myquery_run)
                    deploy_log = {
                        "model_name": model_name,
                        "timestamp":datetime.now().isoformat(),
                        "status": "2",
                        "environment": "staging",
                        "user": "neosoft",
                    }
                    query="""INSERT INTO deploy_log (model_name, timestamp, status, environment, user_name)
                        VALUES (:model_name, TO_TIMESTAMP(:timestamp, 'YYYY-MM-DD"T"HH24:MI:SS.FF6'), :status, :environment, :user_name)"""
                    _id = execute_query(query,opration='insert',params=deploy_log)
            query="""MERGE INTO maintain_status tgt
                    USING (SELECT 'stag_training_status' AS name FROM dual) src
                    ON (tgt.name = src.name)
                    WHEN MATCHED THEN
                        UPDATE SET tgt.status = '0'
                    WHEN NOT MATCHED THEN
                        INSERT (name, status) VALUES ('stag_training_status', '0')"""
            execute_query(query,'insert')

           
        thread = threading.Thread(
            target=long_running_task, kwargs={"post_data": model_name}
        )
        thread.start()
     
        all_intents = db_handler.fetch_training_model()
        _all_intents = []
        if all_intents:
            for idx, x in enumerate(all_intents):
                _all_intents.append(
                    [
                        idx + 1,
                        x.get("model_profile_name"),
                        x.get("status"),
                        pd.to_datetime(x.get("timestamp")),
                        x.get("trained_by"),
                        x.get("model_name"),
                        x.get("deploy"),
                        x.get("_id"),
                        active_count_test(x.get("model_id"), "1", "stage"),
                        active_count_test(x.get("model_id"), "0", "stage"),
                        active_count_test(x.get("model_id"), "1", "prod"),
                        active_count_test(x.get("model_id"), "0", "prod"),
                        x.get("model_id"),
                        x.get("approve_status"),
                    ]
                )
        return render_template("admin/training_table.html", data=_all_intents)
    except Exception as e:
        event_logger.error(e)
        return redirect(
            url_for("intent.display_intents", _external=True, _scheme=config.SSL_SECURITY)
        )


@training_details.route("/replace/prod")
def replace_model_prod():
    try:
        if session.get("islogin") != 1:
            return redirect(url_for("auth.login", _external=True, _scheme=config.SSL_SECURITY))
    except Exception as e:
        event_logger.error(e)
        return render_template("admin/400.html")
    result = {}
    result["status"] = "0"
    
    evn_status = execute_query("SELECT COUNT(*) as evn_status FROM maintain_status WHERE name = 'prod_deploy_status' AND status = '1'",'select')[0]['evn_status']
    if evn_status > 1:
        result["status"] = "1"
        return result
    else:
        id_ = request.args.get("id")
        all_db_intents = execute_query("SELECT * FROM train_data WHERE model_id = :id",'select',params={'id':id_})
        all_intents = []
        for x in all_db_intents:
            all_intents.append(x["model_name"])
            all_intents.append(x["deploy"])
            all_intents.append(x["intent_list"])
        model_name = all_intents[0]
        deploy = all_intents[1]
        intent_list = all_intents[2]
        for x in all_db_intents:
            all_intents.append(x["model_name"])
            all_intents.append(x["deploy"])
        model_name = all_intents[0]
        deploy = all_intents[1]
        try:

            def long_running_task(**kwargs):
                query="""MERGE INTO maintain_status tgt
                    USING (SELECT 'prod_deploy_status' AS name FROM dual) src
                    ON (tgt.name = src.name)
                    WHEN MATCHED THEN
                        UPDATE SET tgt.status = '1'
                    WHEN NOT MATCHED THEN
                        INSERT (name, status) VALUES ('prod_deploy_status', '1')"""
                execute_query(query,'insert')
                
                with rasa_wrapper.RasaAPIWarapper() as rasaApi:
                    status = rasaApi.replace_model_welcome(model_file=model_name)
                    if status == True:
                        if deploy == "2":
                            status = "3"
                        else:
                            status = "1"
                        my_collection_old = """UPDATE train_data SET deploy = '2' WHERE deploy = '3'"""
                        _id = execute_query(my_collection_old,opration='update')
                        update_nlu_data = {
                         
                                "p_status": "0"
                        }
                      
                        _id =execute_query("UPDATE nlu_data SET p_status = :p_status",opration='update',params=update_nlu_data)
                        if intent_list:
                            update_query = """
                                UPDATE nlu_data
                                SET p_status = '1'
                                WHERE nlu_id IN ({})
                            """.format(','.join("'{0}'".format(id) for id in intent_list))
                            nlu_collection=execute_query(update_query,'update')

                        update_nlu_count="""UPDATE train_data
                            SET active_count = (SELECT COUNT(*) FROM nlu_data WHERE p_status = '1'),
                            inactive_count = (SELECT COUNT(*) FROM nlu_data WHERE p_status = '0') where model_id= :model_id"""
                        nlu_obj = {"model_id": id_}
                        _id = execute_query(update_nlu_count,opration='update',params=nlu_obj)
                        
                        update_old_data ="""UPDATE train_data SET deploy = '0' WHERE deploy = '1'"""
                        _id = execute_query(update_old_data,opration='update')

                        update_intent_data = {
                    
                        "deploy": status,
                        "model_name": model_name,
                        "timestamp":datetime.now().isoformat()
                    
                        }
                        my_collection = """UPDATE train_data SET deploy = :deploy,timestamp = TO_TIMESTAMP(:timestamp, 'YYYY-MM-DD"T"HH24:MI:SS.FF6') WHERE model_name = :model_name"""
                        _id = execute_query(my_collection,opration='update',params=update_intent_data)

                        queries_all = """UPDATE train_data
                                SET approve_status = '5'
                                WHERE approve_status = '1'"""
                        _id = execute_query(queries_all,'update')
                        updated_values ={"model_name": model_name}
                        queries = """UPDATE train_data
                                SET approve_status = '1'
                                WHERE model_name = :model_name"""
                        _id =execute_query(queries,'update',params=updated_values)

                        deploy_log = {
                            "model_name": model_name,
                            "timestamp":datetime.now().isoformat(),
                            "status": "1",
                            "environment": "production",
                            "user": "neosoft",
                        }
                        query="""INSERT INTO deploy_log (model_name, timestamp, status, environment, user_name)
                                            VALUES (:model_name, TO_TIMESTAMP(:timestamp, 'YYYY-MM-DD"T"HH24:MI:SS.FF6'), :status, :environment, :user_name)"""
                        _id = execute_query(query,opration='insert',params=deploy_log)
                    else:
                        myquery_run = {"model_name": model_name}
                        update_query = """UPDATE train_data SET deploy = "5" WHERE model_name = :model_name"""
                        _id = execute_query(update_query,opration='update',params=myquery_run)
                        deploy_log = {
                            "model_name": model_name,
                            "timestamp":datetime.now().isoformat(),
                            "status": "1",
                            "environment": "production",
                            "user": "neosoft",
                        }
                        query="""INSERT INTO deploy_log (model_name, timestamp, status, environment, user_name)
                                            VALUES (:model_name, TO_TIMESTAMP(:timestamp, 'YYYY-MM-DD"T"HH24:MI:SS.FF6'), :status, :environment, :user_name)"""
                        _id = execute_query(query,opration='insert',params=deploy_log)              
                    query="""MERGE INTO maintain_status tgt
                    USING (SELECT 'prod_deploy_status' AS name FROM dual) src
                    ON (tgt.name = src.name)
                    WHEN MATCHED THEN
                        UPDATE SET tgt.status = '0'
                    WHEN NOT MATCHED THEN
                        INSERT (name, status) VALUES ('prod_deploy_status', '0')"""
                    execute_query(query,'insert')

            thread = threading.Thread(
                target=long_running_task, kwargs={"post_data": model_name}
            )
            thread.start()

            all_intents = db_handler.fetch_training_model()
            _all_intents = []
            for idx, x in enumerate(all_intents):
                _all_intents.append(
                    [
                        idx + 1,
                        x.get("model_profile_name"),
                        x.get("status"),
                        pd.to_datetime(x.get("timestamp")),
                        x.get("trained_by"),
                        x.get("model_name"),
                        x.get("deploy"),
                        x.get("model_id"),
                        active_count_test(x.get("model_id"), "1", "stage"),
                        active_count_test(x.get("model_id"), "0", "stage"),
                        active_count_test(x.get("model_id"), "1", "prod"),
                        active_count_test(x.get("model_id"), "0", "prod"),
                        x.get("model_id"),
                        x.get("approve_status"),
                    ]
                )
            return render_template("admin/training_table.html", data=_all_intents)
        except Exception as e:
            event_logger.error(e)
            return render_template("admin/500.html")
        
        
@training_details.route("/delete_model", methods=["POST"])
def delete_model():
    try:
        if session.get("islogin") != 1:
            return redirect(url_for("auth.login", _external=True, _scheme=config.SSL_SECURITY))
    except Exception as e:
        event_logger.error(e)
        return render_template("admin/400.html")
    try:
        form_data = request.form.to_dict(flat=False)
        model_id = form_data.get("id")[0]
        
        
        fetch_query = "SELECT model_name FROM train_data WHERE model_id = :model_id"
        model_name=execute_query(fetch_query,'select',params={'model_id':model_id})[0]["model_name"]
        
        
        # Step 2: Delete the data from the traindata table using raw SQL
        delete_query = "DELETE FROM train_data WHERE model_id = :model_id"
        result=execute_query(delete_query, 'delete',params={'model_id':model_id})
        
        # Step 3: Delete the model directory
        model_directory = os.path.join(os.getcwd(), "bot", "models", model_name)
        prod_model_directory = os.path.join(os.getcwd(), "bot", "prod_models", model_name)

        if os.path.exists(model_directory):
            os.remove(model_directory)  # This will delete the entire directory
        if os.path.exists(prod_model_directory):
            os.remove(prod_model_directory)
       
        all_intents = db_handler.fetch_training_model()
        _all_intents = []
        for idx, x in enumerate(all_intents):
            _all_intents.append(
                [
                    idx + 1,
                    x.get("model_profile_name"),
                    x.get("status"),
                    pd.to_datetime(x.get("timestamp")),
                    x.get("trained_by"),
                    x.get("model_name"),
                    x.get("deploy"),
                    x.get("model_id"),
                    active_count_test(x.get("model_id"), "1", "stage"),
                    active_count_test(x.get("model_id"), "0", "stage"),
                    active_count_test(x.get("model_id"), "1", "prod"),
                    active_count_test(x.get("model_id"), "0", "prod"),
                    x.get("model_id"),
                    x.get("approve_status"),
                ]
            )
        return render_template("admin/training_table.html", data=_all_intents)
    except Exception as e:
        event_logger.error(e)
        return render_template("admin/500.html")

@training_details.route("/active_count_test")
def active_count_test(model_id, status, evn):
    try:
        all_db_intents = execute_query("""SELECT intent_list FROM train_data WHERE model_id = :model_id""",'select',params={'model_id':model_id})
        all_intents = []
        nlu_data = ""
        if not all_db_intents[0]['intent_list']:
            intent_list = []
        else:
            for x in all_db_intents:
                all_intents.append(x["intent_list"])
            intent_list = all_intents[0]
            intent_list = ','.join(["'" + str(nlu_id) + "'" for nlu_id in intent_list])
            if status == "1" and evn == "stage":
                nlu_data = execute_query(f"SELECT COUNT(*)  as count FROM nlu_data WHERE s_status = '1' AND nlu_id IN ({intent_list})",'select')[0]['count']
            elif status == "0" and evn == "stage":
                nlu_data =  execute_query(f"SELECT COUNT(*)  as count FROM nlu_data WHERE s_status = '0' AND nlu_id IN ({intent_list})",'select')[0]['count']
            elif status == "1" and evn == "prod":
                nlu_data =  execute_query(f"SELECT COUNT(*)  as count FROM nlu_data WHERE p_status = '1' AND nlu_id IN ({intent_list})",'select')[0]['count']
            elif status == "0" and evn == "prod":
                nlu_data =  execute_query(f"SELECT COUNT(*)  as count FROM nlu_data WHERE p_status = '0' AND nlu_id IN ({intent_list})",'select')[0]['count']
        return str(nlu_data)
    except Exception as e:
        event_logger.error(e)
        return render_template("admin/500.html")


@training_details.route("/view_intent", methods=["POST"])
def view_intent():
    try:
        projectpath = request.form
        query_data = projectpath.to_dict(flat=False)
        model_id = query_data.pop("model_id")[0]
        model_status = query_data.pop("status")[0]
        all_db_intents = execute_query("""SELECT * from train_data where model_id=:model_id""","select",params={'model_id':model_id})
        all_intents = []
        for x in all_db_intents:
            all_intents.append(x["model_profile_name"])
            all_intents.append(x["deploy"])
            all_intents.append(x["intent_list"])
        model_name = all_intents[0]
        deploy = all_intents[1]
        intent_list = all_intents[2]
        intent_list = ','.join(["'" + str(nlu_id) + "'" for nlu_id in intent_list])
        nlu_data_intents = []        
        if model_status == "1":
            model_status_intent = "Active Intents on Staging"
            nlu_data = execute_query(f"SELECT intent from nlu_data where s_status='1' and nlu_id  IN ({intent_list})",'select')
            
        elif model_status == "2":
            model_status_intent = "Inactive Intents on Staging"
            nlu_data = execute_query(f"SELECT intent from nlu_data where s_status='0' and nlu_id  IN ({intent_list})",'select')

        elif model_status == "3":
            model_status_intent = "Active Intents on Production"
            nlu_data = execute_query(f"SELECT intent from nlu_data where p_status='1' and nlu_id  IN ({intent_list})",'select')

        elif model_status == "4":
            model_status_intent = "Inactive Intents on Production"
            nlu_data = execute_query(f"SELECT intent from nlu_data where p_status='0' and nlu_id   IN ({intent_list})",'select')
        for x in nlu_data:
            nlu_data_intents.append(x["intent"])
        return render_template(
            "admin/intent_status.html",
            data=nlu_data_intents,
            model_name=model_name,
            model_status=model_status_intent,
        )
    except Exception as e:
        event_logger.error(e)
        return render_template("admin/500.html")

@training_details.route("/change_status", methods=["POST"])
def change_status():
    try:
        if session.get("islogin") != 1:
            return redirect(url_for("auth.login", _external=True, _scheme=config.SSL_SECURITY))
    except Exception as e:
        event_logger.error(e)
        return render_template("admin/400.html")

    try:
        form_data = request.form.to_dict(flat=False)
        model_id = form_data.get("id")
        status = form_data.get("status")
        if status[0] == "0" or status[0] == "5":
            updated_values = {
                    "model_id": model_id[0]
            }
            query = """UPDATE train_data
                    SET approve_status = '2'
                    WHERE model_id = :model_id """
            _id = execute_query(query,'update',params= updated_values)
        if status[0] == "2":
            updated_values = {
                "model_id": model_id[0]
            }
            queries = """UPDATE train_data
                    SET approve_status = '1'
                    WHERE model_id = :model_id """
            _id = execute_query(query,'update',params= updated_values)
        all_intents = db_handler.fetch_training_model()
        _all_intents = []
        for idx, x in enumerate(all_intents):
            _all_intents.append(
                [
                    idx + 1,
                    x.get("model_profile_name"),
                    x.get("status"),
                    pd.to_datetime(x.get("timestamp")),
                    x.get("trained_by"),
                    x.get("model_name"),
                    x.get("deploy"),
                    x.get("model_id"),
                    active_count_test(x.get("model_id"), "1", "stage"),
                    active_count_test(x.get("model_id"), "0", "stage"),
                    active_count_test(x.get("model_id"), "1", "prod"),
                    active_count_test(x.get("model_id"), "0", "prod"),
                    x.get("model_id"),
                    x.get("approve_status"),
                ]
            )
        return render_template("admin/training_table.html", data=_all_intents)
    except Exception as e:
        event_logger.error(e)
        return render_template("admin/500.html")


@training_details.route("/reject_model", methods=["POST"])
def reject_model():
    try:
        if session.get("islogin") != 1:
            return redirect(url_for("auth.login", _external=True, _scheme=config.SSL_SECURITY))
    except Exception as e:
        event_logger.error(e)
        return render_template("admin/400.html")
    try:
        form_data = request.form.to_dict(flat=False)
        model_id = form_data.get("id")
        status = form_data.get("status")
        train_collection = db_connection["train_data"]
        nlu_collection = db_connection["nlu_data"]
        if status[0] == "2":
            updated_values = {
                "$set": {
                    "approve_status": "4",
                }
            }
            queries = {"model_id": model_id[0]}
            _id = train_collection.update_one(queries, updated_values)

            all_db_intents = train_collection.find(
                {"model_id": model_id[0]}, {"newly_train_intents": 1}
            )
            all_intents = []
            if not all_db_intents:
                newly_train_intents = []
            else:
                for x in all_db_intents:
                    all_intents.append(x["newly_train_intents"])
                newly_train_intents = all_intents[0]
            nlu_collection.update_many(
                {"nlu_id": {"$in": newly_train_intents}},
                {"$set": {"status": "7"}},
                True,
            )
        all_intents = db_handler.fetch_training_model()
        _all_intents = []
        for idx, x in enumerate(all_intents):
            _all_intents.append(
                [
                    idx + 1,
                    x.get("model_profile_name"),
                    x.get("status"),
                    pd.to_datetime(x.get("timestamp")),
                    x.get("trained_by"),
                    x.get("model_name"),
                    x.get("deploy"),
                    x.get("_id"),
                    active_count_test(x.get("model_id"), "1", "stage"),
                    active_count_test(x.get("model_id"), "0", "stage"),
                    active_count_test(x.get("model_id"), "1", "prod"),
                    active_count_test(x.get("model_id"), "0", "prod"),
                    x.get("model_id"),
                    x.get("approve_status"),
                ]
            )
        return render_template("admin/training_table.html", data=_all_intents)
    except Exception as e:
        event_logger.error(e)
        return render_template("admin/500.html")


@training_details.route("/revoke", methods=["POST"])
def revoke():
    try:
        projectpath = request.form
        query_data = projectpath.to_dict(flat=False)
        intent_list = list(query_data.get("intent_list[]")[0].split(" "))
        model_id = query_data.get("model_id")[0]
    except Exception as e:
        event_logger.error(e)
        return render_template("admin/500.html")
    try:
        
        intent_list = ','.join(["'" + str(nlu_id) + "'" for nlu_id in intent_list])
        execute_query(f"UPDATE nlu_data SET status = '7' WHERE nlu_id IN ({intent_list})",'update')
        
        execute_query("""UPDATE train_data SET approve_status = '4' WHERE model_id = :model_id""",'update',params={'model_id':model_id})
        all_intents = db_handler.fetch_training_model()
        _all_intents = []
        if all_intents:
            for idx, x in enumerate(all_intents):
                _all_intents.append(
                    [
                        idx + 1,
                        x.get("model_profile_name"),
                        x.get("status"),
                        pd.to_datetime(x.get("timestamp")),
                        x.get("trained_by"),
                        x.get("model_name"),
                        x.get("deploy"),
                        x.get("_id"),
                        active_count_test(x.get("model_id"), "1", "stage"),
                        active_count_test(x.get("model_id"), "0", "stage"),
                        active_count_test(x.get("model_id"), "1", "prod"),
                        active_count_test(x.get("model_id"), "0", "prod"),
                        x.get("model_id"),
                        x.get("approve_status"),
                    ]
                )
        return render_template("admin/training_table.html", data=_all_intents)
    except Exception as e:
        return "false"
