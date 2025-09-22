from datetime import datetime
import os,pytz
from random import random
from flask_wtf import CSRFProtect
from flask import (
    Flask,
    render_template,
    request,
    session,
    redirect,
    Response,
    url_for,
    flash,
    jsonify,
)
from flask_session import Session
import base64,schedule
from utils.db_connector import execute_query, create_connection, handle_lob_fields
from utils import config,backup_chats
from utils.db_response import (
    get_user_details,
    get_user_roles_permissions,
    save_conversation,
    delete_old_tickets,
    insert_ticket_record,
)
from controller.intent import intent_details
from controller.auth import admin_auth
#from controller.training import training_details
from controller.admin import admin_details
from controller.chatbot import chatbot_details
from controller.response import response_details
from controller.sso_login import sso_auth, get_token, get_latest_token
from utils.db_connector import check_oracle_database
from utils import ingest
from flask import Flask, render_template, request, jsonify
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
from langchain.chains.question_answering import load_qa_chain
from langchain_core.prompts import PromptTemplate
from langchain_community.llms.ollama import Ollama
from langchain.schema import Document
from utils import opti_translate_all,ingest
from threading import Event,Thread
import hashlib,time
import whisper,tempfile
import re
from utils.logger import logger
import requests
import os, redis
import json
from datetime import datetime, timedelta
from datetime import timedelta
import oracledb as cx_Oracle
from flask_cors import CORS
import uuid
import redis
import hashlib

app = Flask(__name__)
CORS(
    app,
    resources={
        r"*": {
            "origins": [
                "*",
                "http://10.0.230.7:8007/",
                "http://10.0.230.41:8007/",
                "http://10.0.230.7:8007",
                "http://10.0.230.41:8007",
            ]
        }
    },
)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "/static/")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.secret_key = config.SECRET_KEY
app.config["SESSION_TYPE"] =config.SESSION_TYPE
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_USE_SIGNER"] = True
app.config["SSL_SECURITY"] = config.SSL_SECURITY
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(seconds=1000000)
app.config["SESSION_COOKIE_NAME"] = "session_data"
app.config['SESSION_REDIS'] = redis.from_url(config.REDIS_URL)
redis_client= redis.from_url(config.REDIS_URL)
SESSION_TTL_SECONDS = 86400  # 1 day
csrf = CSRFProtect(app)
event_logger = logger()

app.register_blueprint(intent_details)
app.register_blueprint(admin_auth)
app.register_blueprint(admin_details)
app.register_blueprint(chatbot_details)
app.register_blueprint(response_details)
app.register_blueprint(sso_auth) 
current_dir = os.path.dirname(os.path.abspath(__file__))  # directory where this script resides

server_session = Session(app)

prompt_file =   "prompts/prompt0.1.txt"
with open(prompt_file, "r") as file:
    system_prompt = file.read()
class RemoveServerHeaderMiddleware:
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        def custom_start_response(status, headers, exc_info=None):
            headers = [(name, value) for name, value in headers if name.lower() != 'server']
            return start_response(status, headers, exc_info)
        return self.app(environ, custom_start_response)

app.wsgi_app = RemoveServerHeaderMiddleware(app.wsgi_app)

@app.route("/")
def dashboard():
    """
    Admin Dashboard
    :return: Admin DashBoard View
    """
    if session.get("islogin") != 1:
        return redirect(
            url_for("auth.login", _external=True, _scheme=config.SSL_SECURITY)
        )
    session["status"] = "dashboard"
    if session.get("islogin") == 1 :
        return redirect(
            url_for(
                "admin.dashboard", _external=True, _scheme=config.SSL_SECURITY
            )
        )
   
def check_db_connection():
    try:
        # Example: Test a simple query to Redis
        redis_client.ping()
        return True
    except redis.ConnectionError:
        return False
