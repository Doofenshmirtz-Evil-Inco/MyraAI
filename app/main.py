import os
import json
import asyncio
import threading
import tempfile
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, Response

from app.tmdb_service import search_movie_candidates
from app.gemini_agent import jarvis_agent
from app.clarification import resolve_candidate
from app.database import export_to_csv_bytes, save_log_to_db
from app.local_audio import LocalSTT, LocalTTS, AudioRecorder
from app.session_manager import session_manager
from app.agent.conversation_manager import ConversationManager

app = FastAPI(title="VoiceLog Movie Assistant")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")
CSV_FILE_PATH = os.path.join(BASE_DIR, "letterboxd_import.csv")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

conversation_manager = ConversationManager(jarvis_agent)

stt_engine = None
tts_engine = None
recorder = None
stt_lock = threading.Lock()
tts_lock = threading.Lock()

PIPER_DIR = os.path.join(BASE_DIR, "piper")
PIPER_MODEL = os.path.join(BASE_DIR, "en_US-lessac-medium.onnx")

@app.on_event("startup")
def startup_event():
    global recorder
    try:
        recorder = AudioRecorder(sample_rate=16000)
    except Exception as e:
        print(f"[Audio Engine Error] Initialization failed: {e}")


def get_tts_engine():
    global tts_engine
    if tts_engine is None:
        with tts_lock:
            if tts_engine is None:
                if os.getenv("USE_KOKORO", "false").casefold() == "true":
                    try:
                        from app.kokoro_tts import KokoroTTS
                        tts_engine = KokoroTTS(
                            voice=os.getenv("KOKORO_VOICE", "af_heart"),
                            lang_code=os.getenv("KOKORO_LANG", "a"),
                            model_path=os.getenv("KOKORO_MODEL_PATH") or None,
                            repo_id=os.getenv("KOKORO_REPO_ID", "hexgrad/Kokoro-82M"),
                        )
                    except Exception as error:
                        print(f"[Voice Warning] Kokoro unavailable: {error}", flush=True)

                if tts_engine is None and os.path.exists(PIPER_DIR) and os.path.exists(os.path.join(PIPER_DIR, "piper.exe")):
                    model_path = os.path.join(PIPER_DIR, "en_US-lessac-medium.onnx")
                    if os.path.exists(model_path):
                        tts_engine = LocalTTS(piper_dir=PIPER_DIR, model_path=model_path)
                if tts_engine is None:
                    print("[Voice Warning] No TTS engine available.", flush=True)
    return tts_engine


def speak_confirmation(text):
    engine = get_tts_engine()
    if engine:
        engine.speak(text)


def get_stt_engine():
    global stt_engine
    if stt_engine is None:
        with stt_lock:
            if stt_engine is None:
                stt_engine = LocalSTT(model_size="base", device="cpu")
    return stt_engine


def transcribe_audio(audio_data):
    return get_stt_engine().transcribe(audio_data)


def transcribe_audio_file(audio_path):
    return get_stt_engine().transcribe_file(audio_path)


def process_transcript(transcript, session_id="default"):
    return conversation_manager.process(session_id, transcript)

def process_conversation(session_id, transcript):
    return conversation_manager.process(session_id, transcript)

@app.get("/")
async def get_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

@app.get("/download-csv")
async def download_csv():
    return Response(
        content=export_to_csv_bytes(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=letterboxd_import.csv"},
    )

@app.post("/api/record-and-log")
async def record_and_log(duration: float = 5.0, background_tasks: BackgroundTasks = None):
    if not recorder:
        return JSONResponse(status_code=500, content={"error": "Local audio services are uninitialized."})

    audio_data = recorder.record_seconds(duration=duration)
    transcript = await asyncio.to_thread(transcribe_audio, audio_data)
    
    if not transcript:
        return {"status": "error", "message": "No speech detected."}

    try:
        result = await asyncio.to_thread(process_conversation, "local-audio", transcript)
        if result.get("speech") and background_tasks:
            background_tasks.add_task(
                speak_confirmation,
                result["speech"]
            )
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/audio-log")
async def audio_log(
    background_tasks: BackgroundTasks,
    session_id: str = Form("default"),
    file: UploadFile = File(...),
):
    suffix = os.path.splitext(file.filename or "audio.webm")[1] or ".webm"
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_path = temp_file.name
            while chunk := await file.read(1024 * 1024):
                temp_file.write(chunk)

        transcript = await asyncio.to_thread(transcribe_audio_file, temp_path)
        print(f"[Audio Upload] Transcribed {file.filename!r}: {transcript!r}", flush=True)
        if not transcript:
            return {"status": "error", "message": "No speech detected."}

        result = await asyncio.to_thread(process_conversation, session_id, transcript)
        result["transcript"] = transcript
        if result.get("speech"):
            background_tasks.add_task(speak_confirmation, result["speech"])
        return result
    except Exception as e:
        print(f"[Audio Upload Error] {e}", flush=True)
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
    finally:
        if temp_path:
            try:
                os.unlink(temp_path)
            except OSError:
                pass

@app.websocket("/ws/log")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    session_id = websocket.query_params.get("session_id", "default")
    print("[WS] Client connected.", flush=True)
    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                data = json.loads(raw_data)
            except json.JSONDecodeError:
                print("[WS] Ignored invalid JSON message.", flush=True)
                await websocket.send_json({
                    "status": "error",
                    "message": "Invalid request payload."
                })
                continue

            transcript = data.get("transcript", "")

            if transcript:
                try:
                    print(f"[WS] Received transcript: {transcript!r}", flush=True)
                    await websocket.send_json({
                        "status": "received",
                        "transcript": transcript
                    })
                    result = await asyncio.to_thread(process_conversation, session_id, transcript)
                    print(f"[WS] Processing result: {result['status']}", flush=True)
                    await websocket.send_json(result)
                    if result.get("speech"):
                        asyncio.create_task(asyncio.to_thread(speak_confirmation, result["speech"]))
                except Exception as e:
                    print(f"[WS Processing Error] {e}", flush=True)
                    await websocket.send_json({
                        "status": "error",
                        "message": f"Failed to process transcript: {e}"
                    })
    except WebSocketDisconnect:
        print("[WS] Client disconnected.")