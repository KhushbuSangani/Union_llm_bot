import os
from utils.logger import logger

from urllib.parse import urljoin
import requests
import json
from . import config
from time import sleep


event_logger = logger()

class RasaAPIWarapper:

    YAML_HEADER = {"Content-Type": "application/yaml"}
    JSON_HEADER = {"Content-Type": "application/json"}

    def train(self, data):

        status = False
        model_name = ""
        url = urljoin(config.BASE_URL, "model/train")
        
        retry_count = 3 

        for _ in range(retry_count):
            try:
                resp = requests.post(url, data=data, headers=self.YAML_HEADER,timeout=36000)
                event_logger.info(resp)
                if resp.status_code == 503:
                    event_logger.info("Received 503 Service Unavailable, retrying...")
                    sleep(5)  # Wait before retrying
                    continue
                elif resp.status_code == 204 or resp.status_code == 200:
                    model_name = resp.headers["filename"]
                    status = True
                    event_logger.info("Request successful:", resp.text)
                    break
                else:
                    event_logger.info(f"Unexpected status code: {resp.status_code}")
                    break
            except requests.exceptions.RequestException as e:
                event_logger.info(f"Request failed: {e}")
                break
      
        event_logger.info(status)
        event_logger.info(model_name) 
        return status, model_name

    def test(self):
        print("test")

    def replace_model(self, model_file):
        status = False
        url = urljoin(config.BASE_URL, "model")
        data = json.dumps({"model_file": "models/" + model_file})
        resp = requests.put(url, data=data, headers=self.JSON_HEADER)
        event_logger.info(resp)
        if resp.status_code == 204:
            status = True
        return status

    def replace_model_welcome(self, model_file):
        status = False
        config.PROD_URL = "http://127.0.0.1:6003"
        url = urljoin(config.PROD_URL, "model")
        data = json.dumps({"model_file": "prod_models/" + model_file})
        resp = requests.put(url, data=data, headers=self.JSON_HEADER)
        if resp.status_code == 204:
            status = True
        return status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return