def check_service_status(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return True
    except requests.RequestException:
        return False

@app.route('/health', methods=['GET'])
def health_check():
    health_status = {
        "base_service": check_service_status(config.BASE_URL),
        "prod_service": check_service_status(config.PROD_URL),
        "redis": check_db_connection(),
        "login_service": check_service_status(config.LOGIN_URL),
        "db_status":check_oracle_database()
    }
    status_code = 200 if all(health_status.values()) else 500
    return jsonify(health_status), status_code


@app.route('/readyz')
def readiness_check():
    # Add logic to check readiness, like DB connections, etc.
    return "OK", 200


@app.route("/admin_login", methods=["GET"])
def admin_login():
    """
    Check User Authentication
    :return: Redirect Dashboard View
    """
    try:
        token = request.args.get("param")
        user_id = execute_query(
            "SELECT emp_number from user_login_history where user_token=:token",
            "select",
            params={"token": token},
        )[0]["emp_number"]
        session["user_id"] = user_id
        session["token"] = token
        check_user = execute_query(
            "SELECT COUNT(*) AS emp_count FROM admin_login WHERE user_id = :user_id ",
            "select",
            params={"user_id": user_id},
        )[0]["emp_count"]
        
        if check_user == 0:
            user = get_user_details(user_id)[0]
            mydict = {
                "id": user["id"],
                "username": user["emp_name"],
                "user_id": user_id,
                "email": user["email_id"],
                "role": "1",
                "status": "1",
                "timestamp": datetime.utcnow().isoformat(),
                "token": token,
            }
            query = """INSERT INTO admin_login (id, username, user_id, email, role, status, timestamp,token) VALUES (:id, :username, :user_id, :email, :role, :status, TO_TIMESTAMP(:timestamp, 'YYYY-MM-DD"T"HH24:MI:SS.FF6'),:token)"""
            execute_query(query, "insert", params=mydict)
        else:
            query = """UPDATE admin_login SET token = :new_token,timestamp= TO_TIMESTAMP(:timestamp, 'YYYY-MM-DD"T"HH24:MI:SS.FF6') WHERE user_id = :user_id"""
            execute_query(
                query,
                "update",
                params={
                    "new_token": token,
                    "timestamp": datetime.utcnow().isoformat(),
                    "user_id": user_id,
                },
            )
        if get_latest_token(user_id) == token:
            user = get_user_details(user_id)
            user_details = []
            for x in user:
                user_details.append(x["emp_name"])
                user_details.append("2")
                user_details.append(x["user_id"])
                user_details.append(x["emp_name"])
            session["islogin"] = 1
            session["name"] = user_details[0]
            session["username"] = user_details[0]
            session["id"] = user_details[2]
            session["user_id"] = user_details[2]
            session["role"] = "2"
            all_access = get_user_roles_permissions(user_details[1])[0]
            access_list_value = all_access.get("access_list", "")
            access_list = [int(value) for value in access_list_value.split(",")]
            session["access"] = access_list
            session.modified = True
            event_logger.info("logged in successfully")
            return redirect(url_for("admin.dashboard", _external=True))
        else:
            flash(message="Invalid Username or Password")
            return redirect(
                url_for("auth.login", _external=True, _scheme=config.SSL_SECURITY)
            )

    except Exception as e:
        event_logger.error(e)
        return f"An error occurred: {str(e)}"


model = None

def save_model_name(name):
    with open("current_model.txt", "w") as f:
        f.write(name)

def load_model_name():
    try:
        with open("current_model.txt", "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return config.MODEL_NAME  # fallback to default if file not found

def load_model(model_name=None):
    global model
    if model_name is None:
        model_name = load_model_name()

    config.MODEL_NAME = model_name
    model = Ollama(
        model=config.MODEL_NAME,
        temperature=0.1,
        base_url=config.OLLAMA_URL
    )
    print(f"Model loaded at startup: {config.MODEL_NAME}")

def get_model():
    global model
    if model is None:
        load_model()
    return model
    
embed_model = None
transcribe_model = None
qdrant_client = None
stop_signals = {}

try:
    stop_signals = {}

   
    embed_model_path = os.path.join(current_dir, "ai4bharat/models--sentence-transformers--all-MiniLM-L6-v2/snapshots/8b3219a92973c328a8e22fadcfa821b5dc75636a")
    transcribe_model_path = os.path.join(current_dir,"ai4bharat/base.pt")
    

    qdrant_client = QdrantClient(
        host=os.getenv("QDRANT_HOST"), 
        port=6333, 
        prefer_grpc=False
    )

    embed_model = SentenceTransformer(embed_model_path)
    transcribe_model = whisper.load_model(transcribe_model_path)

    print("All models loaded successfully.")
except Exception as e:
    print(f"Failed to load models: {e}")
load_model()

@app.route("/change_model", methods=["POST"])
@csrf.exempt
def change_model():
    data = request.get_json()
    new_model = data.get("model_name")

    if not new_model:
        return jsonify({"success": False, "error": "No model selected"})

    try:
        save_model_name(new_model)
        load_model(new_model)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@csrf.exempt
@app.route('/transcribe', methods=['POST'])
def transcribe_audio():
    emp_no = request.form.get('emp_no')
    preferred_language = request.form.get('preferredLanguage')
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400

    audio_file = request.files['audio']
    with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as temp:
        audio_file.save(temp.name)
        print("Saved audio to:", temp.name)

        # Optional: Convert .webm to .wav using ffmpeg-python or subprocess
        wav_path = temp.name.replace(".webm", ".wav")
        os.system(f"ffmpeg -i {temp.name} -ar 16000 -ac 1 {wav_path}")
        language_code = "en"  # Hindi

        # Transcribe
        result = transcribe_model.transcribe(wav_path,language=language_code)
        os.remove(temp.name)
        os.remove(wav_path)
        return jsonify({'text': result['text']})

def query_qdrant(qdrant_client, query_text, embed_model, top_k=2):
    print(query_text,888888888888888888888888888888888888)
    query_embedding = embed_model.encode([query_text])[0].tolist()

    # List all collections
    collections = qdrant_client.get_collections().collections

    all_search_results = []
    max_score_result = None
    for collection in collections:
        search_result = qdrant_client.search(
            collection_name=collection.name,
            query_vector=query_embedding,
            limit=top_k
        )
        if search_result:
            for result in search_result:
                if result.score > 0.4:
                    all_search_results.append({
                        "id": result.id,
                        "score": result.score,
                        "payload": result.payload,
                        "collection": collection.name
                    })
    sorted_results = sorted(all_search_results, key=lambda x: x["score"], reverse=True)
    top_results = sorted_results[:3]

    max_score_result = top_results[0] if top_results else None
    print(max_score_result)   
    return max_score_result

# Function to format Qdrant results
def format_qdrant_results(results):
    formatted_docs = []
    if results:  # Check if results are not empty
        doc = Document(
            page_content=results['payload']['text_chunk'],  # Assuming 'text_chunk' contains the document's content
            metadata=results['payload'].get('metadata', {})  # Add metadata if present, otherwise an empty dictionary
        )
        formatted_docs.append(doc)
    return formatted_docs

# Define the function to handle the conversational chain logic
def get_conversational_chain():   
    print(config.MODEL_NAME,33333333333333333333333333333333333)
    event_logger.info(config.MODEL_NAME)
    prompt = PromptTemplate(template=system_prompt, input_variables=["context", "question"])
    chain = load_qa_chain(model, chain_type="stuff", prompt=prompt)
    return chain    



def get_user_session(user_id):
    """Retrieve session history in Q&A format"""
    key = f"session:{user_id}"
    session_data = redis_client.get(key)
    if not session_data:
        return []

    try:
        history = json.loads(session_data)
    except json.JSONDecodeError:
        return []

    # Optional: filter only well-formed entries
    return [
        {
            "msg": item.get("msg", ""),
            "response": item.get("response", {}),
            "timestamp": item.get("timestamp", 0)
        }
        for item in history
        if item.get("msg") or item.get("response")
    ]

def update_user_session(user_id, msg, response):
    """Update session history and refresh TTL"""
    key = f"session:{user_id}"
    history = get_user_session(user_id)

    history.append({
        "msg": msg,
        "response": response,
        "timestamp": int(time.time())  # Add current epoch timestamp
    })

    # Save updated history back to Redis and refresh TTL
    redis_client.setex(key, SESSION_TTL_SECONDS, json.dumps(history))
    

def delete_user_session(user_id):
    """Delete session history for a user"""
    key = f"session:{user_id}"
    redis_client.delete(key)
    
    
@csrf.exempt
@app.route('/upload_doc', methods=['POST'])
def upload_doc():
    if 'file' not in request.files:
        return render_template("chatbot/chats_llm.html", 
                               bot_response={"text": "No file uploaded"}, 
                               type='upload', 
                               current_time=datetime.now().strftime('%I:%M %p'))

    uploaded_file = request.files['file']

    if uploaded_file.filename == '':
        return render_template("chatbot/chats_llm.html", 
                               bot_response={"text": "No file selected"}, 
                               type='upload', 
                               current_time=datetime.now().strftime('%I:%M %p'))

    # Allow txt, pdf, docx, csv, xlsx
    allowed_types = [
        'text/plain',
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/csv',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    ]
    if uploaded_file.content_type not in allowed_types:
        return render_template("chatbot/chats_llm.html", 
                               bot_response={"text": "Unsupported file type"}, 
                               type='upload', 
                               current_time=datetime.now().strftime('%I:%M %p'))

    # Check file size
    content = uploaded_file.read()
    if len(content) > 1000 * 1024:   # ~1MB
        return render_template("chatbot/chats_llm.html", 
                               bot_response={"text": "File size exceeds 50 KB"}, 
                               type='upload', 
                               current_time=datetime.now().strftime('%I:%M %p'))

    # Reset file pointer
    uploaded_file.stream.seek(0)

    # Extract text depending on file type
    text = ""
    extracted_data = None
    try:
        if uploaded_file.content_type == 'application/pdf':
            text = ingest.extract_text_from_pdf([uploaded_file])
        elif uploaded_file.content_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
            text = ingest.extract_text_from_docx(uploaded_file)
        elif uploaded_file.content_type in ['text/csv', 'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']:
            if uploaded_file.content_type == 'text/csv':
                extracted_data = ingest.extract_text_from_csv(uploaded_file)
            else:
                extracted_data = ingest.extract_data_from_excel(uploaded_file)
            text = json.dumps(extracted_data, ensure_ascii=False, indent=2)  # for LLM summarization
        else:  # plain text
            try:
                text = content.decode('utf-8')
            except UnicodeDecodeError:
                text = content.decode('latin1')
    except Exception as e:
        return render_template("chatbot/chats_llm.html", 
                               bot_response={"text": f"Error extracting text: {str(e)}"}, 
                               type='upload', 
                               current_time=datetime.now().strftime('%I:%M %p'))

    # Send to Ollama
    try:
        ollama_response = requests.post(
            config.OLLAMA_URL + '/api/generate',
            json={
                "model": config.MODEL_NAME,
                "prompt": f"Summarize the following text in 4 lines:\n\n{text}"
            },
            timeout=900
        )

        if ollama_response.status_code == 200:
            lines = ollama_response.text.strip().splitlines()
            final_text = ""
            for line in lines:
                try:
                    data = json.loads(line)
                    final_text += data.get("response", "")
                except json.JSONDecodeError:
                    continue

            user_id = request.form.get("emp_no", "system")
            words = final_text.split()
            if len(words) > 900:
                final_text = " ".join(words[:900]) + "..."
            conversation_id = save_conversation(
                uploaded_file.filename, final_text, user_id,
                model_name=config.MODEL_NAME,
                metadata={"source": "upload"}
            )

            bot_response = {
                "text": final_text,
                "conversation_id": conversation_id
            }
            update_user_session(user_id, uploaded_file.filename, bot_response)

            return render_template("chatbot/chats_llm.html", 
                                   bot_response=bot_response, 
                                   type='upload', 
                                   current_time=datetime.now().strftime('%I:%M %p'))
        else:
            return render_template("chatbot/chats_llm.html", 
                                   bot_response={"text": "Ollama returned an error"}, 
                                   type='upload', 
                                   current_time=datetime.now().strftime('%I:%M %p'))

    except requests.exceptions.RequestException as e:
        return render_template("chatbot/chats_llm.html", 
                               bot_response={"text": f"Ollama server error: {str(e)}"}, 
                               type='upload', 
                               current_time=datetime.now().strftime('%I:%M %p'))

@csrf.exempt
@app.route('/bot_msg_llmbot', methods=['POST'])
def bot_msg_llmbot():
    headers = {"Content-type": "application/json"}
    projectpath = request.form
    query_data = projectpath.to_dict(flat=False)
    msg = query_data.pop("msg")[0]
    type = query_data.pop("type")[0]
    preferred_language =  query_data.pop("preferredLanguage")[0]
    user_id = query_data.pop("emp_no")[0]
    bot_response = {}
    history = []
    primary_language = "eng_Latn"
    actual_msg=msg

    auth=execute_query(f"SELECT COUNT(*) as isactive FROM USER_MASTER WHERE emp_number ='{user_id}' ",'select')
    if not auth or auth[0].get("isactive", 0) == 0:
        return jsonify({
            "text": "Your session has expired or you have been logged out.",
            "expired": True
        }), 401
    # Generate a hash for the message to check caching
    msg_hash = hashlib.sha256(msg.encode()).hexdigest()
    if user_id not in stop_signals:
            stop_signals[user_id] = Event()
    else:
        stop_signals[user_id].clear()
    
    if stop_signals[user_id].is_set():
        bot_response['text'] = "Process stopped by user request."
        stop_signals[user_id].clear()
        return jsonify(bot_response)
   
    if preferred_language and preferred_language != primary_language:
        try:
            # translator = GoogleTranslator(source=preferred_language, target=primary_language)
            msg = opti_translate_all.translate_batch(msg, preferred_language, primary_language)
            #msg = translator.translate(msg)
            # msg=translator
            print(msg,222222222222222222222222)
        except Exception as e:
            bot_response['text'] = f"An error occurred while translating input: {str(e)}"
            return jsonify(bot_response)
   
    # Define a function for processing
    def process_chain():
        try:
            collection_name=''
            cache_docs = ingest.query_qdrant_cache(qdrant_client, msg, embed_model)
            if cache_docs:                                
                bot_response['text'] = cache_docs
                bot_response['source'] = "cache"
                conversation_id = save_conversation(msg, cache_docs, user_id,model_name=config.MODEL_NAME,metadata={})
                bot_response['conversation_id'] = conversation_id
                bot_response['suggested_questions'] = ingest.generate_suggestions_qdrant(qdrant_client, msg, embed_model)
                update_user_session(user_id, actual_msg, bot_response)
            else:

            # Query Qdrant for relevant documents
                relevant_docs = query_qdrant(qdrant_client, msg, embed_model)
                formatted_docs = format_qdrant_results(relevant_docs) if relevant_docs else []


                # Directly use relevant_docs if score > 0.9
                if relevant_docs and relevant_docs['score'] > 0.9:
                    bot_response['text'] = relevant_docs['payload']['text_chunk']
                    bot_response['suggested_questions'] = ingest.generate_suggestions_qdrant(qdrant_client, msg, embed_model)
                else:
                    chain = get_conversational_chain()
                    response = chain({"input_documents": formatted_docs, "question": msg}, return_only_outputs=True)
                    bot_response['text'] = response.get('output_text', "I couldn't generate a relevant response.")
                    bot_response['suggested_questions'] = ingest.generate_suggestions_qdrant(qdrant_client, msg, embed_model)
                collection_name=relevant_docs['collection'] if relevant_docs else None

            if preferred_language != primary_language:
                try:
                    print(bot_response['text'],7777777777777777777777777777777777777777)
                    bot_response['text'] = opti_translate_all.translate_batch(bot_response['text'], primary_language,preferred_language)
                    print(bot_response['text'],9999999999999999999999999999999999999999999)
                    translated_questions = [opti_translate_all.translate_batch(q, primary_language,preferred_language) for q in bot_response['suggested_questions']]
                    bot_response['suggested_questions'] = translated_questions 
                except Exception as e:
                    bot_response['text'] = f"An error occurred while translating response: {str(e)}"
            conversation_id = save_conversation(msg, bot_response['text'], user_id,model_name=config.MODEL_NAME,metadata={"collection_name":collection_name})
            bot_response['conversation_id'] = conversation_id
            update_user_session(user_id, actual_msg, bot_response)
        except Exception as e:
            bot_response['text'] = f"An error occurred: {str(e)}"
            print(f"Error in chain processing: {e}")

    # Start the processing in a thread
    processing_thread = Thread(target=process_chain)
    processing_thread.start()

    # Continuously check the stop signal
    while processing_thread.is_alive():
        if stop_signals[user_id].is_set():
            bot_response['text'] = "Process stopped by user request."
            stop_signals[user_id].clear()
            conversation_id = save_conversation(msg, bot_response['text'], user_id,model_name=config.MODEL_NAME,metadata={})
            bot_response['conversation_id'] = conversation_id
            return render_template("chatbot/chats_llm.html", bot_response=bot_response, type=type, current_time=datetime.now().strftime('%I:%M %p'))

    return render_template("chatbot/chats_llm.html", bot_response=bot_response, type=type, current_time=datetime.now().strftime('%I:%M %p'))

@csrf.exempt
@app.route('/get-history', methods=['GET'])
def get_history():
    user_id = request.args.get('user_id')
    print(user_id,999999999999999999999999999)
    if not user_id:
        return jsonify({"error": "Missing user_id"}), 400

    # Optional: check user is still active
    auth = execute_query(f"SELECT COUNT(*) as isactive FROM USER_MASTER WHERE emp_number ='{user_id}' ", 'select')
    if not auth or auth[0].get("isactive", 0) == 0:
        return jsonify({"error": "User inactive or session expired"}), 401

    # Get session from Redis
    history = get_user_session(user_id)
    return jsonify(history[-10:])

@csrf.exempt
@app.route('/delete_session', methods=['POST'])
def delete_session():
    data = request.get_json()
    user_id = data.get("user_id")
    key = f"session:{user_id}"

    if not user_id:
        return jsonify({"error": "Missing user_id"}), 400

    try:
        redis_client.delete(key)
        return jsonify({"message": "Session deleted"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@csrf.exempt
@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    feedback_data = request.get_json()
    action = feedback_data.get('action')
    text = feedback_data.get('text')
    conversation_id = feedback_data.get('conversation_id')
    user_id = feedback_data.get('emp_no', '')

    # Check for missing user_id
    if not user_id:
        return jsonify({
            "status": "error",
            "message": "User ID is missing"
        }), 400

    try:
        # Common query for updating conversation
        update_query = """
            UPDATE conversation
            SET USER_ACTION = :feedback_action, USER_ID = :user_id, TIMESTAMP = TO_TIMESTAMP(:timestamp, 'YYYY-MM-DD"T"HH24:MI:SS.FF6')
            WHERE ID = :conversation_id
        """
        params = {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            "feedback_action": action,
        }
        execute_query(update_query, "update", params=params)
        if action == 'dislike' and text:
            mobile_no = execute_query('SELECT contactno from user_master WHERE user_id = :user_id', 'select', params={'user_id': user_id})
            token_data = {
                "p_grvc_emp_number": user_id,
                "p_grvc_type_of_query": "Process Issue",
                "p_grvc_module_name": "my_role",
                "p_grvc_subject": text,
                "p_grvc_priority": "Medium",
                "p_grvc_description": text,
                "p_grvc_mob_number": mobile_no[0].get("contactno") if mobile_no else '8888888888',
                "p_grvc_file":""
            }
            auth_token = config.TICKET_API_TOKEN
            #credentials=config.TICKET_API_CREDENTIAL
            credentials = base64.b64encode(f"{config.TICKET_API_USER}:{config.TICKET_API_PASSWORD}".encode('utf-8')).decode('utf-8')
            headers = {
                "token": auth_token,
                "device-type": "android",
                "lang": "en",
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/json",
            }
            response = requests.post(config.TICKET_API_URL, headers=headers, json=token_data, verify=False)
            print(response.text)
            if response.status_code == 200:
                json_data = response.json()
                if json_data.get("status") == True:
                    b1_value = json_data.get("data", {}).get(":B1")
                    result=insert_ticket_record(b1_value, token_data)
                    update_query = """
                        UPDATE conversation
                        SET USER_ACTION = :feedback_action,
                            USER_ID = :user_id,
                            TIMESTAMP = TO_TIMESTAMP(:timestamp, 'YYYY-MM-DD"T"HH24:MI:SS.FF6'),
                            METADATA = JSON_MERGEPATCH(NVL(METADATA, '{}'), '{"ticket_id": "' || :ticket_id || '"}')
                        WHERE ID = :conversation_id
                    """
                    params = {
                        "conversation_id": conversation_id,
                        "user_id": user_id,
                        "timestamp": datetime.now().isoformat(),
                        "feedback_action": action,
                        "ticket_id": b1_value  # Pass the ticket id as a parameter
                    }
                    execute_query(update_query, "update", params=params)
                    return jsonify({
                        "status": "success",
                        "action": action,
                        "message": "Feedback saved successfully"})
                else:
                    message = json_data.get("message")
                    return jsonify({
                        "status": "faild",
                        "action": action,
                        "message": message})
        return jsonify({
            "status": "success",
            "action": action,
            "message": "Feedback saved successfully"
        })

    except Exception as e:
        print(f"Error saving feedback: {e}")
        return jsonify({
            "status": "error",
            "message": "An error occurred while saving the feedback"
        }), 500


@csrf.exempt
@app.route('/stop_process', methods=['POST'])
def stop_process():
    data = request.get_json()
    user_id = data.get("user_id")
    if user_id in stop_signals:
        stop_signals[user_id].set()  # Trigger the stop signal
        print(f"Stop signal triggered for user {user_id}.")
        return jsonify({"status": "success", "message": "Process stopped successfully."}), 200
    else:
        print(f"No active process found for user {user_id}.")
        return jsonify({"status": "error", "message": "No process found for this user."}), 404


import multiprocessing
import subprocess

# def start_tensorflow_worker():
#     subprocess.Popen(["python", "controller/tensorflow_worker.py"])  # Runs in background


@app.route("/testing")
def testing():
    """
    Admin Dashboard
    :return: Admin DashBoard View
    """
    if session.get("islogin") != 1:
        return redirect(
            url_for("auth.login", _external=True, _scheme=config.SSL_SECURITY)
        )
    if session.get("token") != get_latest_token(session.get("user_id")):
        return redirect(
            url_for("auth.login", _external=True, _scheme=config.SSL_SECURITY)
        )
    else:
        session["status"] = "dashboard"

    session["status"] = "testing"
    return render_template(
        "admin/testing.html",
        prod_socket_uri=config.PROD_SOCKET_URI,
        prod_socket_path=config.PROD_SOCKET_PATH,
    )



@csrf.exempt
@app.route("/bot_msg", methods=["POST"])
def bot_msg():
    headers = {"Content-type": "application/json"}
    projectpath = request.form
    query_data = projectpath.to_dict(flat=False)
    msg = query_data.pop("msg")[0]
    type = query_data.pop("type")[0]
    emp_name = query_data.pop("emp_name")[0]
    user_id = query_data.pop("emp_no")[0]
    user_id = str(user_id)
    auth=execute_query(f"SELECT COUNT(*) as isactive FROM USER_MASTER WHERE emp_number ='{user_id}' ",'select')
    try:
        if auth[0]['isactive'] < 1:
            response = [
                    {
                        "recipient_id": "1",
                        "text": "Unauthorized access.",
                    }
                ]

            return render_template("chatbot/chats.html", bot_response=response, type=type)
    except:
        response = [
                    {
                        "recipient_id": "1",
                        "text": "User does not exist",
                    }
                ]
        return render_template("chatbot/chats.html", bot_response=response, type=type)
    
    
    if type == "prod":
        message_url = config.PROD_URL+"/webhooks/rest/webhook"
    else:
        message_url =  config.BASE_URL+"/webhooks/rest/webhook"

    payload_old = '{"sender": "' + user_id + '", "message": "' + msg + '"}'
    r = requests.post(message_url, data=payload_old.encode("utf-8"), headers=headers)
    response = json.loads(r.content)
    save_conversation(msg, response)
    if msg == "confirm" or msg == "Confirm":
        msg_texts = execute_query(
            "SELECT msg from TICKET_CHAT where user_id=:user_id and flag=2",
            "select",
            params={"user_id": user_id},
        )
        msg = [item["msg"] for item in msg_texts]
        msg = " ".join(msg)
        mobile_no = execute_query('SELECT contactno from user_master where user_id=:user_id','select',params={'user_id':user_id})[0]["contactno"]
        if not mobile_no :
            mobile_no="8888888888"
        token_data = {
            "p_grvc_emp_number": user_id,
            "p_grvc_type_of_query": "Process Issue",
            "p_grvc_module_id": 1,
            "p_grvc_subject": msg,
            "p_grvc_priority": "Medium",
            "p_grvc_description": msg,
            "p_grvc_category": "General",
            "p_grvc_mob_number": mobile_no,
        }
        auth_token = config.TICKET_API_TOKEN
        username = config.TICKET_API_USER
        password = config.TICKET_API_PASSWORD
        credentials = base64.b64encode(f"{username}:{password}".encode('utf-8')).decode('utf-8')
        url = config.TICKET_API_URL
        ci_session = config.TICKET_API_SESSION
        headers = {
            "token": auth_token,
            "device-type": "android",
            "lang": "en",
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json",
        }
        req = requests.post(url, headers=headers, json=token_data, verify=False)
        msg = req.text
        if req.status_code == 200:
            json_data = req.json()
            if json_data.get("status") == True:
                b1_value = json_data.get("data", {}).get(":B1")
                all_tickets = execute_query("SELECT * FROM TICKET_GENERATION", "select")
                # if all_tickets[0][0] > 100000:
                #     delete_old_tickets()
                insert_ticket_record(b1_value, token_data)
                response_dict = {
                    "recipient_id": "1",
                    "text": "Thank you for raising the ticket. Your request has been successfully processed. Please find your ticket ID:"
                    + b1_value
                    + ", You can track your queries in Union Prerna by navigating to MyTools -> EKAMHelpdesk -> Employee Dashboard -> My Queries.",
                    "buttons": [{"title": "Main Menu", "payload": "greet"}],
                }
                response = [response_dict]
            else:
                json_data = req.json()
                message = json_data.get("message")
                response_dict = {
                    "recipient_id": "1",
                    "text": message + " Do you want to raise your ticket again.",
                    "buttons": [
                        {"title": "yes", "payload": "yes"},
                        {"title": "no", "payload": "no"},
                    ],
                }
                response = [response_dict]
        sql_query = """UPDATE TICKET_CHECK SET flag = 0 WHERE emp_id = :emp_id"""
        _id = execute_query(sql_query, "insert", params={"emp_id": user_id})
        _id = execute_query(
            "Delete from TICKET_CHAT WHERE user_id = :emp_id",
            "delete",
            params={"emp_id": user_id},
        )
        return render_template("chatbot/chats.html", bot_response=response, type=type)

    elif msg == "add query" or msg == "Add query":
        sql_query = """UPDATE TICKET_CHECK SET flag = 1 WHERE emp_id = :emp_id"""
        id = execute_query(sql_query, "insert", params={"emp_id": user_id})
        response = [{"recipient_id": "1", "text": "ok please continue."}]
        return render_template("chatbot/chats.html", bot_response=response, type=type)

    if (
        response[0].get("text")
        in "I didn't understand you. Do you want to raise a ticket?"
    ):
        all_db_tickets = execute_query(
            "SELECT * FROM TICKET_CHECK WHERE emp_id = :emp_id AND flag = 1",
            "select",
            params={"emp_id": user_id},
        )
        title_flag = len(all_db_tickets)
        if title_flag == 0:
            response = [
                {
                    "recipient_id": "1",
                    "text": "I did not understand! Would you like to raise ticket to address your query.",
                    "buttons": [
                        {"title": "yes", "payload": "yes"},
                        {"title": "no", "payload": "no"},
                    ],
                }
            ]
        elif title_flag == 1:
            update_flag = execute_query(
                "INSERT INTO TICKET_CHAT (user_id, msg,flag) VALUES(:user_id,:msg,2)",
                "insert",
                params={"user_id": user_id, "msg": msg},
            )
            response = [
                {
                    "recipient_id": "1",
                    "text": "Have you completed your query? Please select 'Confirm' if it is finished, otherwise select 'Add Query'",
                    "buttons": [
                        {"title": "confirm", "payload": "Confirm"},
                        {"title": "add query", "payload": "Add query"},
                    ],
                }
            ]
            sql_query = """UPDATE TICKET_CHECK SET flag = 2 WHERE emp_id = :emp_id"""
            return render_template(
                "chatbot/chats.html", bot_response=response, type=type
            )

    if msg == "yes":
        ticket_data = execute_query(
            "SELECT * FROM TICKET_CHECK WHERE emp_id = :emp_id",
            "select",
            params={"emp_id": user_id},
        )
        if len(ticket_data) == 0:
            execute_query(
                "INSERT INTO TICKET_CHECK (emp_id, flag) VALUES (:emp_id, 1) ",
                "insert",
                params={"emp_id": user_id},
            )
        else:
            execute_query(
                "UPDATE TICKET_CHECK SET flag = 1 WHERE emp_id = :emp_id ",
                "insert",
                params={"emp_id": user_id},
            )
        response = [
            {
                "recipient_id": "1",
                "text": "Please share your query below. Include relevant details for a precise response. ",
            }
        ]

        return render_template("chatbot/chats.html", bot_response=response, type=type)
    else:
        _id = execute_query(
            "UPDATE TICKET_CHECK SET flag = 0 WHERE emp_id = :emp_id ",
            "insert",
            params={"emp_id": user_id},
        )

    original_text = response[0]["text"]
    if msg == "greet":
        response[0][
            "text"
        ] = f"Hi {emp_name.title()}, I am EKAM. I am here to help you with your queries related to EKAM. "
    return render_template("chatbot/chats.html", bot_response=response, type=type)


@csrf.exempt
@app.route('/check-recent-feedback', methods=['POST'])
def check_recent_feedback():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        user_id = data.get('user_id')
        if not user_id:
                return jsonify({'error': 'User ID is required'}), 400
            
        
        # Check if user has submitted feedback in the last 7 days
        
        query = """
            SELECT COUNT(*) as total FROM bot_user_feedback 
            WHERE user_id = :user_id AND created_at >= :created_at
        """
        
        seven_days_ago = datetime.now(pytz.utc) - timedelta(days=7)
        result=execute_query(query, 'select', params={"user_id":user_id,"created_at":seven_days_ago})

        if result and len(result) > 0:
                count = result[0]['total']
                return jsonify({'has_recent_feedback': count > 0})
        else:
            return jsonify({'has_recent_feedback': False})
            
    except Exception as e:
        print(f"Error checking recent feedback: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@csrf.exempt
@app.route('/submit-bot-feedback', methods=['POST'])
def submit_bot_feedback():
    data = request.get_json()
    user_id = data.get('user_id')
    experience_rating = data.get('experience_rating')
    response_quality = data.get('response_quality')
    response_time = data.get('response_time')
    suggestion = data.get('suggestion')
    
    # Insert feedback into database
   
    
    query = """
        INSERT INTO bot_user_feedback 
        (user_id, experience_rating, response_quality, response_time, suggestion) 
        VALUES (:user_id, :experience_rating, :response_quality, :response_time, :suggestion)
    """
    
    execute_query(query,'insert',params={"user_id":user_id, "experience_rating":experience_rating, "response_quality":response_quality, "response_time":response_time, "suggestion":suggestion})
   
    
    return jsonify({'status': 'success', 'message': 'Feedback submitted successfully'})




if __name__ == "__main__":
    # start_tensorflow_worker()
    app.secret_key = os.urandom(24)
    schedule.every().day.at("00:00").do(backup_chats.backup_and_delete_conversations)
    scheduler_thread = Thread(target=backup_chats.run_scheduler)
    scheduler_thread.daemon = True  # This will ensure the thread exits when the main program exits
    scheduler_thread.start()
    app.run("0.0.0.0", port="6001", debug=True)
