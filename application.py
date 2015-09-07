"""
application.py: Main file to run catalog app that does:
- Provides a list of items within a variety of categories
- Integrates third party Google Plus and Facebook OAuth user registration
  and authentication
- Authenticated users have the ability to post, edit, and delete their
  own items
- JSON and XML API endpoints for categories and category items
- Image upload capability available per item
"""
__author__ = "Rick Ertl"


# ~~~ Import required modules and classes ~~~
from flask import (Flask, render_template, request, redirect, jsonify,
                   url_for, flash, send_from_directory)

# Required for sqlite DB
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Category, Item, User

# Required for unique session creation
from flask import session as login_session
import random
import string

# Required for GConnect
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

# Required for image upload
import os
import os.path
from werkzeug import secure_filename

# Required for XML API
from jinja2 import Environment, FileSystemLoader

# Required for preventing CSRF
from flask.ext.seasurf import SeaSurf


# Initialize the Flask app
app = Flask(__name__)
csrf = SeaSurf(app)


# Connect to Database and create database session
engine = create_engine('sqlite:///duckies.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


# ~~~ OAuth Authentication and Authorization ~~~
# Create anti-forgery state token
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state)


# Facebook OAuth Connect
# SeaSurf exempt decorator to indicate not to be checked.
@csrf.exempt
@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data
    print "access token received %s " % access_token

    app_id = json.loads(open('fb_client_secrets.json', 'r').read())[
        'web']['app_id']
    app_secret = json.loads(
        open('fb_client_secrets.json', 'r').read())['web']['app_secret']
    url = 'https://graph.facebook.com/oauth/access_token?grant_type=fb_excha' \
          'nge_token&client_id=%s&client_secret=%s&fb_exchange_token=%s' % \
          (app_id, app_secret, access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]

    # Use token to get user info from API
    userinfo_url = "https://graph.facebook.com/v2.4/me"
    # strip expire tag from access token
    token = result.split("&")[0]

    url = 'https://graph.facebook.com/v2.4/me?%s&fields=name,id,email' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    # print "url sent for API access:%s"% url
    # print "API JSON result: %s" % result
    data = json.loads(result)
    login_session['provider'] = 'facebook'
    login_session['username'] = data['name']
    login_session['email'] = data['email']
    login_session['facebook_id'] = data['id']

    # Strip out the information before the equals sign in token
    stored_token = token.split("=")[1]
    login_session['access_token'] = stored_token

    # Get user picture
    url = 'https://graph.facebook.com/v2.4/me/picture?%s&redirect=0&height=' \
          '200&width=200' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    login_session['picture'] = data["data"]["url"]

    # see if user exists
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']

    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 200px; height: 200px;border-radius: 150px;' \
              '-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '

    flash("Now logged in as %s" % login_session['username'])
    return output


# Facebook OAuth Disconnect
# Revoke a current user's token and reset their login_session
@app.route('/fbdisconnect')
def fbdisconnect():
    facebook_id = login_session['facebook_id']
    # The access token must me included to successfully logout
    access_token = login_session['access_token']
    url = 'https://graph.facebook.com/%s/permissions?access_token=%s' % (
        facebook_id, access_token)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    return "you have been logged out"

# Google OAuth Connect
CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Catalog"


# SeaSurf exempt decorator to indicate not to be checked.
@csrf.exempt
@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already '
                                            'connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['credentials'] = credentials
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    # ADD PROVIDER TO LOGIN SESSION
    login_session['provider'] = 'google'

    # see if user exists, if it doesn't make a new one
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 200px; height: 200px;border-radius: 150px;' \
              '-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output


# User Helper Functions
def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
        'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


# Google OAuth Disconnect
# Revoke a current user's token and reset their login_session
@app.route('/gdisconnect')
def gdisconnect():
    # Only disconnect a connected user.
    credentials = login_session.get('credentials')
    if credentials is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = credentials.access_token
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] != '200':
        # For whatever reason, the given token was invalid.
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


# Disconnect based on provider
@app.route('/disconnect')
def disconnect():
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
            del login_session['credentials']
            del login_session['gplus_id']
            del login_session['username']
            del login_session['email']
            del login_session['picture']
        if login_session['provider'] == 'facebook':
            fbdisconnect()
            del login_session['facebook_id']
            del login_session['username']
            del login_session['email']
            del login_session['picture']
            del login_session['user_id']
            del login_session['provider']
        flash("You have successfully been logged out.")
        return redirect(url_for('showCategories'))
    else:
        flash("You were not logged in")
        return redirect(url_for('showCategories'))


