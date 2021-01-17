import os
import requests
import urllib.parse

from flask import redirect, render_template, request, session
from functools import wraps


# render meddage as an apology to user
def apology(message, code=400):

    # escape special characters
    # https://github.com/jacebrowning/memegen#special-characters
    def escape(s):
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


# decorate routes to require login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/")
        return f(*args, **kwargs)
    return decorated_function
