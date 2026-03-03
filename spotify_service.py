"""
Spotify OAuth + Playlist Service
---------------------------------
Handles token exchange, auto-refresh, track search, playlist creation,
and adding tracks — using the current /items endpoint (not the deprecated /tracks).
"""

import os
import json
import time
import base64
import requests

CLIENT_ID     = os.getenv('SPOTIFY_CLIENT_ID', '')
CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET', '')
TOKEN_FILE    = os.getenv('SPOTIFY_TOKEN_FILE', 'spotify_token.json')

SCOPES    = 'playlist-modify-public playlist-modify-private playlist-read-private user-read-private'
AUTH_URL  = 'https://accounts.spotify.com/authorize'
TOKEN_URL = 'https://accounts.spotify.com/api/token'
API_BASE  = 'https://api.spotify.com/v1'


# ── Auth helpers ──────────────────────────────────────────────────────────────

def is_configured():
    return bool(CLIENT_ID and CLIENT_SECRET)


def is_authenticated():
    if not os.path.exists(TOKEN_FILE):
        return False
    token = _load_token()
    return bool(token and token.get('access_token'))


def get_auth_url(redirect_uri):
    if not is_configured():
        raise ValueError("Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in your environment.")
    params = {
        'client_id':     CLIENT_ID,
        'response_type': 'code',
        'redirect_uri':  redirect_uri,
        'scope':         SCOPES,
    }
    return requests.Request('GET', AUTH_URL, params=params).prepare().url


def handle_callback(code, redirect_uri):
    """Exchange the auth code for an access/refresh token and save it."""
    credentials = _b64(f"{CLIENT_ID}:{CLIENT_SECRET}")
    resp = requests.post(TOKEN_URL, data={
        'grant_type':   'authorization_code',
        'code':         code,
        'redirect_uri': redirect_uri,
    }, headers={
        'Authorization': f'Basic {credentials}',
        'Content-Type':  'application/x-www-form-urlencoded',
    })
    resp.raise_for_status()
    token = resp.json()
    token['expires_at'] = time.time() + token.get('expires_in', 3600)
    _save_token(token)


# ── Internal token management ─────────────────────────────────────────────────

def _b64(s):
    return base64.b64encode(s.encode()).decode()


def _load_token():
    with open(TOKEN_FILE) as f:
        return json.load(f)


def _save_token(token):
    with open(TOKEN_FILE, 'w') as f:
        json.dump(token, f)


def _get_access_token():
    token = _load_token()
    if time.time() < token.get('expires_at', 0) - 60:
        return token['access_token']

    # Refresh
    credentials = _b64(f"{CLIENT_ID}:{CLIENT_SECRET}")
    resp = requests.post(TOKEN_URL, data={
        'grant_type':    'refresh_token',
        'refresh_token': token['refresh_token'],
    }, headers={
        'Authorization': f'Basic {credentials}',
        'Content-Type':  'application/x-www-form-urlencoded',
    })
    if resp.ok:
        new_token = resp.json()
        new_token['expires_at'] = time.time() + new_token.get('expires_in', 3600)
        new_token.setdefault('refresh_token', token['refresh_token'])
        _save_token(new_token)
        return new_token['access_token']

    return token['access_token']


def _headers():
    return {'Authorization': f'Bearer {_get_access_token()}'}


# ── API calls ─────────────────────────────────────────────────────────────────

def search_track(name, artist):
    """Return the best matching track dict, or None."""
    for q in [f'track:{name} artist:{artist}', name]:
        resp = requests.get(f'{API_BASE}/search', headers=_headers(),
                            params={'q': q, 'type': 'track', 'limit': 1})
        resp.raise_for_status()
        items = resp.json().get('tracks', {}).get('items', [])
        if items:
            t = items[0]
            return {
                'uri':    t['uri'],
                'name':   t['name'],
                'artist': t['artists'][0]['name'],
                'album':  t['album']['name'],
                'image':  t['album']['images'][-1]['url'] if t['album']['images'] else None,
            }
    return None


def create_playlist(name, description='', public=False):
    """Create a playlist for the current user. Returns {'id': ..., 'url': ...}."""
    resp = requests.post(f'{API_BASE}/me/playlists', headers=_headers(), json={
        'name':        name,
        'description': description,
        'public':      public,
    })
    resp.raise_for_status()
    data = resp.json()
    return {'id': data['id'], 'url': data['external_urls']['spotify']}


def add_tracks(playlist_id, uris):
    """
    Add tracks to a playlist (up to 100 per request).

    NOTE: Uses /items — NOT the deprecated /tracks endpoint.
    As of late 2024, /tracks returns 403 for new Spotify apps;
    /items is the current, working endpoint.
    """
    h = {**_headers(), 'Content-Type': 'application/json'}
    for i in range(0, len(uris), 100):
        resp = requests.post(
            f'{API_BASE}/playlists/{playlist_id}/items',
            headers=h,
            json={'uris': uris[i:i + 100]},
        )
        resp.raise_for_status()