# ~~~ CRUD SECTION ~~~
# Show all categories
@app.route('/')
@app.route('/categories/')
def showCategories():
    categories = session.query(Category).order_by(asc(Category.name))
    if 'username' not in login_session:
        return render_template('public_categories.html', categories=categories)
    else:
        return render_template('categories.html', categories=categories)


# Create a new category
@app.route('/categories/new/', methods=['GET', 'POST'])
def newCategory():
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        newCategory = Category(name=request.form['name'],
                               user_id=login_session['user_id'])
        session.add(newCategory)
        flash('New %s Category Successfully Created' % newCategory.name)
        session.commit()
        return redirect(url_for('showCategories'))
    else:
        return render_template('newCategory.html')


# Edit a category
@app.route('/categories/<int:category_id>/edit/', methods=['GET', 'POST'])
def editCategory(category_id):
    if 'username' not in login_session:
        return redirect('/login')
    editedCategory = session.query(Category).filter_by(id=category_id).one()
    if editedCategory.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized" \
               " to edit this category. Please create your own category in " \
               "order to edit.');}</script><body onload='myFunction()''>"
    if request.method == 'POST':
        if request.form['name']:
            editedCategory.name = request.form['name']
            flash('Successfully Edited %s Category' % editedCategory.name)
            return redirect(url_for('showCategories'))
    else:
        return render_template('editCategory.html', category=editedCategory)


# Delete a category
@app.route('/categories/<int:category_id>/delete/', methods=['GET', 'POST'])
def deleteCategory(category_id):
    if 'username' not in login_session:
        return redirect('/login')
    categoryToDelete = session.query(Category).filter_by(id=category_id).one()
    if categoryToDelete.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized" \
               " to delete this restaurant. Please create your own category" \
               " in order to delete.');}</script><body onload='myFunction()''>"
    if request.method == 'POST':
        session.delete(categoryToDelete)
        flash('%s Successfully Deleted' % categoryToDelete.name)
        session.commit()
        return redirect(url_for('showCategories', category_id=category_id))
    else:
        return render_template('deleteCategory.html',
                               category=categoryToDelete)


# Show all category products/items
@app.route('/categories/<int:category_id>/')
@app.route('/categories/<int:category_id>/items/')
def showAllItems(category_id):
    category = session.query(Category).filter_by(id=category_id).one()
    creator = getUserInfo(category.user_id)
    username = creator.name
    picture = creator.picture
    items = session.query(Item).filter_by(category_id=category_id).all()
    if 'username' not in login_session or creator.id != \
            login_session['user_id']:
        return render_template('public_products.html', items=items,
                               category=category, creator=creator,
                               username=username, picture=picture)
    else:
        return render_template('products.html', items=items, category=category,
                               username=username, picture=picture)

# IMAGE UPLOAD CAPABILITY
# This is the path to the upload directory
app.config['UPLOAD_FOLDER'] = os.path.realpath('.') + '/static/uploads'
# These are the file extensions accepted
app.config['ALLOWED_EXTENSIONS'] = set(['txt', 'pdf', 'png', 'jpg', 'jpeg',
                                        'gif'])


# For a given file, return whether it's an allowed type or not
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in app.config['ALLOWED_EXTENSIONS']


# Function to process the file upload
def imageUpload(file):
    # Check if the file is one of the allowed types/extensions
    if file and allowed_file(file.filename):
        # Make the filename safe, remove unsupported chars
        filename = secure_filename(file.filename)
        # Move the file form the temporal folder to the specified upload folder
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return filename


# This route is expecting a parameter containing the name of a file.
# Then it will locate that file in the upload directory and show
# it on the browser.
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename)


# Create a new item
@app.route('/categories/<int:category_id>/items/new/', methods=['GET', 'POST'])
def newItem(category_id):
    if 'username' not in login_session:
        return redirect('/login')
    category = session.query(Category).filter_by(id=category_id).one()
    if login_session['user_id'] != category.user_id:
        return "<script>function myFunction() {alert('You are not authorized" \
               " to create new items to this category. Please create your" \
               " own category in order to add.');}</script><body onload='" \
               "myFunction()''>"
    if request.method == 'POST':
        # Check if file selected for upload
        if request.files['image']:
            filename = imageUpload(request.files['image'])
            newItem = Item(name=request.form['name'], description=request.form[
                'description'], image=url_for('uploaded_file',
                                              filename=filename),
                           price=request.form['price'],
                           category_id=category_id, user_id=category.user_id)
        else:
            newItem = Item(name=request.form['name'], description=request.form[
                'description'], image='/uploads/no-image.png',
                           price=request.form['price'],
                           category_id=category_id,
                           user_id=category.user_id)
        session.add(newItem)
        session.commit()
        flash('New %s Item Successfully Created' % (newItem.name))
        return redirect(url_for('showAllItems', category_id=category_id))
    else:
        return render_template('newItem.html', category_id=category_id,
                               category=category)


