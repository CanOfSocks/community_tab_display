import os
import shutil
import glob
import json
import math
from random import shuffle
import templates
import process_ytct_logs
import order
import rss

with open('config.json', 'r') as f:
    config = json.load(f)

latest_posts = []

def sort_latest_posts(posts):
    global latest_posts
    if config.get("rss_feed_amount", 0) > 0:
        latest_posts.append(posts)
        latest_posts = sorted(latest_posts, key=lambda x: x["_published"]["lastUpdatedTimestamp"], reverse=True)
        latest_posts = latest_posts[:config.get("rss_feed_amount")]


def get_picture_files(path, post_ID):
    # Create a list to store all picture files
    picture_files = []

    # List of picture extensions
    extensions = ['png', 'jpg', 'jpeg', 'gif']

    # Use glob to match the pattern 'variable*.extension'
    for ext in extensions:
        picture_files.extend(glob.glob(f"{path}/{post_ID}*.{ext}"))

    return picture_files

def get_extra_files(path, post_ID):
    files = glob.glob(f"{path}/{post_ID}*")
    #print(files)
    return files

def get_json_files(path):
    # Use glob to match the pattern '/*.json'
    json_files = glob.glob(path + '/*.json')
    return json_files

def processFolder(file_directory, html_directory, web_root_directory, ytct_log=None, sorted_posts=None, clear_log=False):
    print(f"Processing directory: {file_directory}")
    jsonFiles = get_json_files(file_directory)
    folder_name = os.path.basename(file_directory)
    posts = []
    for file in jsonFiles:
        # Add posts to array, ignore if loaded json does not have post_id field
        try:
            with open(file, 'r', encoding='utf-8') as f:
                post = json.load(f)
                if post.get("post_id", None) is None:
                    continue
                posts.append(post)

        except Exception as e:
            print(e)
    
    post_order = []
    if ytct_log is not None and sorted_posts is not None:
        post_order = process_ytct_logs.main(log_file=os.path.join(file_directory, ytct_log), json_file=os.path.join(file_directory, sorted_posts))

    posts = order.sort_posts(posts=posts,sorted_array=post_order)
    
    page = 1
    current = 1
    table_html = []
    max_pages = int(math.ceil(float(len(posts))/config.get('posts_per_page')))
       
    for idx, post in enumerate(posts):
        pictures = get_picture_files(file_directory, post['post_id'])
        files = get_extra_files(file_directory, post['post_id'])
        
        post_id_json = "{0}.json".format(post['post_id'])
        files = [
            file for file in files 
            if file not in pictures and not file.endswith(post_id_json)
        ]
        
        table_html.append(templates.makePost(post, pictures, file_directory, web_root_directory, folder_name, files))

        post['files'] = files
        
        if current % config.get('posts_per_page') == 0 or idx == len(posts) - 1:
            print("Generating page {0}".format(page))
            pagination = templates.generatePagination(page, max_pages, html_directory, folder_name, web_root_directory)
            page_html = templates.writePage(table_html, pagination)
            
            html_folder = os.path.join(html_directory, folder_name)
            os.makedirs(html_folder, exist_ok=True)
            file = os.path.join(html_folder, "{0}.html".format(page))
            with open(file, 'w', encoding='utf-8') as f:
                f.write(page_html)
            page += 1
            current = 1
            table_html = []
        current += 1
        
    home_thumbnail = ""
    home_text = ""
    home_latest = ""
    home_posts = len(posts)

    for post in posts:
        try:
            if post['author']['authorThumbnail']['thumbnails'][len(posts[0]['author']['authorThumbnail']['thumbnails'])-1]['url'] is not None and post['author']['authorText']['runs'][0]['text'] is not None and post['_published']['lastUpdatedTimestamp']:
                home_thumbnail = post['author']['authorThumbnail']['thumbnails'][len(posts[0]['author']['authorThumbnail']['thumbnails'])-1]['url']
                home_text = post['author']['authorText']['runs'][0]['text']
                home_latest = post['_published']['lastUpdatedTimestamp']
                break
        except:
            pass
    sort_latest_posts(posts)
    return home_thumbnail, home_text, home_posts, home_latest       
    

def generateHTML(files_directory, html_directory, web_root_directory, ytct_log=None, sorted_posts=None, clear_log=False):
    
    folders = []
    for root, dirs, files in os.walk(files_directory):
        #Shuffle directiories for testing
        #shuffle(dirs)
        print("Found {1} directories: {0}".format(dirs, len(dirs)))
        
        for dir in dirs:
            thumbnail, channel, count, latest = processFolder(os.path.join(root, dir), html_directory, web_root_directory, ytct_log, sorted_posts, clear_log)
            info = {
                "folder": dir.replace(web_root_directory, ''),
                "thumbnail": thumbnail,
                "channel": channel,
                "count": count,
                "latest": latest
            }
            folders.append(info)
            
    print("Generating index page")
    
    folders = sorted(folders, key=lambda x: x['folder'])
    index_html = templates.makeIndex(folders, html_directory, web_root_directory)
    file = '{0}/index.html'.format(web_root_directory)
    with open(file, 'w', encoding='utf-8') as f:
        f.write(index_html)

    if config.get("rss_feed_file", None) is not None and config.get("rss_feed_amount", 0) > 0:
        rss.create_RSS

    print("Finished")

def copyStyles(web_root_directory):
    script_file = os.path.abspath('./script.js')
    script_html = "{0}/script.js".format(web_root_directory)
    shutil.copyfile(script_file, script_html)
    
    script_file = os.path.abspath('./styles.css')
    script_html = "{0}/styles.css".format(web_root_directory)
    shutil.copyfile(script_file, script_html)

# Copy style files
copyStyles(config.get('web_root_directory'))
# Call the function with the path to your directory
generateHTML(config.get('files_directory'), config.get('html_directory'), config.get('web_root_directory'), config.get('ytct_log'), config.get('sorted_posts'), config.get('clear_log', False))
