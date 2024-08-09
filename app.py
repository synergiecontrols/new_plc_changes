import atexit
from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from forms import RegistrationForm, LoginForm, Csrf
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import snap7
import time
from datetime import datetime, time as t, timedelta
import pandas as pd
from flask_socketio import SocketIO
import threading
import logging
import config
from sqlalchemy import func, or_, and_
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    current_user,
    login_required,
)
from functools import wraps
from flask import abort
from sqlalchemy.sql import text
import openpyxl
import os
from flask_wtf.csrf import CSRFProtect
from apscheduler.schedulers.background import BackgroundScheduler

from datetime import datetime


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = (
    "postgresql://postgres:synergie1234@localhost/synergie_change"
)
secret_key = os.urandom(24)
app.config["SECRET_KEY"] = secret_key
csrf = CSRFProtect(app)
csrf.init_app(app)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
socketio = SocketIO(app)


# Initialize Flask-Login ------------------------------------------------------------------------------
login_manager = LoginManager(app)
login_manager.login_view = "login"  # Set the login view for unauthorized users
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "info"


@login_manager.user_loader  # to store ueser id in session
def load_user(user_id):
    return User.query.get(int(user_id))


# jinja template filter ------------------------------------------------------------------------


@app.template_filter("format_datetime")
def format_datetime(value):
    if isinstance(value, datetime):
        return (
            value.strftime("%Y-%m-%d %H:%M:%S") + f".{value.microsecond // 10000:02d}"
        )
    return value


# Register the filter
app.jinja_env.filters["format_datetime"] = format_datetime


# models.py -------------------------------------------------------------------------------------------------------------------

class Data_count(db.Model):
    __tablename__ = "data_count"
    id = db.Column(db.Integer, primary_key=True)
    billet_count = db.Column(db.Integer, nullable=False)
    energy_consumption = db.Column(db.Integer, nullable=False)
    fuel_consumption = db.Column(db.Integer, nullable=False)
    time_stamp = db.Column(db.DateTime, default=datetime.utcnow)


class Cobble_count(db.Model):
    __tablename__ = "cobble_count"
    id = db.Column(db.Integer, primary_key=True)
    cobble_count = db.Column(db.Integer, nullable=False)
    time_stamp = db.Column(db.DateTime, default=datetime.utcnow)


class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    department = db.Column(db.String(100), nullable=False)


class Event(db.Model):
    __tablename__ = "events"
    id = db.Column(db.Integer, primary_key=True)
    event_start = db.Column(db.DateTime, nullable=False)
    event_stop = db.Column(db.DateTime, nullable=False)
    event_name = db.Column(db.String(100), nullable=True)
    reason = db.Column(db.String(300), nullable=True)
    department = db.Column(db.String(100), nullable=True)
    approved_events = db.Column(db.Boolean, default=False)
    event_area = db.Column(db.String(100), nullable=True)
    time_stamp = db.Column(db.DateTime, default=datetime.utcnow)
    time_delay = db.Column(db.Float, nullable=True)
    is_submitted = db.Column(db.Boolean, default=False)
    remark = db.Column(db.String(500), nullable=True)

    submitted_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    rejected_by_id_l1 = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    rejected_by_id_l2 = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    rejected_by_id_l3 = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    rejected_by_id_l4 = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    approved_by_id_l1 = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    approved_by_id_l2 = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    approved_by_id_l3 = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    approved_by_id_l4 = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    assigned_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    submitted_by = db.relationship(
        "User", foreign_keys=[submitted_by_id], backref="submitted_events"
    )
    rejected_by_l1 = db.relationship(
        "User", foreign_keys=[rejected_by_id_l1], backref="rejected_events_l1"
    )
    rejected_by_l2 = db.relationship(
        "User", foreign_keys=[rejected_by_id_l2], backref="rejected_events_l2"
    )
    rejected_by_l3 = db.relationship(
        "User", foreign_keys=[rejected_by_id_l3], backref="rejected_events_l3"
    )
    rejected_by_l4 = db.relationship(
        "User", foreign_keys=[rejected_by_id_l4], backref="rejected_events_l4"
    )
    approved_by_l1 = db.relationship(
        "User", foreign_keys=[approved_by_id_l1], backref="approved_events_l1"
    )
    approved_by_l2 = db.relationship(
        "User", foreign_keys=[approved_by_id_l2], backref="approved_events_l2"
    )
    approved_by_l3 = db.relationship(
        "User", foreign_keys=[approved_by_id_l3], backref="approved_events_l3"
    )
    approved_by_l4 = db.relationship(
        "User", foreign_keys=[approved_by_id_l4], backref="approved_events_l4"
    )
    assigned_by = db.relationship(
        "User", foreign_keys=[assigned_by_id], backref="assigned_events"
    )

    notifications = db.relationship("Notification", back_populates="event")


class IdleTime(db.Model):
    __tablename__ = "idle_times"
    id = db.Column(db.Integer, primary_key=True)
    idle_time = db.Column(db.Float, nullable=False)
    time_stamp = db.Column(db.DateTime, default=datetime.utcnow)


class Notification(db.Model):
    __tablename__ = "notification"
    id = db.Column(db.Integer, primary_key=True)
    notification_msg = db.Column(db.String(300), nullable=True)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)
    time_stamp = db.Column(db.DateTime, default=datetime.utcnow)
    event = db.relationship("Event", back_populates="notifications")


class Daily_data_count(db.Model):
    __tablename__ = "daily_data_count"
    id = db.Column(db.Integer, primary_key=True)
    daily_billet_count = db.Column(db.Integer, nullable=False)
    daily_cobble_count = db.Column(db.Integer, nullable=False)
    daily_energy_consumption = db.Column(db.Integer, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)


# Logger setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# PLC Configuration ------------------------------------------------------------
PLC_IP = config.PLC_IP
RACK_NO = config.RACK_NO
SLOT_NO = config.SLOT_NO
DB_NUMBER = config.DB_NUMBER
NUM_BYTES_TO_READ = config.NUM_BYTES_TO_READ


# Global variables -------------------------------------------------------------
billet_count = 0
cobble_count = 0
down_time = 0
shut_down_time = 0
idle_time = 0
time_delay = 0
event_name = ""
area = ""
machine_running = False
cobble_produced = False
billet_produced = False
billet_is_rolling = False
idle_time_start_flag = False
idle_time_start = 0
idle_time_stop = 0
event_logged = False

# PLC Data --------------------------------------------------------------------

plc_data_processed = {
    "billet_count": 0,
    "cobble_count": 0,
    "down_time": 0,
    "shut_down_time": 0,
    "idle_time": 0,
    "event_start": datetime.now(),
    "event_stop": datetime.now(),
    "time_delay": 0,
    "energy_consumption": 0,
    "fuel_consumption": 0,
    "event_name": "",
    "event_area": "",
    "department": "",
    "reason": "",
}


# services -------------------------------------------------------------------


def add_data_count(data):

    try:
        if data["billet_count"] <= 0:
            logger.info("Billet count is zero or negative, data not added")
            return None

        data_count = Data_count(
            billet_count=data["billet_count"],
            energy_consumption=data["energy_consumption"],
            fuel_consumption=data["fuel_consumption"],
            time_stamp=datetime.now(),
        )
        db.session.add(data_count)
        db.session.commit()

        logger.info("Data added successfully")

    except Exception as e:
        db.session.rollback()
        logger.info(f"Error occurred while adding data count: {e}")
        return None
    

def add_cobble_count(data):

    try:
        if data["cobble_count"] <= 0:
            logger.info("cobble count is zero or negative, data not added")
            return None

        cobble_count = Cobble_count(

            cobble_count=data["cobble_count"],
            time_stamp=datetime.now(),
        )
        db.session.add(cobble_count)
        db.session.commit()

        logger.info("Cobble added successfully")

    except Exception as e:
        db.session.rollback()
        logger.info(f"Error occurred while adding data count: {e}")
        return None



def add_event(data):
    global last_event_id
    try:
        logger.info("event adding................")

        event = Event(
            event_start=data["event_start"],
            event_stop=data["event_stop"],
            event_name=data["event_name"],
            reason=data.get("reason", ""),
            department=data.get("department", ""),
            approved_events=data.get("approved_events", False),
            event_area=data.get("event_area", ""),
            time_delay=data.get("time_delay"),
            time_stamp=datetime.now(),

        )
        logger.info(f"event-------------------------------:{event.event_area}")
        db.session.add(event)
        db.session.commit()

        last_event_id = event.id

        logger.info(f"event_id =--------------------------------- {last_event_id}")
    except Exception as e:
        db.session.rollback()
        logger.info(f"Error occurred while adding event: {e}")
        return None


def add_idle_time(data):
    try:
        idle_time_entry = IdleTime(
            idle_time=data["idle_time"],
            time_stamp=datetime.now(),
        )
        db.session.add(idle_time_entry)
        db.session.commit()
        logger.info(f"idle_time:{ data["idle_time"]}")
    except Exception as e:
        db.session.rollback()
        logger.info(f"Error occurred while adding idle time: {e}")
        return None


