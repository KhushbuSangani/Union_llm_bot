from app import app
from dotenv import load_dotenv
import os
from flask import url_for

load_dotenv()


def setSecretKey(flaskapp):
    flaskapp.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
    return flaskapp


def test_login():
    with app.test_client() as test_client:
        response = test_client.get("/login")
        assert response.status_code == 200


def test_admin_login():
    flaskapp = setSecretKey(app)
    with flaskapp.test_client() as test_client:
        # Without Form Data
        response = test_client.post("/admin_login")
        assert response.status_code == 200

        # With Wrong Form Data
        response = test_client.post(
            "/admin_login", data={"username": "test", "password": "test"}
        )
        assert response.status_code == 302
        response.location == url_for("auth.login", _external=True, _scheme="https")

        # With Correct Form Data
        response = test_client.post(
            "/admin_login",
            data={"username": os.getenv("username"), "password": os.getenv("password")},
        )
        assert response.status_code == 302
        assert response.location == url_for(
            "dashboard", _external=True, _scheme="https"
        )

        # With Correct Form Data - Admin
        response = test_client.post(
            "/admin_login",
            data={
                "username": os.getenv("admin_username"),
                "password": os.getenv("admin_password"),
            },
        )
        assert response.status_code == 302
        assert response.location == url_for(
            "admin.dashboard", _external=True, _scheme="https"
        )

        # With Correct Form Data - Author
        response = test_client.post(
            "/admin_login",
            data={
                "username": os.getenv("author_username"),
                "password": os.getenv("author_password"),
            },
        )
        assert response.status_code == 302
        assert response.location == url_for(
            "admin.author_dashboard", _external=True, _scheme="https"
        )

        # With Correct Form Data - Approver
        response = test_client.post(
            "/admin_login",
            data={
                "username": os.getenv("approver_username"),
                "password": os.getenv("approver_password"),
            },
        )
        assert response.status_code == 302
        assert response.location == url_for(
            "admin.approver_dashboard", _external=True, _scheme="https"
        )


def test_sign_out():
    flaskapp = setSecretKey(app)
    with flaskapp.test_client() as test_client:
        response = test_client.get("/sign_out")
        assert response.status_code == 302 or response.status_code == 200
