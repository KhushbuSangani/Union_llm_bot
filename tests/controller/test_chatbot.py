from app import app
from dotenv import load_dotenv
import os
from flask import url_for

load_dotenv()


def setSecretKey(flaskapp):
    flaskapp.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
    return flaskapp


def test_chatbot_dashboard():
    with app.test_client() as test_client:
        response = test_client.get("/chatbot")

        assert response.status_code == 302 or response.status_code == 200

        if response.status_code == 302:
            assert response.location == url_for(
                "auth.login", _external=True, _scheme="https"
            )


def test_chatbot_sign_out():
    flaskapp = setSecretKey(app)
    with flaskapp.test_client() as test_client:
        response = test_client.get("/chatbot/sign_out")
        assert response.status_code == 302 or response.status_code == 200


def test_chatbot_login():
    with app.test_client() as test_client:
        response = test_client.get("/chatbot/login")
        assert response.status_code == 302 or response.status_code == 200


def test_chatbot_admin_login():
    flaskapp = setSecretKey(app)
    with flaskapp.test_client() as test_client:
        # Without Form Data
        response = test_client.post("/chatbot/admin_login")
        assert response.status_code == 200

        # With Wrong Form Data
        response = test_client.post(
            "/chatbot/admin_login", data={"username": "test", "password": "test"}
        )
        assert response.status_code == 302
        response.location == url_for("chatbot.login", _external=True, _scheme="https")

        response = test_client.post(
            "/chatbot/admin_login",
            data={"username": os.getenv("username"), "password": os.getenv("password")},
        )
        assert response.status_code == 302
        assert response.location == url_for(
            "chatbot.dashboard", _external=True, _scheme="https"
        )