def add_notification(event_id, msg):
    try:
        notification = Notification(notification_msg=msg, event_id=event_id)

        db.session.add(notification)
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        logger.info(f"Error occurred while adding idle time: {e}")


def query_max_values(start_time, end_time):
    total_billet_count = (
        db.session.execute(
            text(
                """SELECT billet_count AS total_billet_count
                FROM data_count
                WHERE time_stamp >= :start_time AND time_stamp < :end_time
                ORDER BY time_stamp DESC
                LIMIT 1;"""
            ),
            {"start_time": start_time, "end_time": end_time},
        ).scalar()
        or 0
    )

    # Fetch the latest cobble count within the given time slot
    total_cobble_count = (
        db.session.execute(
            text(
                """SELECT cobble_count AS total_cobble_count
                FROM cobble_count
                WHERE time_stamp >= :start_time AND time_stamp < :end_time
                ORDER BY time_stamp DESC
                LIMIT 1;"""
            ),
            {"start_time": start_time, "end_time": end_time},
        ).scalar()
        or 0
    )

    # Fetch the latest energy consumption within the given time slot
    total_energy_consume = (
        db.session.execute(
            text(
                """SELECT energy_consumption AS total_energy_consume
                FROM data_count
                WHERE time_stamp >= :start_time AND time_stamp < :end_time
                ORDER BY time_stamp DESC
                LIMIT 1;"""
            ),
            {"start_time": start_time, "end_time": end_time},
        ).scalar()
        or 0
    )

    return total_billet_count, total_cobble_count, total_energy_consume


def add_data_to_daily_data_count():
    with app.app_context():
        now = datetime.now()

        # Define the start and end times for Shift A (8 AM to 8 PM today)
        start_time_a = datetime.combine(now.date(), t(8, 0, 0))
        end_time_a = datetime.combine(now.date(), t(20, 0, 0))

        # Define the start and end times for Shift B (8 PM today to 8 AM tomorrow)
        start_time_b = end_time_a
        end_time_b = start_time_b + timedelta(hours=12)

        # Function to query the max count and energy

        # Check if the current time is close to the end of Shift A (e.g., 7:56 PM)
        if now.time() >= t(7, 56) and now.time() < t(8, 0):
            total_billet_count_a, total_cobble_count_a, total_energy_consume_a = (
                query_max_values(start_time_a, end_time_a)
            )
            daily_data_count_a = Daily_data_count(
                daily_billet_count=total_billet_count_a,
                daily_cobble_count=total_cobble_count_a,
                daily_energy_consumption=total_energy_consume_a,
                date=now.date(),
            )
            db.session.add(daily_data_count_a)
            db.session.commit()

        # Check if the current time is close to the end of Shift B (e.g., 7:56 AM)
        elif now.time() >= t(7, 56) and now.time() < t(8, 0):
            total_billet_count_b, total_cobble_count_b, total_energy_consume_b = (
                query_max_values(start_time_b, end_time_b)
            )
            daily_data_count_b = Daily_data_count(
                daily_billet_count=total_billet_count_b,
                daily_cobble_count=total_cobble_count_b,
                daily_energy_consumption=total_energy_consume_b,
                date=(
                    now.date()
                    if now.time() < t(8, 0)
                    else now.date() + timedelta(days=1)
                ),
            )
            db.session.add(daily_data_count_b)
            db.session.commit()


# decoratores -------------------------------- decoratores


def role_required(*roles):

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Please login to view this page")
                return redirect(url_for("login", next=request.url))
            elif current_user.role not in roles:
                flash("You are  not authorized user to access this page")
                return redirect(url_for("index"))
            return f(*args, **kwargs)

        return decorated_function

    return decorator


# functionalities ----------------------------------------------------------------------


@app.route("/submit_event", methods=["POST"])
@login_required
@role_required("operator")
def submit_event():
    global last_event_id
    form = Csrf()  # Initialize the CSRF form
    if form.validate_on_submit():  # Ensure CSRF validation
        try:
            data = request.form
            department = data.get("department")
            reason = data.get("reason")
            reason_input = data.get("reasonInput")
            event_area = data.get("eventarea")

            with app.app_context():
                # Update the last event with the provided reason and department
                if last_event_id:
                    event = db.session.get(Event, last_event_id)
                    event.department = department
                    event.reason = reason_input if reason == "Other" else reason
                    event.event_area = event_area
                    event.submitted_by_id = current_user.id
                    event.is_submitted = True  # Mark the event as submitted
                    db.session.commit()
                    flash("event submitted succesfully")
                    msg = f"event {last_event_id} submitted succesfully by  {current_user.name}-{current_user.role}"
                    add_notification(last_event_id, msg)

            return redirect("/")
        except Exception as e:
            logger.error(
                f"Error occurred while updating event with department and reason: {e}"
            )
            return jsonify({"status": "error", "message": str(e)}), 500
    else:
        logger.error("CSRF token is missing or invalid.")
        return (
            jsonify(
                {"status": "error", "message": "CSRF token is missing or invalid."}
            ),
            400,
        )


@app.route("/unsubmitted_events")
@login_required
@role_required("operator", "admin", "planthead")
def unsubmitted_events():
    with app.app_context():
        events = Event.query.filter_by(is_submitted=False).all()
        return render_template("unsubmitted_events.html", events=events)


@app.route("/submit_event_form/<int:event_id>")
@login_required
@role_required("operator")
def submit_event_form(event_id):
    form = Csrf()  # for csrf token
    event = Event.query.get_or_404(event_id)
    app.logger.debug(f"Event: {event}")
    return render_template("submit_event_form.html", event=event, form=form)


@app.route("/submit_event/<int:event_id>", methods=["POST"])  ## missed event submission
@login_required
@role_required("operator")
def submit_event_with_id(event_id):
    try:

        data = request.form
        department = data.get("department")
        reason = data.get("reason")
        reason_input = data.get("reasonInput", "")
        event_area = data.get("eventarea")

        # Validate department and reason
        if not department or not reason:
            raise ValueError("Department and reason are required fields.")

        with app.app_context():
            # Update the event with the provided reason and department
            event = Event.query.get_or_404(event_id)
            event.department = department
            event.reason = reason_input if reason == "Other" else reason
            event.event_area = event_area
            event.submitted_by_id = current_user.id
            event.is_submitted = True  # Mark the event as submitted
            db.session.commit()
            flash("Event submitted succesfully")
            msg = f"event {event_id} submitted succesfully by  {current_user.name}-{current_user.role}"
            add_notification(event_id, msg)

        # Redirect to the appropriate route after submitting the event
        return redirect(url_for("unsubmitted_events"))

    except Exception as e:
        logger.error(
            f"Error occurred while updating event with department and reason: {e}"
        )
        flash("department and reason are mandatory fields")
        return redirect(url_for("unsubmitted_events"))


# approved or unapproved events -----------------------------------


@app.route("/unapproved_events")
@login_required
@role_required(
    "engineerarea1",
    "engineerarea2",
    "engineerarea3",
    "electrichead",
    "operationalhead",
    "mechanicalhead",
    "planthead",
    "admin",
    "operator",
)
def unapproved_events():
    with app.app_context():
        form = Csrf()
        user_department = current_user.department

        if current_user.role in ["planthead", "admin", "operator"]:
            events = Event.query.filter(
                and_(
                    Event.approved_events == False,
                    Event.is_submitted == True,
                    Event.rejected_by_id_l3 == None,
                    Event.rejected_by_id_l4 == None,
                    Event.rejected_by_id_l2 == None,
                    Event.rejected_by_id_l1 == None,
                )
            ).all()

        elif current_user.role in ["electrichead", "operationalhead", "mechanicalhead"]:
            events = Event.query.filter(
                and_(
                    Event.approved_events == False,
                    Event.is_submitted == True,
                    Event.rejected_by_id_l3 == None,
                    Event.rejected_by_id_l4 == None,
                    Event.rejected_by_id_l2 == None,
                    Event.rejected_by_id_l1 == None,
                    Event.department == user_department,
                )
            ).all()
        elif current_user.role in ["engineerarea1", "engineerarea2", "engineerarea3"]:
            area_filter = {
                "engineerarea1": "CH1",
                "engineerarea2": "CH2",
                "engineerarea3": "CB",
            }.get(current_user.role)

            events = Event.query.filter(
                and_(
                    Event.approved_events == False,
                    Event.is_submitted == True,
                    Event.rejected_by_id_l3 == None,
                    Event.rejected_by_id_l4 == None,
                    Event.rejected_by_id_l2 == None,
                    Event.rejected_by_id_l1 == None,
                    Event.department == user_department,
                    Event.event_area == area_filter,
                )
            ).all()

        return render_template("unapproved_events.html", events=events, form=form)


