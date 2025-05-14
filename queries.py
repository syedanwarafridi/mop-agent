from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from models import ParentPost, OurPostReply, OurReply
from database import SessionLocal

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
    recent_posts = db.query(ParentPost).order_by(ParentPost.created_at.desc()).limit(limit).all()

    # Unzip the posts into separate lists
    post_ids = [post.post_id for post in recent_posts]
    usernames = [post.username for post in recent_posts]
    contents = [post.content for post in recent_posts]
    created_ats = [post.created_at for post in recent_posts]

    return contents