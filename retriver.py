import requests
import os
from twitter_apis import get_my_tweets_and_replies
import psycopg2
import re
from langchain_community.tools.tavily_search import TavilySearchResults
from dotenv import load_dotenv

load_dotenv()

# -----------------------> Similarity/Distance BASE API <----------------------- #
def distance_api(query: str):
    BASE_URL = "https://mop.rekt.life/v1/query"
    PARAMS = {"query": query}
    
    try:
        response = requests.get(BASE_URL, params=PARAMS)

        if response.status_code == 200:
            response = response.json()
            top_items = sorted(response["data"], key=lambda x: x['distance'])[:3] 
            return [item for item in top_items]
        else:
            return {"error": f"Error {response.status_code}: {response.text}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {e}"}
    
# -----------------------> Token API BASE API <----------------------- #
def token_api(query: str):
    url = "http://mop.rekt.life/v1/search"
    try:
        response = requests.get(url, params={"query": query})
        
        if response.status_code == 200:
            return response.json()
        else:
            # return {"error": f"Request failed with status code {response.status_code}", "details": response.text}
            return {"data": f" "}
    
    except requests.exceptions.RequestException as e:
        return {"error": "Request exception occurred", "details": str(e)}
    
# -----------------------> Last Update API <----------------------- #
def last_update_api():
    url = "https://mop.rekt.life/v1/update/crypto_assets"
    try:
        response = requests.get(url)
        response.raise_for_status()

        data = response.json()
        if isinstance(data, dict) and data.get("success") and isinstance(data.get("data"), list) and len(data["data"]) == 2:
            coinmarketcap_update = data["data"][0].get("last_update", "N/A")
            solana_tracker_update = data["data"][1].get("last_update", "N/A")
            return {
                "coinmarketcap_update": coinmarketcap_update,
                "solana_tracker_update": solana_tracker_update
            }
        else:
            return {"error": "Unexpected JSON structure or missing data."}
    except requests.exceptions.RequestException as e:
        return {"error": "Request exception occurred", "details": str(e)}
    except ValueError:
        return {"error": "Failed to parse JSON response."}
    
# -------------------------> Update Data API <----------------------- #
def update_api():
    url = "https://mop.rekt.life/v1/update/crypto_assets"
    try:
        response = requests.post(url)
        
        if response.status_code == 200: 
            return response.json()
        else:
            return {"error": f"Request failed with status code {response.status_code}", "details": response.text}
    
    except requests.exceptions.RequestException as e:
        return {"error": "Request exception occurred", "details": str(e)}

# -----------------------> Tavily API for replies <----------------------- #
tavily_api_key = os.getenv('TAVILY_API_KEY')

os.environ['TAVILY_API_KEY'] = tavily_api_key
def tavily_data(query: str):
    try:
        tool = TavilySearchResults(
            max_results=5,
            include_domains=[
                "https://crypto.news/",
                "https://cointelegraph.com/",
                "https://dexscreener.com/"
            ],
            include_images=False,
            include_videos=False,
            include_links=True
        )
        results = tool.invoke(query)

        if not isinstance(results, list):
            raise ValueError("Unexpected result format: Expected a list.")

        filtered_results = [
            {"title": item.get("title", "No Title"), "content": item.get("content", "No Content")}
            for item in results
        ]

        return filtered_results

    except Exception as e:
        # Optionally, log the error or re-raise it depending on the use case
        print(f"Error occurred in tavily_data: {e}")
        return []


# -----------------------> Tavily google search <----------------------- #
def google_search(query: str):
    try:
        tool = TavilySearchResults(
            max_results=3,
            include_images=False,
            include_videos=False,
            include_links=True
        )
        results = tool.invoke(query)

        if not isinstance(results, list):
            raise ValueError("Unexpected result format: Expected a list.")

        return results

    except Exception as e:
        print(f"Error occurred in google_search: {e}")
        return []


# -----------------------> Tavily for POSTs <----------------------- #
tavily_api_key = os.getenv('TAVILY_API_KEY')

os.environ['TAVILY_API_KEY'] = tavily_api_key
def tavily_for_post(query: str, source_set: int = 1):
    if source_set == 1:
        sources = [
            "https://watcher.guru/news/"
        ]
    elif source_set == 2:
        sources = [
            "https://u.today/latest-cryptocurrency-news"
        ]
    else:  # source_set == 3
        sources = [
            "https://www.coindesk.com/latest-crypto-news",
            "https://www.theblock.co/latest-crypto-news"
        ]

    tool = TavilySearchResults(
        max_results=2,
        include_domains=sources,
        include_images=False,
        include_videos=False,
        include_links=True
    )
    results = tool.invoke(query)
    return [{"title": item["title"], "content": item["content"]} for item in results]

