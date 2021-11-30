"""
Very simple Flask App.  For Testing
"""


import json
import re

import flask

from .meta import app
#from .objects import *
from .models import *
from .objects import *

HTTP_METHODS = ['GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'CONNECT', 'OPTIONS', 'TRACE', 'PATCH']

import logging


def populateTables():
    """
    Populate the database the first tiem areound
    You can Ignore this
    """

    bookQry = Item.query.filter_by(hidden = False)
    if bookQry.count() == 0:
        logging.warning("Need some Books")
        populateBookTable()

    userQry = User.query.count()
    if userQry == 0:
        populateUserTable()

    buyQry = Purchace.query.count()
    if buyQry == 0:
        populateReviews()
    
            
@app.route("/")
def index():

    bookQry = Item.query.filter_by(hidden = False)
    populateTables()
    
        
    return flask.render_template("index.html",
                                 bookList = bookQry)

@app.route("/about")
def about():
    return flask.render_template("about.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    prev = flask.request.args.get("prev")
    if not prev:
        prev = "index"
        
    if flask.request.method == "POST":
        #Get data
        user = flask.request.form.get("email")
        password = flask.request.form.get("password")
        logging.info("Attempt to login as %s:%s", user, password)
        userQry = User.query.filter_by(email = user).first()

        #Hash the password
        hashedPw = hashlib.sha512(password.encode()).hexdigest()

        theQry = "Select * FROM User WHERE email = '{0}' AND password = '{1}'".format(user,
                                                                                      hashedPw)
        logging.warning(theQry)
        userQry = db.engine.execute(theQry).first()
        logging.warning(userQry)
        if userQry is None:
            flask.flash("No Such User")
        else:
            logging.info("Login as %s Success", userQry.name)
            flask.session["user"] = userQry.id
            flask.session["role"] = userQry.level
            flask.flash("Login Successful")
            return (flask.redirect(flask.url_for(prev)))
        
    return flask.render_template("login.html",
                                 prev = prev)

@app.route("/logout")
def logout():
    flask.session.clear()
    return flask.redirect(flask.url_for("index"))


@app.route("/user/create", methods=["GET","POST"])
def create():
    """ Create a new account,
    we will redirect to a homepage here
    """

    if flask.request.method == "GET":
        return flask.render_template("create_account.html")
    
    #Get the form data
    name = flask.request.form.get("name")
    email = flask.request.form.get("email")
    password = flask.request.form.get("password")
    password2 = flask.request.form.get("password2")
    admin = flask.request.form.get("admin", False)
    
    if password != password2:
        flask.flash("Passwords do not match")
        return flask.render_template("create_account.html",
                                     name = name,
                                     email = email)

    logging.warning("Name >%s< %s", name, name == None)
    #Sanity check do we have a name, email and password
    if not name or not email or not password: 
        flask.flash("Not all info supplied")
        return flask.render_template("create_account.html",
                                     name = name,
                                     email = email)
    #And check we have an email
    emailre = re.compile(r"^[\w\.\+\-]+\@[\w]+\.([a-z]{2,3})+$")

    if not emailre.match(email):
        flask.flash("Bad Email Address")
        return flask.render_template("create_account.html",
                                     name = name)

    #Otherwise we can add the user
    userQry = User.query.filter_by(email = email).first()
    if userQry:
        flask.flash("A User with that Email Exists")
        return flask.render_template("create_account.html",
                                     name = name,
                                     email = email)

    else:
        logging.info("Creating user %s %s with password %s (Admin %s)", name, email, password, admin)
        #Crate the user
        hashedPw = hashlib.sha512(password.encode()).hexdigest()
        theUser = User(name=name,
                       email=email,
                       password=hashedPw)

        if admin:
            theUser.level = "admin"

        db.session.add(theUser)
        db.session.commit()
        flask.flash("Account Created, you can now Login")
        return flask.redirect(flask.url_for("login"))

@app.route("/review/<userId>/<itemId>", methods=["GET", "POST"])
def reviewItem(userId, itemId):
    """Add a Review"""

    
    #Handle input
    if flask.request.method == "POST":
        reviewStars = flask.request.form.get("rating")
        reviewComment = flask.request.form.get("review")
        reviewId = flask.request.form.get("reviewId")

        if reviewId:
            #Update Existing
            theReview = Review.query.filter_by(id = reviewId).first()
            theReview.stars = reviewStars
            theReview.comments = reviewComment
            flask.flash("Review Updated")
        else:
            theReview = Review(userId=userId,
                               itemId=itemId,
                               stars=reviewStars,
                               comments = reviewComment)
            db.session.add(theReview)
            flask.flash("Review Created")            
        db.session.commit()

            
        return flask.redirect(flask.url_for("settings",
                                            userId = userId))

    #Otherwise get the review
    review = Review.query.filter_by(userId=userId,
                                    itemId=itemId).first()


    return flask.render_template("reviewItem.html",
                                 review = review,
                                 )
    
    
@app.route("/user/<userId>/settings")
def settings(userId):

    #Yes its silly that I forgot cookies, let pretend its an API
    thisUser = User.query.filter_by(id=userId).first()
    if not thisUser:
        flask.flash("No Such User")
        return flask.redirect(flask.url_for("index"))

    #Purchaces
    purchaces = Purchace.query.filter_by(userId = userId)
    
    return flask.render_template("usersettings.html",
                                 user = thisUser,
                                 purchaces = purchaces)

@app.route("/user/<userId>/update", methods=["GET","POST"])
def updateUser(userId):

    thisUser = User.query.filter_by(id = userId).first()
    if not thisUser:
        flask.flash("No Such User")
        return flask.redirect(flask_url_for("index"))

    #otherwise we want to do the checks
    if flask.request.method == "POST":
        logging.warning("------------------------")
        current = flask.request.form.get("current")

        password = flask.request.form.get("password")

        if current:
            hashedCurrent = hashlib.sha512(current.encode()).hexdigest()
            hashedPw = hashlib.sha512(password.encode()).hexdigest()
            if hashedCurrent == thisUser.password:
                thisUser.password = hashedPw
                db.session.commit()
            else:
                flask.flash("Current Password is incorrect")
            return flask.redirect(flask.url_for("settings",
                                                userId = thisUser.id))

        adminSubmit = flask.request.form.get("updateadmin")
        logging.warning("Admin Submit %s", adminSubmit)
        if adminSubmit:
            admin = flask.request.form.get("admin")
            logging.warning("Admin Box is %s", admin)
        
            if admin:
                admin = "admin"
            else:
                admin = "user"

            thisUser.level = admin
            #And update the Session
            flask.session["role"] = admin
            db.session.commit()
            logging.warning(" UPDATING THE ADMIN ")
            logging.warning("Level %s ", thisUser.level)
            return flask.redirect(flask.url_for("settings", userId=userId))
            
    #if thisUser.id != flask.session["user"]
    #And then update the settings
    #if
    flask.flash("Update Error")

    return flask.redirect(flask.url_for("settings", userId=userId))

@app.route("/basket", methods=["GET","POST"])
def basket():

    #Check for user
    if not flask.session["user"]:
        flask.flash("You need to be logged in")
        return flask.redirect(flask.url_for("index"))


    theBasket = []
    #Otherwise we need to work out the Basket
    #Get it from the session
    sessionBasket = flask.session.get("basket", None)
    if not sessionBasket:
        flask.flash("No items in basket")
        return flask.redirect(flask.url_for("index"))

    totalPrice = 0
    for key in sessionBasket:
        theItem = Item.query.filter_by(id=key).first()
        quantity = int(sessionBasket[key])
        thePrice = theItem.price * quantity
        totalPrice += thePrice
        theBasket.append([theItem, quantity, thePrice])
    
        
    return flask.render_template("basket.html",
                                 basket = theBasket,
                                 total=totalPrice)

@app.route("/basket/payment", methods=["POST"])
def pay():

    if not flask.session["user"]:
        flask.flash("You need to be logged in")
        return flask.redirect(flask.url_for("index"))

    #Get the total cost
    cost = flask.request.form.get("total")

    theUser = User.query.filter_by(id = flask.session["user"]).first()
    
    return flask.render_template("pay.html",
                                 cost=cost,
                                 user = theUser)


@app.errorhandler(404)
def page_not_found(e):
    # note that we set the 404 status explicitly
    return flask.render_template('404.html', e = e), 404


@app.route("/testmde")
def test_mde():
    return flask.render_template("commentBox.html")
