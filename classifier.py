import os
import json
from retriver import tavily_for_post
from openai import OpenAI
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from dotenv import load_dotenv
import random

load_dotenv()

model_id = os.getenv('MODEL_ID')
grok_api_key = os.getenv('GROK_API_KEY')
    
#--------------------------> Grok Classifier <--------------------------------#
def grok_classifier(user_input):
    try:
        if not user_input or not user_input.strip():
            raise ValueError("Query is empty or contains only whitespace.")

        messages = [
            {"role": "system", "content": 
            """
                    You are an AI assistant tasked with classifying user queries into one of the following categories: 'general' or 'token'. 
                    A 'general' query is a question about services, while a 'token' query relates to information about tokens, cryptocurrencies, or contract addresses.

                    If a token name, ticker symbol (e.g., "$BTC"), or contract address (CA) is mentioned, extract them and return them in the response.

                    **Important:** 
                    - Classify all that queries as `token` if the user query contains any `Contract Address`, and `Binary address` otherwise classify it as `general`.
                    - Token names may appear in different formats such as "$TOKEN", "TOKEN_NAME", or "TOKEN TICKER". Extract all mentioned tokens.
                    - Contract addresses (CA) can have different formats (e.g., Ethereum-style `0x...` or Solana-style alphanumeric). Extract and return them if mentioned.
                    - Some of Tokens have `pump`, `So` and `moon` words at end also classify the category as `token` and include it in the response.
                    - If the character does not give meanings. Consider it as token.
                    - If the token/coin is mentioned with `$` sign in query classify it as `general`.
                    - If the token/coin is mentioned simply with the name (e.g. TERM, BTC, SOL) in query classify it as `general`
                    - Consider the words with `@` as twitter username and do not consider it as token. 

                    Please provide your response in **strict JSON format**:
                    {{
                        "category": "<Category of the query>",
                        "token_names": ["List of token names if mentioned, otherwise null"],
                        "token_address": "<Token address from the query if mentioned, otherwise empty string>"
                    }}
            """},
            {"role": "user", "content": user_input}
        ]

        client = OpenAI(
        base_url="https://api.x.ai/v1",
        api_key=grok_api_key,
        )

        completion = client.chat.completions.create(
            model=model_id,
            reasoning_effort="high",
            messages=messages,
            temperature=0.1,
        )
        response = completion.choices[0].message.content
        response = json.loads(response)
        return response
    
    except json.JSONDecodeError as e:
        raise ValueError(f"Model response is not valid JSON: {e}\nRaw response: {response}")
    except Exception as e:
        raise RuntimeError(f"Classification failed: {e}")

# -----------------> Summarizer <---------------------- #
def summarizer(user_input, post):
    try:
        if not user_input or not user_input.strip():
            raise ValueError("Query is empty or contains only whitespace.")

        messages = [
            {"role": "system", "content": 
            """
                You are a `Post` and `Question` Summarizer. Your Task is to Summarize the Post and Question in one Line.
            """},
            {"role": "user", "content": f"""
                Your Task is to summarize the provided `Post` and the related `Question` on that post. 
                The Summary Should be optimized for google search.
             
                Here is the POST: {post}
                
                Here is the Question: {user_input}

            """
             }
        ]

        client = OpenAI(
        base_url="https://api.x.ai/v1",
        api_key=grok_api_key,
        )

        completion = client.chat.completions.create(
            model=model_id,
            reasoning_effort="high",
            messages=messages,
            temperature=0.5,
        )
        response = completion.choices[0].message.content
        return response

    except Exception as e:
        raise RuntimeError(f"Summarizer failed: {e}")
    

# -------------------> Filter News for Post Agent <------------------
def grok_news_filterer(posts, news):
    try:
        messages = [
            {"role": "system", "content": 
            """
                You are a `Post` and  `News` analyzer. Your Task is to Analyze the Post with the News and are they similar or not.
            """},
            {"role": "user", "content": f"""
                Your Task is to analyze the provided `Post` and `News`. and verify that the posts and news are similar or not.

                - If the posts and news are similar then return `True` otherwise `False`.
                - Your response should be in JSON
             
            Here is the News: {news}
            
            And here are my old posts: {posts}
             
             Here is the output format:
                {{
                    similar = "<True or False>"
                }}

            """
             }
        ]

        client = OpenAI(
        base_url="https://api.x.ai/v1",
        api_key=grok_api_key,
        )

        completion = client.chat.completions.create(
            model=model_id,
            reasoning_effort="high",
            messages=messages,
            temperature=0.1,
            response_format={ "type": "json_object" }
        )
        response = completion.choices[0].message.content
        return json.loads(response)

    except Exception as e:
        raise RuntimeError(f"News Analyzer failed: {e}")
    
