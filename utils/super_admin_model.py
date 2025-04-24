from utils.db_connector import execute_query
from datetime import datetime
import json


def fetch_all_user():
    """
    Fetch User List
    :return: User List(list)
    """
    user_list = execute_query(
        """SELECT * FROM admin_login WHERE status != '0' ORDER BY admin_id DESC""",
        opration="select",
    )
    return user_list


def insert_user(query_data):
    """
    Insert User
    :return: Insert User(list)
    """
    query_data = query_data.to_dict(flat=False)
    name = query_data.pop("name")[0]
    username = query_data.pop("username")[0]
    role = query_data.pop("role")[0]
    email = query_data.pop("email")[0]
    ct = datetime.now()
    ts = ct.timestamp()
    nlu_time = int(ts*1000)
    admin_id = str(nlu_time) + str(ts ^ (ts >> 3) ^ (ts >> 5))

    password = query_data.pop("password")[0]

    mydict = {
        "password": password,
        "role": role,
        "username": username,
        "email": email,
        "name": name,
        "admin_id": str(admin_id),
        "status": "1",
        "timestamp": datetime.utcnow().isoformat(),
    }
    insert_sql = """
                    INSERT INTO admin_login (
                        password, role, username, email, name, admin_id, status, timestamp
                    ) VALUES (
                        :password, :role, :username, :email, :name, :admin_id, :status, :timestamp
                    )
                """
    _id = execute_query(insert_sql, "insert", params=mydict)


def update_user(query_data):
    """
    Update user Role basis of admin id
    :return: User Role(list)
    """
    query_data = query_data.to_dict(flat=False)
    role = query_data.pop("role")[0]
    admin_id = query_data.pop("admin_id")[0]
    updated_values = {"role": role, "admin_id": admin_id}
    _id = execute_query(
        """UPDATE admin_login SET role = :role WHERE admin_id = :admin_id""",
        "update",
        params=updated_values,
    )
    return _id


def fetch_all_role():
    """
    Fetch Role List
    :return: User Role(list)
    """
    role_list = execute_query(
        """SELECT * FROM admin_role ORDER BY role_id DESC""", "select"
    )
    return role_list


def admin_role_access(access):
    """
    All role related to particular user
    :return: String of all role
    """
    access_role = ""
    for all_access in access:
        if access_role != "":
            add = access_role + " , "
        else:
            add = access_role
        if all_access == "1":
            access_role = add + "Add Intent"
        if all_access == "2":
            access_role = add + "Intent List"
        if all_access == "3":
            access_role = add + "Training Status"
        if all_access == "4":
            access_role = add + "Pending List"
        if all_access == "5":
            access_role = add + "Intent Mapping"
        if all_access == "6":
            access_role = add + "All Chats"
        if all_access == "7":
            access_role = add + "Testing"
    return access_role


def insert_role(query_data):
    """
    Insert User
    :return: Insert User(list)
    """
    query_data = query_data.to_dict(flat=False)
    name = query_data.pop("name")[0]
    access = query_data.pop("access[]")
    access_list = []
    for access_data in access:
        access_list.append(access_data)

    ct = datetime.now()
    ts = ct.timestamp()
    nlu_time = int(ts*1000)
    role_id = str(nlu_time) + str(ts ^ (ts >> 3) ^ (ts >> 5))
    mydict = {"role_id": role_id, "role_name": name, "access_list": access_list}
    query = """INSERT INTO admin_role (role_id, role_name, access_list) VALUES (:1, :2, :3)"""
    _id = execute_query(query, "insert", params=mydict)
    return _id


def update_role(query_data):
    """
    Update user Role basis of admin id
    :return: User Role(list)
    """
    query_data = query_data.to_dict(flat=False)
    role_id = query_data.pop("role_id")[0]
    access = query_data.pop("access[]")
    access_list = []
    for access_data in access:
        access_list.append(access_data)
    updated_values = {
        "access_list": json.dump(access_list),
        "role_id": role_id,
    }
    _id = execute_query(
        """UPDATE admin_role SET access_list = :access_list WHERE role_id = :role_id""",
        "update",
        params=updated_values,
    )
    return _id