@app.route("/handle_event_action<int:event_id>", methods=["POST"])
@login_required
@role_required(
    "engineerarea1",
    "engineerarea2",
    "engineerarea3",
    "electrichead",
    "operationalhead",
    "mechanicalhead",
    "planthead",
    "admin",
)
def handle_event_action(event_id):
    event = Event.query.get_or_404(event_id)
    current_role = current_user.role
    action = request.form.get("action")
    remark = request.form.get("remark", "") + "-" + f"{current_user.name}"

    # Check if admin has already taken action
    if event.approved_by_id_l4 is not None or event.rejected_by_id_l4 is not None:
        flash("Event action already taken by higher authority")
        return redirect(url_for("unapproved_events"))

    # Check if planthead has already taken action (excluding admin)
    if (event.approved_by_id_l3 is not None or event.rejected_by_id_l3 is not None) and current_role != "admin":
        flash("Event action already taken by higher authority")
        return redirect(url_for("unapproved_events"))

    if current_role in ["engineerarea1", "engineerarea2", "engineerarea3"]:
        if action == "approve":
            if current_role == "engineerarea1" and event.event_area == "CH1":
                event.approved_events = True
                event.approved_by_id_l1 = current_user.id
            elif current_role == "engineerarea2" and event.event_area == "CH2":
                event.approved_events = True
                event.approved_by_id_l1 = current_user.id
            elif current_role == "engineerarea3" and event.event_area == "CB":
                event.approved_events = True
                event.approved_by_id_l1 = current_user.id
            else:
                flash("Event is not from your area")
                return redirect(url_for("unapproved_events"))
        elif action == "reject":
            if current_role == "engineerarea1" and event.event_area == "CH1":
                event.approved_events = False
                event.rejected_by_id_l1 = current_user.id
            elif current_role == "engineerarea2" and event.event_area == "CH2":
                event.approved_events = False
                event.rejected_by_id_l1 = current_user.id
            elif current_role == "engineerarea3" and event.event_area == "CB":
                event.approved_events = False
                event.rejected_by_id_l1 = current_user.id
            else:
                flash("Event is not from your area")
                return redirect(url_for("unapproved_events"))
    elif current_role in ["electrichead", "operationalhead", "mechanicalhead"]:
        if action == "approve":
            event.approved_events = True
            event.approved_by_id_l2 = current_user.id
        elif action == "reject":
            event.approved_events = False
            event.rejected_by_id_l2 = current_user.id
    elif current_role == "planthead":
        if action == "approve":
            event.approved_events = True
            event.approved_by_id_l3 = current_user.id
        elif action == "reject":
            event.approved_events = False
            event.rejected_by_id_l3 = current_user.id
    elif current_role == "admin":
        if action == "approve":
            event.approved_events = True
            event.approved_by_id_l4 = current_user.id
        elif action == "reject":
            event.approved_events = False
            event.rejected_by_id_l4 = current_user.id

    event.remark = remark
    db.session.commit()
    msg = f"event {event_id} {event.event_name} {action}ed by {current_user.name}-:-{current_user.role}"
    add_notification(event_id, msg)
    flash(f"Event {action}ed successfully")
    return redirect(url_for("unapproved_events"))



@app.route("/rejected_events")
@login_required
@role_required(
    "electrichead",
    "operationalhead",
    "mechanicalhead",
    "operator",
    "planthead",
    "admin",
)
def rejected_events():
    with app.app_context():
        form = Csrf()
        user_department = current_user.department

        if current_user.role == "admin":
            events = Event.query.filter(
                and_(
                    Event.approved_events == False,
                    Event.is_submitted == True,
                    or_(
                        Event.rejected_by_id_l4 != None,
                        Event.rejected_by_id_l3 != None,
                        Event.rejected_by_id_l2 != None,
                        Event.rejected_by_id_l1 != None,
                    ),
                )
            ).all()
        elif current_user.role == "planthead":
            events = Event.query.filter(
                and_(
                    Event.approved_events == False,
                    Event.is_submitted == True,
                    or_(
                        Event.rejected_by_id_l4 != None,
                        Event.rejected_by_id_l3 != None,
                        Event.rejected_by_id_l2 != None,
                        Event.rejected_by_id_l1 != None,
                    ),
                )
            ).all()
        elif current_user.role in ["electrichead", "operationalhead", "mechanicalhead"]:
            events = Event.query.filter(
                and_(
                    Event.approved_events == False,
                    Event.is_submitted == True,
                    Event.department == user_department,
                    or_(
                        Event.rejected_by_id_l4 != None,
                        Event.rejected_by_id_l3 != None,
                        Event.rejected_by_id_l2 != None,
                        Event.rejected_by_id_l1 != None,
                    ),
                )
            ).all()
        else:
            events = Event.query.filter(
                and_(
                    Event.approved_events == False,
                    Event.is_submitted == True,
                    Event.department == user_department,
                    or_(
                        Event.rejected_by_id_l4 != None,
                        Event.rejected_by_id_l3 != None,
                        Event.rejected_by_id_l2 != None,
                        Event.rejected_by_id_l1 != None,
                    ),
                )
            ).all()

        return render_template("rejectedevents.html", events=events, form=form)


@app.route("/approved_events")
@login_required
@role_required(
    "electrichead",
    "operator",
    "operationalhead",
    "mechanicalhead",
    "planthead",
    "admin",
)
def approved_events():
    with app.app_context():
        form = Csrf()
        user_department = current_user.department

        if current_user.role in ["admin", "operator"]:
            events = Event.query.filter(
                and_(
                    Event.approved_events == True,
                    Event.is_submitted == True,
                    or_(
                        Event.approved_by_id_l4 != None,
                        Event.approved_by_id_l3 != None,
                        Event.approved_by_id_l2 != None,
                        Event.approved_by_id_l1 != None,
                    ),
                )
            ).all()
        elif current_user.role == "planthead":
            events = Event.query.filter(
                and_(
                    Event.approved_events == True,
                    Event.is_submitted == True,
                    or_(
                        Event.approved_by_id_l4 != None,
                        Event.approved_by_id_l3 != None,
                        Event.approved_by_id_l2 != None,
                        Event.approved_by_id_l1 != None,
                    ),
                )
            ).all()
        elif current_user.role in ["electrichead", "operationalhead", "mechanicalhead"]:
            events = Event.query.filter(
                and_(
                    Event.approved_events == True,
                    Event.is_submitted == True,
                    Event.department == user_department,
                    or_(
                        Event.approved_by_id_l4 != None,
                        Event.approved_by_id_l3 != None,
                        Event.approved_by_id_l2 != None,
                        Event.approved_by_id_l1 != None,
                    ),
                )
            ).all()
        else:
            events = Event.query.filter(
                and_(
                    Event.approved_events == True,
                    Event.is_submitted == True,
                    Event.department == user_department,
                    or_(
                        Event.approved_by_id_l4 != None,
                        Event.approved_by_id_l3 != None,
                        Event.approved_by_id_l2 != None,
                        Event.approved_by_id_l1 != None,
                    ),
                )
            ).all()

        return render_template("approvedevents.html", events=events, form=form)


@login_required
@role_required(
    "engineerarea1",
    "operator",
    "engineerarea2",
    "engineerarea3",
    "electrichead",
    "operationalhead",
    "mechanicalhead",
    "planthead",
    "admin",
)
def get_events_rejected_by_self():
    with app.app_context():
        user_id = current_user.id
        rejected_events = Event.query.filter(
            (Event.rejected_by_id_l1 == user_id)
            | (Event.rejected_by_id_l2 == user_id)
            | (Event.rejected_by_id_l3 == user_id)
            | (Event.rejected_by_id_l4 == user_id)
        ).all()
        return rejected_events


@login_required
@role_required(
    "engineerarea1",
    "operator",
    "engineerarea2",
    "engineerarea3",
    "electrichead",
    "operationalhead",
    "mechanicalhead",
    "planthead",
    "admin",
)
def get_events_approved_by_self():
    with app.app_context():
        user_id = current_user.id
        approved_events = Event.query.filter(
            (Event.approved_by_id_l1 == user_id)
            | (Event.approved_by_id_l2 == user_id)
            | (Event.approved_by_id_l3 == user_id)
            | (Event.approved_by_id_l4 == user_id)
        ).all()
        return approved_events


# Define function assign event to other department if department is not correct--------------------------------------------
@app.route("/assign_to_other_department/<int:event_id>", methods=["POST"])
def assign_to_other_department(event_id):
    new_department = request.form.get("new_department")
    if not new_department:
        flash("Please change department", "error")
        return redirect(
            url_for("some_view_function")
        )  # Replace 'some_view_function' with the relevant view function

    try:
        event = Event.query.filter_by(id=event_id).first()
        if event:
            event.assigned_by_id = current_user.id
            event.department = new_department
            event.rejected_by_id_l1 = None
            event.rejected_by_id_l2 = None
            event.rejected_by_id_l3 = None
            event.rejected_by_id_l4 = None
            event.approved_by_id_l1 = None
            event.approved_by_id_l2 = None
            event.approved_by_id_l3 = None
            event.approved_by_id_l4 = None
            db.session.commit()
            flash("Event reassigned successfully", "success")
            msg = f"event {last_event_id} reassigned  succesfully by {current_user.name}-{current_user.role}"
            add_notification(last_event_id, msg)
        else:
            flash("Event not found", "error")
    except Exception as e:
        db.session.rollback()
        flash(f"An error occurred while reassigning the event: {str(e)}", "error")

    return redirect(url_for("rejected_events"))


# --------------------------------- logic ------------------------------------------------------------plc listner---------------------------------------------------


