from fastapi import FastAPI, Request, HTTPException
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv
from inference import grok_inference
from classifier import grok_classifier, grok_post_writer, find_most_similar_replies
from retriver import get_combined_stats_with_api, clean_tweet_text
from twitter_apis import post_tweets, get_latest_top3_posts, get_replies_to_tweets, extract_usernames_from_excel, filter_replies_by_usernames, filter_recent_replies, filter_unreplied_tweets, reply_to_tweet, extract_mentions, add_username_to_excel
from fastapi.responses import JSONResponse
import traceback
from pydantic import BaseModel
import tweepy
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi.middleware.cors import CORSMiddleware
import pytz
import datetime
from queries import create_parent_post, create_our_post_reply, create_our_reply, get_recent_parent_posts, get_replied_usernames_for_parent_post
from database import init_db, SessionLocal

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -----> Schedular <----- #
us_eastern = pytz.timezone('US/Eastern')
scheduler = AsyncIOScheduler(timezone=us_eastern)

async def scheduled_post_tweet(app: FastAPI):
    request = Request({"type": "http", "app": app})
    await post_tweet(request)

async def scheduled_reply_to_recent(app: FastAPI):
    request = Request({"type": "http", "app": app})
    await reply_to_recent_tweets(request)

#async def scheduled_reply_to_mention(app: FastAPI):
#    request = Request({"type": "http", "app": app})
#    await reply_to_mention_tweets(request)

# -----> Fastapi Setup <----- #
@asynccontextmanager
async def lifespan(app: FastAPI):

    app.state.auth = tweepy.OAuth1UserHandler(
        consumer_key=os.getenv("CONSUMER_API_KEY"),
        consumer_secret=os.getenv("CONSUMER_API_SECRET"),
        callback="http://127.0.0.1:8000/callback"
    )

    # Post Tweet – 3 times a day
    scheduler.add_job(scheduled_post_tweet, CronTrigger(hour=13, minute=50), args=[app])
    # scheduler.add_job(scheduled_post_tweet, CronTrigger(hour=8, minute=10, timezone=us_eastern), args=[app])
    # scheduler.add_job(scheduled_post_tweet, CronTrigger(hour=21, minute=0, timezone=us_eastern), args=[app])

    # Reply to Recent – 7 times a day
    scheduler.add_job(scheduled_reply_to_recent, CronTrigger(hour=14, minute=10), args=[app])
    # scheduler.add_job(scheduled_reply_to_recent, CronTrigger(hour=17, minute=0, timezone=us_eastern), args=[app])
    # scheduler.add_job(scheduled_reply_to_recent, CronTrigger(hour=9, minute=0, timezone=us_eastern), args=[app])
    # scheduler.add_job(scheduled_reply_to_recent, CronTrigger(hour=11, minute=0, timezone=us_eastern), args=[app])
    # scheduler.add_job(scheduled_reply_to_recent, CronTrigger(hour=22, minute=0, timezone=us_eastern), args=[app])
    # scheduler.add_job(scheduled_reply_to_recent, CronTrigger(hour=23, minute=0, timezone=us_eastern), args=[app])
    #scheduler.add_job(scheduled_reply_to_recent, CronTrigger(hour=21, minute=0), args=[app])

    # Reply to Mention – 3 times a day
    #scheduler.add_job(scheduled_reply_to_mention, CronTrigger(hour=2, minute=30), args=[app])
    #scheduler.add_job(scheduled_reply_to_mention, CronTrigger(hour=10, minute=30), args=[app])
    #scheduler.add_job(scheduled_reply_to_mention, CronTrigger(hour=18, minute=30), args=[app])

    scheduler.start()

    yield

    scheduler.shutdown(wait=False)
    del app.state.auth

app = FastAPI(lifespan=lifespan)

init_db()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----> OAuth Flow Initiation API <----- #
@app.get("/start-oauth", summary="Start OAuth Flow", response_description="URL to authorize the app")
async def start_oauth(request: Request):
    try:
        auth = request.app.state.auth
        auth_url = auth.get_authorization_url()
        return {
            "success": True,
            "response": {
                "message": "Visit this URL to authorize the app",
                "auth_url": auth_url
            }
        }
    except tweepy.TweepyException as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "message": str(e)
                }
            }
        )

# -----> OAuth Callback API <----- #
@app.get("/callback", summary="Handle OAuth Callback", response_description="Access tokens from OAuth flow")
async def oauth_callback(request: Request, oauth_token: str, oauth_verifier: str):
    try:
        auth = request.app.state.auth
        auth.request_token = {"oauth_token": oauth_token}
        access_token, access_token_secret = auth.get_access_token(oauth_verifier)

        # Save tokens to .env (optional, for convenience)
        with open(".env", "a") as f:
            f.write(f"\nACCESS_TOKEN={access_token}\nACCESS_TOKEN_SECRET={access_token_secret}\n")

        return {
            "success": True,
            "response": {
                "message": "OAuth flow completed. Tokens saved to .env.",
                "access_token": access_token,
                "access_token_secret": access_token_secret
            }
        }
    except tweepy.TweepyException as e:
        raise HTTPException(status_code=400, detail=str(e))

