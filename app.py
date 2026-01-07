from flask import Flask, render_template, request, abort, make_response, send_from_directory, make_response, Response
from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache
from flask_compress import Compress
from sqlalchemy import func, desc
from datetime import datetime
import time
import logging
import json
import os
from dotenv import load_dotenv

import urllib.parse
# Import your existing models
# Assuming models are in a file named models.py, otherwise paste them here.
from database import Base, CommunityPost, PostContentBlock, PostAttachment

app = Flask(__name__)

load_dotenv()
# --- Configuration ---
# Update URI to your actual database
app.config['SQLALCHEMY_DATABASE_URI']  = os.getenv('DATABASE_URL') 
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 280,  # Recycle connections before the DB timeout (usually 300s)
}

# Cache Config (Simple in-memory cache for demonstration)
# For production, use 'redis' or 'memcached'
app.config['CACHE_TYPE'] = 'SimpleCache' 
app.config['CACHE_DEFAULT_TIMEOUT'] = 1800  # 30 minutes server-side default

# Init extensions
db = SQLAlchemy(app, model_class=Base)
cache = Cache(app)

app.config['COMPRESS_MIN_SIZE'] = 5000
Compress(app)

# --- Helper to add Cache-Control headers ---
def add_cache_headers(response, max_age=3600, must_revalidate=False):
    """Adds client-side caching headers with optional 'must-revalidate'."""
    cache_control = f'public, max-age={max_age}'
    if must_revalidate:
        cache_control += ', must-revalidate'
    response.headers['Cache-Control'] = cache_control
    return response


# --- Routes ---

@app.route('/')
@cache.cached(timeout=1800) # Server-side cache: 30 mins
def index():
    """
    Home Page: Lists authors with their latest post details.
    Optimized to fetch latest profile pic and timestamp per channel.
    """
    # Subquery 1: Get the latest timestamp for each channel
    latest_posts_sub = db.session.query(
        CommunityPost.channel_id,
        func.max(CommunityPost.timestamp).label('max_ts')
    ).group_by(CommunityPost.channel_id).subquery()

    # Subquery 2: Count total posts per channel
    count_sub = db.session.query(
        CommunityPost.channel_id,
        func.count(CommunityPost.post_id).label('post_count')
    ).group_by(CommunityPost.channel_id).subquery()

    # Main Query: Join CommunityPost with the subqueries to get full details of the latest post
    # We join on channel_id AND timestamp to get the specific row that is the "latest"
    authors = db.session.query(
        func.distinct(CommunityPost.channel_id).label('channel_id'),
        CommunityPost.channel_name,
        CommunityPost.profile_pic_url,
        CommunityPost.timestamp,
        count_sub.c.post_count
    ).join(
        latest_posts_sub, 
        (CommunityPost.channel_id == latest_posts_sub.c.channel_id) & 
        (CommunityPost.timestamp == latest_posts_sub.c.max_ts)
    ).join(
        count_sub,
        CommunityPost.channel_id == count_sub.c.channel_id
    ).order_by(desc(CommunityPost.timestamp)).all()

    response = make_response(render_template('index.html', authors=authors))
    return add_cache_headers(response)


@app.route('/channel/<channel_id>')
@cache.cached(timeout=1800, query_string=True) # Cache based on URL params too
def channel_page(channel_id):
    """
    Channel Page: Paginated posts for a specific author.
    """
    # Pagination Logic
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    
    # Enforce Hard Limit
    if limit > 30: limit = 30
    if limit < 1: limit = 1

    # Query
    query = db.session.query(CommunityPost)\
        .filter(CommunityPost.channel_id == channel_id)\
        .order_by(desc(CommunityPost.timestamp))
    
    # Use SQLAlchemy pagination
    # error_out=False returns empty list instead of 404 on out of range, 
    # but we handle empty items manually below.
    pagination = query.paginate(page=page, per_page=limit, error_out=False)

    if not pagination.items and page != 1:
        # If page > 1 and no items, it's a 404
        abort(404)
    elif not pagination.items and page == 1:
        # If page 1 has no items, the channel probably doesn't exist
        abort(404)

    response = make_response(render_template(
        'channel_posts.html', 
        posts=pagination.items, 
        pagination=pagination, 
        channel_id=channel_id,
        channel_name=pagination.items[0].channel_name if pagination.items else "Unknown"
    ))
    return add_cache_headers(response)


@app.route('/post/<post_id>')
@cache.cached(timeout=1800)
def single_post(post_id):
    """
    Single Post Page: Loads a specific post.
    """
    post = db.session.query(CommunityPost).filter(CommunityPost.post_id == post_id).first()
    
    if not post:
        abort(404)

    response = make_response(render_template('single_post.html', post=post))
    return add_cache_headers(response)

@app.route('/style.css')
def serve_css():
    return add_cache_headers(make_response(send_from_directory('static', 'style.css')), max_age=3600, must_revalidate=True)

@app.route('/script.js')
def serve_js():
    return add_cache_headers(make_response(send_from_directory('static', 'script.js')), max_age=3600, must_revalidate=True)

@app.route('/favicon.ico')
def favicon():
    try:
        return add_cache_headers(make_response(send_from_directory('static', 'favicon.ico')), max_age=3600, must_revalidate=True)
    except FileNotFoundError:
        abort(404)

@app.route('/files/<path:filename>')
def serve_file(filename):
    """
    Serves files under /files directory.
    - Preserves subdirectory structure.
    - If ?download=true, serves as an attachment.
    """
    download = request.args.get('download', 'false').lower() == 'true'

    try:
        response = make_response(send_from_directory('files', filename, as_attachment=download))
        return add_cache_headers(response, max_age=3600, must_revalidate=True)
    except FileNotFoundError:
        abort(404)


from email import utils
import mimetypes

@app.template_filter('get_mime_type')
def get_mime_type(path: str) -> str:
    mime_type, _ = mimetypes.guess_file_type(path)
    return mime_type or "application/octet-stream"

@app.route('/rss/rss.xml')
@cache.cached(timeout=1800)
def rss_feed():
    posts = (
        db.session.query(CommunityPost)
        .order_by(desc(CommunityPost.timestamp))
        .limit(100)
        .all()
    )

    last_build_date = (
        utils.format_datetime(posts[0].timestamp)
        if posts else
        utils.format_datetime(datetime.now())
    )

    xml_body = render_template(
        'rss.xml',
        posts=posts,
        last_build_date=last_build_date,
        format_date=utils.format_datetime,
        get_mime_type=get_mime_type
    )

    return add_cache_headers(Response(xml_body, mimetype="application/rss+xml"))

@app.template_filter('quote_url')
def quote_url(url):
    if not url:
        return ""
    # Handle Windows backslashes and already-encoded backslashes
    if os.path.sep == "\\":
        url = url.replace("\\", "/")
        url = url.replace("%5C", "/")
    
    # Encode special characters but keep / safe
    return urllib.parse.quote(url, safe='/')

if __name__ == '__main__':
    app.run(debug=True, port=os.getenv("FLASK_RUN_PORT", 5000))