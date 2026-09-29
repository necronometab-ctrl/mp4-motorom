from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import os, uuid, subprocess, tempfile, shutil, traceback

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"], allow_credentials=False)

@app.get("/")
def root():
    return {"status":"ok - motor el"}

@app.post("/convert")
async def convert(audio: UploadFile = File(...), image: UploadFile = File(None), bg_color: str = Form("#070708"), resolution: str = Form("720p"), mode: str = Form("waveform")):
    try:
        tmpdir = tempfile.mkdtemp()
        audio_path = os.path.join(tmpdir, "in" + os.path.splitext(audio.filename or ".mp3")[1])
        with open(audio_path, "wb") as f:
            shutil.copyfileobj(audio.file, f)

        size = os.path.getsize(audio_path)
        print(f"Audio {size} bytes")
        if size > 15*1024*1024:
            return JSONResponse({"error":"Tul nagy file! Max 15MB a free tieren. Probald kisebb mp3-al"}, status_code=413)

        image_path = None
        if image and getattr(image, 'filename', None):
            image_path = os.path.join(tmpdir, "cover.jpg")
            with open(image_path, "wb") as f:
                f.write(await image.read())

        out = os.path.join(tmpdir, "out.mp4")
        W,H = (640,360) # Kicsi felbontas hogy ne haljon meg a 512MB RAM

        if image_path:
            cmd = ["ffmpeg","-y","-loop","1","-i",image_path,"-i",audio_path,"-vf",f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color={bg_color.replace('#','0x')},format=yuv420p","-c:v","libx264","-preset","ultrafast","-crf","30","-c:a","aac","-b:a","96k","-shortest","-movflags","+faststart",out]
        else:
            cmd = ["ffmpeg","-y","-f","lavfi","-i",f"color=c={bg_color}:s={W}x{H}:d=10","-i",audio_path,"-c:v","libx264","-preset","ultrafast","-crf","30","-c:a","aac","-b:a","96k","-shortest","-movflags","+faststart","-vf","format=yuv420p",out]

        print("CMD:", " ".join(cmd))
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if r.returncode!=0:
            print(r.stderr[-2000:])
            return JSONResponse({"error": r.stderr[-2000:]}, status_code=500)

        return FileResponse(out, filename="konvertalt.mp4", media_type="video/mp4")
    except subprocess.TimeoutExpired:
        return JSONResponse({"error":"Timeout - tul hosszu zene vagy tul nagy file free tieren"}, status_code=504)
    except Exception as e:
        print(traceback.format_exc())
        return JSONResponse({"error": str(e)}, status_code=500)
