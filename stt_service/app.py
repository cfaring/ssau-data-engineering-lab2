import os
import tempfile
from pathlib import Path
from typing import Iterable

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from faster_whisper import WhisperModel

app = FastAPI(title="STT server", version="1.0.0")

MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "small")
MODEL_DIR = os.getenv("WHISPER_MODEL_DIR")
COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
DEVICE = os.getenv("WHISPER_DEVICE", "cpu")


def load_model() -> WhisperModel:
    source = MODEL_DIR or MODEL_SIZE
    return WhisperModel(
        source,
        device=DEVICE,
        compute_type=COMPUTE_TYPE,
    )


model = load_model()


def format_timestamp(seconds: float) -> str:
    total_milliseconds = int(seconds * 1000)
    hours, remainder = divmod(total_milliseconds, 3600 * 1000)
    minutes, remainder = divmod(remainder, 60 * 1000)
    secs, milliseconds = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{milliseconds:03}"


def segments_to_srt(segments: Iterable) -> str:
    srt_blocks = []
    for idx, segment in enumerate(segments, start=1):
        start = format_timestamp(segment.start)
        end = format_timestamp(segment.end)
        text = segment.text.strip()
        srt_blocks.append(f"{idx}\n{start} --> {end}\n{text}")
    return "\n\n".join(srt_blocks)


@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    suffix = Path(file.filename or "audio.wav").suffix or ".wav"
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            contents = await file.read()
            tmp.write(contents)
            tmp_path = tmp.name

        segments, _ = model.transcribe(
            tmp_path,
            beam_size=int(os.getenv("WHISPER_BEAM_SIZE", "5")),
            vad_filter=True,
            temperature=0,
        )
        srt_text = segments_to_srt(segments)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if "tmp_path" in locals() and os.path.exists(tmp_path):
            os.remove(tmp_path)

    return JSONResponse({"data": srt_text})
