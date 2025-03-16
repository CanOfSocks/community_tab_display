import json
import os
import xml.etree.ElementTree as ET
from xml.dom import minidom
import mimetypes
import urllib.parse
import time
from email.utils import formatdate

def prettify(elem):
    """Return a pretty-printed XML string for the Element."""
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml()

def get_content(info):
    content_text = ""
    if info.get('content_text') is not None and info['content_text'].get('runs') is not None:
        for run in info['content_text']['runs']:
            if run.get('urlEndpoint') is not None:
                content_text += run['urlEndpoint'].get('url')
            elif run.get('browseEndpoint') is not None:
                content_text += 'https://youtube.com{0}'.format(run['browseEndpoint'].get('url'))
            elif run.get('navigationEndpoint') is not None:
                content_text += 'https://youtube.com{0}'.format(run['navigationEndpoint'].get('commandMetadata').get('webCommandMetadata').get('url'))
            else:
                content_text += ' {0}'.format(run['text'])
    return content_text

def create_RSS(posts, rss_file_path, root_dir, website_base_url="//"):
    # Create RSS root
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")

    # Add general channel info
    ET.SubElement(channel, "title").text = "YouTube Community Posts Feed"
    ET.SubElement(channel, "link").text = "https://www.youtube.com"
    ET.SubElement(channel, "description").text = "RSS Feed for multiple YouTube channels"
    ET.SubElement(channel, "lastBuildDate").text = formatdate(time.time(), usegmt=True)  # RFC-822 date format

    # Process all JSON posts
    for data in posts:
        post_id = data.get("post_id", "")
        channel_id = data.get("channel_id", "")
        channel_name = data.get("author", {}).get("authorText", {}).get("runs", [{}])[0].get("text", "")
        files = data.get("files", [])
        timestamp = data.get("_published", {}).get("lastUpdatedTimestamp", 0)

        # Generate post link
        post_link = "{0}#{1}".format(
            urllib.parse.quote("{0}posts/{1}/{2}.html".format(
                website_base_url, data.get('index', {}).get('path', ""),
                data.get('index', {}).get('page', "")
            ), safe=":/?=&"),
            data.get('index', {}).get('row', 0)
        )

        # Convert timestamp to RFC-822 format
        pub_date = formatdate(timestamp, usegmt=True) if timestamp else formatdate(time.time(), usegmt=True)

        # Get content safely wrapped in CDATA
        description = get_content(data)

        # Create an RSS item
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = channel_name  # Use channel name as title
        ET.SubElement(item, "channel_id").text = channel_id  # Include channel ID
        ET.SubElement(item, "link").text = post_link  # Post link
        ET.SubElement(item, "guid", isPermaLink="false").text = post_id  # Unique post ID
        ET.SubElement(item, "pubDate").text = pub_date
        ET.SubElement(item, "description").text = description  # Wrapped in CDATA

        # Add file attachments
        for file_path in files:
            mime_type, _ = mimetypes.guess_type(file_path)
            file_path = file_path.replace(root_dir, website_base_url)
            if not mime_type:
                mime_type = "application/octet-stream"  # Default MIME type if unknown
            ET.SubElement(item, "enclosure", type=mime_type, url=urllib.parse.quote(file_path, safe=":/?=&"))

    # Ensure output directory exists
    os.makedirs(os.path.dirname(rss_file_path), exist_ok=True)

    # Pretty print and save XML
    rss_content = prettify(rss)  # Ensure this function properly formats XML
    with open(rss_file_path, 'w', encoding='utf-8') as f:
        f.write(rss_content)

    print(f"RSS feed generated: {rss_file_path}")