def listen_events(plc_data_processed):
    event_data = {
        "event_name": plc_data_processed.get("event_name", "N/A"),
        "event_start": plc_data_processed.get("event_start", "N/A").strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "event_stop": plc_data_processed.get("event_stop", "N/A").strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "time_delay": plc_data_processed.get("time_delay", "N/A"),
        "event_area": plc_data_processed.get("event_area", "N/A"),
    }
    logger.info(f"Event data: {event_data}")
    socketio.emit("new_event", event_data)


def machine_status(int_data):
    global machine_running, time_delay, cobble_produced, idle_time_stop, event_logged

    try:
        with app.app_context():  # Ensure this code runs within the application context
            if int_data[0] == 2:  # If machine stops
                if (
                    machine_running and not event_logged
                ):  # If machine was running before and event not logged
                    if cobble_produced:
                        plc_data_processed["event_stop"] = datetime.now()
                        time_delay = (
                            plc_data_processed["event_stop"]
                            - plc_data_processed["event_start"]
                        ).total_seconds()
                        plc_data_processed["event_name"] = (
                            f"machine stopped due to {plc_data_processed['event_name']}"
                        )
                        if int_data[2] == 4:
                            plc_data_processed["event_area"] = "CH1"
                        elif int_data[2] == 5:
                            plc_data_processed["event_area"] = "CH2"
                        elif int_data[2] == 6:
                            plc_data_processed["event_area"] = "CB"
                        plc_data_processed["time_delay"] = time_delay
                        add_event(plc_data_processed)
                        listen_events(plc_data_processed)
                        plc_data_processed["event_stop"] = datetime.now()
                        plc_data_processed["event_start"] = datetime.now()
                        plc_data_processed["event_name"] = ""
                        plc_data_processed["time_delay"] = 0
                    if int_data[0] == 1 and int_data[5] == 0 and idle_time_start_flag:
                        idle_time_stop = int_data[-1]
                        idle_time_func()
                        event_logged = True
                    machine_running = False
                    plc_data_processed["event_start"] = datetime.now()
                    plc_data_processed["event_name"] = "Machine stopped"
                    plc_data_processed["event_area"] = ""
                    event_logged = True

            elif int_data[0] == 1:  # If machine starts
                if not machine_running and not event_logged:
                    machine_running = True
                    plc_data_processed["event_stop"] = datetime.now()
                    time_delay = (
                        plc_data_processed["event_stop"]
                        - plc_data_processed["event_start"]
                    ).total_seconds()
                    plc_data_processed["event_name"] = plc_data_processed["event_name"]
                    plc_data_processed["time_delay"] = time_delay
                    add_event(plc_data_processed)
                    listen_events(plc_data_processed)
                    plc_data_processed["event_stop"] = datetime.now()
                    plc_data_processed["event_start"] = datetime.now()
                    plc_data_processed["event_name"] = ""
                    plc_data_processed["time_delay"] = 0
                    event_logged = True
    except Exception as e:
        logger.error(f"Machine status error: {e}")


def cobble_status(int_data):
    global cobble_produced
    try:
        with app.app_context():  # Ensure this code runs within the application context
            if machine_running and int_data[1] == 3 and not cobble_produced:
                if int_data[2] == 4 and not cobble_produced:
                    cobble_produced = True
                    plc_data_processed["cobble_count"] += 1
                    plc_data_processed["event_name"] = "Cobble detected"
                    plc_data_processed["event_start"] = datetime.now()
                    add_cobble_count(plc_data_processed)

                elif int_data[3] == 5 and not cobble_produced:
                    cobble_produced = True
                    plc_data_processed["cobble_count"] += 1
                    plc_data_processed["event_name"] = "Cobble detected"
                    plc_data_processed["event_start"] = datetime.now()
                    add_cobble_count(plc_data_processed)

                elif int_data[4] == 6 and not cobble_produced:
                    cobble_produced = True
                    plc_data_processed["cobble_count"] += 1
                    plc_data_processed["event_name"] = "Cobble detected"
                    plc_data_processed["event_start"] = datetime.now()
                    add_cobble_count(plc_data_processed)


            elif not machine_running:
                cobble_produced = False

            if machine_running and cobble_produced and int_data[1] == 0:
                plc_data_processed["event_stop"] = datetime.now()
                time_delay = (
                    plc_data_processed["event_stop"] - plc_data_processed["event_start"]
                ).total_seconds()
                plc_data_processed["event_name"] = plc_data_processed["event_name"]
                plc_data_processed["time_delay"] = time_delay
                cobble_produced = False

                plc_data_processed["energy_consumption"] = int_data[6]
                plc_data_processed["fuel_consumption"] = int_data[7]

                add_event(plc_data_processed)
                listen_events(plc_data_processed)
                # add_data_count(plc_data_processed)
                plc_data_processed["event_stop"] = datetime.now()
                plc_data_processed["event_start"] = datetime.now()
                plc_data_processed["event_name"] = ""
                plc_data_processed["time_delay"] = 0
    except Exception as e:
        logger.error(f"Error in cobble status: {e}")


def billet_production_count(int_data):
    global billet_is_rolling, idle_time_start, idle_time_start_flag, idle_time_stop
    try:
        with app.app_context():
            cobble_status(int_data)  # Uncomment if you need cobble status processing here
            if int_data[5] == 7:
                    if not billet_is_rolling:
                        billet_is_rolling = True
                    if idle_time_start_flag:
                        idle_time_stop = int_data[-1]
                        idle_time_func()

                    # Fetch the latest billet count from the database using the text function
                    last_billet_count_result = db.session.execute(
                        text(
                            "SELECT billet_count FROM public.data_count ORDER BY time_stamp DESC LIMIT 1"
                        )
                    ).scalar()  # Fetch the single value

                    last_billet_count = (
                        last_billet_count_result
                        if last_billet_count_result is not None
                        else 0
                    )
                    logger.info(f"Last Billet Count from DB:{last_billet_count}")

                    last_cobble_count_result = db.session.execute(
                        text(
                            "SELECT cobble_count FROM public.cobble_count ORDER BY time_stamp DESC LIMIT 1"
                        )
                    ).scalar()  # Fetch the single value

                    last_cobble_count = (
                        last_cobble_count_result
                        if last_cobble_count_result is not None
                        else 0
                    )
                    logger.info(f"Last cobble Count from DB:{last_cobble_count}")

                    plc_data_processed["billet_count"] = int_data[8]

                    cobble_status(
                        int_data
                    )  # Uncomment if you need cobble status processing here

                    logger.info(
                        f"Current Billet Count from PLC:{plc_data_processed["billet_count"]}"
                    )

                    if (
                        int_data[1] == 0
                        and int_data[5] == 7
                        and int_data[8]
                        >= (
                            plc_data_processed["billet_count"]
                            - plc_data_processed["cobble_count"]
                        )
                    ):
                        if last_billet_count != (
                            plc_data_processed["billet_count"]
                            - plc_data_processed["cobble_count"]
                        ):
                            plc_data_processed["billet_count"] = (
                                plc_data_processed["billet_count"]
                                - plc_data_processed["cobble_count"]
                            )
                            plc_data_processed["energy_consumption"] = int_data[6]
                            plc_data_processed["fuel_consumption"] = int_data[7]
                            billet_is_rolling = False
                            add_data_count(plc_data_processed)
                            logger.info(
                                f"New Billet Count added to DB:{ plc_data_processed["billet_count"]}"
                            )
                    if last_cobble_count < plc_data_processed["cobble_count"]:
                        plc_data_processed["billet_count"] = (
                            plc_data_processed["billet_count"]
                            - plc_data_processed["cobble_count"]
                        )
                        add_data_count(plc_data_processed)
                        logger.info(
                            f"New cobble Count added to DB: {plc_data_processed["cobble_count"]}"
                        )

            elif (
                int_data[0] == 1
                and int_data[1] == 0
                and int_data[5] == 0
                and not idle_time_start_flag
            ):
                idle_time_start = int_data[-1]
                idle_time_start_flag = True
                billet_is_rolling = False
                logger.info("Idle Time Start: %s", idle_time_start)
            
    except Exception as e:
        logger.error(f"Error in billet production count: {e}")


def idle_time_func():
    global idle_time_start, idle_time_start_flag, idle_time_stop
    try:
        with app.app_context():
            idle_time_stop = datetime.strptime(idle_time_stop, "%Y-%m-%d %H:%M:%S")
            idle_time_start = datetime.strptime(idle_time_start, "%Y-%m-%d %H:%M:%S")
            plc_data_processed["idle_time"] = (
                idle_time_stop - idle_time_start
            ).total_seconds()
            add_idle_time(plc_data_processed)
            plc_data_processed["idle_time"] = 0
            idle_time_start_flag = False
    except Exception as e:
        logger.error(f"Idle time function error: {e}")


