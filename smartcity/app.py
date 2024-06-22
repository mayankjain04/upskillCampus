import os
from flask import Flask, render_template, redirect, request, url_for, jsonify, session, flash
from flask_session import Session
import requests
from contextlib import contextmanager
from werkzeug.security import generate_password_hash, check_password_hash
import pymysql
from helpers import login_required
from helpers import searchAddress

app= Flask(__name__)

host = 'localhost'
user = 'root'
password = os.getenv('ROOT_SQL_PASSWORD')
db = 'smartcity'

@contextmanager
def get_connection():
    connection = pymysql.connect(
        host=host,
        user=user,
        password=password,
        database=db,
    )
    try:
        yield connection
    finally:
        if 'db' in locals():
            db.close()
        connection.close()
 
# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

API_KEY = os.getenv('HERE_API_KEY')

@app.route("/", methods=["GET", "POST"])
def index():
    return render_template("index.html")

@app.route('/login', methods=["GET", "POST"])
def login():
        if request.method == "POST":
            # checking for the validity of data submitted by login
            session.clear()
            username = request.form.get("username")
            password = request.form.get("password")
            with get_connection() as connection:
                with connection.cursor(pymysql.cursors.DictCursor) as cursor:  # Use DictCursor to get dictionaries instead of tuples
                    cursor.execute("SELECT user_id, pw_hash FROM users WHERE username = %s", (username,))
                    result = cursor.fetchone()
                    if not result:
                        return render_template("login.html", message="user not registered")
                    if not check_password_hash(result['pw_hash'], password):
                        return render_template("login.html", message="incorrect password")
                    session['user_id'] = result['user_id']
                    session['username'] = username
                    return redirect('/')
        else:
            if 'user_id' in session:
                # this happens when the user is trying to log out
                session.clear()
                return redirect("/")
            # this happens when user is trying to log in
            return render_template("login.html")

@app.route('/register', methods=["GET", "POST"])
def register():
        if request.method == "POST":
            username = request.form.get("username")
            password = request.form.get("password")
            confirmation = request.form.get("confirm")
            if not (username and password):
                return render_template("register.html", message="you sneaky son of a gun, insert valid data.")
            if not confirmation == password:
                return render_template("register.html", message="passwords do not match")
            with get_connection() as connection:
                with connection.cursor(pymysql.cursors.DictCursor) as cursor:  # Use DictCursor to get dictionaries instead of tuples
                    cursor.execute("SELECT user_id FROM users WHERE username = %s", (username,))
                    result = cursor.fetchone()
                    if result:
                        return render_template("register.html", message="username not available")
                    hashed_pw = generate_password_hash(password)
                    cursor.execute("INSERT INTO users (username, pw_hash) VALUES (%s, %s)", (username, hashed_pw))
                    connection.commit()
                    cursor.execute("SELECT user_id FROM users WHERE username = %s", (username,))
                    result = cursor.fetchone()
                    session['user_id'] = result['user_id']
                    session['username'] = username
                    return redirect("/")
        else:
            return render_template("register.html")

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
        if request.method=='POST':
            NewName = request.form.get('NewName')
            with get_connection() as connection:
                with connection.cursor(pymysql.cursors.DictCursor) as cursor:  # Use DictCursor to get dictionaries instead of tuples
                    if NewName:
                        cursor.execute("SELECT user_id FROM users WHERE username = %s", (NewName,))
                        result = cursor.fetchone()
                        if result:
                            flash('username not available', 'duplicate_username')
                            return redirect(url_for('profile'))
                        cursor.execute("UPDATE users SET username = %s WHERE user_id = %s", (request.form.get('NewName'), session['user_id'], ))
                        connection.commit()
                        cursor.execute("UPDATE test SET username = %s WHERE username = %s", (request.form.get('NewName'), session['username'], ))
                        connection.commit()
                        session['username'] = request.form.get('NewName')
                    if request.form.get('NewPass'):
                        cursor.execute("UPDATE users SET password = %s WHERE user_id = %s", (request.form.get('NewPass'), session['user_id'], ))
                        connection.commit()
                    return redirect(url_for('profile', rowdeleted='true'))
        else:
            username = request.args.get('username', session.get('username'))
            with get_connection() as connection:
                with connection.cursor(pymysql.cursors.DictCursor) as cursor:
                    return render_template("profile.html",username=username)

