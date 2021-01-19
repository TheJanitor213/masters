''' App.py Initialisation of Yoco API '''

from os import getenv
from datetime import datetime, timedelta
from flask import Flask, request, Blueprint
from zappa.asynchronous import task
from app.processing import processing

app = Flask(__name__)
app.register_blueprint(processing)
app.config.from_object('config')