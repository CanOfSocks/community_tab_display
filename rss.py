import json
import os
import xml.etree.ElementTree as ET
import mimetypes

def create_RSS(posts, rss_file_path, root_dir, website_base_url=""):
    # Create RSS root
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")

    # Add general channel info
    ET.SubElement(channel, "title").text = "YouTube Community Posts Feed"
    ET.SubElement(channel, "link").text = "https://www.youtube.com"
    ET.SubElement(channel, "description").text = "RSS Feed for multiple YouTube channels"

    # Process all JSON files in the directory
    for data in posts:

        # Extract required fields
        post_id = data.get("post_id", "")
        channel_id = data.get("channel_id", "")
        channel_name = data.get("author", {}).get("authorText", {}).get("runs", [{}])[0].get("text", "")
        files = data.get("files", [])

        # Extract required fields
        post_id = data.get("post_id", "")
        channel_id = data.get("channel_id", "")
        channel_name = data.get("author", {}).get("authorText", {}).get("runs", [{}])[0].get("text", "")
        files = data.get("files", [])

        # Create an item for each post
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "post_id").text = post_id
        ET.SubElement(item, "channel_id").text = channel_id
        ET.SubElement(item, "channel_name").text = channel_name

        # Add file locations
        for file_path in files:
            mime_type, _ = mimetypes.guess_type(file_path)
            file_path = file_path.replace(root_dir,website_base_url)
            if not mime_type:
                mime_type = "application/octet-stream"  # Default if unknown
            ET.SubElement(item, "file", type=mime_type).text = file_path

    # Convert XML to string
    xml_str = ET.tostring(rss, encoding="utf-8").decode()

    os.makedirs(os.path.dirname(rss_file_path), exist_ok=True)
    with open(rss_file_path, "w", encoding="utf-8") as f:
        f.write(xml_str)

    print(f"RSS feed generated: {rss_file_path}")
