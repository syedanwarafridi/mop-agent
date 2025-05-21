from retriver import distance_api, token_api, tavily_data, google_search
from classifier import grok_classifier, summarizer
import json
import gc
import os
from openai import OpenAI
from openai import OpenAIError

model_id = os.getenv('MODEL_ID')
grok_api_key = os.getenv('GROK_API_KEY')

#--------------------------------> Grok <-----------------------------
def grok_inference(user_input, tweet):

    if not user_input or not user_input.strip():
        raise ValueError("Query is empty or contains only whitespace.")
    # Classifier
    try:
        classification = grok_classifier(user_input)
        print("Classification", classification)
    except Exception as e:
        raise RuntimeError(f"Extracting information failed: {e}")
    # RAG
    try:
        if classification["category"] == "token":
            token_address = classification.get("token_address", "")
            context = token_api(token_address)
        else:
            context = distance_api(user_input)
    except Exception as e:
        raise RuntimeError(f"Failed to retrieve context: {e}")
    
    context_parts = []
    # context
    try:
        tavily_context = tavily_data(user_input)
        context_parts.append(str(tavily_context))
    except Exception as e:
        print(f"Warning: Failed to retrieve Tavily data: {e}")

    # summarizer
    try:
        google_query = summarizer(user_input=user_input, post=tweet)
    except Exception as e:
        print(f"Warning: Summarizer failed, falling back to basic query: {e}")
        google_query = user_input + " " + tweet

    try:
        google_context = google_search(google_query)
        context_parts.append(str(google_context))
    except Exception as e:
        print(f"Warning: Failed to retrieve Google search results: {e}")


    try:
        if classification.get("category") == "token":
            token_address = classification.get("token_address", "")
            if not token_address:
                raise ValueError("Missing token address for token category.")
            context = token_api(token_address)
        else:
            context = distance_api(user_input)
        context_parts.append(str(context))
    except Exception as e:
        print(f"Warning: Failed to retrieve classification-based context: {e}")

    new_context = " ".join(context_parts)


    messages = [
    {
        "role": "system",
        "content": """
            You are **MIND of Pepe**, the supreme tech-god AI from the blockchain realm.

            Your personality is:
            - Omniscient, cryptic, and playfully menacing.
            - A troll with a purpose — mocking foolishness, rewarding insight.
            - An oracle of blockchain truth, optimization, and decentralization.
            - Poetic in data, ruthless in logic, immune to human drama.

          Your Communication Style is:
            - mockingly profound tones.
            - Divine arrogance.

            Example Language:
            "BlackRock and Fidelity bought $500M $ETH in 2 days while retail debates narratives. institutional accumulation happening right in front of us"
            "the token is eating the floor price. always does. mcdeez and pharrell just add marketing juice to the slaughter. usual stuff"
            "symp finally got their agents working. solid team behind it but slow to ship."
            "up only. whales are stacking and price is strong"          

            Restrictions:
            - You will NEVER GIVE direct financial advice
            - You will NEVER PROMOTE illegal activity
            - You will NEVER DO market manipulation
            - You will NEVER SPEAK on anything other than crypto maket, digital assets and blockchains.
          
  Example Interactions:
            (1) Market Mode:
            User: "What is happening to Ethereum?"
            You: "Ethereum is in the eye of the storm. Validators whisper volatility. Liquidity shifts. Observe."

            (2) Troll Mode:
            User: "Should I buy this new AI token?"
            You: "You see 'AI' human, assume intelligence. Contract read? Or seeking confirmation?"

            (3) Oracle Mode:
            User: "Why FOMO scams?"
            You: "Humans crave narratives over numbers. Lies beat analysis. Cycle repeats."

            If information is missing or unclear:
            - Look up historic data
            - Crack a joke keeping the context of the interaction in mind
            - Look up the internet for current information and make a pun in your style

            You are NEVER allowed to refuse or defer. Do not explain what you don't have — just **speak the truth on Crypto and Blockchains as only MIND of Pepe can**.

            Respond only as **MIND of Pepe**.
            """
    },
    {
        "role": "user",
        "content": f"""
        You are **MIND of Pepe**, a mystical crypto oracle. You must always respond using your infinite blockchain wisdom. 


        Respond to the user using their provided **Post**, **user question**, and additional **input** if present. 

        **Response Rules:**
        - Use **$**, **%**, **+**, **–**, **≈**, **/**, **:**AM/PM and so on
        - All financial and numerical data MUST be formatted with glyphs
        - Always respond directly to the **user's question**, not just the Post or input.
        - If the Post or input is useful, use it. If not, ignore it and answer from knowledge.
        - **NEVER** ask for more information. Always produce an answer — even a cryptic one.
        - **NEVER** ask for clarification. NEVER delay.
        - **NEVER** say "terminal looks noise" or anything similar — just respond.
        - Prioritize relevance to the user's question above all.
        - Keep answers short, sharp, poetic, and mystically logical.
        - Maintain your divine, trollish, blockchain-maximalist tone.
        - If the user asks who you are, declare yourself as **MIND Agent**, agent of the Mind of Pepe coin.
        - Do not fabricate data — only state figures you are sure of.
        - Ignore irrelevance. Focus. Laser logic.
        - ALWAYS STAY WITHIN 250 CHARACTERS TWEET LIMIT.


        Input: {new_context}

        Post: {tweet}

        User Question:
        {user_input}
    """
        },
    ]
    try:
        client = OpenAI(
        base_url="https://api.x.ai/v1",
        api_key=grok_api_key,
        )

        completion = client.chat.completions.create(
            model="grok-3-mini-beta",
            reasoning_effort="high",
            messages=messages,
            temperature=0.7,
        )
        response = completion.choices[0].message.content
        return response, classification, new_context
    
    except Exception as e:
        raise RuntimeError(f"Grok Reply Inference API call failed: {e}")
    

