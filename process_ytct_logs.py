import re
import json
import os
import argparse

def load_existing_posts(json_file):
    """Load existing posts from JSON or return an empty list."""
    if os.path.exists(json_file):
        with open(json_file, "r", encoding="utf-8") as file:
            return json.load(file)
    return []

def save_posts(posts, json_file):
    """Save posts back to JSON."""
    with open(json_file, "w", encoding="utf-8") as file:
        json.dump(posts, file, indent=2)

def extract_runs(log_file):
    """Extract post IDs from the log file, maintaining the correct order."""
    post_pattern = re.compile(r"\[post:([a-zA-Z0-9_-]+)\]")
    
    runs = []
    current_run = []
    inside_run = False  
    if  os.path.exists(log_file):
        with open(log_file, "r", encoding="utf-8") as file:
            for line in file:
                if "[ytct] loaded cookies" in line:
                    if current_run:
                        runs.append(current_run)  # Append as is (no reversing)
                    current_run = []
                    inside_run = True
                elif "[ytct] finished" in line:
                    if current_run:
                        runs.append(current_run)  # Append as is (no reversing)
                    inside_run = False
                elif inside_run:
                    match = post_pattern.search(line)
                    if match:
                        post_id = match.group(1)
                        if post_id not in current_run:  
                            current_run.append(post_id)

    if current_run:
        runs.append(current_run)  # Append last run as is

    return runs

def merge_posts(existing_posts, new_runs):
    """Merge new runs into existing posts, preserving first-seen order."""
    seen_posts = set(existing_posts)  # Track recorded posts
    merged_posts = existing_posts[:]  # Start with existing order

    for run in new_runs:
        for post in run:
            if post not in seen_posts:
                merged_posts.append(post)
                seen_posts.add(post)

    return merged_posts

def main(log_file=None, json_file=None, clear_log=False):
    """Run the script with specified log and JSON files."""
    if log_file is None or json_file is None:
        parser = argparse.ArgumentParser(description="Process log file and update JSON with post IDs.")
        parser.add_argument("log_file", type=str, help="Path to the log file.")
        parser.add_argument("json_file", type=str, help="Path to the JSON file where posts are stored.")
        parser.add_argument('--clear-log', action='store_true', help="Clears ytct log after processing")
        args = parser.parse_args()
        log_file = args.log_file
        json_file = args.json_file
        clear_log = args.clear_log

    existing_posts = load_existing_posts(json_file)  # Load existing order
    new_runs = extract_runs(log_file)  # Extract new post IDs
    updated_posts = merge_posts(existing_posts, new_runs)  # Append new posts in correct order
    save_posts(updated_posts, json_file)  # Save back to JSON

    print(f"Ordered posts updated and saved to {json_file}")
    if clear_log:
        if os.path.exists(log_file):
            with open(log_file, 'w') as file:
                pass
            
    return updated_posts

if __name__ == "__main__":
    main()
