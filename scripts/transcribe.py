#!/usr/bin/env python3
"""Audio scout-note transcription pipeline for Acme Sports.

Design (two paths, because this FEVM workspace has NO server-side transcription
model — no Whisper serving endpoint, and the Foundation Model chat API rejects
audio content blocks):

  PRIMARY (production, documented): a Whisper model on Databricks Model Serving.
    Set env TRANSCRIBE_ENDPOINT to the endpoint name. We POST the audio to its
    OpenAI-compatible /audio/transcriptions style invocation and read the text.
    The moment such an endpoint exists, this path activates with no code change.

  FALLBACK (works today, no infra): the caller supplies the transcript text
    (the React app captures it with the browser Web Speech API while recording).
    transcribe() returns that text and we still store the raw audio in the volume.

Either way, the transcript .txt is written to the documents volume as a normal
scout note so the Genie Agent can retrieve it at query time.
"""
import os, json, subprocess, urllib.request, base64, datetime

PROFILE = os.environ.get("DBX_PROFILE", "YOUR_PROFILE")
HOST = os.environ.get("DBX_HOST", "https://YOUR_WORKSPACE.cloud.databricks.com")
TRANSCRIBE_ENDPOINT = os.environ.get("TRANSCRIBE_ENDPOINT", "")  # e.g. "whisper-large-v3"
VOL_BASE = "/Volumes/acme_sports/demo/documents"
ENV = {**os.environ, "DATABRICKS_AUTH_STORAGE": "plaintext"}


def _token():
    r = subprocess.run(["databricks", "auth", "token", "-p", PROFILE],
                       capture_output=True, text=True, env=ENV)
    return json.loads(r.stdout)["access_token"]


def transcribe(audio_bytes, filename, client_transcript=None, token=None):
    """Return (transcript_text, method). Tries Whisper serving, else client text."""
    if TRANSCRIBE_ENDPOINT:
        try:
            tok = token or _token()
            b64 = base64.b64encode(audio_bytes).decode()
            body = json.dumps({"inputs": {"audio": [b64], "filename": [filename]}}).encode()
            req = urllib.request.Request(
                f"{HOST}/serving-endpoints/{TRANSCRIBE_ENDPOINT}/invocations",
                data=body, method="POST",
                headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
            d = json.load(urllib.request.urlopen(req, timeout=180))
            # pyfunc returns {"predictions": ["..."]} or {"text": "..."}
            preds = d.get("predictions") or d.get("text") or d
            text = preds[0] if isinstance(preds, list) else str(preds)
            return text.strip(), f"whisper:{TRANSCRIBE_ENDPOINT}"
        except Exception as e:
            print(f"[transcribe] Whisper endpoint failed ({e}); falling back.")
    if client_transcript:
        return client_transcript.strip(), "browser-web-speech-api"
    raise RuntimeError("No transcription available: set TRANSCRIBE_ENDPOINT or supply client_transcript.")


def upload_to_volume(volume_path, data_bytes, token=None):
    """PUT bytes to a UC volume path via the Files API (creates parents)."""
    tok = token or _token()
    url = f"{HOST}/api/2.0/fs/files{volume_path}?overwrite=true"
    req = urllib.request.Request(url, data=data_bytes, method="PUT",
        headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/octet-stream"})
    urllib.request.urlopen(req, timeout=120)
    return volume_path


def build_transcript_doc(player_name, player_id, scout_name, body,
                         fixture="(uploaded via app)", status="Active", date=None):
    date = date or datetime.date.today().isoformat()
    return (f"ACME SPORTS — SCOUT NOTE (VOICE TRANSCRIPT)\n"
            f"Player: {player_name}\nPlayer ID: {player_id}\nScout: {scout_name}\n"
            f"Date: {date}\nFixture observed: {fixture}\nStatus: {status}\n\nSUMMARY:\n{body}\n")


def ingest_audio_note(audio_bytes, audio_filename, player_name, player_id,
                      scout_name="App Upload", client_transcript=None, token=None):
    """Full pipeline: transcribe -> write audio + transcript to the volume."""
    tok = token or _token()
    text, method = transcribe(audio_bytes, audio_filename, client_transcript, tok)
    stem = os.path.splitext(os.path.basename(audio_filename))[0]
    audio_vpath = f"{VOL_BASE}/audio/{stem}.wav"
    tx_vpath = f"{VOL_BASE}/transcripts/scout_note_{stem}.txt"
    upload_to_volume(audio_vpath, audio_bytes, tok)
    doc = build_transcript_doc(player_name, player_id, scout_name, text)
    upload_to_volume(tx_vpath, doc.encode(), tok)
    return {"transcript": text, "method": method,
            "audio_path": audio_vpath, "transcript_path": tx_vpath}


if __name__ == "__main__":
    import sys
    audio = sys.argv[1] if len(sys.argv) > 1 else "data/audio/scout_test.wav"
    # The browser Web Speech API would produce this; for the CLI test we pass the known text.
    client_tx = ("Powerful ball carrier through the half spaces, draws fouls in dangerous "
                 "areas. Needs to sharpen his final ball under pressure. Good value now but "
                 "the fee is rising. Recommend we make a decision this window.")
    res = ingest_audio_note(open(audio, "rb").read(), os.path.basename(audio),
                            "Morgan Rogers", "p_rogers", scout_name="Priya Nair (voice memo)",
                            client_transcript=client_tx)
    print(json.dumps(res, indent=2))