# -----------------------> RAG DB STATS <----------------------- #
def get_rag_db_stats():
    db_params = {
        'host': '147.93.40.59',
        'port': 5432,
        'dbname': 'postgres',
        'user': 'postgres',
        'password': 'vrHwHn0VNZq5h7z2nbe4bZworOaW5GEr'
    }

    try:
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT SUM(reltuples)::BIGINT AS total_rows
            FROM pg_class
            WHERE relkind = 'r';
        """)
        total_rows = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM crypto_assets_embeddings;")
        total_news_items = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM trending_tokens;")
        total_trending_tokens = cursor.fetchone()[0]

        last_news_update = cursor.fetchone()
        last_news_update = last_news_update[0] if last_news_update else None

        cursor.close()
        conn.close()

        stats = {
            'total_rows_in_rag_db': total_rows,
            'total_news_items_processed': total_news_items,
            'total_trending_tokens_processed': total_trending_tokens,
        }

        return stats

    except psycopg2.Error as e:
        print(f"Database error: {e}")
        return None

# -----------------------> Full STATS <----------------------- #
def get_combined_stats_with_api():
    twitter_data = get_my_tweets_and_replies()
    db_data = get_rag_db_stats()

    api_data = last_update_api()

    if twitter_data is None or db_data is None or "error" in api_data:
        print("Error retrieving data from one or more sources.")
        return None

    combined_data = {**twitter_data, **db_data, **api_data}
    return combined_data

# --------------> Cleaner <------------------
def clean_tweet_text(text: str) -> str:
    # Remove markdown links, plain URLs, and bracketed URLs with optional leading/trailing phrases
    text = re.sub(
        r'''
        (?:\b(?:check\s+out|read\s+more|more\s+at|visit|see|explore)\b\s*)?  # optional leading
        (\[.*?\]\(.*?\)|                # [text](url)
         \[.*?(https?://|www\.)\S*?\]|  # [Source: http://...]
         https?://\S+|                  # http(s) URLs
         www\.\S+)                      # www URLs
        (\s*(?:for\s+more\s+details|or|and)?\.?)?  # optional trailing
        ''',
        '',
        text,
        flags=re.IGNORECASE | re.VERBOSE
    )

    # Remove common filler phrases
    text = re.sub(
        r'\b(?:stay\s+tuned\s+for\s+more\s+updates!?|'
        r'more\s+details\s+coming\s+soon!?|'
        r'keep\s+an\s+eye\s+out\s+for\s+updates!?|'
        r'updates\s+to\s+follow!?|'
        r'more\s+to\s+come!?|'
        r'we\'ll\s+be\s+back\s+with\s+more!?|'
        r'find\s+out\s+more\s+soon!?|'
        r'learn\s+more\s+soon!?)\b',
        '',
        text,
        flags=re.IGNORECASE
    )

    # Normalize spacing and punctuation
    text = re.sub(r'\s{2,}', ' ', text).strip()
    text = re.sub(r'\s+([.,!?])', r'\1', text)

    return text

# -----------------------> CMC API <----------------------- #
import requests

def get_latest_cmc_articles():
    try:
        endpoint = "http://168.231.107.232:6969/content"
        response = requests.get(endpoint, timeout=10)
        response.raise_for_status()
        data = response.json()

        end_markers = [
            "Table of Contents",
            "min s read",
            "min read",
            "0 likes"
        ]

        cleaned_articles = []
        for item in data:
            title = item.get("title")
            text = item.get("text")
            if title and text:
                # Find the earliest end marker in the text
                end_index = len(text)
                for marker in end_markers:
                    idx = text.find(marker)
                    if idx != -1 and idx < end_index:
                        end_index = idx

                cleaned_text = text[:end_index].strip()

                cleaned_articles.append({
                    "title": title.strip(),
                    "text": cleaned_text
                })

        return cleaned_articles

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except requests.exceptions.ConnectionError:
        print("Error connecting to the server.")
    except requests.exceptions.Timeout:
        print("Request timed out.")
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
    except ValueError:
        print("Failed to parse JSON response.")

    return None


# -----------------------> CMC Latest data API <----------------------- #
api_key=os.getenv("CMC_API_KEY"),
def fetch_crypto_latest_quotes(symbols):
    url = 'https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest'
    parameters = {
        'symbol': symbols,
        'convert': 'USD'
    }
    headers = {
        'Accepts': 'application/json',
        'X-CMC_PRO_API_KEY': "6553862c-73cd-46cc-aa70-0963bbe6a0ea",
    }

    try:
        response = requests.get(url, headers=headers, params=parameters)
        response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)
        data = response.json()

        # Check for API-level errors
        if data.get("status", {}).get("error_code", 0) != 0:
            error_msg = data["status"].get("error_message", "Unknown error")
            print(f"API Error: {error_msg}")
            return None

        return data

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except requests.exceptions.ConnectionError:
        print("Error: Connection error.")
    except requests.exceptions.Timeout:
        print("Error: Request timed out.")
    except requests.exceptions.RequestException as err:
        print(f"An unexpected error occurred: {err}")
    except Exception as e:
        print(f"Unexpected error: {e}")

    return None
