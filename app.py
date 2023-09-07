import json
import smtplib
from datetime import datetime
from email.message import EmailMessage

from flask import Flask, render_template, request, redirect, jsonify, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.exceptions import BadRequestKeyError

# init app
app = Flask(__name__)
# init db
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///temperatures.db'
db = SQLAlchemy(app)

# Configure the limiter rate for all routes
limiter = Limiter(get_remote_address, app=app,  default_limits=["5 per minute"])

app.config['SECRET_KEY'] = 'your_secret_key'
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)


class User(UserMixin):
    pass


@login_manager.user_loader
def load_user(user_id):
    user = User()
    user.id = user_id
    return user


@app.errorhandler(500)
def internal_server_error(e):
    send_email(e)
    return "Internal Server Error", 500


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


class Creds(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(15), nullable=False)
    pw = db.Column(db.String(25), nullable=False)


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


@app.route("/")
def root():
    return redirect(url_for("login"))


@app.route('/fermpi/')
@login_required
@limiter.limit("1 per second")  # custom call limit
def fermpi():  # put application's code here
    temps = Temperature.query.order_by(Temperature.timestamp.desc()).limit(10).all()
    set_temps = TempSet.query.first()
    return render_template('index.html', temps=temps, set_temps=set_temps)


# Route to get the parameters for fermentation from the server
@app.route('/fermpi/get-set-temp', methods=['GET'])
def get_set_temp():
    temp_set_value = TempSet.query.first()
    return f"{temp_set_value.temp_set},{temp_set_value.th_set},{temp_set_value.th_outer}".encode()


# Route to which the client posts its present fermentation temps to the server
@app.route('/fermpi/temp-client', methods=['POST'])
def temp_client():
    try:
        data = request.json
        temp = Temperature(temp_inner=data['temp_inner'], temp_outer=data['temp_outer'], temp_set=data['temp_set'])
        db.session.add(temp)
        db.session.commit()
    except Exception as e:
        send_email(str(e))
    return jsonify({'message': 'Temperature saved!'}), 200


# Route to update the parameters for fermentation in the server db
@app.route('/fermpi/update-set-temp', methods=['POST'])
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
        return redirect("/fermpi/")
    except Exception as e:
        send_email(e)
        "There was an issue updating the temps."


@app.route('/login', methods=['GET', 'POST'])
def login():
    # Replace with proper authentication
    creds = Creds.query.first()
    if request.form.get('user') == creds.user:
        if request.form.get('password') == creds.pw:
            user = User()
            user.id = 'your_id'
            login_user(user)
            return redirect(url_for('fermpi'))
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
    # in terminal, if port not open: flask run --host=0.0.0.0 --port=5000 --debug

# TODO: get it all to work on the server
# TODO: set file ownership on production server
