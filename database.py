import sys
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, String, Text, Integer, Boolean, DateTime, ForeignKey, select
)
from sqlalchemy.orm import relationship, sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import IntegrityError
from sqlalchemy.dialects.mysql import insert

import logging

import os
from dotenv import load_dotenv
load_dotenv()
# --- 1. Database Setup ---
# Using SQLite for this example, but you can swap the connection string for MySQL/Postgres
DATABASE_URL = os.getenv('DATABASE_ADMIN_URL', os.getenv('DATABASE_URL')) 
Base = declarative_base()

# --- 2. Define Models ---

class CommunityPost(Base):
    __tablename__ = 'community_posts'

    post_id = Column(String(50), primary_key=True)
    channel_id = Column(String(24), nullable=False)
    channel_name = Column(Text)
    profile_pic_url = Column(Text)
    timestamp = Column(DateTime, nullable=False)
    likes_count = Column(Integer, default=0)
    is_members_only = Column(Boolean, default=False)

    # Relationships ordered by auto-incrementing IDs
    content_blocks = relationship(
        "PostContentBlock",
        back_populates="post",
        order_by="PostContentBlock.id",
        cascade="all, delete-orphan"
    )

    attachments = relationship(
        "PostAttachment",
        back_populates="post",
        order_by="PostAttachment.id",
        cascade="all, delete-orphan"
    )


class PostContentBlock(Base):
    __tablename__ = 'post_content_blocks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(
        String(50),
        ForeignKey('community_posts.post_id'),
        index=True
    )
    text_content = Column(Text)
    link_url = Column(Text)

    post = relationship("CommunityPost", back_populates="content_blocks")


class PostAttachment(Base):
    __tablename__ = 'post_attachments'

    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(
        String(50),
        ForeignKey('community_posts.post_id'),
        index=True
    )
    file_type = Column(String(10))
    file_path = Column(Text, nullable=False)

    post = relationship("CommunityPost", back_populates="attachments")

# Create Engine and Tables
engine = create_engine(DATABASE_URL)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# --- 3. Parsing & Storage Logic ---
def parse_shorthand(value):
    # Mapping suffixes to their numerical multipliers
    multipliers = {
        'K': 1000,
        'M': 1000000,
        'B': 1000000000
    }

    # Ensure we are working with an upper-case string
    value = str(value).upper().strip()

    # Check if the last character is one of our suffixes
    if value[-1] in multipliers:
        suffix = value[-1]
        number_part = float(value[:-1]) # Everything except the suffix
        return int(number_part * multipliers[suffix])
    
    # If no suffix, just convert to float then int
    return int(float(value))

