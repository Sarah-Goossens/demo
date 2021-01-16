import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

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


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    data_user = db.execute("SELECT * FROM users WHERE id = :id", id=session["user_id"])
    cash = data_user[0]['cash']

    total_list = []

    data_buy = db.execute("SELECT * FROM portofolio WHERE id = :id", id=session["user_id"])
    for stocks in data_buy:
        stock = stocks['stock']
        price = stocks['price']
        share = stocks['share']
        total_list.append(stocks['price'] * stocks['share'])
    grand_total = cash + sum(total_list)
    return render_template("index.html", data_buy=data_buy, cash=cash, grand_total=grand_total)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    if request.method == "POST":

        # kijken of er een symbol is ingevuld
        if not request.form.get('symbol'):
            return apology('must provide symbol', 403)

        # kijken of de symbol bestaat
        if lookup(request.form.get('symbol')) == None:
            return apology('invalid symbol', 400)

        # kijken of de shares amount is ingevuld
        if not request.form.get("shares"):
            return apology('must provide a number of shares', 403)

        # kijken of de shares amount een positieve integer is
        if not request.form.get("shares").isdigit():
            return apology('invalid number of shares', 400)

        if int(request.form.get("shares")) < 1:
            return apology('invalid number of shares', 400)

        stock = request.form.get('symbol')
        shares_amount = int(request.form.get("shares"))

        # data over de stock verzamelen en de cash verzamelen
        stock_data = lookup(request.form.get('symbol'))
        price = stock_data['price']
        cash = db.execute("SELECT cash FROM users WHERE id = :id", id=session["user_id"])
        kosten = price * shares_amount

        # kijken of gebruiker het kan betalen
        if (cash[0]['cash']) < kosten:
            return apology('Not enough money', 403)

        # geld aftrekken en tabel updaten
        new_cash = (cash[0]['cash']) - kosten
        db.execute("UPDATE users SET cash = :cash WHERE id = :id", cash=new_cash, id=session["user_id"])

        # gegevens toevoegen aan database: als de stock al eerder is gekocht wordt het geupdate, anders wordt er een nieuwe rij ingevoegd
        data = db.execute("SELECT * FROM portofolio WHERE id = :id AND stock = :stock", id=session["user_id"], stock=stock)
        if len(data) < 1:
            db.execute("INSERT INTO portofolio (id, stock, share, price) VALUES (?,?,?,?)",
                       session["user_id"], stock, shares_amount, price)
        else:
            db.execute("UPDATE portofolio SET share = share + :share, price = :price WHERE id = :id AND stock = :stock",
                       share=shares_amount, price=price, id=session["user_id"], stock=stock)

        return redirect("/")

    else:
        return render_template("buy.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    if request.method == "POST":
        quote = lookup(request.form.get('symbol'))

        # als de quote niet gevonden kan worden
        if quote == None:
            return apology("invalid symbol", 400)

        return render_template("quoted.html", quote=quote)

    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # Forget any user_id
    session.clear()

    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Ensure password was submitted
        elif not request.form.get("confirmation"):
            return apology("must provide password confirmation", 400)

        # Ensure password and password confirmed match
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("passwords didn't match", 400)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        if len(rows) != 0:
            return apology("username taken", 400)

        password = generate_password_hash(request.form.get("password"))
        session["user_id"] = db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", request.form.get("username"), password)

        # Redirect user to home page
        return redirect("/")

    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":

        # kijken of een symbool is ingevuld
        if not lookup(request.form.get('symbol')):
            return apology('invalid symbol', 400)

        # kijken of de shares amount is ingevuld
        if not request.form.get("shares"):
            return apology('must provide a number of shares', 400)

        # kijken of de shares amount een positieve integer is
        if not request.form.get("shares").isdigit():
            return apology('invalid number of shares', 400)

        if int(request.form.get("shares")) < 1:
            return apology('invalid number of shares', 400)

        # Query database for stock
        portofolio_data = db.execute("SELECT * FROM portofolio WHERE id = :id AND stock = :stock",
                                     id=session["user_id"], stock=request.form.get("symbol"))

        # Ensure user has stock
        if len(portofolio_data) < 1:
            return apology("invalid stock", 403)

        shares = int(request.form.get("shares"))
        stock = request.form.get("symbol")

        # hoeveelheid shares na de verkoop
        new_shares = (portofolio_data[0]['share']) - shares

        # kijken of genoeg shares heeft om te verkopen
        if new_shares < 0:
            return apology('not enough shares to sell', 400)
        elif new_shares == 0:
            db.execute("DELETE FROM portofolio WHERE id=:id AND stock=:stock", id=session["user_id"], stock=stock)
        elif new_shares > 0:
            db.execute("UPDATE portofolio SET share=:shares WHERE id=:id AND stock=:stock",
                       shares=new_shares, id=session["user_id"], stock=stock)

        # cash aanpassen
        stock_data = lookup(request.form.get('symbol'))
        opbrengst = shares * stock_data['price']
        db.execute("UPDATE users SET cash= cash + :opbrengst WHERE id=:id", opbrengst=opbrengst, id=session["user_id"])
        return redirect("/")

    else:
        stocksset = set()
        portofolio = db.execute("SELECT stock FROM portofolio WHERE id=:id", id=session["user_id"])
        for stock in portofolio:
            stocksset.add(stock['stock'])
        stocks = list(stocksset)
        return render_template("sell.html", stocks=stocks)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)


