# Spotify AI Playlist Generator — Flask

Minimal Flask service for generating Spotify playlists with an LLM.
Handles the full OAuth 2.0 flow, token refresh, track search, playlist creation, and adding tracks.

---

## ⚠️ Important: `/items` not `/tracks`

As of late 2024, Spotify deprecated `POST /playlists/{id}/tracks`.
New apps receive **403 Forbidden** on that endpoint.
This project uses the current endpoint:

```
POST /v1/playlists/{playlist_id}/items   ✅
POST /v1/playlists/{playlist_id}/tracks  ❌ deprecated → 403
```

---

## Setup

### 1. Create a Spotify App

1. Go to [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard)
2. Create a new app
3. Under **APIs used** → check **Web API**
4. Add Redirect URI: `http://127.0.0.1:5050/api/spotify/callback`
5. Copy your **Client ID** and **Client Secret**

### 2. Configure environment

```bash
cp .env.example .env
# fill in SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Add your LLM

In `app.py`, implement `_generate_songs_with_ai(prompt)`.
It must return a list of dicts:

```python
[{'name': 'Bohemian Rhapsody', 'artist': 'Queen'}, ...]
```

Works with any LLM — Claude, OpenAI, Gemini, local models, etc.

### 5. Run

```bash
python app.py
```

Then open `http://127.0.0.1:5050/api/spotify/connect` to authenticate.

---

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/spotify/status` | Auth status |
| GET | `/api/spotify/connect` | Start OAuth flow |
| GET | `/api/spotify/callback` | OAuth callback (set this as Redirect URI) |
| POST | `/api/spotify/disconnect` | Remove local token |
| POST | `/api/spotify/generate-playlist` | Generate + create playlist |

### Generate playlist — request body

```json
{
  "name": "Friday Night Vibes",
  "prompt": "upbeat indie pop for a road trip",
  "public": false
}
```

### Generate playlist — response

```json
{
  "playlist_url": "https://open.spotify.com/playlist/...",
  "playlist_id": "...",
  "tracks_added": [
    {"uri": "spotify:track:...", "name": "...", "artist": "...", "album": "...", "image": "..."}
  ],
  "not_found": ["Song that wasn't on Spotify – Artist"]
}
```

---

## Notes

- Token is stored locally in `spotify_token.json` (auto-refreshed)
- Development Mode apps are limited to 25 users — sufficient for personal use
- `spotify_service.py` is framework-agnostic; use it standalone without Flask if needed