def read_plc_and_write_to_excel(plc):
    global event_logged
    while True:
        try:
            if plc.get_connected():
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                data = plc.read_area(
                    snap7.types.Areas.DB, DB_NUMBER, 0, NUM_BYTES_TO_READ
                )

                start_stop = snap7.util.get_int(data, 0)
                cobble = snap7.util.get_int(data, 2)
                cobble_sh1 = snap7.util.get_int(data, 4)
                cobble_sh2 = snap7.util.get_int(data, 6)
                cobble_cb = snap7.util.get_int(data, 8)
                billet_rolling = snap7.util.get_int(data, 10)
                energy_cons = snap7.util.get_real(data, 12)
                fuel_cons = snap7.util.get_real(data, 16)
                billet_count = snap7.util.get_int(data, 20)

                int_data = [
                    start_stop,
                    cobble,
                    cobble_sh1,
                    cobble_sh2,
                    cobble_cb,
                    billet_rolling,
                    energy_cons,
                    fuel_cons,
                    billet_count,
                    timestamp,
                ]

                logger.info(f"Data read from DB2: {int_data}")
                machine_status(int_data)
                billet_production_count(int_data)
                event_logged = False

            else:
                logger.warning("Connection to PLC lost.")
                break
        except snap7.exceptions.Snap7Exception as e:
            logger.error(f"An error occurred: {e}")

        time.sleep(0.5)


# --------------------------------- logic -----------------------------------------------------------------------------

# download excel sheet for each page


def download_excel_file(
    time_slots, billet_data, cobble_data, energy_consumption_data, day_or_hr
):
    data = {
        f"Time Slot {day_or_hr}": time_slots,
        "Billet": billet_data,
        "Cobble": cobble_data,
        "Energy Consumption": energy_consumption_data,
    }

    df = pd.DataFrame(data)

    total_count = {
        f"Time Slot {day_or_hr}": "Total Count",
        "Billet": df["Billet"].sum(),
        "Cobble": df["Cobble"].sum(),
        "Energy Consumption": df["Energy Consumption"].sum(),
    }

    # Create a DataFrame for the total count
    total_count_df = pd.DataFrame([total_count])

    # Concatenate the total count to the original DataFrame
    df = pd.concat([df, total_count_df], ignore_index=True)

    file_path = f"count_data_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.xlsx"
    df.to_excel(file_path, index=False, engine="openpyxl")

    return file_path


@app.route("/download/<page_type>", methods=["POST"])
@login_required
def download(page_type):
    global daily_data_dict, daily_data_dict_month
    now = datetime.now()
    date = now.date()

    if page_type == "today":
        count_data = fetch_hourly_data(date)
        time_slots = list(count_data["cobble"].keys())
        billet_data = list(count_data["billet"].values())
        cobble_data = list(count_data["cobble"].values())
        energy_consumption_data = list(count_data["energy"].values())

        file_path = download_excel_file(
            time_slots, billet_data, cobble_data, energy_consumption_data, "(Hrs)"
        )
    elif page_type == "yesterday":
        date -= timedelta(days=1)
        count_data = fetch_hourly_data(date)
        time_slots = list(count_data["cobble"].keys())
        billet_data = list(count_data["billet"].values())
        cobble_data = list(count_data["cobble"].values())
        energy_consumption_data = list(count_data["energy"].values())

        file_path = download_excel_file(
            time_slots, billet_data, cobble_data, energy_consumption_data, "(Hrs)"
        )
    elif page_type == "week":
        count_data = daily_data_dict
        time_slots = list(count_data["date"])
        billet_data = list(count_data["billet"])
        cobble_data = list(count_data["cobble"])
        energy_consumption_data = list(count_data["energy"])

        file_path = download_excel_file(
            time_slots, billet_data, cobble_data, energy_consumption_data, "(Days)"
        )
    elif page_type == "month":
        count_data = daily_data_dict_month
        time_slots = list(count_data["date"])
        billet_data = list(count_data["billet"])
        cobble_data = list(count_data["cobble"])
        energy_consumption_data = list(count_data["energy"])

        file_path = download_excel_file(
            time_slots, billet_data, cobble_data, energy_consumption_data, "(Days)"
        )

    else:
        return "Invalid page type", 400

    return send_file(file_path, as_attachment=True)


# Function to fetch hourly data for a given date----------------------------------------------
def fetch_hourly_data(date):
    hourly_data = {
        "cobble": {},
        "billet": {},
        "energy": {},
    }
    total_idle_time = list()

    # Ensure you are within the application context
    with app.app_context():
        # Determine start and end dates based on input date
        if date == datetime.now().date():
            # Today's date: 8 AM to tomorrow's 8 AM
            start_time = datetime.combine(date, datetime.min.time()) + timedelta(hours=8)
            end_time = start_time + timedelta(days=1)
        else:
            # Yesterday's date: 8 AM to today's 8 AM
            start_time = datetime.combine(date, datetime.min.time()) + timedelta(hours=8)
            end_time = start_time + timedelta(days=1)

        # Initialize cobble count with zeros for each hour range
        current_time = start_time
        while current_time < end_time:
            start_hour = current_time.hour
            end_hour = (start_hour + 1) % 24
            hour_range = f"{start_hour}-{end_hour}"
            hourly_data["cobble"][hour_range] = 0
            current_time += timedelta(hours=1)

        # Loop through each hour range from start_time to end_time
        while start_time < end_time:
            start_hour = start_time.hour
            end_hour = (start_hour + 1) % 24

            # Calculate start and end timestamps for the current hour range
            start_timestamp = start_time
            end_timestamp = start_time + timedelta(hours=1)

            # Query data from the database
            filtered_data = (
                Data_count.query.filter(Data_count.time_stamp >= start_timestamp)
                .filter(Data_count.time_stamp < end_timestamp)
                .order_by(Data_count.time_stamp.asc())
                .all()
            )

            # Query data to fetch idle time
            total_idle = (
                db.session.query(func.sum(IdleTime.idle_time))
                .filter(IdleTime.time_stamp >= start_timestamp)
                .filter(IdleTime.time_stamp < end_timestamp)
                .scalar()
            )

            total_idle_time.append(total_idle)

            # Extract relevant counts for billet and energy
            first_billet_count = filtered_data[0].billet_count if filtered_data else 0
            last_billet_count = filtered_data[-1].billet_count if filtered_data else 0

            first_energy_consumption = filtered_data[0].energy_consumption if filtered_data else 0
            last_energy_consumption = filtered_data[-1].energy_consumption if filtered_data else 0

            # Count cobbles within the hour range
            cobble_count = (
                db.session.query(func.count(Cobble_count.id))
                .filter(Cobble_count.time_stamp >= start_timestamp)
                .filter(Cobble_count.time_stamp < end_timestamp)
                .scalar()
            )

            # Store results in hourly_data dictionaries
            hour_range = f"{start_hour}-{end_hour}"
            hourly_data["billet"][hour_range] = (first_billet_count, last_billet_count)
            hourly_data["energy"][hour_range] = (first_energy_consumption, last_energy_consumption)
            hourly_data["cobble"][hour_range] = cobble_count

            # Move to the next hour
            start_time += timedelta(hours=1)

        # Calculate differences for billet and energy counts

        for key, data_dict in hourly_data.items():
            if key != "cobble":  # Cobble data is already the count for the hour
                for hour_range, counts in data_dict.items():
                    if isinstance(counts, tuple) and len(counts) == 2:
                        diff = counts[1] - counts[0]

                        if counts[1] != counts[0] and diff != 0 and counts[0] != 0:
                            diff += 1

                        data_dict[hour_range] = diff
                
        total_idle_time_sum = 0
        for value in total_idle_time:
            if value is None:
                continue
            else:
                total_idle_time_sum += value

        total_idle_time_sum = total_idle_time_sum / 3600
        total_idle_time_sum = round(total_idle_time_sum, 2)

    hourly_data["total_idle_time"] = total_idle_time_sum

    return hourly_data





