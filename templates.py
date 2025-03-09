from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote
#import config
import json
import html
from os import path

with open('config.json', 'r') as f:
    config = json.load(f)

def pretty_html(html_page):
    
    # Parse the HTML
    soup = BeautifulSoup(html_page, 'html.parser')

    # Tags and attributes to check
    tags_and_attributes = {
        'a': 'href',
        'link': 'href',
        'img': 'src',
        'script': 'src',
        # Add more tags and their relevant attributes as needed
    }

    # Iterate over each tag and its corresponding attribute
    for tag, attribute in tags_and_attributes.items():
        for element in soup.find_all(tag, {attribute: True}):
            original_url = element[attribute]
            encoded_url = quote(original_url, safe=':/')
            element[attribute] = encoded_url

    # Print the modified HTML
    #print(soup.prettify())
    
    
    soup = soup.prettify()
    
    return str(soup)

def writePage(table_html, pagination_html):
    #print(table_html)
    html_page = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
	<link rel="stylesheet" type="text/css" href="/styles.css">
</head>
<body>
	<div class="home-button">
        <a href="/">Home</a>
    </div>
	<div class="container">
		<table>
            {0}
		</table>
		<div class="clearfix"></div>
		{1}
	</div>
	<script src="/script.js"></script>
</body>
</html>""".format(''.join(table_html), pagination_html)
    #return html_page
    
    return pretty_html(html_page)

def makePost(info, pictures, file_directory, web_root_directory, folder_name, row, files=None):
    print("Processing post: {0}".format(info['post_id']))

    # Add timestamp variable to new row
    html_page = '<tr id="{1}" data-timestamp="{0}"><td>'.format(info['_published']['lastUpdatedTimestamp'], row)
    # Add header profile picture
    if info['author']['authorThumbnail'] is None:
        html_page += '<div class="post-header"><img src="" alt="Profile Picture">'
    else:
        html_page += '<div class="post-header"><img src="{0}" alt="Profile Picture">'.format(info['author']['authorThumbnail']['thumbnails'][len(info['author']['authorThumbnail']['thumbnails'])-1]['url'])
    # Add channel name/link
    html_page += '<div><h3><a href="//www.youtube.com/channel/{0}" target="_blank" rel="noopener noreferrer">{1}</a></h3>'.format(info['channel_id'],info['author']['authorText']['runs'][0]['text'])
    # Add membership only badge if present
    if info.get('sponsor_only_badge') is not None:
        html_page += "<p><i>Members only</i></p>"
    # Close header
    html_page += "</div></div>"
    
    # Start post content
    html_page += '<div class="post-content">'
    # Join any content fields, replace newline characters with paragraph
    content_text = ""
    if info.get('content_text') is not None and info['content_text'].get('runs') is not None:
        for run in info['content_text']['runs']:
            if run.get('urlEndpoint') is not None:
                content_text += '<a href="{0}" target="_blank" rel="noopener noreferrer">{1}</a>'.format(run['urlEndpoint'].get('url'), html.escape(run['text'])).replace('\r\n', '</p><p>').replace('\n', '</p><p>')
            elif run.get('browseEndpoint') is not None:
                content_text += '<a href="//youtube.com{0}" target="_blank" rel="noopener noreferrer">{1}</a>'.format(run['browseEndpoint'].get('url'), html.escape(run['text'])).replace('\r\n', '</p><p>').replace('\n', '</p><p>')
            elif run.get('navigationEndpoint') is not None:
                content_text += '<a href="//youtube.com{0}" target="_blank" rel="noopener noreferrer">{1}</a>'.format(run['navigationEndpoint'].get('commandMetadata').get('webCommandMetadata').get('url'), html.escape(run['text'])).replace('\r\n', '</p><p>').replace('\n', '</p><p>')
            else:
                content_text += ' {0}'.format(html.escape(run['text'])).replace('\r\n', '</p><p>').replace('\n', '</p><p>')
    html_page += '<p>{0}</p>'.format(content_text)
    
    # Add any associated pictures
    i = 1
    for picture in pictures:
        path = picture.replace(web_root_directory, '')
        html_page += '<img src="/{0}" alt="Post Image {1}" loading="lazy">'.format(path,i)
        i += 1
    # Close post content div
    html_page += "</div>"
    
    # Add post footer
    if info['vote_count'] is not None:
        html_page += '<div class="post-footer"><p>{0} likes</p><a href="//www.youtube.com/channel/UCL_qhgtOy0dy1Agp8vkySQg/community?lb={1}" target="_blank" rel="noopener noreferrer">{1}</a></div>'.format(info['vote_count']['simpleText'],info['post_id'])
    
    if config.get('download_mask'):
        #Create download buttons
        html_page += '<div class="download-buttons"><a href="{0}/{1}/{2}.json">Download JSON</a>'.format(config.get('download_mask'), folder_name, info['post_id'])
        i = 1
        # If only one picture, don't include number, otherwise number buttons
        if len(pictures) == 1:
            path = pictures[0].replace(file_directory, '')
            html_page += '<a href="{0}/{1}{2}">Download Image</a>'.format(config.get('download_mask'), folder_name, path)
        else:
            for picture in pictures:
                path = picture.replace(file_directory, '')
                html_page += '<a href="{0}/{1}{2}">Download Image {3}</a>'.format(config.get('download_mask'), folder_name,path,i)
                i += 1
        i = 1
        if files:
            for file in files:
                path = file.replace(file_directory, '')
                html_page += '<a href="{0}/{1}{2}">Download File {3}</a>'.format(config.get('download_mask'), folder_name,path,i)
                i += 1
        # Close download buttons
        html_page += "</div>"
    
    # Finish row
    html_page += "</td></tr>"
    
    return html_page


def makeIndex(folder_list, html_directory, web_root_directory):
    posts_dir = html_directory.replace(web_root_directory, '')
    html_page = '<!DOCTYPE html><html><head><link rel="stylesheet" type="text/css" href="/styles.css"></head><body><div class="home-button"><a href="/">Home</a></div><div class="container"><table>'
    for folder in folder_list:
        # Add timestamp variable to new row
        if folder.get('latest'):
            html_page += '<tr data-timestamp="{0}"><td>'.format(folder.get('latest'))
        else:
            html_page += '<tr><td>'
        # Add header profile picture
        html_page += '<div class="post-header"><img src="{0}" alt="Profile Picture">'.format(folder.get('thumbnail'))
        # Add channel name/link
        html_page += '<div><h3><a href="{2}/{0}/1.html">{1}</a></h3>'.format(folder.get('folder'),folder.get('channel'), posts_dir)
        # Add post count
        html_page += '<p>{0} posts</p>'.format(folder.get('count'))
        
        # Add last updated
        html_page += '<i>Last update:</i>'
        # Close row
        html_page += '</div></div></td></tr>'
    html_page += '</table><div class="clearfix"></div></div><script src="/script.js"></script></body></html>'
    return pretty_html(html_page)


def generatePagination(page, max_pages, html_path, folder_name, web_root_directory):
    html_folder = html_path.replace(web_root_directory, '')
    html_page = '<div class="pagination"> \n'
    if page > 1:
        url = urljoin(html_folder, "{0}/{1}/{2}.html".format(html_folder, folder_name, page-1))
        html_page += '<a href="/{0}">&lt;</a>'.format(url)
    else:
        html_page += '<a> </a>'
    html_page += '<a>{0}</a>'.format(page)
    if page < max_pages:
        url = urljoin(html_folder, "{0}/{1}/{2}.html".format(html_folder, folder_name, page+1))
        html_page += '<a href="/{0}">&gt;</a>'.format(url)
    else:
        html_page += '<a> </a>'
        
    return html_page