# -----> MOP-Bot Response Generation API <----- #
@app.get("/bot-response", summary="Generate Bot Response", response_description="The generated response from the model.")
async def get_bot_response(request: Request, query: str):
    try:
        if not query or not query.strip():
            return {
                "success": False,
                "error": {
                    "message": "Query cannot be empty."
                }
            }

        response = grok_inference(query, "")

        return {
            "success": True,
            "response": {
                "message": response
            }
        }

    except Exception as e:
        return {
            "success": False,
            "error": {
                "message": str(e)
            }
        }


# -----> Query Classification Response Generation API <----- #
@app.get("/classifier-response", summary="Classifier Response", response_description="The generated response from the classifier.")
async def get_classifier_response(query: str):
    try:
        classification = grok_classifier(query)
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "response": {
                    "message": classification
                }
            }
        )
    except Exception as e:
        error_message = str(e)
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "message": error_message
                }
            }
        )

# -------> Twitter Post API <----- #
@app.post("/post-tweet", summary="Post a Tweet", response_description="The tweet content and status.")
async def post_tweet(request: Request):
    try:
        current_hour = pytz.timezone('US/Eastern').localize(datetime.datetime.now()).hour
        if current_hour in [8, 13, 21]:
            source_set = {8: 1, 7: 2, 21: 3}.get(current_hour, 1)
        else:
            source_set = 3
        
        posts = get_recent_parent_posts()
        tweet_content = grok_post_writer(source_set=source_set, posts=posts)
        # text = clean_tweet_text(tweet_content)
        # print("Tweet Content: ", text)
        
        response = post_tweets(tweet_content.lower())

        if isinstance(response, str):
            return JSONResponse(status_code=400, content={"success": False, "error": {"message": response}})
        if response.get("error"):
            return JSONResponse(status_code=400, content={"success": False, "error": {"message": response["error"]}})
        #Store in DB
        create_parent_post("MINDAgent", tweet_content, response["tweet_id"])
        return {
            "success": True,
            "response": {
                "message": "Tweet posted successfully.",
                "tweet": tweet_content,
                "tweet_id": response.get("tweet_id")
            }
        }

    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"success": False, "error": {"message": str(e)}})

#----------> My Posts Tweet-Replies API <-------- #
@app.post("/reply-to-recent", summary="Reply to Recent Tweets", response_description="Replies posted successfully.")
async def reply_to_recent_tweets(request: Request):
    try:

        list_of_posts = get_latest_top3_posts()
        logger.info(f"get_latest_top3_posts returned: {list_of_posts}")

        if isinstance(list_of_posts, dict) and "error" in list_of_posts:
            logger.error(f"Error in get_latest_top3_posts: {list_of_posts['error']}")
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": {
                        "message": list_of_posts["error"]
                    }
                }
            )

        if not isinstance(list_of_posts, list):
            logger.error(f"Expected list_of_posts to be a list, got {type(list_of_posts)}")
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": {
                        "message": "Invalid response from get_latest_top3_posts: expected a list"
                    }
                }
            )

        posts = []
        for post in list_of_posts:
            if not isinstance(post, dict) or 'tweet_id' not in post:
                logger.error(f"Invalid post format: {post}")
                continue
            posts.append(post)

        if not posts:
            logger.info("No valid posts found to process")
            return {
                "success": True,
                "response": {
                    "message": "No recent posts to reply to.",
                    "replied_tweets": []
                }
            }

        list_of_replies = get_replies_to_tweets(posts)
        logger.info(f"Retrieved {len(list_of_replies)} replies")
        twitter_post_ids = list({reply['conversation_id'] for reply in list_of_replies})
        replied_usernames = set(get_replied_usernames_for_parent_post(twitter_post_ids))

        filtered_replies = [
        reply_tuple for reply_tuple in list_of_replies
        if reply_tuple['username'] not in replied_usernames
        ]
        logger.info(f"Filtered Replies: {filtered_replies}")
        #usernames = extract_usernames_from_excel()
        #usernames_filtered_replies = filter_replies_by_usernames(list_of_replies, usernames)

        similar_filtered_replies = find_most_similar_replies(filtered_replies)
        logger.info(f"Similar Replies: {similar_filtered_replies}")

        if not similar_filtered_replies:
            similar_filtered_replies = filter_recent_replies(filtered_replies)
            logger.info(f"There are no similar replies so latest replies to be responded: {similar_filtered_replies}")

        unreplied_tweets, details = filter_unreplied_tweets(similar_filtered_replies)
        logger.info(f"Un-replied Tweets: {unreplied_tweets}")

        replied_tweets = []
        for tweet in unreplied_tweets:
            query = tweet['text']
            tweet_id = tweet['tweet_id']
            parent_post = tweet['parent_post_text']
            response, classification, context = grok_inference(query, parent_post)

            reply_result = reply_to_tweet(tweet_id, response)

            if reply_result.get("success"):
                logger.info(f"Replied to tweet {tweet_id}")
                replied_tweets.append(tweet_id)
            else:
                logger.error(f"Failed to reply to tweet {tweet_id}: {reply_result.get('error')}")

            try:
                create_our_post_reply(
                    username=details[0]["replying_user"],
                    content=details[0]["reply_text"],
                    twitter_tweet_id=details[0]["reply_tweet_id"],
                    twitter_post_id=details[0]["conversation_id"]
                )
                create_our_reply(
                    content=response,
                    twitter_reply_id=reply_result.get("tweet_id"),
                    twitter_tweet_id=details[0]["reply_tweet_id"]
                )
                logger.info("Recent Tweets are stored in the Database")
            except Exception as db_error:
                logger.error(f"Failed to store tweet/reply in the database: {db_error}")
                traceback.print_exc()

        logger.info(f"Replied to {len(replied_tweets)} recent tweets")
        return {
            "success": True,
            "response": {
                "message": "Replies posted successfully.",
                "replied_tweets": replied_tweets
            }
        }

    except Exception as e:
        logger.error(f"Error in reply_to_recent_tweets: {e}")
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "message": str(e)
                }
            }
        )

