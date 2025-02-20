import requests
from flask import Flask, session, redirect, url_for, request, jsonify
import os
from flask_cors import CORS

app = Flask(__name__)
# Enable CORS with credentials support
CORS(app, supports_credentials=True)

# Spotify API credentials
SPOTIFY_CLIENT_ID = '92f8f0e47b274a4e94dfbcea2f333999'
SPOTIFY_CLIENT_SECRET = 'd4fbbe4928b84e79916e135a414c91c8'
SPOTIFY_REDIRECT_URI = 'https://music-widget.onrender.com/callback'

app.secret_key = os.urandom(24)  # Required for session management

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
    
    # If there's an error (e.g. invalid_grant), clear session and prompt re-login
    if 'error' in response_data:
        session.clear()
        return f"Error exchanging code: {response_data}. Please <a href='/login'>login</a> again."
    
    access_token = response_data.get('access_token')
    refresh_token = response_data.get('refresh_token')

    if not access_token or not refresh_token:
        session.clear()
        return f"Error: {response_data}. Please <a href='/login'>login</a> again."

    session['access_token'] = access_token
    session['refresh_token'] = refresh_token

    return redirect('/profile')

def refresh_access_token():
    refresh_token = session.get('refresh_token')
    if not refresh_token:
        return None  

    data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'client_id': SPOTIFY_CLIENT_ID,
        'client_secret': SPOTIFY_CLIENT_SECRET,
    }
    
    response = requests.post('https://accounts.spotify.com/api/token', data=data)
    response_data = response.json()
    new_access_token = response_data.get('access_token')
    
    if new_access_token:
        session['access_token'] = new_access_token
        return new_access_token
    
    return None

@app.route('/profile')
def profile():
    access_token = session.get('access_token')
    if not access_token:
        new_token = refresh_access_token()
        if not new_token:
            return redirect(url_for('login'))
        access_token = new_token

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    response = requests.get("https://api.spotify.com/v1/me", headers=headers)
    if response.status_code != 200:
        return f"Error: Unable to fetch user profile from Spotify - {response.json()}"
    
    user_info = response.json()
    return f"Hello, {user_info['display_name']}! Your Access Token: {access_token}"

@app.route('/currently-playing')
def currently_playing():
    access_token = session.get('access_token')
    if not access_token:
        new_token = refresh_access_token()
        if not new_token:
            return redirect(url_for('login'))
        access_token = new_token

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    response = requests.get("https://api.spotify.com/v1/me/player/currently-playing", headers=headers)

    if response.status_code == 401:
        new_token = refresh_access_token()
        if new_token:
            headers['Authorization'] = f'Bearer {new_token}'
            response = requests.get("https://api.spotify.com/v1/me/player/currently-playing", headers=headers)

    # If no content (204), return empty data with album_image_url key
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