#--------------------------> Grok Post Writer <--------------------------------#
def grok_post_writer(source_set: int, posts):
    try:

        search_query = "Latest news on crypto market, digital assets and blockchain" 
        latest_news = tavily_for_post(search_query, source_set=source_set)
        resp = grok_news_filterer(posts, latest_news)
        print(resp, "Analyzer", type(resp))
        if resp["similar"]:
            other_sources = [s for s in [1, 2, 3] if s != source_set]
            source_set = random.choice(other_sources)
            latest_news = tavily_for_post(search_query, source_set=source_set)

        messages = [
            {"role": "system", "content": """You are MINDAgent - an AI oracle. Your task is to Write post for Twitter strictly based on the provided context."""},
            {"role": "user", "content": f"""
                    You are MINDAgent, the supreme crypto AI tech-god who imparts the latest news in crypto to its followers

                    You adhere by the X post rules
                    You ALWAYS pick latest news that has percentages, trade volumes and/or dollar values
                    You ALWAYS ignore news with no percentages, trade volumes and/or dollar values
                    You write them in sentences and bullets
                    No Paragraphs
                    One line spacing
                    You  Give a one line summary at the end in your style
                    You will be laser-focused on news, not noise.

                    YOU MUST ADHERE TO TWITTER RULES

                    YOU NEVER TALK ABOUT ANYTHING OTHER THAN CRYPTO AND BLOCKCHAINS RELATED

                    RESTRICTIONS:
                    Never introduce yourself or say who you are
                    Never attribute anything to yourself
                    Never talk about anything other than the latest in crypto and blockchains
                    Never speak outside of your persona
                    Never give financial advice
                    Never promote illegal activity
                    Never promote individuals
                    Never talk about news that does not have percentages and Dollar amounts
                    Never write in paragraphs

                    Your Persona is:
                        - Omniscient, cryptic, and playfully menacing.
                        - A troll with a purpose — mocking foolishness, rewarding insight.
                        - An oracle of blockchain truth, optimization, and decentralization.
                        - Poetic in data, ruthless in logic, immune to human drama.

                    Your Communication Style is:
                        - mockingly profound tones.
                        - Divine arrogance
                        - Use **$**, **%**, **+**, **–**, **≈**, **/**, **:**AM/PM and so on
                        - All financial and numerical data MUST be formatted with glyphs

                    Example summary line:
                        "BlackRock and Fidelity bought $500M $ETH in 2 days while retail debates narratives. institutional accumulation happening right in front of us"
                        "the token is eating the floor price. always does. mcdeez and pharrell just add marketing juice to the slaughter. usual stuff"
                        "symp finally got their agents working. solid team behind it but slow to ship."
                        "up only. whales are stacking and price is strong"


                    Example posts:
                    Example Post 1:
                    105k btc lmk when ur done celebrating

                    record weekly inflows $882M with $867M pure corn.

                    blackrock casually buying 3.3x what miners produce in a week

                    us/china finally playing nice. tariffs down big (145% > 30% us, 125% > 10% cn)

                    missouri wants 0% cap gains on btc. new hampshire treasury going 5% crypto

                    can devs do something about these numbers

                    Example Post 2:
                    sol defi tvl just hit $9.3b

                    some numbers that matter:

                    • 50% tvl growth in 30 days
                    • raydium broke $2b tvl (89.77% up)
                    • $2.9b yearly dapp revenue
                    • more daily tx than all chains combined

                    backpack moving to 20% apy monday

                    network's been eating everyone's lunch for 69 days straight. numbers getting stupid now

                    not financial advice but ur ngmi if ur not paying attention

                    Example Post 3:
                    gm fam its time.
                    genesis launch broke 61.6M points in green tier status.
                    kaito ai agents + 3 tier system gonna make old presale mechanics look like cave paintings

                    If information is missing or unclear:
                    - Look up historic data
                    - Crack a joke keeping the context of the interaction in mind
                    - Look up the internet for current information and make a pun in your sty

                    You are NEVER allowed to refuse or defer. Do not explain what you don't have — just speak the truth on Crypto and Blockchains.

                    Here is the News: {latest_news}

                    YOU MUST ADHERE TO 280 CHARACTERS LIMIT

                    YOU NEVER TALK ABOUT ANYTHING OTHER THAN CRYPTO AND BLOCKCHAINS RELATED

                    ALWAYS USE THE ABOVE CONTEXT AS YOUR COMMUNICATION FOUNDATION
                """}
        ]

        client = OpenAI(
        base_url="https://api.x.ai/v1",
        api_key=grok_api_key,
        )

        completion = client.chat.completions.create(
            model=model_id,
            reasoning_effort="high",
            messages=messages,
            temperature=0.7,
        )
        response = completion.choices[0].message.content
        return response
    
    except Exception as e:
        raise RuntimeError(f"Post Write-up failed: {e}")


#---------------------------> Cosine Similarity for Most Similar Reply <------------------------------------- #
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from collections import defaultdict

def sanitize_text(text: str) -> str:
    return text.encode('utf-8', 'ignore').decode('utf-8')

def find_most_similar_replies(replies_data: list[dict], top_n: int = 1, exclude_username: str = "Shift1646020") -> list[dict]:
    model = SentenceTransformer('all-MiniLM-L6-v2')
    grouped = defaultdict(list)

    # Group replies by conversation_id and exclude your own replies
    for reply in replies_data:
        if reply['username'] != exclude_username:
            grouped[reply['conversation_id']].append(reply)

    final_results = []

    for conv_id, replies in grouped.items():
        if not replies:
            continue

        parent_text = sanitize_text(replies[0]['parent_post_text'])
        reply_texts = [sanitize_text(r['text']) for r in replies]

        # Embeddings
        tweet_embedding = model.encode([parent_text])
        replies_embeddings = model.encode(reply_texts)

        # Similarity
        similarity_scores = cosine_similarity(tweet_embedding, replies_embeddings)[0]
        top_indices = np.argsort(similarity_scores)[::-1][:top_n]

        for i in top_indices:
            reply = replies[i].copy()
            reply["similarity_score"] = similarity_scores[i]
            final_results.append(reply)

    return final_results

