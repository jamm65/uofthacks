import json
import os
import time
from dotenv import load_dotenv
from twelvelabs import TwelveLabs

load_dotenv()

# Initialize Twelve Labs API
API_KEY = os.getenv("TWELVE_LABS_API_KEY")
INDEX_NAME = "recipe"
RECIPE_SUMMARY_PROMPT = "List ingredients used, and appliances needed. Summarize this video into a recipe instruction, do not list more than 10 steps."

def get_index(client):
    # from index list, get recipe index id
    indexes = client.indexes.list()

    if not indexes:
        print("No indexes found.")
    else:
        # print("Your indexes and their IDs:")
        for idx in indexes:
            # print(f"- Name: {idx.index_name}, ID: {idx.id}")
            if (idx.index_name == INDEX_NAME):
                recipe_index = idx

    if not recipe_index.id:
        raise RuntimeError("Failed to get the index.")
    print(f"Got index: {recipe_index.index_name}")
    return recipe_index

def get_client():
    return TwelveLabs(api_key=API_KEY)

def check_and_upload_video(client, index, file_name: str) -> object:
    # check if the video is already uploaded as indexed asset
    indexed_assets = client.indexes.indexed_assets.list(index_id=index.id)
    existing_indexed = [a for a in indexed_assets if a.system_metadata.filename == file_name]
    if existing_indexed:
        indexed_asset_id = existing_indexed[0].id
        print(f"{file_name} already indexed: {indexed_asset_id}")
        return existing_indexed[0]
    else:
        print(f"{file_name} not found, uploading...")
        return upload_video(client, index, file_name)

def upload_video(client, index, file_name: str):
    # create the asset
    asset = client.assets.create(
        method="direct",
        file=open(file_name, "rb")
    )
    print(f"Created asset: id={asset.id}")

    return index_video(client, index.id, asset.id)

def index_video(client, index_id, asset_id):
    # create the indexed asset
    indexed_asset = client.indexes.indexed_assets.create(
        index_id=index_id,
        asset_id=asset_id,
        enable_video_stream=True
    )
    print(f"Created indexed asset: id={indexed_asset.id}")

    # wait for indexing to complete
    print("Waiting for indexing to complete.")
    while True:
        indexed_asset = client.indexes.indexed_assets.retrieve(
            index_id=index_id,
            indexed_asset_id=indexed_asset.id
        )
        print(f"  Status={indexed_asset.status}")
        if indexed_asset.status == "ready":
            print("Indexing complete!")
            break
        elif indexed_asset.status == "failed":
            raise RuntimeError("Indexing failed")
        time.sleep(5)
    return indexed_asset

def create_video_summary(client, indexed_asset):
    print("\nGenerating video summary...\n")
    summary_text = ""
    text_stream = client.analyze_stream(
        video_id=indexed_asset.id,
        prompt=RECIPE_SUMMARY_PROMPT, # Example: "Summarize this video"
        # temperature=0.2,
        # max_tokens=1024,
    )

    for text in text_stream:
        if text.event_type == "text_generation":
            summary_text += text.text
            print(text.text, end="")
    print()
    return summary_text


def main():

    # video_url = input("Enter video URL: ")
    client = get_client()
    index = get_index(client)

    indexed_assets = client.indexes.indexed_assets.list(index_id=index.id)
    for asset in indexed_assets:
        print(f"Asset: id={asset.id}, name={asset.system_metadata.filename}")
   
    indexed_asset = check_and_upload_video(client, index, "test video.mp4")
    # create_video_summary(client, indexed_asset)

    while True:
        query = input("\nEnter search query (or 'quit' to exit): ")
        if query.lower() == "quit":
            break
       
        search_results = client.search.query(
            index_id=index.id,
            query_text=query, # Example: "Steve Jobs"
            search_options=["visual", "audio"],
            operator="or", # Optional: Use "and" to find segments matching all modalities
            # transcription_options=["lexical", "semantic"]  # Optional: Control transcription matching (Marengo 3.0 only, requires "transcription" in search_options)
            filter=json.dumps({"id":[indexed_asset.id]})
        )

        print("\nSearch results:")
        print("Each result shows a video clip that matches your query:\n")
        for i, clip in enumerate(search_results):
            start_min = int(clip.start // 60)
            start_sec = int(clip.start % 60)
            end_min = int(clip.end // 60)
            end_sec = int(clip.end % 60)
            if (i >= 5):
                break
            print(f"Result {i + 1}:")
            print(f"  Video Name: {clip.video_id}")  # Unique identifier of the video
            print(f"  Rank: {clip.rank}")  # Relevance ranking (1 = most relevant)
            print(f"  Time: {start_min}m {start_sec}s - {end_min}m {end_sec}s")  # When this moment occurs in the video
            print()
   
    print("Exiting program.")


if __name__ == "__main__":
    main()
