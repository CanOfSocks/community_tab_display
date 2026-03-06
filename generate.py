
import glob
import json
from pathlib import Path
import database
import os
import posixpath

from pathlib import Path
import argparse

import logging

config = {}

latest_posts = []

existing = set()

def sort_latest_posts(posts):
    global latest_posts
    if config.get("rss_feed_amount", 0) > 0:
        latest_posts += posts
        sorted_posts = sorted(latest_posts, key=lambda x: x["_published"]["lastUpdatedTimestamp"], reverse=True)
        latest_posts = sorted_posts[:config.get("rss_feed_amount")]


def get_relative_to_web_root(files_path, web_root):
    """
    Returns the path of files_path relative to web_root, 
    formatted as a web-standard POSIX path with a leading slash.
    """
    # 1. Resolve to absolute paths to ensure the comparison is accurate
    p = Path(files_path).resolve()
    root = Path(config.get("post_root")).resolve()
    
    try:
        # 2. Get the relative portion
        relative = p.relative_to(root)
        
        # 3. Use posixpath.join and .as_posix() for clean formatting.
        # posixpath.normpath ensures that if relative is ".", it returns "/"
        web_path = posixpath.join(config.get("web_root"), relative.as_posix())
        return posixpath.normpath(web_path)
        
    except ValueError:
        # Case: files_path is not under web_root. 
        # Returns absolute POSIX path (e.g., C:/temp or /var/log)
        return p.as_posix()

def get_picture_files(path, post_ID, web_root):
    """
    Returns a list of picture files (png, jpg, jpeg, gif)
    relative to the web root.
    """
    picture_files = []
    extensions = ['png', 'jpg', 'jpeg', 'gif']

    for ext in extensions:
        for f in glob.glob(f"{path}/{post_ID}*.{ext}"):
            picture_files.append(get_relative_to_web_root(f, web_root))
    
    return picture_files

def get_extra_files(path, post_ID, web_root):
    """
    Returns a list of all files matching post_ID* relative to the web root.
    """
    files = []
    for f in glob.glob(f"{path}/{post_ID}*"):
        files.append(get_relative_to_web_root(f, web_root))
    return files

def get_json_files(path, web_root):
    """
    Returns a list of all JSON files in a path relative to the web root.
    """
    json_files = []
    for f in glob.glob(f"{path}/*.json"):
        json_files.append(get_relative_to_web_root(f, web_root))
    return json_files


def process_file(file):
    
    post = {}
    with open(file, 'r', encoding='utf-8') as f:
        post = json.load(f)
        if isinstance(post, list):
            logging.warning("Post is list (possibly sorted list?) returning...")
            return
        if post.get("post_id", None) is None:
            raise ValueError("unable to find post id, JSON is not valid")
        
    if existing and post.get("post_id") in existing:
        return
        
    json_files = [get_relative_to_web_root(file, config.get("web_root"))]

    picture_files = get_picture_files(path=os.path.dirname(file), post_ID=post.get("post_id"), web_root=config.get("web_root"))

    extra_files = get_extra_files(path=os.path.dirname(file), post_ID=post.get("post_id"), web_root=config.get("web_root"))

    extra_files = list(set(extra_files) - set(json_files) - set(picture_files))

    database.store_post(info=post, pictures=picture_files, json_files=json_files, files=extra_files)

def main(config_file="", ignore_existing=False):
    if not config_file:
        raise ValueError("No config file specified")
    global config
    with open(config_file, 'r', encoding="utf-8") as f:
        config = json.load(f)

    # Create SQL tables if they don't exist
    database.Base.metadata.create_all(database.engine)
    # Set the root directory
    root_dir = Path(config.get("post_root"))

    # Recursively find all .json files
    json_files = list(root_dir.rglob('*.json'))

    if ignore_existing:
        global existing
        existing = database.get_existing_posts()

    logging.info("Found {0} posts".format(len(json_files)))
    for file in json_files:
        try:
            process_file(file)
        except Exception as e:
            logging.exception("Error occurred processing json: {0} - {1}".format(file, e))

if __name__ == "__main__":
    # Create the parser
    parser = argparse.ArgumentParser(description="Loader")

    parser.add_argument('config', type=str, default="config.json", help='Config File Location')

    parser.add_argument('--skip-existing', action='store_true', help="Skip posts existing in database")
    
    # Parse the arguments
    args = parser.parse_args()

    main(config_file=args.config, ignore_existing=args.skip_existing)