from email.message import EmailMessage
from flask import Flask, render_template, request, redirect, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

import json
import smtplib

from werkzeug.exceptions import BadRequestKeyError

# from werkzeug.serving import run_simple

# init app
app = Flask(__name__)
# init db
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///temperatures.db'
db = SQLAlchemy(app)

# Configure the limiter rate for all routes
limiter = Limiter(get_remote_address, app=app,  default_limits=["5 per minute"])


# define db
class Temperature(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow())
    temp_inner = db.Column(db.Float, nullable=False)
    temp_outer = db.Column(db.Float, nullable=False)
    temp_set = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f"<New Temp.Record: {self.id}|{self.temp_inner}|{self.temp_outer}|{self.temp_set}"

    # create db in terminal (venc active)
    # new python session:
    # from app import app, db
    # app.app_context().push()
    # db.create_all()


class TempSet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    temp_set = db.Column(db.Float, nullable=False)
    th_set = db.Column(db.Float, nullable=False)
    th_outer = db.Column(db.Float, nullable=False)


def send_email(error):
    with open("./static/mail.json") as f:
        data = json.load(f)
    msg = EmailMessage()
    msg.set_content(f"Your Flask app on your server has crashed.\nHere is the error msg:\n\n"
                    f"{error}")
    msg['Subject'] = 'fermPi server app crashed'
    msg['From'] = data['from']
    msg['To'] = data['to']

    # Establish a connection to your SMTP server
    with smtplib.SMTP(data['smtp_server'], data['port']) as server:
        server.starttls()
        server.login(data['from'], data['password'])
        server.send_message(msg)


@app.errorhandler(500)
def internal_server_error(e):
    send_email(e)
    return "Internal Server Error", 500


@app.route('/brewpi/')
@limiter.limit("1 per second")  # custom call limit
def hello_world():  # put application's code here
    temps = Temperature.query.order_by(Temperature.timestamp.desc()).limit(10).all()

    # set init temps if db is empty
    if TempSet.query.count() == 0:
        init_temps = TempSet(temp_set=18, th_set=1, th_outer=5)

        try:
            db.session.add(init_temps)
            db.session.commit()
        except Exception as e:
            send_email(e)
            return f"There was an issue initializing the set_temps"

    set_temps = TempSet.query.first()
    return render_template('index.html', temps=temps, set_temps=set_temps)


# Route to which the client posts its present fermentation temps to the server
@app.route('/brewpi/temp-client', methods=['POST'])
def temp_client():
    data = request.json
    try:
        temp = Temperature(temp_inner=data['temp_inner'], temp_outer=data['temp_outer'], temp_set=data['temp_set'])
        db.session.add(temp)
        db.session.commit()
    except Exception as e:
        send_email(str(e))
    return jsonify({'message': 'Temperature saved!'}), 200


# Route to get the parameters for fermentation from the server
@app.route('/brewpi/get-set-temp', methods=['GET'])
def get_set_temp():
    temp_set_value = TempSet.query.first()
    # return jsonify({'temp_set': temp_set_value.temp_set}), 200
    return f"{temp_set_value.temp_set},{temp_set_value.th_set},{temp_set_value.th_outer}".encode()


# Route to update the parameters for fermentation in the server db
@app.route('/brewpi/update-set-temp', methods=['POST'])
def update_set_temp():
    try:
        update_temps = TempSet.query.first()
        update_temps.temp_set = request.form['temp_set']
        update_temps.th_set = request.form['th_set']
        update_temps.th_outer = request.form['th_outer']
    except BadRequestKeyError as e:
        send_email(e)
        print("Getting Temps form db failed. ")

    try:
        db.session.commit()
        return redirect("/brewpi/")
    except Exception as e:
        send_email(e)
        "There was an issue updating the temps."



if __name__ == '__main__':
    # in terminal, if port not open: flask run --host=0.0.0.0 --port=5000 --debug
    # run_simple('0.0.0.0', port=5000, application=app)
    db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)

# TODO: get it all to work on the server
# TODO: set file ownership on production server

