"""
Minimal Flask app — Spotify Playlist Generator
-----------------------------------------------
Endpoints:
  GET  /api/spotify/status            → is configured / authenticated?
  GET  /api/spotify/connect           → redirect to Spotify OAuth
  GET  /api/spotify/callback          → OAuth callback (set as Redirect URI in dashboard)
  POST /api/spotify/disconnect        → delete local token
  POST /api/spotify/generate-playlist → generate + create playlist via AI
  POST /api/spotify/manual-playlist   → create playlist from a supplied song list
"""

import os
import json
from flask import Flask, request, jsonify, redirect
import spotify_service

app = Flask(__name__)
PORT = int(os.getenv('PORT', 5050))


# ── Auth routes ───────────────────────────────────────────────────────────────

@app.route('/api/spotify/status')
def spotify_status():
    return jsonify({
        'configured':    spotify_service.is_configured(),
        'authenticated': spotify_service.is_authenticated(),
    })


@app.route('/api/spotify/connect')
def spotify_connect():
    redirect_uri = f'http://127.0.0.1:{PORT}/api/spotify/callback'
    auth_url = spotify_service.get_auth_url(redirect_uri)
    return redirect(auth_url)


@app.route('/api/spotify/callback')
def spotify_callback():
    code  = request.args.get('code')
    error = request.args.get('error')
    if error or not code:
        return jsonify({'error': error or 'No code returned'}), 400
    redirect_uri = f'http://127.0.0.1:{PORT}/api/spotify/callback'
    spotify_service.handle_callback(code, redirect_uri)
    return '''<script>window.close();</script><p>Connected! You can close this tab.</p>'''


@app.route('/api/spotify/disconnect', methods=['POST'])
def spotify_disconnect():
    token_file = spotify_service.TOKEN_FILE
    if os.path.exists(token_file):
        os.remove(token_file)
    return jsonify({'ok': True})


# ── Playlist generation ───────────────────────────────────────────────────────

@app.route('/api/spotify/generate-playlist', methods=['POST'])
def generate_playlist():
    try:
        if not spotify_service.is_authenticated():
            return jsonify({'error': 'Not authenticated'}), 401

        data          = request.get_json() or {}
        prompt        = data.get('prompt', '').strip()
        playlist_name = data.get('name', '').strip()
        public        = data.get('public', False)

        if not prompt:
            return jsonify({'error': 'prompt is required'}), 400
        if not playlist_name:
            return jsonify({'error': 'name is required'}), 400

        # ── Replace this block with your preferred LLM ────────────────────
        songs = _generate_songs_with_ai(prompt)
        # songs = [{'name': 'Bohemian Rhapsody', 'artist': 'Queen'}, ...]
        # ──────────────────────────────────────────────────────────────────

        found, not_found = [], []
        for song in songs:
            result = spotify_service.search_track(song['name'], song['artist'])
            if result:
                found.append(result)
            else:
                not_found.append(f"{song['name']} – {song['artist']}")

        if not found:
            return jsonify({'error': 'No songs found on Spotify'}), 404

        playlist = spotify_service.create_playlist(playlist_name, prompt, public)
        spotify_service.add_tracks(playlist['id'], [t['uri'] for t in found])

        return jsonify({
            'playlist_url':  playlist['url'],
            'playlist_id':   playlist['id'],
            'tracks_added':  found,
            'not_found':     not_found,
        })

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def _generate_songs_with_ai(prompt):
    """
    Call your preferred LLM to generate a list of songs.
    Replace this with OpenAI / Claude / Gemini / etc.

    Must return a list of dicts: [{'name': ..., 'artist': ...}, ...]
    """
    # Example stub — replace with real LLM call:
    raise NotImplementedError(
        "Implement _generate_songs_with_ai() with your LLM of choice.\n"
        "Expected return: [{'name': 'Song Title', 'artist': 'Artist Name'}, ...]"
    )


# ── Manual playlist ───────────────────────────────────────────────────────────

@app.route('/api/spotify/manual-playlist', methods=['POST'])
def manual_playlist():
    """
    Create a playlist from a user-supplied song list.

    Request body:
        {
          "name": "My Playlist",
          "public": false,
          "songs": [
            {"name": "Bohemian Rhapsody", "artist": "Queen"},
            {"name": "Blinding Lights", "artist": "The Weeknd"},
            {"name": "Stayin' Alive"}
          ]
        }

    The "artist" field is optional — omit it to search by song name only.
    """
    try:
        if not spotify_service.is_authenticated():
            return jsonify({'error': 'Not authenticated'}), 401

        data          = request.get_json() or {}
        songs         = data.get('songs', [])
        playlist_name = data.get('name', '').strip()
        public        = data.get('public', False)

        if not songs:
            return jsonify({'error': 'songs is required'}), 400
        if not playlist_name:
            return jsonify({'error': 'name is required'}), 400

        found, not_found = [], []
        for song in songs:
            result = spotify_service.search_track(
                song.get('name', ''), song.get('artist', '')
            )
            if result:
                found.append(result)
            else:
                label = song['name']
                if song.get('artist'):
                    label += f" – {song['artist']}"
                not_found.append(label)

        if not found:
            return jsonify({'error': 'No songs found on Spotify'}), 404

        playlist = spotify_service.create_playlist(playlist_name, 'Manual playlist', public)
        spotify_service.add_tracks(playlist['id'], [t['uri'] for t in found])

        return jsonify({
            'playlist_url': playlist['url'],
            'playlist_id':  playlist['id'],
            'tracks_added': found,
            'not_found':    not_found,
        })

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=PORT, debug=False)
