import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, jsonify
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required

from datetime import date
import random



# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///chouvie.db")

# Make sure API key is set
# if not os.environ.get("API_KEY"):
#     raise RuntimeError("API_KEY not set")



@app.route("/")
def index():
    return render_template("index.html")



@app.route("/create", methods=["GET", "POST"])
def create():

    if request.method == "POST":

        # create group code
        # TODO: nice group names (API)
        group = random.randint(1, 100000)

        # create user
        try:
            db.execute("INSERT INTO users(name) VALUES (?);", request.form.get("name"))
        except:
            flash("Nickname already taken! Choose a different name")
            return render_template("create.html")

        user_id = db.execute("SELECT id FROM users WHERE name=?;", request.form.get("name"))[0].get("id")

        # create group
        taken = db.execute("SELECT id FROM groups WHERE name=?;", str(group))
        while len(taken) != 0:
            group = random.randint(1, 100000)
            taken = db.execute("SELECT id FROM groups WHERE name=?;", str(group))
        db.execute("INSERT INTO groups(name, owner, state, created) VALUES (?, ?, ?, ?);", str(group), user_id, "pending", date.today())

        group_id = db.execute("SELECT id FROM groups WHERE name=?;", str(group))[0].get("id")

        db.execute("INSERT INTO group_members(group_id, user_id) VALUES (?, ?);", group_id, user_id) #dubbelop?

        # set session
        session["user_id"] = user_id
        session["group_id"] = group_id
        session["members"] = []

        # send to waiting room
        return redirect("/waiting-room")

    return render_template("create.html")



@app.route("/join", methods=["GET", "POST"])
def join():

    if request.method == "POST":

        # fetch group_id
        group_id = db.execute("SELECT id FROM groups WHERE name=?;", request.form.get("group"))

        if len(group_id) != 1:
            flash("That's not a valid group name")
            return render_template("join.html")
            # return apology("Not a valid group name", 400)

        else:
            group_id = group_id[0].get("id")

        # create user
        try:
            db.execute("INSERT INTO users(name) VALUES (?);", request.form.get("name"))
        except:
            flash("Nickname already taken! Choose a different name")
            return render_template("join.html", group=request.form.get("group"))

        user_id = db.execute("SELECT id FROM users WHERE name=?;", request.form.get("name"))[0].get("id")

        # link user to group
        db.execute("INSERT INTO group_members(group_id, user_id) VALUES (?, ?);", group_id, user_id)

        # set session
        session["user_id"] = user_id
        session["group_id"] = group_id
        session["members"] = []

        # send to waitingroom page
        return redirect("/waiting-room")

    else:

        return render_template("join.html")



# TODO: optimaliseren en checken
@app.route("/members")
@login_required
def members():

    # get current groupmembers from database and session
    members = getMembers(session["group_id"])
    current = session["members"]

    # fill add with members that are stored in the database but not yet in the user's session
    add = [member for member in members if member not in current]

    # update mebers in user's session
    session["members"] = members

    # check current groupstate
    state = db.execute("SELECT state FROM groups WHERE id=?;", session["group_id"])[0].get("state")

    if state == "questioning":
        done = True

    else: done = False

    # render response and return data
    return jsonify({'data': render_template('response.html', members=add), 'done' : done})




@app.route("/waiting-room", methods=["GET", "POST"])
@login_required
def waiting_room():

    if request.method == "POST":

        # update group state to questioning
        db.execute("UPDATE groups SET state=? WHERE id=?;", "questioning", session["group_id"])

        return render_template("questions.html")

    else:

        # fetch group name, state and members
        row = db.execute("SELECT name, state FROM groups WHERE id = ?;", session["group_id"])
        group = row[0].get("name")
        members = getMembers(session["group_id"])

        is_owner = False

        # check if user is group owner
        owner = db.execute("SELECT * FROM groups WHERE owner=?;", session["user_id"])
        if len(owner) == 1:
            is_owner = True

        # redirect to questioning if state is not pending
        if row[0].get("state") != "pending":
            return render_template("questions.html")

        return render_template("waiting_room.html", group=group, is_owner=is_owner)


@app.route("/questions", methods=["GET", "POST"])
@login_required
def questions():

    if request.method == "POST":

        # TODO: Lune

        return render_template("top_three.html")

    else:
        return render_template("questions.html")



@app.route("/top_three", methods=["GET", "POST"])
@login_required
def top_three():

    if request.method == "POST":

        # TODO: Martijn

        return redirect("/result")
        # or: return render_template("result.html")

    else:

        return render_template("top_three.html")



@app.route("/result")
@login_required
def result():

    # TODO: Martijn

    # somewhere at the end call on funciton done() - maybe 1hr after final result is given

    return render_template("result.html")



@app.route("/solo", methods=["GET", "POST"])
def solo():

    if request.method == "POST":

        # TODO: Yenly

        return redirect("/solo")
        # or: return render_template("solo.html")

    else:

        return render_template("solo.html")



@app.route("/netflix-and-chill", methods=["GET", "POST"])
def netflix_and_chill():

    if request.method == "POST":

        # TODO: Sabine

        return redirect("/netflix-and-chill")
        # or: return render_template("netflix_and_chill.html")

    else:

        return render_template("netflix_and_chill.html")




#######################################################################################################################

# fetch group members
def getMembers(group_id):
    names = db.execute("SELECT name FROM users WHERE id in (SELECT user_id FROM group_members WHERE group_id=?);", group_id)
    members = []

    for name in names:
        print("name: ", name.get("name"))
        members.append(name.get("name"))

    return members



# delete user (and group)
def done():
    db.execute("DELETE FROM group_members WHERE user_id=?;", session["user_id"])
    db.execute("DELETE FROM users WHERE id=?;", session["user_id"])
    owner = db.execute("SELECT * FROM groups WHERE owner=?;", session["user_id"])

    if owner[0] == 1:
        db.execute("DELETE FROM groups WHERE id=?;", session["group_id"])

    session.clear()


# TEMPORARY: handle errors
def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
