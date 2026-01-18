import threading
from flask import Flask, jsonify, redirect, request, render_template, url_for
from yt_dlp import YoutubeDL
from pathlib import Path
import json
import twelvelabs_api as api

summary_text = ""  # global variable to store the text so far
indexed_asset = None
client = None
server = Flask(__name__)

@server.route('/')
def index():
    return render_template('index.html')

@server.route('/search-endpoint', methods=['GET'])
def search():
    global indexed_asset
    global client
    url = request.args.get('query')
    if url:
        print("Received URL:", url)
        
        #--DOWNLOADING VIDEO ------------------------------------------------
        output_dir = Path("~/uofthacks/static/videos").expanduser()
        output_dir.mkdir(exist_ok=True)

        ydl_opts = {
            "format": "bestvideo+bestaudio/best",
            "merge_output_format": "mp4",
            # "outtmpl": str(output_dir / "%(title)s.%(ext)s"),
            "outtmpl": str(output_dir / "current.%(ext)s"),
            "ffmpeg_location": r"C:\Users\janwa\ffmpeg\bin",  # <-- Add this line, adjust if your path differs
        }
        
        # with YoutubeDL(ydl_opts) as ydl:
        #     ydl.download([url])
            
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            filename = ydl.prepare_filename(info)
            print(filename)
            
            # filename = Path(ydl.prepare_filename(info)).name
                    
        
        client = api.get_client()
        index = api.get_index(client)

        indexed_assets = client.indexes.indexed_assets.list(index_id=index.id)
        for asset in indexed_assets:
            print(f"Asset: id={asset.id}, name={asset.system_metadata.filename}")
   
        indexed_asset = api.check_and_upload_video(client, index, filename)

        return redirect(url_for('display'))
    return "No URL provided", 400

# @server.route('/display')
# def display():
    
#     return render_template('display.html')

# def create_video_summary_background(client, indexed_asset):
#     global summary_text
#     summary_text = ""
#     print("trying to start stream")
#     text_stream = client.analyze_stream(
#         video_id=indexed_asset.id,
#         prompt=api.RECIPE_SUMMARY_PROMPT,
#         # temperature=0.2,
#         # max_tokens=1024,
#     )
#     print("text stream generated")
#     for text in text_stream:
#         if text.event_type == "text_generation":
#             print(text.text, end="")
#             summary_text += text.text  # append new text

# # Start the background thread somewhere (for example, on a button click)
# def start_summary_thread():
#     print("start summary thread")
#     threading.Thread(target=create_video_summary_background, args=(client, indexed_asset)).start()

@server.route('/display')
def display():
    global summary_text
    summary_text = api.create_video_summary(client, indexed_asset)
    return render_template('display.html', right=summary_text)

# @server.route('/get-summary')
# def get_summary():
#     print("get summary")
#     return jsonify({"right": summary_text})


if __name__ == "__main__":
    server.run(debug=True)
