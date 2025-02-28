import json
import os

def sort_posts(posts, sorting_filename=None, sorted_array=None):
    """
    Sorts posts based on an ordered list of post IDs from a JSON file.
    - Posts in the ordered list retain their order.
    - Unseen posts (not in the ordered list) are placed at the back, sorted by timestamp (latest first).

    :param posts: List of dictionaries, each containing 'post_id' and 'timestamp'.
    :param sorting_filename: JSON file containing an ordered list of post IDs.
    :return: Sorted list of posts.
    """
    # Load the ordered post IDs from the JSON file
    ordered_post_ids = []
    if sorted_array is None and os.path.exists(sorting_filename):
        try:
            with open(sorting_filename, "r") as file:
                ordered_post_ids = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            pass
    # If sorted array is passed, use that instead
    elif sorted_array is not None:
        ordered_post_ids = sorted_array

    # Create an index mapping for ordered post IDs
    order_index = {post_id: i for i, post_id in enumerate(ordered_post_ids)}

    # Sort posts:
    # - Existing items follow the predefined order
    # - Unseen items go to the back, sorted by timestamp (latest first)
    sorted_posts = sorted(
        posts,
        key=lambda post: (order_index.get(post["post_id"], float('inf')), -post.get('_published',{}).get('lastUpdatedTimestamp',0))
    )

    return sorted_posts
