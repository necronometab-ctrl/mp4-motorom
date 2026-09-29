import os, uuid, subprocess, tempfile
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False
)

@app.get("/")
def root():
    return {"status":"ok - tavoli ffmpeg motor megy"}

@app.post("/convert")
async def convert(
    audio: UploadFile = File(...),
    image: UploadFile = File(None),
    bg_color: str = Form("#070708"),
    resolution: str = Form("720p"),
    mode: str = Form("waveform")
):
    tmpdir = tempfile.mkdtemp()
    audio_path = os.path.join(tmpdir, "audio" + os.path.splitext(audio.filename)[1])
    with open(audio_path, "wb") as f:
        f.write(await audio.read())

    image_path = None
    if image and image.filename:
        image_path = os.path.join(tmpdir, "cover" + os.path.splitext(image.filename)[1])
        with open(image_path, "wb") as f:
            f.write(await image.read())

    W, H = (1080, 1920) if resolution == "1080p_portrait" else (1280, 720)
    output_path = os.path.join(tmpdir, f"{uuid.uuid4().hex}.mp4")
    bg = bg_color.replace("#","0x")

    if image_path:
        if mode == "waveform":
            filter_c = f"[0:v]scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color={bg}[base];[1:a]showwaves=s={W}x200:mode=line:colors=white:draw=full,format=rgba[wave];[base][wave]overlay=0:{H}-200:format=auto,format=yuv420p[v]"
            cmd = ["ffmpeg","-y","-loop","1","-i",image_path,"-i",audio_path,"-filter_complex",filter_c,"-map","[v]","-map","1:a","-c:v","libx264","-c:a","aac","-b:a","192k","-shortest","-movflags","+faststart",output_path]
        else:
            vf = f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color={bg},format=yuv420p"
            cmd = ["ffmpeg","-y","-loop","1","-i",image_path,"-i",audio_path,"-vf",vf,"-c:v","libx264","-c:a","aac","-b:a","192k","-shortest","-movflags","+faststart",output_path]
    else:
        if mode == "waveform":
            filter_c = f"color=c={bg_color}:s={W}x{H}[base];[1:a]showwaves=s={W}x200:mode=line:colors=white:draw=full,format=rgba[wave];[base][wave]overlay=0:{H}-200:format=auto,format=yuv420p[v]"
            cmd = ["ffmpeg","-y","-f","lavfi","-i",f"color=c={bg_color}:s={W}x{H}","-i",audio_path,"-filter_complex",filter_c,"-map","[v]","-map","1:a","-c:v","libx264","-c:a","aac","-b:a","192k","-shortest","-movflags","+faststart",output_path]
        else:
            cmd = ["ffmpeg","-y","-f","lavfi","-i",f"color=c={bg_color}:s={W}x{H}:d=10","-i",audio_path,"-c:v","libx264","-c:a","aac","-b:a","192k","-shortest","-movflags","+faststart","-vf","format=yuv420p",output_path]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode!= 0:
        return {"error": result.stderr[-3000:]}
    return FileResponse(output_path, filename="konvertalt.mp4", media_type="video/mp4")
