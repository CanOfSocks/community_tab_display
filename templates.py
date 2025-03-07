from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote
import config
import html
from os import path

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
        {0}
		<div class="clearfix"></div>
		{1}
	</div>
	<script src="/script.js"></script>
</body>
</html>""".format(''.join(table_html), pagination_html)
    #return html_page
    
    return pretty_html(html_page)

def makePost(info, pictures, file_directory, web_root_directory, folder_name, files=None):
    print("Processing post: {0}".format(info['post_id']))

    # Start post container div
    html_page = '<div class="post" data-timestamp="{0}">'.format(info['_published']['lastUpdatedTimestamp'])

    # Add header with profile picture and channel name
    html_page += '<div class="post-header">'
    if info['author']['authorThumbnail'] is None:
        html_page += '<img src="" alt="Profile Picture" loading="lazy">'
    else:
        html_page += '<img src="{0}" alt="Profile Picture" loading="lazy">'.format(
            info['author']['authorThumbnail']['thumbnails'][-1]['url']
        )

    html_page += '<div><h3><a href="//www.youtube.com/channel/{0}" target="_blank" rel="noopener noreferrer">{1}</a></h3>'.format(
        info['channel_id'], info['author']['authorText']['runs'][0]['text']
    )

    # Add membership badge if applicable
    if info.get('sponsor_only_badge'):
        html_page += "<p><i>Members only</i></p>"

    html_page += "</div></div>"  # Close header div

    # Post content
    html_page += '<div class="post-content">'
    content_text = ""

    if info.get('content_text') and info['content_text'].get('runs'):
        for run in info['content_text']['runs']:
            text = html.escape(run.get('text', ''))
            if run.get('urlEndpoint'):
                content_text += '<a href="{0}" target="_blank" rel="noopener noreferrer">{1}</a>'.format(
                    run['urlEndpoint']['url'], text
                )
            elif run.get('browseEndpoint'):
                content_text += '<a href="//youtube.com{0}" target="_blank" rel="noopener noreferrer">{1}</a>'.format(
                    run['browseEndpoint']['url'], text
                )
            elif run.get('navigationEndpoint'):
                content_text += '<a href="//youtube.com{0}" target="_blank" rel="noopener noreferrer">{1}</a>'.format(
                    run['navigationEndpoint']['commandMetadata']['webCommandMetadata']['url'], text
                )
            else:
                content_text += " " + text

    html_page += '<p>{0}</p>'.format(content_text)

    # Add images with lazy loading
    for i, picture in enumerate(pictures, start=1):
        path = picture.replace(web_root_directory, '')
        html_page += '<img src="/{0}" alt="Post Image {1}" loading="lazy">'.format(path, i)

    html_page += "</div>"  # Close post-content div

    # Post footer (likes and link)
    if info['vote_count']:
        html_page += '<div class="post-footer">'
        html_page += '<p>{0} likes</p>'.format(info['vote_count']['simpleText'])
        html_page += '<a href="//www.youtube.com/channel/UCL_qhgtOy0dy1Agp8vkySQg/community?lb={1}" target="_blank" rel="noopener noreferrer">{1}</a>'.format(
            info['vote_count']['simpleText'], info['post_id']
        )
        html_page += "</div>"

    # Download buttons
    if config.download_mask:
        html_page += '<div class="download-buttons">'
        html_page += '<a href="{0}/{1}/{2}.json">Download JSON</a>'.format(config.download_mask, folder_name, info['post_id'])

        if pictures:
            for i, picture in enumerate(pictures, start=1):
                path = picture.replace(file_directory, '')
                label = "Download Image" if len(pictures) == 1 else f"Download Image {i}"
                html_page += '<a href="{0}/{1}{2}">{3}</a>'.format(config.download_mask, folder_name, path, label)

        if files:
            for i, file in enumerate(files, start=1):
                path = file.replace(file_directory, '')
                html_page += '<a href="{0}/{1}{2}">Download File {3}</a>'.format(config.download_mask, folder_name, path, i)

        html_page += "</div>"  # Close download-buttons div

    html_page += "</div>"  # Close post div

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
