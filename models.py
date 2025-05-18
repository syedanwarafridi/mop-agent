from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class ParentPost(Base):
    __tablename__ = "parent_posts"

    post_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)
    twitter_post_id = Column(String(100), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class OurPostReply(Base):
    __tablename__ = "our_post_replies"

    tweet_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), nullable=False)
    # twitter_user_id = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    twitter_tweet_id = Column(String(100), nullable=False)
    twitter_post_id = Column(String(100), ForeignKey("parent_posts.twitter_post_id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class OurReply(Base):
    __tablename__ = "our_replies"

    reply_id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, nullable=False)
    # twitter_user_id = Column(Integer, nullable=False)
    twitter_reply_id = Column(String(100), nullable=False)
    twitter_tweet_id = Column(String(100), ForeignKey("our_post_replies.twitter_tweet_id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class CMCNews(Base):
    __tablename__ = "cmc_news"

    news_id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

# ------------------------------------------------------------------------------------->
# class MentionPost(Base):
#     __tablename__ = "mention_post"

#     mention_id = Column(Integer, primary_key=True, autoincrement=True)
#     username = Column(String(100), nullable=False)
#     content = Column(Text, nullable=False)
#     mention_post_id = Column(String(100), nullable=False, unique=True)

# class MentionReply(Base):
#     __tablename__ = "mention_replies"

#     mention_tweet_id = Column(Integer, primary_key=True, autoincrement=True)
#     username = Column(String(100), nullable=False)
#     # twitter_user_id = Column(Integer, nullable=False
#     content = Column(Text, nullable=False)
#     twitter_mention_tweet_id = Column(String(100), nullable=False)
#     mention_post_id = Column(String(100), ForeignKey("mention_post.mention_post_id"), nullable=False)

# class OurReplyToMention(Base):
#     __tablename__ = "our_replies"

#     reply = Column(Integer, primary_key=True, autoincrement=True)
#     content = Column(Text, nullable=False)
#     # twitter_user_id = Column(Integer, nullable=False)
#     twitter_reply_id = Column(String(100), nullable=False)
#     mention_tweet_id = Column(Integer, ForeignKey("mention_replies.mention_tweet_id"))
# ------------------------------------------------------------------------------------->
