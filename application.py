import os
import math
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


@app.route("/",methods=["GET"])
@login_required
def index():
    user_in_id =  session["user_id"]
    print(user_in_id)
    indexdata = db.execute("SELECT * FROM index_table WHERE index_id = ?", user_in_id)
    for j in range(0,(len(indexdata))):
        symbol = indexdata[j]["stock_symbol"]
        indexdictionary = lookup(symbol)
        index_price = indexdictionary["price"]
        db.execute("UPDATE index_table SET buying_price = ? WHERE index_id = ? AND stock_symbol = ?", index_price, user_in_id, symbol)
    INDEXHTMLDATA = db.execute("SELECT index_id, stock_symbol, SUM(shares), buying_price  FROM index_table WHERE index_id = ? GROUP BY stock_symbol ORDER BY stock_symbol", user_in_id)
    indexcashrequest = db.execute("SELECT * FROM users WHERE id = ?", user_in_id)
    INDEXUSERCASH = float(indexcashrequest[0]["cash"])
    HTMLTOTALPRICELIST = []
    HTMLSYMBOL = []
    HTMLNAME =[]
    HTMLSHARES = []
    HTMLCURRENTPRICE = []

    # do the loop in html here and do separate loop for html
    for i in range(0,len(INDEXHTMLDATA)):
        HTMLSYMBOL.append(INDEXHTMLDATA[i]["stock_symbol"])
        HTMLDICTIONARY = lookup(HTMLSYMBOL[i])
        HTMLNAME.append(HTMLDICTIONARY["name"])
        HTMLSHARES.append(INDEXHTMLDATA[i]["SUM(shares)"])
        HTMLCURRENTPRICE.append(INDEXHTMLDATA[i]["buying_price"])
        HTMLTOTALPRICELIST.append(int(INDEXHTMLDATA[i]["SUM(shares)"]) * float(INDEXHTMLDATA[i]["buying_price"]))
    print(len(HTMLSYMBOL))
    print(HTMLSYMBOL)
    HTMLGAIN = sum(HTMLTOTALPRICELIST) + INDEXUSERCASH
    LENGTH = []
    for z in range(0,len(HTMLSYMBOL)):
        LENGTH.append(z)

    # find the gain by looping over the index table once again and mutiply the shares and their current prices and add it with the usercad
    return render_template("index.html", indexusercash = INDEXUSERCASH, htmlsymbol = HTMLSYMBOL, htmlname = HTMLNAME, htmlshares = HTMLSHARES, htmlcurrentprice = HTMLCURRENTPRICE, htmlgain = HTMLGAIN, length = LENGTH)










@app.route("/buy_result",methods=["GET", "POST"])
@login_required
def buy_result():
    return render_template("buy_result.html")


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    #update the index table
    if request.method == "POST":
        if not request.form.get("stock"):
            return apology("must provide stock symbol", 403)
        elif not request.form.get("number of shares"):
            return apology("must provide number of shares", 403)


        STOCKSYMBOL = request.form.get("stock")
        NUMBER = request.form.get("number of shares")
        user_id =  session["user_id"]
        print(user_id)
        price={}
        price = lookup(STOCKSYMBOL)
        if price == None:
           return apology("symbol you searched does not exist", 403)
        NAME = price["name"]
        STOCKPRICE = price["price"]
        TOTALPRICE = float(price["price"])*int(NUMBER)
        cashrequest = db.execute("SELECT * FROM users WHERE id = ?", user_id)
        USERCASH = float(cashrequest[0]["cash"])
        REMANINGCASH = (float(USERCASH) - float(TOTALPRICE))
        if TOTALPRICE > USERCASH:
            return apology("you dont have enough money to buy", 403)
        else:
            # create a table and actually buy
            db.execute("INSERT INTO buying (buyer_id, shares, stock_symbol, buying_price) VALUES(?,?,?,?) ",user_id, NUMBER, STOCKSYMBOL, STOCKPRICE)
            db.execute("UPDATE users SET cash = ? WHERE id = ?", REMANINGCASH, user_id)
            db.execute("INSERT INTO index_table (index_id, shares, stock_symbol, buying_price) VALUES(?,?,?,?) ",user_id, NUMBER, STOCKSYMBOL, STOCKPRICE)
            DATE = db.execute("SELECT CURRENT_TIMESTAMP")
            DATETIME = DATE[0]["CURRENT_TIMESTAMP"]
            db.execute("INSERT INTO history2 (history_id, shares, stock_symbol, price, time_stamp) VALUES(?,?,?,?,?) ",user_id, NUMBER, STOCKSYMBOL, STOCKPRICE, DATETIME)
            return render_template("buy_result.html", usercash=USERCASH, stocksymbol=STOCKSYMBOL, name=NAME, number=NUMBER, stockprice=STOCKPRICE, totalprice=TOTALPRICE, remainingcash=REMANINGCASH)












    else:

        return render_template("buy.html")



