import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

db_user = os.getenv('DB_USER')
db_password = os.getenv('DB_PASSWORD')
db_host = os.getenv('DB_HOST')
db_name = os.getenv('DB_NAME')
db_port = os.getenv('DB_PORT')

# SQL schema
schema_sql = """
CREATE TABLE parent_posts (
    post_id SERIAL PRIMARY KEY,
    username VARCHAR(100),
    content VARCHAR(1000),
    twitter_post_id VARCHAR(50)
);

CREATE TABLE our_post_replies (
    tweet_id SERIAL PRIMARY KEY,
    username VARCHAR(100),
    twitter_user_id INTEGER,
    content VARCHAR(1000),
    twitter_tweet_id VARCHAR(50),
    post_id INTEGER REFERENCES parent_posts(post_id)
);

CREATE TABLE mention_replies (
    mention_tweet_id SERIAL PRIMARY KEY,
    username VARCHAR(100),
    twitter_user_id INTEGER,
    content VARCHAR(1000),
    twitter_mention_tweet_id INTEGER,
    post_id INTEGER REFERENCES parent_posts(post_id)
);

CREATE TABLE our_replies (
    reply SERIAL PRIMARY KEY,
    content VARCHAR(1000),
    twitter_user_id INTEGER,
    twitter_reply_id INTEGER,
    tweet_id INTEGER REFERENCES our_post_replies(tweet_id),
    mention_tweet_id INTEGER REFERENCES mention_replies(mention_tweet_id)
);
"""

def create_schema():
    try:
        conn = psycopg2.connect(
            dbname=db_name,
            user=db_user,
            password=db_password,
            host=db_host,
            port=db_port
        )
        cursor = conn.cursor()
        cursor.execute(schema_sql)
        conn.commit()
        print("Schema created successfully.")

    except psycopg2.Error as e:
        print("Error creating schema:", e)

    finally:
        if conn:
            cursor.close()
            conn.close()

if __name__ == "__main__":
    create_schema()