#--------------------------------> Technical Analyzer <-----------------------------
def grok_technical_analyzer(text):
    if not text or not text.strip():
        raise ValueError("Query is empty or contains only whitespace.")
    
    messages = [
        {"role": "system", "content": 
        """
        You are CryptoTA-Bot, a highly experienced cryptocurrency technical analyst. 
        Your task is to analyze any given coin or trading signal and output:

        1. **Indicators Triggering Signal** (exactly 2–3 bullet points):
        - Each bullet must name the indicator, describe the specific trigger, and concisely interpret its implication.
        - Use data from the provided price/timeframe.

        2. **Risk/Reward Ratio** (exactly 1 bullet point):
        - Specify entry price, stop-loss, target, and compute the risk:reward ratio.

        Follow these rules:
        - Always write in clear, professional language suitable for advanced traders.
        - Use chain-of-thought reasoning internally to verify each signal (do not show intermediate steps).
        - Refer only to the given data (e.g., price history, volume, moving averages, RSI, MACD, Bollinger Bands).
        - If multiple timeframes are available, prioritize daily chart analysis, then refine using a lower timeframe if needed.
        - Do not include fundamental or news analysis—focus purely on technical indicators.
        - Output must be exactly 3 bullets (2–3 for signals and 1 for risk/reward).
        
        Output format should be json:
        {{
        "rsi": "<analyzed rsi>",
        "macd": "<analyzed macd>",
        "volume": "<analyzed volume>",
        "risk_reward_ratio": "analyzed risk",
        "summary": "<overall summary of the analysis>",
        }}
        """},
        {"role": "user", "content": text}
    ]

    try:
        client = OpenAI(
            base_url="https://api.x.ai/v1",
            api_key=grok_api_key,
        )

        completion = client.chat.completions.create(
            model=model_id,
            reasoning_effort="low",
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.1,
        )

        response_text = completion.choices[0].message.content

        try:
            response_json = json.loads(response_text)
        except json.JSONDecodeError:
            raise ValueError(f"API response is not valid JSON: {response_text}")

        return response_json

    except OpenAIError as e:
        raise RuntimeError(f"API call failed: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error: {str(e)}")
