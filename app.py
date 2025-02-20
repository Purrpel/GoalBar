import uuid
import requests
from flask import Flask, session, redirect, url_for, request, jsonify, render_template_string
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app, supports_credentials=True)

app.secret_key = os.urandom(24)

# Spotify API credentials (update these if needed)
# Spotify API credentials
SPOTIFY_CLIENT_ID = '7932813b9bec4fb6a6416d2bf407bb93'
SPOTIFY_CLIENT_SECRET = '24a9ab57885842a08b9ddead4b9fbdf0'
SPOTIFY_REDIRECT_URI = 'https://music-widget.onrender.com/callback'

# In‑memory store for user tokens: { user_key: { "access_token": ..., "refresh_token": ... } }
user_tokens = {}

@app.route('/')
def home():
    return 'Welcome to the Spotify App! <a href="/login">Login with Spotify</a>'

@app.route('/login')
def login():
    auth_url = (
        f"https://accounts.spotify.com/authorize?response_type=code&client_id={SPOTIFY_CLIENT_ID}"
        f"&redirect_uri={SPOTIFY_REDIRECT_URI}&scope=user-read-currently-playing%20user-read-playback-state"
    )
    return redirect(auth_url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return "Error: Missing code in callback"
    
    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': SPOTIFY_REDIRECT_URI,
        'client_id': SPOTIFY_CLIENT_ID,
        'client_secret': SPOTIFY_CLIENT_SECRET,
    }
    
    response = requests.post('https://accounts.spotify.com/api/token', data=data)
    response_data = response.json()
    
    if 'error' in response_data:
        session.clear()
        return f"Error exchanging code: {response_data}. Please <a href='/login'>login</a> again."
    
    access_token = response_data.get('access_token')
    refresh_token = response_data.get('refresh_token')
    
    if not access_token or not refresh_token:
        session.clear()
        return f"Error: {response_data}. Please <a href='/login'>login</a> again."
    
    # Generate a unique key for the user
    user_key = str(uuid.uuid4())
    # Store tokens in our in‑memory dictionary
    user_tokens[user_key] = {
        "access_token": access_token,
        "refresh_token": refresh_token
    }
    
    # Optionally store user_key in session for convenience
    session['user_key'] = user_key
    
    # Display the unique key to the user so they can use it in their widget
    return render_template_string(
        "<h1>Login Successful!</h1><p>Your widget key is: <strong>{{ user_key }}</strong></p>"
        "<p>Copy this key and paste it in your widget configuration.</p>",
        user_key=user_key
    )

def refresh_access_token(user_key):
    tokens = user_tokens.get(user_key)
    if not tokens or 'refresh_token' not in tokens:
        return None
    refresh_token_val = tokens['refresh_token']
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token_val,
        'client_id': SPOTIFY_CLIENT_ID,
        'client_secret': SPOTIFY_CLIENT_SECRET,
    }
    
    response = requests.post('https://accounts.spotify.com/api/token', data=data)
    response_data = response.json()
    new_access_token = response_data.get('access_token')
    if new_access_token:
        user_tokens[user_key]['access_token'] = new_access_token
        return new_access_token
    return None

@app.route('/currently-playing')
def currently_playing():
    # Expecting the widget to pass the unique key as a query parameter
    user_key = request.args.get('userKey')
    if not user_key or user_key not in user_tokens:
        return jsonify({"error": "Invalid or missing userKey"}), 400
    
    tokens = user_tokens[user_key]
    access_token = tokens.get('access_token')
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    response = requests.get("https://api.spotify.com/v1/me/player/currently-playing", headers=headers)
    
    if response.status_code == 401:
        # Access token expired, attempt to refresh
        new_token = refresh_access_token(user_key)
        if new_token:
            headers['Authorization'] = f'Bearer {new_token}'
            response = requests.get("https://api.spotify.com/v1/me/player/currently-playing", headers=headers)
    
    if response.status_code == 204:
        return jsonify({
            "track": "",
            "artists": "",
            "album_image_url": "",
            "is_playing": False,
            "progress_ms": 0,
            "duration_ms": 0
        }), 200
    elif response.status_code != 200:
        return jsonify({
            "error": "Failed to fetch currently playing",
            "details": response.json()
        }), response.status_code
    
    data = response.json()
    if data and data.get('item'):
        track_name = data['item'].get('name', 'Unknown Title')
        artists = ", ".join([artist['name'] for artist in data['item'].get('artists', [])])
        is_playing = data.get('is_playing', False)
        progress_ms = data.get('progress_ms', 0)
        duration_ms = data['item'].get('duration_ms', 1)
        album_images = data['item'].get('album', {}).get('images', [])
        album_image_url = album_images[0]['url'] if album_images else ""
        return jsonify({
            "track": track_name,
            "artists": artists,
            "album_image_url": album_image_url,
            "is_playing": is_playing,
            "progress_ms": progress_ms,
            "duration_ms": duration_ms
        })
    
    return jsonify({
        "track": "",
        "artists": "",
        "album_image_url": "",
        "is_playing": False,
        "progress_ms": 0,
        "duration_ms": 0
    }), 200

if __name__ == '__main__':
    app.run(port=3000, debug=True)