@app.route("/save-location", methods=["POST"])
def save_location():
    data = request.get_json()
    session['latitude'] = data['latitude']
    session['longitude'] = data['longitude']

    # Process the location data (e.g., save to database, perform some action, etc.)
    print(f"Received location: Latitude = {session['latitude']}, Longitude = {session['longitude']}")
    if session.get("user_id", ''):
        with get_connection() as connection:
            with connection.cursor(pymysql.cursors.DictCursor) as cursor:  # Use DictCursor to get dictionaries instead of tuples
                cursor.execute("UPDATE USERS SET latitude = %s, longitude = %s WHERE user_id = %s", (session.get("latitude"), session.get("longitude"), session.get("user_id"),))
                connection.commit()
    return jsonify({"message": "Location saved successfully"}), 200

@app.route('/traffic', methods=["GET", "POST"])
def traffic():
    if request.method=="POST":
        address = request.form.get("address", "Berlin")
        radius = request.form.get('radius', '1000')
        lat, lng, add, code = searchAddress(address)
        return render_template('traffic.html', latitude=lat, longitude=lng, label=add, code=code, radius=radius)
    else:
        lat = session.get("latitude", 28.63097)
        lng = session.get("longitude", 77.2172)
        radius = 1000
        print(session.get("latitude", 'default'))
    return render_template('traffic.html', latitude=lat, longitude=lng, radius=radius)

# the below code belongs to /traffic_data and produces error encoding characters like : and , into the link. maybe someone will fix it
# params = {
#     'in' : "circle:" +  str(session.get("latitude")) + "," + str(session.get("longitude")),
#     'r' : '2000',
#     'locationReferencing' : 'olr',
#     'apiKey' : API_KEY
# }
# url = requests.Request('GET', endpoint, params=params).prepare().url

@app.route('/traffic_data', methods=["GET", "POST"])
def get_traffic_data():
    latitude = request.args.get('latitude', session.get('latitude', 0))
    longitude = request.args.get('longitude', session.get('longitude', 0))
    radius = request.args.get('radius', 1000)
    endpoint = f'https://data.traffic.hereapi.com/v7/flow'
    url = f'{endpoint}?in=circle:{latitude},{longitude};r={radius}&locationReferencing=shape&apiKey={API_KEY}'
    print(f"Traffic Request URL: {url}")
    response = requests.get(url)
    data = response.json()
    results = data.get('results', [])

    traffic_data = []
    time = data.get('sourceUpdated', [])
    traffic_data.append({
        'sourceUpdated': time,
        'routeData': [],
        'flows': []
    })
    for result in results:
        location = result.get('location', {})
        current_flow = result.get('currentFlow', {})
        shape_links = location.get('shape', {}).get('links', [])

        confidence = current_flow.get('confidence', {})
        jamFactor = current_flow.get('jamFactor', {})
        traversability = current_flow.get('traversability', {})
        routelength = location.get('length', {})
        description = location.get('description', {})
        traffic_data[0]['routeData'].append({
            'routeName': description,
            'routeLength': routelength,
            'status': traversability,
            'jamStatus': jamFactor,
            'reliabilityFactor': confidence,
        })
        for link in shape_links:
            points = link.get('points', [])
            # length = link.get('length', 0)
            coordinates = [[point['lat'], point['lng']] for point in points]
            
            traffic_data[0]['flows'].append({
                'coordinates': coordinates,
                # 'length': length,
                'routeName': description,
                'routeLength': routelength,
                'jamStatus': jamFactor,
            })
    return jsonify({'Results': traffic_data})

@app.route('/show', methods=["GET", "POST"])
def show():
    if request.method=='POST':
        location = request.form.get('city_show', "India")
        # Make a request to the HERE API
        url = f'https://geocode.search.hereapi.com/v1/geocode'
        params = {
            'q': location,
            'apiKey': API_KEY
        }
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            return render_template("show.html", items=data.get('items', []))
        else:
            return f"Error: {response.status_code}"
    else:
        return render_template("show.html")

@app.route('/see')
def see():
    return render_template('see.html')

@app.route('/documentation')
def documentation():
    return render_template('documentation.html')

@app.route('/support')
def support():
    if request.method=='POST':
            with get_db_connection() as connection:
                with connection.cursor(pymysql.cursors.DictCursor) as cursor:  # Use DictCursor to get dictionaries instead of tuples
                    db.execute("INSERT INTO feedback (username, feedback) VALUES(%s, %s)", (session.get('username'), request.form.get('feedback')))
                    connection.commit()
                    flash('Response submitted successfully!', 'success')
                    return redirect("/support")
    else:
        return render_template("support.html")

if __name__ == '__main__':
    app.run(debug=True)