# Edit an item
@app.route('/categories/<int:category_id>/items/<int:item_id>/edit',
           methods=['GET', 'POST'])
def editItem(category_id, item_id):
    if 'username' not in login_session:
        return redirect('/login')
    category = session.query(Category).filter_by(id=category_id).one()
    editedItem = session.query(Item).filter_by(id=item_id).one()
    if login_session['user_id'] != category.user_id:
        return "<script>function myFunction() {alert('You are not authorized" \
               " to edit items to this category. Please create your own" \
               " category in order to edit.');}</script><body " \
               "onload='myFunction()''>"
    if request.method == 'POST':
        # Check if file selected for upload
        if request.files['image']:
            filename = imageUpload(request.files['image'])
            editedItem.image = url_for('uploaded_file', filename=filename)
            if request.form['name']:
                editedItem.name = request.form['name']
            if request.form['description']:
                editedItem.description = request.form['description']
            if request.form['price']:
                editedItem.price = request.form['price']
        else:
            if request.form['name']:
                editedItem.name = request.form['name']
            if request.form['description']:
                editedItem.description = request.form['description']
            if request.form['price']:
                editedItem.price = request.form['price']
        session.add(editedItem)
        session.commit()
        flash('Item Successfully Edited')
        return redirect(url_for('showAllItems', category_id=category_id))
    else:
        return render_template('editItem.html', category_id=category_id,
                               item_id=item_id, item=editedItem,
                               category=category)


# Delete an item
@app.route('/categories/<int:category_id>/items/<int:item_id>/delete',
           methods=['GET', 'POST'])
def deleteItem(category_id, item_id):
    if 'username' not in login_session:
        return redirect('/login')
    category = session.query(Category).filter_by(id=category_id).one()
    items = session.query(Item).filter_by(category_id=category_id).all()
    itemToDelete = session.query(Item).filter_by(id=item_id).one()
    if login_session['user_id'] != category.user_id:
        return "<script>function myFunction() {alert('You are not authorized" \
               " to delete items to this category. Please create your own" \
               " category in order to delete.');}</script><body " \
               "onload='myFunction()''>"
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        flash('Item Successfully Deleted')
        return redirect(url_for('showAllItems', category_id=category_id))
    else:
        return render_template('deleteItem.html', item=itemToDelete,
                               category=category)


# ~~~ API ENDPOINTS SECTION ~~~
# JSON API to view all Categories
@app.route('/categories/JSON')
def categoriesJSON():
    categories = session.query(Category).all()
    return jsonify(categories=[r.serialize for r in categories])


# JSON API to view Category Items
@app.route('/categories/<int:category_id>/items/JSON')
def categoryItemsJSON(category_id):
    category = session.query(Category).filter_by(id=category_id).one()
    items = session.query(Item).filter_by(category_id=category_id).all()
    return jsonify(items=[i.serialize for i in items])


# JSON API to view Item Information
# @app.route('/categories/<int:category_id>/items/<int:item_id>/JSON')
# def ItemJSON(category_id, item_id):
#     item = session.query(Item).filter_by(id=item_id).one()
#     return jsonify(item=item.serialize)


# XML API to view all Categories
@app.route("/categories/XML", methods=["GET"])
def categoriesXML():
    base_dir = os.path.realpath(os.path.dirname(__file__))
    # Configure jinja for internal templates
    env = Environment(
        autoescape=True,
        extensions=['jinja2.ext.i18n'],
        loader=FileSystemLoader(
            os.path.join(base_dir, 'templates')
        )
    )
    categories = session.query(Category).order_by(asc(Category.name))
    category_xml = env.get_template("categories.xml").render(
        categories=categories)
    response = make_response(category_xml)
    response.headers["Content-Type"] = "application/xml"
    return response


# XML API to view Category Items
@app.route("/categories/<category_id>/items/XML", methods=["GET"])
def categoryItemsXML(category_id):
    base_dir = os.path.realpath(os.path.dirname(__file__))
    # Configure jinja for internal templates
    env = Environment(
        autoescape=True,
        extensions=['jinja2.ext.i18n'],
        loader=FileSystemLoader(
            os.path.join(base_dir, 'templates')
        )
    )
    category = session.query(Category).filter_by(id=category_id).one()
    items = session.query(Item).filter_by(category_id=category_id).all()
    items_xml = env.get_template("products.xml").render(
        items=items)
    response = make_response(items_xml)
    response.headers["Content-Type"] = "application/xml"
    return response


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
