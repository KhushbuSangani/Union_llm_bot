import os
import oracledb as cx_Oracle
from utils import config
from utils.logger import logger

event_logger = logger()


try:
    connection = cx_Oracle.connect(
        user=config.ORACLE_USER,
        password=config.ORACLE_PASSWORD,
        dsn=config.ORACLE_HOST,
    )
    cursor = connection.cursor()

    # List of SQL queries to create all required tables
    tables = [
        {
            "sql": """
                CREATE TABLE admin_role (
                    role_id NUMBER,
                    role_name VARCHAR2(50),
                    access_list VARCHAR2(100)
                )
            """,
            "name": "admin_role"
        },
        {
            "sql": """
                CREATE TABLE admin_login (
                    ID VARCHAR2(50),
                    ROLE VARCHAR2(10),
                    USERNAME VARCHAR2(50),
                    USER_ID VARCHAR2(20),
                    STATUS VARCHAR2(10),
                    TIMESTAMP VARCHAR2(50),
                    TOKEN VARCHAR2(100),
                    EMAIL VARCHAR2(255)
                )
            """,
            "name": "admin_login"
        },
        {
            "sql": """
                CREATE TABLE nlu_data (
                    intent VARCHAR2(255),
                    response_type VARCHAR2(255),
                    response_text CLOB,
                    response_payload CLOB,
                    title VARCHAR2(255),
                    description CLOB,
                    status VARCHAR2(255),
                    p_status VARCHAR2(255),
                    s_status VARCHAR2(255),
                    nlu_id VARCHAR2(255) PRIMARY KEY,
                    query CLOB,
                    entity VARCHAR2(255),
                    timestamp TIMESTAMP,
                    user_id VARCHAR2(255)
                )
            """,
            "name": "nlu_data"
        },
        {
            "sql": """
                CREATE TABLE train_data (
                    model_name VARCHAR2(255),
                    timestamp TIMESTAMP,
                    model_id VARCHAR2(20),
                    status VARCHAR2(1),
                    deploy VARCHAR2(1),
                    prod_active_count NUMBER,
                    prod_inactive_count NUMBER,
                    file_list CLOB,
                    newly_train_files CLOB,
                    trained_by VARCHAR2(255)
                )
            """,
            "name": "train_data"
        },
        {
            "sql": """
                CREATE TABLE training_log (
                    model_name VARCHAR2(255),
                    model_id VARCHAR2(24),
                    timestamp TIMESTAMP,
                    status VARCHAR2(1),
                    user_name VARCHAR2(255)
                )
            """,
            "name": "training_log"
        },
        {
            "sql": """
                CREATE TABLE TRAINING_SCHEDULE (
                    MODEL_NAME VARCHAR2(255 BYTE),
                    MODEL_PROFILE_NAME VARCHAR2(255 BYTE),
                    TIMESTAMP TIMESTAMP(6),
                    SCHEDULE_TIME TIMESTAMP(6),
                    MODEL_ID VARCHAR2(255 BYTE),
                    STATUS VARCHAR2(1 BYTE)
                )
            """,
            "name": "TRAINING_SCHEDULE"
        },
        {
            "sql": """
                CREATE TABLE TICKET_GENERATION (
                    ID VARCHAR2(255 BYTE),
                    MODULE_NAME VARCHAR2(255 BYTE),
                    TOKEN_NUMBER VARCHAR2(15 BYTE),
                    EMP_NUMBER NUMBER(38, 0),
                    TYPE_OF_QUERY VARCHAR2(255 BYTE),
                    SUBJECT CLOB,
                    DESCRIPTION CLOB,
                    PRIORITY VARCHAR2(20 BYTE),
                    MOBILE_NUM VARCHAR2(15 BYTE).
                    FILE CLOB
                )
            """,
            "name": "TICKET_GENERATION"
        },
        {
            "sql": """
                CREATE TABLE TICKET_CHECK (
                    ID VARCHAR2(250 BYTE),
                    EMP_ID VARCHAR2(255 BYTE),
                    FLAG NUMBER(38, 0)
                )
            """,
            "name": "TICKET_CHECK"
        },
        {
            "sql": """
                CREATE TABLE MAINTAIN_STATUS (
                    ID VARCHAR2(24 BYTE),
                    NAME VARCHAR2(255 BYTE),
                    STATUS VARCHAR2(1 BYTE)
                )
            """,
            "name": "MAINTAIN_STATUS"
        },
        {
            "sql": """
                CREATE TABLE DEPLOY_LOG (
                    MODEL_NAME VARCHAR2(255 BYTE),
                    TIMESTAMP TIMESTAMP(6),
                    STATUS VARCHAR2(1 BYTE),
                    ENVIRONMENT VARCHAR2(50 BYTE),
                    USER_NAME VARCHAR2(50 BYTE)
                )
            """,
            "name": "DEPLOY_LOG"
        },
        {
            "sql": """
                CREATE TABLE xSATION (
                    ID VARCHAR2(24 BYTE),
                    USER_ID VARCHAR2(50 BYTE),  
                    QUERY VARCHAR2(255 BYTE),
                    RESPONSE_TEXT VARCHAR2(4000 BYTE),
                    ADMIN_ACTION VARCHAR(10 BYTE),
                    ADMIN_ID VARCHAR2(50 BYTE),
                    USER_ACTION VARCHAR(10 BYTE),
                    MODEL_USED VARCHAR2(100 BYTE),
                    FEEDBACK_MSG VARCHAR2(255 BYTE),
                    TIMESTAMP TIMESTAMP,
                    METADATA CLOB
                )
            """,
            "name": "CONVERSATION"
        },
        {
            "sql": """
                CREATE TABLE TICKET_CHAT(
                    user_id VARCHAR2(10),
                    flag VARCHAR2(10),
                    msg VARCHAR2(255)
                )
            """,
            "name": "TICKET_CHAT"
        },
        {
            "sql": """
                CREATE TABLE UPLOADED_LLM_FILES (
                    file_id           VARCHAR2(100 BYTE),
                    file_name         VARCHAR2(255) NOT NULL,
                    file_format       VARCHAR2(50) NOT NULL,
                    file_size         VARCHAR2(255) NOT NULL,
                    upload_date       TIMESTAMP(6),
                    created_by        VARCHAR2(100) NOT NULL,
                    file_status       VARCHAR2(50) DEFAULT 'pending' NOT NULL,
                    file_path         VARCHAR2(4000) NOT NULL,
                    comments          VARCHAR2(1000),
                    last_updated      DATE DEFAULT SYSDATE
                )
            """,
            "name": "UPLOADED_LLM_FILES"
        },
    ]

    # Loop through the table creation queries
    for table in tables:
        try:
            cursor.execute(table["sql"])
            connection.commit()
            print(f"{table['name']} table created successfully.")
            event_logger.info(f"{table['name']} table created successfully.")
        except Exception as e:
            event_logger.error(f"Error creating {table['name']} table: {e}")

except Exception as e:
    event_logger.error(f"Database connection error: {e}")