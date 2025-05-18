from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from models import ParentPost, OurPostReply, OurReply, CMCNews
from database import SessionLocal
from sqlalchemy.exc import SQLAlchemyError
import requests
from sqlalchemy import desc

# ----------------> Create Parent Post <---------------------
def create_parent_post(username: str, content: str, twitter_post_id: str):
    db: Session = SessionLocal()
    try:
        # Check for existing Twitter post ID
        existing_post = db.query(ParentPost).filter(ParentPost.twitter_post_id == twitter_post_id).first()
        if existing_post:
            raise ValueError("Post with this Twitter ID already exists.")

        new_post = ParentPost(
            username=username,
            content=content,
            twitter_post_id=twitter_post_id
        )

        db.add(new_post)
        db.commit()
        db.refresh(new_post)
        return new_post

    except IntegrityError:
        db.rollback()
        raise ValueError("Failed to insert post. Integrity error or duplicate.")

    finally:
        db.close()

#----------------------> Create Replies on Our Post <---------------------------#
def create_our_post_reply(username: str, content: str, twitter_tweet_id: str, twitter_post_id: str):
    db: Session = SessionLocal()
    try:
        # if the parent post exists
        parent = db.query(ParentPost).filter(ParentPost.twitter_post_id == twitter_post_id).first()
        if not parent:
            raise ValueError(f"No parent post found with twitter_post_id: {twitter_post_id}")

        #if this reply already exists
        existing = db.query(OurPostReply).filter(
            OurPostReply.twitter_tweet_id == twitter_tweet_id
        ).first()
        if existing:
            raise ValueError("Reply with this Twitter tweet ID already exists.")

        new_reply = OurPostReply(
            username=username,
            # twitter_user_id=twitter_user_id,
            content=content,
            twitter_tweet_id=twitter_tweet_id,
            twitter_post_id=twitter_post_id
        )

        db.add(new_reply)
        db.commit()
        db.refresh(new_reply)
        return new_reply

    except IntegrityError as e:
        db.rollback()
        raise ValueError("Failed to insert reply. Integrity error.") from e

    finally:
        db.close()

#----------------------> Create Our New Replies <---------------------------#
def create_our_reply(content: str, twitter_reply_id: str, twitter_tweet_id: str):
    db: Session = SessionLocal()
    try:
        # Check if the original tweet exists in our_post_replies
        parent_tweet = db.query(OurPostReply).filter(
            OurPostReply.twitter_tweet_id == twitter_tweet_id
        ).first()

        if not parent_tweet:
            raise ValueError(f"No OurPostReply found with twitter_tweet_id: {twitter_tweet_id}")

        # Optional: check for duplicate reply
        existing = db.query(OurReply).filter(
            OurReply.twitter_reply_id == twitter_reply_id
        ).first()
        if existing:
            raise ValueError("OurReply with this twitter_reply_id already exists.")

        new_reply = OurReply(
            content=content,
            twitter_reply_id=twitter_reply_id,
            twitter_tweet_id=twitter_tweet_id
        )

        db.add(new_reply)
        db.commit()
        db.refresh(new_reply)
        return new_reply

    except IntegrityError as e:
        db.rollback()
        raise ValueError("Failed to insert OurReply due to integrity error.") from e

    finally:
        db.close()

# ---------------------> 3 Most Recent Posts <---------------
def get_recent_parent_posts(limit: int = 3):
    db: Session = SessionLocal()
    try:
        recent_posts = (
            db.query(ParentPost)
            .order_by(ParentPost.created_at.desc())
            .limit(limit)
            .all()
        )

        if not recent_posts:
            print("No recent posts found.")
            return []

        contents = [post.content for post in recent_posts]
        return contents

    except Exception as e:
        print(f"Error occurred while fetching recent parent posts: {e}")
        return []

    finally:
        db.close()

#---------------------------------------> responded users <------------------------------
def get_replied_usernames_for_parent_post(twitter_post_ids):

    db: Session = SessionLocal()
    try:
        results = (
            db.query(OurPostReply.username)
            .join(OurReply, OurReply.twitter_tweet_id == OurPostReply.twitter_tweet_id)
            .filter(OurPostReply.twitter_post_id.in_(twitter_post_ids))
            .distinct()
            .all()
        )
        return [username for (username,) in results]

    except SQLAlchemyError as e:
        print(f"Database error occurred: {e}")
        return []

    finally:
        db.close()

#---------------------------------------> Fetch Articles from CMC and store <------------------------------
import requests

def fetch_articles(endpoint="http://168.231.107.232:6969/content"):
    try:
        response = requests.get(endpoint, timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Failed to fetch articles: {e}")
        return None

def store_articles():
    articles = fetch_articles()
    db: Session = SessionLocal()
    if not articles:
        print("No articles to store.")
        return

    try:
        for article in articles:
            new_entry = OurReply(
                title=article["title"],
                content=article["text"]
            )
            db.add(new_entry)
        db.commit()
        print("Articles stored successfully.")
    except SQLAlchemyError as db_err:
        db.rollback()
        print(f"Database error: {db_err}")
    except Exception as e:
        print(f"Unexpected error: {e}")

#---------------------------------------> Extract CMC Articles/News from db <------------------------------
from sqlalchemy import desc

def get_latest_articles():
    try:
        db: Session = SessionLocal()
        limit = 3
        articles = (
            db.query(CMCNews)
            .order_by(desc(CMCNews.created_at))
            .limit(limit)
            .all()
        )
        return articles[0]
    except Exception as e:
        print(f"Error fetching latest articles: {e}")
        return []
