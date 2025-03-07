import os
import shutil
import glob
import json
import config
import math
from random import shuffle
import templates



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

def processFolder(file_directory, html_directory, web_root_directory):
    print(f"Processing directory: {file_directory}")
    jsonFiles = get_json_files(file_directory)
    folder_name = os.path.basename(file_directory)
    posts = []
    for file in jsonFiles:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                post = json.load(f)
                if post.get("post_id", None) is None:
                    continue
                posts.append(post)
        except Exception as e:
            print(e)
    posts.sort(key=lambda x: x.get('_published', {}).get('lastUpdatedTimestamp'), reverse=True)
    
    page = 1
    current = 1
    table_html = []
    max_pages = int(math.ceil(float(len(posts))/config.posts_per_page))
       
    for idx, post in enumerate(posts):
        pictures = get_picture_files(file_directory, post['post_id'])
        files = get_extra_files(file_directory, post['post_id'])
        
        post_id_json = "{0}.json".format(post['post_id'])
        files = [
            file for file in files 
            if file not in pictures and not file.endswith(post_id_json)
        ]
        
        table_html.append(templates.makePost(post, pictures, file_directory, web_root_directory, folder_name, files))
        
        if current % config.posts_per_page == 0 or idx == len(posts) - 1:
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
    return home_thumbnail, home_text, home_posts, home_latest       
    

def generateHTML(files_directory, html_directory, web_root_directory):
    
    folders = []
    for root, dirs, files in os.walk(files_directory):
        #Shuffle directiories for testing
        #shuffle(dirs)
        print("Found {1} directories: {0}".format(dirs, len(dirs)))
        
        for dir in dirs:
            thumbnail, channel, count, latest = processFolder(os.path.join(root, dir), html_directory, web_root_directory)
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
    print("Finished")

def copyStyles(web_root_directory):
    script_file = os.path.abspath('./script.js')
    script_html = "{0}/script.js".format(web_root_directory)
    shutil.copyfile(script_file, script_html)
    
    script_file = os.path.abspath('./styles.css')
    script_html = "{0}/styles.css".format(web_root_directory)
    shutil.copyfile(script_file, script_html)

# Copy style files
copyStyles(config.web_root_directory)
# Call the function with the path to your directory
generateHTML(config.files_directory, config.html_directory, config.web_root_directory)