# -----> Reply to Mention Tweets API <----- #
@app.post("/reply-to-mention", summary="Reply to Mention Tweets", response_description="Replies posted to mentions successfully.")
async def reply_to_mention_tweets(request: Request):
    try:
        list_of_replies = await extract_mentions()
        logger.info(f"extract_mentions returned: {list_of_replies}")

        if not isinstance(list_of_replies, list):
            logger.error(f"Expected list_of_replies to be a list, got {type(list_of_replies)}")
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": {
                        "message": "Invalid response from extract_mentions: expected a list"
                    }
                }
            )

        usernames = extract_usernames_from_excel()
        usernames_filtered_replies = filter_replies_by_usernames(list_of_replies, usernames)
        logger.info(f"Filtered {len(usernames_filtered_replies)} replies by usernames")

        time_filtered_replies = filter_recent_replies(usernames_filtered_replies)
        logger.info(f"Filtered {len(time_filtered_replies)} recent replies")

        unreplied_tweets = filter_unreplied_tweets(time_filtered_replies)
        logger.info(f"Found {len(unreplied_tweets)} unreplied tweets: {unreplied_tweets}")

        if not unreplied_tweets:
            logger.info("No unreplied mentions found to process")
            return {
                "success": True,
                "response": {
                    "message": "No unreplied mentions to reply to.",
                    "replied_tweets": []
                }
            }

        replied_tweets = []
        for tweet in unreplied_tweets:
            query = tweet['text']
            tweet_id = tweet['tweet_id']
            parent_post = tweet['parent_post_text']
            logger.info(f"Processing mention {tweet_id}, query: {query}")

            if not query or not isinstance(query, str):
                logger.error(f"Invalid query for mention {tweet_id}: {query}")
                continue

            try:
                response, classification, context = grok_inference(query, parent_post)
                logger.info(f"Inference output for mention {tweet_id}: response={response}")
            except Exception as e:
                logger.error(f"Inference failed for mention {tweet_id}: {e}")
                continue

            if not response or not isinstance(response, str):
                logger.error(f"Invalid inference response for mention {tweet_id}: {response}")
                continue

            reply_result = reply_to_tweet(tweet_id, response)
            if reply_result.get("success"):
                logger.info(f"Replied to mention {tweet_id} with tweet_id {reply_result.get('tweet_id')}")
                replied_tweets.append(tweet_id)
            else:
                logger.error(f"Failed to reply to mention {tweet_id}: {reply_result.get('error')}")

        logger.info(f"Replied to {len(replied_tweets)} mention tweets")
        return {
            "success": True,
            "response": {
                "message": "Replies posted to mentions successfully.",
                "replied_tweets": replied_tweets
            }
        }

    except Exception as e:
        logger.error(f"Error in reply_to_mention_tweets: {e}")
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "message": str(e)
                }
            }
        )

# --------------------> Stats API < ---------------------------
@app.get("/stats", summary="System Statistics", response_description="Aggregated stats from Twitter, RAG DB, and API.")
async def stats():
    try:
        stats = get_combined_stats_with_api()
        return {
            "success": True,
            "stats": stats
        }

    except Exception as e:
        logger.error(f"Error in /stats endpoint: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "message": str(e)
                }
            }
        )

# --------------------> Whitelist the user < ---------------------------
class UsernameRequest(BaseModel):
    username: str

@app.post("/add-username", summary="Add a new username", response_description="Username added successfully.")
async def add_username(request: Request, payload: UsernameRequest):
    try:
        username = payload.username.strip()
        if not username:
            raise HTTPException(status_code=400, detail="Username cannot be empty.")

        add_username_to_excel(username)
        return {
            "success": True,
            "response": {
                "message": f"Username '{username}' has been added successfully."
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": {
                "message": str(e)
            }
        }

# ------------------> System Health Check API <-------------------- #
@app.get("/health", summary="Health Check", response_description="Returns health status of the service.")
async def health_check():
    return {
        "success": True,
        "response": {
            "status": "ok",
            "message": "Service is up and running."
        }
    }