def store_post(info:dict , pictures=[], files=[], json_files=[]):
    post_id = info['post_id']

    # --- 1. Extract Metadata (Same as your original logic) ---
    try:
        # Safely navigate to the last thumbnail URL
        author_thumb = (info.get('author', {}) \
                        .get('authorThumbnail', {}) or {} ) \
                        .get('thumbnails', [{}])[-1] \
                        .get('url', None) \
                        or \
                        (info.get("original_post") \
                        .get('author', {}) \
                        .get('authorThumbnail', {}) or {} ) \
                        .get('thumbnails', [{}])[-1] \
                        .get('url')

        # Safely navigate to the channel name text
        chan_name = (info.get('author', {}) \
                        .get('authorText', {}) or {} ) \
                        .get('runs', [{}])[0] \
                        .get('text', None) \
                        or \
                        (info.get("original_post") \
                        .get('author', {}) \
                        .get('authorText', {}) or {} ) \
                        .get('runs', [{}])[0] \
                        .get('text', 'Unknown')
        
        
        # Safe Like Conversion
        likes_text = info.get('vote_count', {}).get('simpleText', None)
        likes = parse_shorthand(likes_text.replace(',', '')) if likes_text else 0
        
        # Timestamp
        ts = info.get('_published', {}).get('lastUpdatedTimestamp')
        timestamp = datetime.fromtimestamp(int(ts)) if ts else datetime.utcnow()

        # --- 2. Insert Parent (INSERT IGNORE) ---
        post_values = {
            "post_id": post_id,
            "channel_id": info.get('channel_id'),
            "channel_name": chan_name,
            "profile_pic_url": author_thumb,
            "timestamp": timestamp,
            "likes_count": likes,
            "is_members_only": (info.get('sponsor_only_badge') is not None)
        }

        # Using prefix_with("IGNORE") for MariaDB
        parent_stmt = insert(CommunityPost).values(post_values).prefix_with("IGNORE")
        session.execute(parent_stmt)

        # --- 3. Insert Content Blocks (INSERT IGNORE) ---
        if info.get('content_text', {}).get('runs'):
            block_list = []
            for run in info['content_text']['runs']:
                url = None
                if run.get('urlEndpoint'):
                    url = run['urlEndpoint'].get('url')
                elif run.get('browseEndpoint'):
                    url = "https://youtube.com" + run['browseEndpoint'].get('url', '')
                elif run.get('navigationEndpoint'):
                    cmd_meta = run.get('navigationEndpoint', {}).get('commandMetadata', {}).get('webCommandMetadata', {})
                    if cmd_meta.get('url'):
                        url = "https://youtube.com" + cmd_meta['url']
                block_list.append({
                    "post_id": post_id, # Manual Foreign Key
                    "text_content": run.get('text', ''),
                    "link_url": url 
                })
            
            if block_list:
                block_stmt = insert(PostContentBlock).values(block_list).prefix_with("IGNORE")
                session.execute(block_stmt)

        # --- 4. Insert Attachments (INSERT IGNORE) ---
        attachment_list = []
        for f_path in json_files:
            attachment_list.append({"post_id": post_id, "file_type": 'JSON', "file_path": f_path})
        for f_path in pictures:
            attachment_list.append({"post_id": post_id, "file_type": 'IMAGE', "file_path": f_path})
        for f_path in files:
            attachment_list.append({"post_id": post_id, "file_type": 'FILE', "file_path": f_path})

        if attachment_list:
            attr_stmt = insert(PostAttachment).values(attachment_list).prefix_with("IGNORE")
            session.execute(attr_stmt)

        session.commit()
        logging.info(f"Processed Post ID: {post_id}")

    except Exception as e:
        session.rollback()
        logging.exception(f"Critical error storing Post ID {post_id}: {e}")

def get_existing_posts():
    return set(session.scalars(select(CommunityPost.post_id)))

# --- 4. Retrieval Logic (Recreating the Data Structures) ---

def retrieve_post_data(post_id):
    """
    Query the database and reconstruct the 'info', 'pictures', and 'files' 
    structures required by the HTML generator.
    """
    post = session.query(CommunityPost).filter_by(post_id=post_id).first()
    
    if not post:
        logging.warning("Post not found.")
        return None, None, None

    # Reconstruct 'info' dictionary
    info = {
        'post_id': post.post_id,
        'channel_id': post.channel_id,
        '_published': {'lastUpdatedTimestamp': str(post.timestamp)},
        'sponsor_only_badge': True if post.is_members_only else None,
        'vote_count': {'simpleText': post.likes_count} if post.likes_count else None,
        'author': {
            'authorThumbnail': {
                'thumbnails': [{'url': post.profile_pic_url}] # Mocking list structure
            } if post.profile_pic_url else None,
            'authorText': {
                'runs': [{'text': post.channel_name}]
            }
        },
        'content_text': {'runs': []}
    }

    # Reconstruct Content Runs (Order is guaranteed by SQLAlchemy relationship)
    for block in post.content_blocks:
        run_dict = {'text': block.text_content}
        
        # If there was a URL, we need to reconstruct an endpoint structure
        # so the HTML generator detects it.
        if block.link_url:
            # For simplicity, we can map all links back to urlEndpoint 
            # or handle logic to check if it contains youtube.com to map back to browseEndpoint
            # This is a simplified reconstruction:
            run_dict['urlEndpoint'] = {'url': block.link_url}
        
        info['content_text']['runs'].append(run_dict)

    # Reconstruct Lists
    pictures = [a.file_path for a in post.attachments if a.attachment_type == 'IMAGE']
    files = [a.file_path for a in post.attachments if a.attachment_type == 'FILE']

    return info, pictures, files