@app.route("/history")
@login_required
def history():
    user_in_id = session["user_id"]
    historydata = db.execute("SELECT * FROM history2 WHERE history_id = ?", user_in_id)
    HISTORYSYMBOL =[]
    HISTORYSHARES = []
    HISTORYPRICE = []
    HISTORYTRANSACTION = []
    for i in range(0,len(historydata)):
        HISTORYSYMBOL.append(historydata[i]["stock_symbol"])
        HISTORYSHARES.append(historydata[i]["shares"])
        HISTORYPRICE.append(historydata[i]["price"])
        HISTORYTRANSACTION.append(historydata[i]["time_stamp"])
    LENGTH = []
    for z in range(0,len(HISTORYSYMBOL)):
        LENGTH.append(z)
    return render_template("history.html", htmlsymbol=HISTORYSYMBOL, htmlshares = HISTORYSHARES, htmlcurrentprice = HISTORYPRICE, transactions = HISTORYTRANSACTION, length = LENGTH)






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



@app.route("/result",methods=["GET", "POST"])
@login_required
def result():
    return render_template("result.html")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():

    if request.method == 'POST':


        if not request.form.get("quote"):
           return apology("give some stock symbol to search", 403)


        data = request.form.get("quote")
        quotedictionary = {}
        quotedictionary = lookup(data)
        print(quotedictionary)

        if quotedictionary == None:
           return apology("symbol you searched does not exist", 403)
        else:
            return render_template("result.html", QUOTEDICTIONARY=quotedictionary)

    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == 'POST':

        # Ensure the user typed in the user name and username is unique
        if not request.form.get("username"):
            return apology("must provide username", 403)
        names = db.execute("SELECT username FROM users WHERE username = ?", request.form.get("username"))
        if len(names) != 0:
            return apology("user name already exist must provide unique user name", 403)

        # ensure the user typed in password
        if not request.form.get("password"):
            return apology("must provide password", 403)


        # ensure the confirmation password is given and it is equal to password
        if not request.form.get("confirm password"):
            return apology("must provide confirmation password", 403)


        # if all conditions are verified then inserting user information in database
        name = request.form.get("username")
        password = generate_password_hash(request.form.get("password"))
        db.execute("INSERT INTO users (username ,hash) VALUES (? , ?)", name, password)



        return redirect("/login")
    else:
        return render_template("register.html")



@app.route("/sell_result",methods=["GET", "POST"])
@login_required
def sell_result():
    return render_template("sell_result.html")



@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if request.method == "POST":





        if not request.form.get("sellstock"):
            return apology("must provide stock symbol to sell", 403)
        elif not request.form.get("number of sharestosell"):
            return apology("must provide number of shares to sell", 403)




        SELLSTOCKSYMBOL = request.form.get("sellstock")
        sellingdictionary = lookup(SELLSTOCKSYMBOL)
        SELLINGSTOCKNAME = sellingdictionary["name"]
        NUMBER_SELL = int(request.form.get("number of sharestosell"))
        sell_user_id =  session["user_id"]
        INDEX_DATA = db.execute("SELECT index_id, stock_symbol, SUM(shares), buying_price  FROM index_table WHERE index_id = ? AND stock_symbol = ? GROUP BY stock_symbol", sell_user_id,  SELLSTOCKSYMBOL)
        sellcashrequest = db.execute("SELECT * FROM users WHERE id = ?", sell_user_id)
        BEFOREUSERCASH = float(sellcashrequest[0]["cash"])
        if len(INDEX_DATA) == 0:
            return apology("must provide right symbol which own")
        SELLING_PRICE = INDEX_DATA[0]["buying_price"]
        SELLINGTOTALPRICE = float(SELLING_PRICE) * NUMBER_SELL
        SELLINGREMANINGCASH = (float(BEFOREUSERCASH) + float(SELLINGTOTALPRICE))
        REMAININGSHARES = int(INDEX_DATA[0]["SUM(shares)"]) - NUMBER_SELL





        if len(INDEX_DATA) == 0:
            return apology("you do own that stock")






        if int(INDEX_DATA[0]["SUM(shares)"]) < int(NUMBER_SELL):
            return apology("you don't own enough stocks")
        else:
            db.execute("INSERT INTO selling (seller_id, selling_shares, stock_symbol, selling_price) VALUES(?,?,?,?) ",sell_user_id, NUMBER_SELL, SELLSTOCKSYMBOL, SELLING_PRICE)
            db.execute("UPDATE users SET cash = ? WHERE id = ?", SELLINGREMANINGCASH, sell_user_id)
            db.execute("UPDATE index_table SET shares = ? WHERE index_id = ? AND stock_symbol = ?", REMAININGSHARES, sell_user_id, SELLSTOCKSYMBOL)
            if REMAININGSHARES == 0:
                db.execute("DELETE FROM index_table WHERE index_id = ? AND shares = 0",sell_user_id)
            DATE = db.execute("SELECT CURRENT_TIMESTAMP")
            DATETIME = DATE[0]["CURRENT_TIMESTAMP"]
            NUMBER = -NUMBER_SELL
            db.execute("INSERT INTO history2 (history_id, shares, stock_symbol, price, time_stamp) VALUES(?,?,?,?,?) ",sell_user_id, NUMBER, SELLSTOCKSYMBOL, SELLING_PRICE, DATETIME)

            return render_template("sell_result.html", usercash=BEFOREUSERCASH , stocksymbol=SELLSTOCKSYMBOL, name=SELLINGSTOCKNAME, number =NUMBER_SELL, stockprice=SELLING_PRICE, totalprice=SELLINGTOTALPRICE, remainingcash=SELLINGREMANINGCASH)












    else:

        return render_template("sell.html")








    # update the index table


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