def fetch_data(page_type):
    try:
        # Ensure you are within the Flask application context
        with app.app_context():
            # Get the current date
            current_date = datetime.now()

            if page_type == "month":
                # Calculate start and end dates for the current month
                start_date = datetime(current_date.year, current_date.month, 1)
                if current_date.month == 12:
                    next_month = datetime(current_date.year + 1, 1, 1)
                else:
                    next_month = datetime(current_date.year, current_date.month + 1, 1)
                end_date = next_month - timedelta(days=1)

                # Query to fetch daily data within the current month
                daily_data = (
                    Daily_data_count.query.filter(Daily_data_count.date >= start_date)
                    .filter(Daily_data_count.date <= end_date)
                    .order_by(Daily_data_count.date.asc())
                    .all()
                )

                total_idle = (
                    db.session.query(func.sum(IdleTime.idle_time))
                    .filter(IdleTime.time_stamp >= start_date)
                    .filter(IdleTime.time_stamp < next_month)
                    .scalar()
                )

                # Create a dictionary to hold the data with all dates in the month
                data_dict = {
                    start_date
                    + timedelta(days=i): {
                        "daily_billet_count": 0,
                        "daily_cobble_count": 0,
                        "daily_energy_consumption": 0,
                    }
                    for i in range((end_date - start_date).days + 1)
                }
            elif page_type == "week":
                # Calculate start and end dates for the last 7 days excluding today
                end_of_week = current_date - timedelta(days=1)
                start_of_week = end_of_week - timedelta(days=6)
                year = start_of_week.year
                month = start_of_week.month
                day = start_of_week.day

                start_of_week = datetime(year, month, day)

                # Query to fetch daily data within the last 7 days excluding today
                daily_data = (
                    Daily_data_count.query.filter(
                        Daily_data_count.date >= start_of_week
                    )
                    .filter(Daily_data_count.date <= end_of_week)
                    .order_by(Daily_data_count.date.asc())
                    .all()
                )

                total_idle = (
                    db.session.query(func.sum(IdleTime.idle_time))
                    .filter(IdleTime.time_stamp >= start_of_week)
                    .filter(IdleTime.time_stamp <= end_of_week)
                    .scalar()
                )

                # Create a dictionary to hold the data with all dates in the last 7 days
                data_dict = {
                    start_of_week
                    + timedelta(days=i): {
                        "daily_billet_count": 0,
                        "daily_cobble_count": 0,
                        "daily_energy_consumption": 0,
                    }
                    for i in range((end_of_week - start_of_week).days + 1)
                }
            else:
                raise ValueError("Invalid page_type. Expected 'month' or 'week'.")

            # Check if total_idle is None and set to 0 if it is
            if total_idle is None:
                total_idle = 0

            total_idle = total_idle / 3600  # Convert to hours
            total_idle = round(total_idle, 2)

            # Populate the dictionary with actual data
            for data in daily_data:
                if data.date in data_dict:
                    data_dict[data.date]["daily_billet_count"] = (
                        data.daily_billet_count or 0
                    )
                    data_dict[data.date]["daily_cobble_count"] = (
                        data.daily_cobble_count or 0
                    )
                    data_dict[data.date]["daily_energy_consumption"] = (
                        data.daily_energy_consumption or 0
                    )


            # Calculate totals
            total_billet_count = sum(
                item["daily_billet_count"] for item in data_dict.values()
            )
            total_cobble_count = sum(
                item["daily_cobble_count"] for item in data_dict.values()
            )
            total_energy_consumption = sum(
                item["daily_energy_consumption"] for item in data_dict.values()
            )

            totals = {
                "total_billet_count": total_billet_count,
                "total_cobble_count": total_cobble_count,
                "total_energy_consumption": total_energy_consumption,
            }

            # Convert the dictionary back to a list of tuples for easier handling
            data_list = [
                (
                    date,
                    values["daily_billet_count"],
                    values["daily_cobble_count"],
                    values["daily_energy_consumption"],
                )
                for date, values in data_dict.items()
            ]

            return data_list, totals, total_idle

    except Exception as e:
        logger.error(f"Error fetching data: {e}")
        return [], {}, 0.0  # Return default empty values


def cal_efficiency(billet, total_billet):
    if total_billet == 0:
        return 0  # Avoid division by zero
    efficiency = (billet / total_billet) * 100

    return round(efficiency, 0)


### routes-----------------------------------------------------------------------------------------------------


@app.route("/")
@login_required
def index():
    form = Csrf()  # Assuming Csrf is your CSRF protection form
    now = datetime.now()

    # Define the start time (for demo, adjust as needed)
    start_time = datetime.combine(now.date(), t(8, 0, 0))

    # Calculate the end time
    end_time = start_time + timedelta(hours=24)

    # Fetching data
    running_billet_count, running_cobble, running_energy_consume = query_max_values(
        start_time, end_time
    )

    efficiency = cal_efficiency(
        running_billet_count, (running_billet_count + running_cobble)
    )

    # Fetch hourly data for today
    date = datetime.now().date()
    hourly_data_today = fetch_hourly_data(date)

    # Prepare data for Chart.js and table
    cobble_hour_ranges = list(hourly_data_today["cobble"].keys())
    cobble_count = list(hourly_data_today["cobble"].values())
    billet_hour_ranges = list(hourly_data_today["billet"].keys())
    billet_count = list(hourly_data_today["billet"].values())
    energy_hour_ranges = list(hourly_data_today["energy"].keys())
    energy_count = list(hourly_data_today["energy"].values())
    idle_time = hourly_data_today["total_idle_time"]

    return render_template(
        "/todayproduction/todayproduction.html",
        form=form,
        running_energy_consume=running_energy_consume,
        running_cobble=running_cobble,
        running_billet_count=running_billet_count,
        cobble_hour_ranges=cobble_hour_ranges,
        cobble_count=cobble_count,
        billet_hour_ranges=billet_hour_ranges,
        billet_count=billet_count,
        energy_hour_ranges=energy_hour_ranges,
        energy_count=energy_count,
        idle_time=idle_time,
        efficiency=efficiency,
    )


@app.route("/shifta")
@login_required
def todayshifta():
    form = Csrf()  # for csrf token ref
    with app.app_context():
        now = datetime.now()

        # Define the start time
        start_time = datetime.combine(now.date(), t(8, 0, 0))

        # Calculate the end time after 24 hours
        end_time = start_time + timedelta(hours=12)

        # Function to query the max count and energy

        date = datetime.now().date()
        hourly_data_today = fetch_hourly_data(date)

        running_billet_count, running_cobble, running_energy_consume = query_max_values(
            start_time, end_time
        )
        efficiency = cal_efficiency(
            running_billet_count, (running_billet_count + running_cobble)
        )
        # Prepare data for Chart.js and table
        cobble_hour_ranges = list(hourly_data_today["cobble"].keys())
        cobble_count = list(hourly_data_today["cobble"].values())
        billet_hour_ranges = list(hourly_data_today["billet"].keys())
        billet_count = list(hourly_data_today["billet"].values())
        energy_hour_ranges = list(hourly_data_today["energy"].keys())
        energy_count = list(hourly_data_today["energy"].values())
        idle_time = hourly_data_today["total_idle_time"]

    return render_template(
        "/todayproduction/shiftAtoday.html",
        form=form,
        running_energy_consume=running_energy_consume,
        running_cobble=running_cobble,
        running_billet_count=running_billet_count,
        cobble_hour_ranges=cobble_hour_ranges,
        cobble_count=cobble_count,
        billet_hour_ranges=billet_hour_ranges,
        billet_count=billet_count,
        energy_hour_ranges=energy_hour_ranges,
        energy_count=energy_count,
        idle_time=idle_time,
        efficiency=efficiency,
    )


@app.route("/shiftb")
@login_required
def todayshiftb():
    form = Csrf()  # for csrf token ref
    with app.app_context():
        now = datetime.now()

        # fetch shiftA total production 
        start_time_a =  datetime.combine(now.date(), t(8, 0, 0))

        # Calculate the end time after 24 hours
        end_time_a = start_time_a + timedelta(hours=12)

        # Function to query the max count and energy

        running_billet_count_a, running_cobble_a, running_energy_consume_a = query_max_values(
            start_time_a, end_time_a
        )






        # Define the start time
        start_time_b = datetime.combine(now.date() , t(20, 0, 0))

        # Calculate the end time after 12 hours
        end_time_b =start_time_a + timedelta(hours=12)

        # end_time = start_time + timedelta(hours=4)
        # Function to query the max count and energy

        date = datetime.now().date() - timedelta(days=1)
        hourly_data_yesterday = fetch_hourly_data(date)

        running_billet_count_b, running_cobble_b, running_energy_consume_b = query_max_values(
            start_time_b, end_time_b
        )

        # Calculate differences and apply the condition
        running_billet_count = running_billet_count_b - running_billet_count_a if running_billet_count_b - running_billet_count_a > 0 else 0
        running_cobble = running_cobble_b - running_cobble_a if running_cobble_b - running_cobble_a > 0 else 0
        running_energy_consume = running_energy_consume_b - running_energy_consume_a if running_energy_consume_b - running_energy_consume_a > 0 else 0



        efficiency = cal_efficiency(
            running_billet_count, (running_billet_count + running_cobble)
        )
        date = datetime.now().date()
        hourly_data_today = fetch_hourly_data(date)

        # Prepare data for Chart.js and table
        cobble_hour_ranges = list(hourly_data_today["cobble"].keys())
        cobble_count = list(hourly_data_today["cobble"].values())
        billet_hour_ranges = list(hourly_data_today["billet"].keys())
        billet_count = list(hourly_data_today["billet"].values())
        energy_hour_ranges = list(hourly_data_today["energy"].keys())
        energy_count = list(hourly_data_today["energy"].values())
        idle_time = hourly_data_today["total_idle_time"]

    return render_template(
        "/todayproduction/shiftBtoday.html",
        form=form,
        running_energy_consume=running_energy_consume,
        running_cobble=running_cobble,
        running_billet_count=running_billet_count,
        cobble_hour_ranges=cobble_hour_ranges,
        cobble_count=cobble_count,
        billet_hour_ranges=billet_hour_ranges,
        billet_count=billet_count,
        energy_hour_ranges=energy_hour_ranges,
        energy_count=energy_count,
        idle_time=idle_time,
        efficiency = efficiency 
    )


