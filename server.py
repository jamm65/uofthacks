import threading
from flask import Flask, jsonify, redirect, request, render_template, url_for
from yt_dlp import YoutubeDL
from pathlib import Path
import json
import twelvelabs_api as api
from dotenv import load_dotenv

summary_text = "Generating Summary..."  # global variable to store the text so far
summary_finished = False  # flag to indicate if summary generation is complete
search_finished = False  # flag to indicate if search is complete
index = None
indexed_asset = None
client = None
filename = ""
server = Flask(__name__)
start = 0
end = 10

load_dotenv()

@server.route('/')
def index():
    return render_template('index.html')

@server.route('/search-endpoint', methods=['GET'])
def search():
    global index, indexed_asset, client, filename

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
            "outtmpl": str(output_dir / "%(title)s.%(ext)s"),
            "ffmpeg_location": r"C:\ffmpeg-8.0.1-essentials_build\bin",  # <-- Add this line, adjust if your path differs
        }
            
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            # filename = ydl.prepare_filename(info)
            filename = Path(ydl.prepare_filename(info)).name
            print(filename)        
        
        client = api.get_client()
        index = api.get_index(client)

        indexed_assets = client.indexes.indexed_assets.list(index_id=index.id)
        for asset in indexed_assets:
            print(f"Asset: id={asset.id}, name={asset.system_metadata.filename}")
   
        indexed_asset = api.check_and_upload_video(client, index, filename)

        return redirect(url_for('display'))
    return "No URL provided", 400


def create_video_summary_background(client, indexed_asset):
    global summary_text
    global summary_finished
    summary_text = ""
    print("trying to start stream")
    text_stream = client.analyze_stream(
        video_id=indexed_asset.id,
        prompt=api.RECIPE_SUMMARY_PROMPT,
        # temperature=0.2,
        # max_tokens=1024,
    )
    print("text stream generated")
    for text in text_stream:
        if text.event_type == "text_generation":
            if (summary_text == "Generating Summary..."):
                summary_text = ""  # reset initial text
            print(text.text, end="")
            summary_text += text.text  # append new text
    summary_finished = True

# Start the background thread somewhere (for example, on a button click)
def start_summary_thread():
    global summary_finished
    summary_finished = False
    print("start summary thread")
    threading.Thread(target=create_video_summary_background, args=(client, indexed_asset)).start()

@server.route('/display')
def display():
    start_summary_thread()
    return render_template('display.html', filename=filename)

@server.route('/get-summary')
def get_summary():
    print("get summary")
    return jsonify({"bottom_left": "", "right": summary_text, "finished": summary_finished})

def search_video(user_query):
    global start, end, search_finished
    print("search video")
    query = user_query
    search_results = client.search.query(
        index_id=index.id,
        query_text=query, # Example: "Steve Jobs"
        search_options=["visual", "audio"],
        operator="or", # Optional: Use "and" to find segments matching all modalities
        # transcription_options=["lexical", "semantic"]  # Optional: Control transcription matching (Marengo 3.0 only, requires "transcription" in search_options)
        filter=json.dumps({"id":[indexed_asset.id]})
    )

    print("\nSearch results:")
    if search_results:
        clip = search_results.items[0]
        start = max(clip.start - 3, 0)
        end = clip.end + 3
        print(f"Result 1:")
        print(f"  Rank: {clip.rank}")
        print(f"  Time: {start} - {end} seconds")
        print()
    search_finished = True
    print("search finished")

@server.route('/search-video', methods=['POST'])
def start_search_video_thread():
    global search_finished
    search_finished = False
    print("start search video thread")
    query = request.json.get('query', '')
    threading.Thread(target=search_video, args=(query,)).start()
    return jsonify({"status": "search started"})

@server.route('/get-search-result')
def get_search_result():
    global start, end, search_finished
    print("get search result")
    return jsonify({"finished" : search_finished, "start": start, "end": end})


if __name__ == "__main__":
    server.run(debug=True)
