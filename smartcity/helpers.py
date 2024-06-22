import os
from flask import redirect, session, render_template, jsonify
from functools import wraps
import requests

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return render_template("login.html", message="Must log-in to view profile")
        return f(*args, **kwargs)

    return decorated_function

def searchAddress(address):
        apiKey = os.getenv('HERE_API_KEY')
        url = f'https://geocode.search.hereapi.com/v1/geocode?q={address}&apiKey={apiKey}'
        print(f"The address url is: {url}")
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            items=data.get('items', [])
            if items:
                position = items[0].get("position", {})
                lat = position.get("lat")
                lng = position.get("lng")
                address = items[0].get("address", {})
                add = address.get("label")
                code = address.get("postalCode")
                return lat, lng, add, code
            return None, None, None, None
        else:
            return f"Error: {response.status_code}"