@app.route("/yesterday")
@login_required
def yesterday():
    form = Csrf()  # for csrf token ref
    with app.app_context():
        now = datetime.now()

        # Define the start time
        start_time = datetime.combine(now.date() - timedelta(days=1), t(8, 0, 0))

        # Calculate the end time after 24 hours
        end_time = start_time + timedelta(hours=24)

        # Function to query the max count and energy

        date = datetime.now().date() - timedelta(days=1)
        hourly_data_yesterday = fetch_hourly_data(date)

        running_billet_count, running_cobble, running_energy_consume = query_max_values(
            start_time, end_time
        )

        efficiency = cal_efficiency(
            running_billet_count, (running_billet_count + running_cobble)
        )

        cobble_hour_ranges = list(hourly_data_yesterday["cobble"].keys())
        cobble_count = list(hourly_data_yesterday["cobble"].values())
        billet_hour_ranges = list(hourly_data_yesterday["billet"].keys())
        billet_count = list(hourly_data_yesterday["billet"].values())
        energy_hour_ranges = list(hourly_data_yesterday["energy"].keys())
        energy_count = list(hourly_data_yesterday["energy"].values())
        idle_time = hourly_data_yesterday["total_idle_time"]

    return render_template(
        "yesterdayproduction/yesterday.html",
        form=form,
        running_energy_consume=running_energy_consume,
        running_cobble=running_cobble,
        running_billet_count=running_billet_count,
        cobble_hour_ranges=cobble_hour_ranges,
        cobble_count=cobble_count,
        billet_hour_ranges=billet_hour_ranges,
        billet_count=billet_count,
        energy_hour_ranges=energy_hour_ranges,
        energy_count=energy_count,
        idle_time=idle_time,
        efficiency=efficiency,
    )


@app.route("/yesterdayshifta")
@login_required
def yesterdayshifta():
    form = Csrf()  # for csrf token ref
    with app.app_context():
        now = datetime.now()

        # Define the start time
        start_time = datetime.combine(now.date() - timedelta(days=1), t(8, 0, 0))

        # Calculate the end time after 24 hours
        end_time = start_time + timedelta(hours=12)

        # Function to query the max count and energy

        date = datetime.now().date() - timedelta(days=1)
        hourly_data_yesterday = fetch_hourly_data(date)

        running_billet_count, running_cobble, running_energy_consume = query_max_values(
            start_time, end_time
        )
        efficiency = cal_efficiency(
            running_billet_count, (running_billet_count + running_cobble)
        )

        cobble_hour_ranges = list(hourly_data_yesterday["cobble"].keys())
        cobble_count = list(hourly_data_yesterday["cobble"].values())
        billet_hour_ranges = list(hourly_data_yesterday["billet"].keys())
        billet_count = list(hourly_data_yesterday["billet"].values())
        energy_hour_ranges = list(hourly_data_yesterday["energy"].keys())
        energy_count = list(hourly_data_yesterday["energy"].values())
        idle_time = hourly_data_yesterday["total_idle_time"]
    return render_template(
        "yesterdayproduction/yesterdayshifta.html",
        form=form,
        running_energy_consume=running_energy_consume,
        running_cobble=running_cobble,
        running_billet_count=running_billet_count,
        cobble_hour_ranges=cobble_hour_ranges,
        cobble_count=cobble_count,
        billet_hour_ranges=billet_hour_ranges,
        billet_count=billet_count,
        energy_hour_ranges=energy_hour_ranges,
        energy_count=energy_count,
        idle_time=idle_time,
        efficiency=efficiency,
    )


@app.route("/yesterdayshiftb")
@login_required
def yesterdayshiftb():
    form = Csrf()  # for csrf token ref
    with app.app_context():
        now = datetime.now()

        # fetch shiftA total production 
        start_time_a = datetime.combine(now.date() - timedelta(days=1), t(8, 0, 0))

        # Calculate the end time after 24 hours
        end_time_a = start_time_a + timedelta(hours=12)

        # Function to query the max count and energy

        running_billet_count_a, running_cobble_a, running_energy_consume_a = query_max_values(
            start_time_a, end_time_a
        )






        # Define the start time
        start_time_b = datetime.combine(now.date() - timedelta(hours=24), t(20, 0, 0))

        # Calculate the end time after 12 hours
        end_time_b = datetime.combine(now.date(), t(8, 0, 0))

        # end_time = start_time + timedelta(hours=4)
        # Function to query the max count and energy

        date = datetime.now().date() - timedelta(days=1)
        hourly_data_yesterday = fetch_hourly_data(date)

        running_billet_count_b, running_cobble_b, running_energy_consume_b = query_max_values(
            start_time_b, end_time_b
        )

        # Calculate differences and apply the condition
        running_billet_count = running_billet_count_b - running_billet_count_a if running_billet_count_b - running_billet_count_a > 0 else 0
        running_cobble = running_cobble_b - running_cobble_a if running_cobble_b - running_cobble_a > 0 else 0
        running_energy_consume = running_energy_consume_b - running_energy_consume_a if running_energy_consume_b - running_energy_consume_a > 0 else 0




        efficiency = cal_efficiency(
            running_billet_count, (running_billet_count + running_cobble)
        )

        cobble_hour_ranges = list(hourly_data_yesterday["cobble"].keys())
        cobble_count = list(hourly_data_yesterday["cobble"].values())
        billet_hour_ranges = list(hourly_data_yesterday["billet"].keys())
        billet_count = list(hourly_data_yesterday["billet"].values())
        energy_hour_ranges = list(hourly_data_yesterday["energy"].keys())
        energy_count = list(hourly_data_yesterday["energy"].values())
        idle_time = hourly_data_yesterday["total_idle_time"]

    return render_template(
        "yesterdayproduction/yesterdayshiftb.html",
        form=form,
        running_energy_consume=running_energy_consume,
        running_cobble=running_cobble,
        running_billet_count=running_billet_count,
        cobble_hour_ranges=cobble_hour_ranges,
        cobble_count=cobble_count,
        billet_hour_ranges=billet_hour_ranges,
        billet_count=billet_count,
        energy_hour_ranges=energy_hour_ranges,
        energy_count=energy_count,
        idle_time=idle_time,
        efficiency=efficiency,
    )


@app.route("/weeklyproduction")
@login_required
def weeklyproduction():
    global daily_data_dict
    form = Csrf()  # for csrf token ref
    # Get the current date
    daily_data_dict = {}
    current_date = datetime.now()
    end_date = current_date - timedelta(days=1)
    start_date = end_date - timedelta(days=6)

    dates = [
        (start_date + timedelta(days=i)).day
        for i in range((end_date - start_date).days + 1)
    ]

    daily_data, weekly_totals, total_idle_week = fetch_data("week")

    efficiency = cal_efficiency(
        weekly_totals["total_billet_count"],
        (weekly_totals["total_billet_count"] + weekly_totals["total_cobble_count"]),
    )

    # Check if daily_data is empty and handle accordingly
    if not daily_data:
        flash("No data available for the selected period.", "warning")
        daily_data = [(date, 0, 0, 0) for date in dates]

    form = Csrf()  # for csrf token ref

    # Initialize lists to hold daily data for billet, cobble, and energy
    daily_data_billet = []
    daily_data_cobble = []
    daily_data_energy = []

    # Extract data for each day
    for data in daily_data:
        daily_data_billet.append(data[1])
        daily_data_cobble.append(data[2])
        daily_data_energy.append(data[3])

    daily_data_dict = {
        "date": dates,
        "cobble": daily_data_cobble,
        "billet": daily_data_billet,
        "energy": daily_data_energy,
    }

    return render_template(
        "/weeklyproduction/weeklyproduction.html",
        form=form,
        daily_data=daily_data,
        weekly_totals=weekly_totals,
        dates=dates,
        daily_data_billet=daily_data_billet,
        daily_data_cobble=daily_data_cobble,
        daily_data_energy=daily_data_energy,
        total_idle_week=total_idle_week,
        efficiency=efficiency,
    )


@app.route("/monthlyproduction")
@login_required
def monthlyproduction():
    global daily_data_dict_month
    # Get the current date
    current_date = datetime.now()

    # Calculate start and end dates for the current month
    start_date = datetime(current_date.year, current_date.month, 1)
    if current_date.month == 12:
        next_month = datetime(current_date.year + 1, 1, 1)
    else:
        next_month = datetime(current_date.year, current_date.month + 1, 1)
    end_date = next_month - timedelta(days=1)

    # Create an array of dates for the current month represented as day numbers
    dates = [
        (start_date + timedelta(days=i)).day
        for i in range((end_date - start_date).days + 1)
    ]

    # Fetch daily data and monthly totals
    daily_data, monthly_totals, total_idle_month = fetch_data("month")
    form = Csrf()  # for csrf token ref
    efficiency = cal_efficiency(
        monthly_totals["total_billet_count"],
        (monthly_totals["total_billet_count"] + monthly_totals["total_cobble_count"]),
    )
    # Initialize lists to hold daily data for billet, cobble, and energy
    daily_data_billet = []
    daily_data_cobble = []
    daily_data_energy = []

    # Extract data for each day
    for data in daily_data:
        daily_data_billet.append(data[1])
        daily_data_cobble.append(data[2])
        daily_data_energy.append(data[3])

    daily_data_dict_month = {
        "date": dates,
        "cobble": daily_data_cobble,
        "billet": daily_data_billet,
        "energy": daily_data_energy,
    }

    # Render the template with the data
    return render_template(
        "/monthlyproduction/monthlyproduction.html",
        form=form,
        daily_data=daily_data,
        monthly_totals=monthly_totals,
        dates=dates,
        daily_data_billet=daily_data_billet,
        daily_data_cobble=daily_data_cobble,
        daily_data_energy=daily_data_energy,
        total_idle_month=total_idle_month,
        efficiency=efficiency,
    )


