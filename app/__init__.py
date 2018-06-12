from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import config

app = Flask(__name__)
app.config.from_pyfile('../config.py')
db = SQLAlchemy(app)
migrate = Migrate(app, db)

from app import route, models, weixin, template_msg
