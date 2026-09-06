# MyraAI

MyraAI is a local voice assistant for logging watched media. It records audio in the browser, uploads it when you pause, transcribes it with Faster-Whisper, extracts movie details with Gemini, resolves the title through TMDB, and stores the result in SQLite. CSV is generated on demand.Uses KokoroTTS for conversational speech.

## Requirements

- Windows
- Python 3.12
- NVIDIA GPU with CUDA support recommended
- Chrome or Edge for microphone recording
- Gemini API key
- TMDB API key
- Optional: Redis for persistent clarification sessions across workers

The supported runtime for this project is `myenv`. It contains the CUDA-enabled PyTorch and the Kokoro 0.7 runtime. Do not start the server from `yapenv` if you want GPU Kokoro.

## Environment Setup

From PowerShell in the project directory:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\myenv\Scripts\Activate.ps1
python --version
```

The expected Python version is `3.12.x`.

Install the application dependencies:

```powershell
python -m pip install -r requirements.txt
```

Install the optional Kokoro 0.7 stack:

```powershell
python -m pip install "kokoro==0.7.16" soundfile
python -m pip install numpy==1.26.4 "scipy<1.15"
```

The project uses the legacy Kokoro v0.19 checkpoint. Place this file in the project root:

```text
kokoro-v0_19.pth
```

## Configuration

Create or update `.env` in the project root:

```env
TMDB_API_KEY=your_tmdb_api_key
GEMINI_API_KEY=your_gemini_api_key

USE_KOKORO=true
KOKORO_MODEL_PATH=D:\Repos\Yap\kokoro-v0_19.pth
KOKORO_DEVICE=cuda
KOKORO_VOICE=af_heart
KOKORO_LANG=a
```

Never commit `.env` or expose API keys in source control.

If Kokoro is disabled or unavailable, the application falls back to Piper when the Piper executable and voice model are present in `piper/`.

## Start the Server

Activate `myenv`, then run:

```powershell
.\myenv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Open the application at:

```text
http://127.0.0.1:8000/
```

For a clean production-like local run without the file watcher:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The TTS model loads lazily on the first spoken confirmation, so server startup should not wait for Kokoro initialization.
Kokoro is the single response voice. The browser does not use its default speech-synthesis voice, which avoids an unexpected second or male voice.

## Using the Application

1. Open the URL in Chrome or Edge.
2. Wait for `Connected to Gemini Agent`.
3. Click the microphone button.
4. Speak a complete entry, for example: `I watched Dune Part Two, 4.5 stars, incredible visuals.`
5. Click the microphone button again to pause and upload the recording.
6. Wait for the transcript, TMDB match, and logged confirmation.
7. Use `Export CSV` to download the current database contents.

If TMDB returns multiple candidates, MyraAI asks for clarification. Record a follow-up such as `the 2016 one` or `option two`, then pause again. The pending clarification is stored for five minutes. Redis is used when available; otherwise a local TTL fallback is used.

MyraAI also supports multi-turn diary conversations. For example:

```text
You: Finally watched Parasite.
Jarvis: Nice. What did you think of it, and what rating would you give it?
You: Absolutely loved it.
Jarvis: What rating would you give it out of 5?
You: 4.5.
Jarvis: Logged.
```

Conversation state is explicit and persisted for the session. States include `CHAT`, `MENTIONED_MOVIE`, `CONFIRMING_MOVIE`, `COLLECTING_LOG_DETAILS`, `READY_TO_LOG`, and `LOGGED`. The manager does not ask for a watched date when the user gives a relative date such as `yesterday`; Gemini supplies the inferred date.

Successful log responses include both the Letterboxd-compatible `entry` and a structured contract:

```json
{
  "intent": "LOGGED",
  "movie": {"title": "Dune: Part Two", "tmdb_id": 693134, "year": "2024"},
  "watch": {"date": "2026-09-06", "rating": 4.5, "rewatch": false},
  "review": "The visuals were insane."
}
```

## Data Storage

- SQLite database: `MyraAI.db`
- CSV export: `GET /download-csv`
- Legacy import source: `letterboxd_import.csv`
- Uploaded audio: temporary files only; they are deleted after transcription

The browser sends recorded audio to:

```text
POST /api/audio-log
```

The WebSocket fallback endpoint is:

```text
/ws/log
```

## Optional Redis

Redis is not required for local development. Without Redis, the application uses an in-process five-minute fallback store. To use Redis, start Redis locally and optionally configure:

```env
REDIS_URL=redis://localhost:6379/0
```

## Validation

Run these checks from the activated `myenv`:

```powershell
python -m pip check
python -m compileall -q app
python -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
curl.exe -s -o NUL -w "HTTP %{http_code}\n" http://127.0.0.1:8000/
curl.exe -s -o NUL -w "CSV %{http_code}\n" http://127.0.0.1:8000/download-csv
```

To test the audio pipeline with the included fixture:

```powershell
curl.exe -s -X POST `
  -F "session_id=readme-test" `
  -F "file=@test.m4a" `
  http://127.0.0.1:8000/api/audio-log
```

A successful response contains `status: success` and an `entry`. An ambiguous title returns `status: clarification`; submit a second recording using the same `session_id` to resolve it.

## Troubleshooting

### Server starts with the wrong Python

Check the command line:

```powershell
Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" |
  Where-Object { $_.CommandLine -match 'uvicorn.*app.main:app' } |
  Select-Object ProcessId, CommandLine
```

The command should contain:

```text
D:\Repos\Yap\myenv\Scripts\python.exe
```

### Kokoro does not load

Confirm all of the following:

```powershell
python --version
python -c "import kokoro, torch; print(kokoro.__version__); print(torch.cuda.is_available())"
Test-Path .\kokoro-v0_19.pth
```

Expected values are Python 3.12, Kokoro `0.7.16`, CUDA `True`, and an existing checkpoint.

### Redis warning

A Redis connection warning is acceptable for local development. The application continues with its five-minute in-memory fallback.

### Microphone does not record

Use Chrome or Edge, allow microphone access for `127.0.0.1`, and click pause after speaking. The browser records locally until pause; no audio is uploaded continuously.