@app.route("/setting")
@login_required
def setting():
    return render_template("setting.html")


# excel for delay report-----------------------------------
@app.route("/download_delay_report", methods=["POST"])
@login_required
def delay_report_excel():
    def create_delay_excel_report():
        report = get_delayreport()

        columns = report.keys()
        df = pd.DataFrame(report.fetchall(), columns=columns)

        file_path = "delay_report.xlsx"
        df.to_excel(file_path, index=False)

        return file_path

    file_path = create_delay_excel_report()

    return send_file(file_path, as_attachment=True)


# setting delay report function -------------------------------------------------------------------


def get_delayreport():
    report = db.session.execute(
        text(
            """select e.event_name,e.event_start,e.event_stop ,e.event_area,
                                     e.time_delay,e.reason,e.department from public.events  as e where e.department is not null and
                                       e.reason is not null and e.approved_events ='true' 
                                     AND e.event_start >= date_trunc('day', now() - interval '1 day') 
                                    AND e.event_start < date_trunc('day', now());  

                                     """
        )
    )
    return report


# setting delay report function -------------------------------------------------------------------


@app.route("/delayreport")
@login_required
def delayreport():
    # add_data_to_daily_data_count()
    form = Csrf()  # for csrf token ref

    report = get_delayreport()

    return render_template("/delayreports/delayreport.html", form=form, report=report)


@app.route("/delayreportOperation")
@login_required
def delayreportOperation():
    form = Csrf()  # for csrf token ref
    report = get_delayreport()

    return render_template(
        "/delayreports/delayreportOperation.html", form=form, report=report
    )


@app.route("/delaymechanical")
@login_required
def delaymechanical():
    form = Csrf()  # for csrf token ref
    report = get_delayreport()

    return render_template(
        "/delayreports/delaymechanical.html", form=form, report=report
    )


@app.route("/delaytechnical")
@login_required
def delaytechnical():
    form = Csrf()  # for csrf token ref
    report = get_delayreport()

    return render_template(
        "/delayreports/delaytechnical.html", form=form, report=report
    )


@app.route("/delayother")
@login_required
def delayother():
    form = Csrf()  # for csrf token ref
    report = get_delayreport()

    return render_template("/delayreports/delayother.html", form=form, report=report)


# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------


@app.route("/working")
@login_required
def working():
    return render_template("working.html")


# user ------------------------------------------------------------------


@app.route("/userprofile")
@login_required
@role_required(
    "electrichead",
    "operator",
    "operationalhead",
    "mechanicalhead",
    "planthead",
    "admin",
    "engineerarea1",
    "engineerarea2",
    "engineerarea3",
)
def userprofile():
    approved_events_by_self = get_events_approved_by_self()
    rejected_events_by_self = get_events_rejected_by_self()

    return render_template(
        "profilepage.html",
        user=current_user,
        approved_events_by_self=approved_events_by_self,
        rejected_events_by_self=rejected_events_by_self,
    )


# user login and registration  -------------------------------------------------------------------------


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            flash(f"WELCOME {current_user.name} , Log in Successful!!!", "success")
            return redirect(url_for("index"))
        else:
            flash("Login Unsuccessful. Please check email and password", "danger")
    return render_template("user/login.html", form=form)


@app.route("/logout")
@login_required
def logout():
    app.logger.info(f"User {current_user.id} is logging out")
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(
            form.password.data, method="pbkdf2:sha256"
        )
        new_user = User(
            email=form.email.data,
            name=form.name.data,
            password=hashed_password,
            role="user",
            department=form.department.data,
        )
        email = form.email.data
        user = User.query.filter_by(email=email).first()
        if user:
            flash("User with this email id already present", "error")
        else:
            db.session.add(new_user)
            db.session.commit()
            flash("You have successfully Created new User!", "success")
            return redirect(url_for("usermanagement"))

    return render_template("user/registration.html", form=form)


# -----------admin  functionality -----------------------------------------------------------------------------------------------------------


@app.route("/admin")
@login_required
@role_required("admin")
def admin():
    form = Csrf()
    now = datetime.now()

    data_list, week_totals, total_idle = fetch_data("week")
    data_list, month_totals, total_idle = fetch_data("month")

    todays_count = {
        "billet_today": "",
        "cobble_today": "",
        "energy_today": "",
    }

    yesterdays_count = {
        "billet_yesterday": "",
        "cobble_yesterday": "",
        "energy_yesterday": "",
    }

    start_time_today = datetime.combine(now.date(), t(8, 0, 0))
    end_time_today = start_time_today + timedelta(hours=24)
    running_billet_count_today, running_cobble_today, running_energy_consume_today = (
        query_max_values(start_time_today, end_time_today)
    )

    todays_count["billet_today"] = running_billet_count_today
    todays_count["cobble_today"] = running_cobble_today
    todays_count["energy_today"] = running_energy_consume_today

    start_time_yesterday = datetime.combine(now.date() - timedelta(days=1), t(8, 0, 0))
    end_time_yesterday = start_time_yesterday + timedelta(hours=24)
    (
        running_billet_count_yesterday,
        running_cobble_yesterday,
        running_energy_consume_yesterday,
    ) = query_max_values(start_time_yesterday, end_time_yesterday)

    yesterdays_count["billet_yesterday"] = running_billet_count_yesterday
    yesterdays_count["cobble_yesterday"] = running_cobble_yesterday
    yesterdays_count["energy_yesterday"] = running_energy_consume_yesterday

    return render_template(
        "admin.html",
        week_totals=week_totals,
        month_totals=month_totals,
        todays_count=todays_count,
        yesterdays_count=yesterdays_count,
        form=form,
    )


@app.route("/usermanagement")
@login_required
@role_required("admin")
def usermanagement():
    form = Csrf()
    userlist = User.query.all()
    return render_template("user/usermanagement.html", userlist=userlist, form=form)


@app.route("/update_user_role/<int:user_id>", methods=["POST"])
@login_required
def update_user_role(user_id):

    new_role = request.form["role"]
    user = User.query.get(user_id)
    if user:
        user.role = new_role
        db.session.commit()
    return redirect(url_for("usermanagement"))


@app.route("/delete_user/<int:user_id>", methods=["POST"])
@login_required
@role_required("admin")
def delete_user(user_id):
    form = Csrf()
    user = User.query.get(user_id)
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for("usermanagement"))


@app.route("/notification")
@login_required
def notification():
    notification = Notification.query.order_by(Notification.time_stamp.desc()).all()

    return render_template("notification/notification.html", notification=notification)


@socketio.on("connect")
def handle_connect():
    logger.info("Client connected")


@socketio.on("disconnect")
def handle_disconnect():
    logger.info("Client disconnected")


def plc_thread():
    with app.app_context():
        while True:
            plc = snap7.client.Client()
            try:
                plc.connect(PLC_IP, RACK_NO, SLOT_NO)
                if plc.get_connected():
                    logger.info("Connection to PLC successful")
                    read_plc_and_write_to_excel(plc)
                else:
                    logger.error("Failed to connect to PLC")
            except Exception as e:
                logger.error(f"PLC connection error: {e}")
            finally:
                plc.disconnect()



def schedule_task():
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=add_data_to_daily_data_count, trigger="cron", hour=7, minute=58
    )
    logger.info("Scheduled task to add daily count to daily data count at 07:58.")
    
    try:
        scheduler.start()
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")
    
    # Shut down the scheduler when exiting the app
    atexit.register(lambda: shutdown_scheduler(scheduler))

def shutdown_scheduler(scheduler):
    try:
        scheduler.shutdown()
        logger.info("Scheduler shut down successfully.")
    except Exception as e:
        logger.error(f"Error shutting down scheduler: {e}")



import sys

from apscheduler.triggers.cron import CronTrigger

def restart_flask_app():
    logger.info("Restarting Flask app...")
    python = sys.executable
    time.sleep(10)
    os.execl(python, python, * sys.argv)  # This will restart the Flask app

def schedule_task_restart():
    scheduler = BackgroundScheduler()
    scheduler.start()
    
    # Schedule the restart task
    trigger = CronTrigger(hour=8, minute=00)  # 8 AM daily
    scheduler.add_job(restart_flask_app, trigger)
    
    logger.info("Scheduler started successfully.")

    # Ensure the scheduler shuts down properly
    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("Scheduler shut down successfully.")
    except Exception as e:
        logger.error(f"Error shutting down scheduler: {e}")


if __name__ == "__main__":
    with app.app_context():
        scheduler_thread = threading.Thread(target=schedule_task_restart)
        scheduler_thread.daemon = True
        scheduler_thread.start()

    plc_thread_instance = threading.Thread(target=plc_thread)
    plc_thread_instance.daemon = True
    plc_thread_instance.start()

    socketio.run(app, port=5001, host="0.0.0.0")
