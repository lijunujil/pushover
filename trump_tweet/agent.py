import os
import json
import requests
import re

# --- Configuration from GitHub Secrets ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # or DeepSeek key
PUSHOVER_USER = os.getenv("PUSHOVER_USER_KEY")
PUSHOVER_TOKEN = os.getenv("PUSHOVER_APP_TOKEN")
STATE_FILE = "last_seen.json"


# --- Helper Functions ---

def get_new_posts(last_id=None):
    """
    Fetch recent Trump posts and return a list of new posts
    since the last processed post (oldest first).
    """
    url = "https://truthsocial.io/api/v1/@realDonaldTrump"
    r = requests.get(url, timeout=10)
    data = r.json()

    new_posts = []
    for post in data:
        if post["id"] == last_id:
            break  # Stop when we reach last processed post
        text = re.sub("<.*?>", "", post["content"]).strip()
        new_posts.append({"id": post["id"], "text": text})

    return list(reversed(new_posts))  # Oldest first


def summarize(text):
    """
    Generate a short AI summary of a post for push notification.
    """
    prompt = f"Summarize in one short sentence for a push notification: {text}"
    resp = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}]
        }
    )
    resp_json = resp.json()
    return resp_json["choices"][0]["message"]["content"].strip()


def send_push(title, message):
    """
    Send a push notification via Pushover.
    """
    r = requests.post("https://api.pushover.net/1/messages.json", data={
        "token": PUSHOVER_TOKEN,
        "user": PUSHOVER_USER,
        "title": title,
        "message": message,
    })
    print(f"Push sent: {r.status_code}, {r.text}")


# --- Main Agent Logic ---

def main():
    # Load last processed post ID
    try:
        last_seen = json.load(open(STATE_FILE))
        last_id = last_seen.get("last_id")
    except FileNotFoundError:
        last_id = None

    # Fetch new posts
    new_posts = get_new_posts(last_id)
    if not new_posts:
        print("No new posts since last check.")
        return

    # Process each post
    for post in new_posts:
        text_lower = post["text"].lower()
        if "china" in text_lower:
            summary = summarize(post["text"])
            send_push("Trump on China", summary)
        else:
            print("New post not about China.")

        # Update last_seen state after each post
        json.dump({"last_id": post["id"]}, open(STATE_FILE, "w"))


if __name__ == "__main__":
    main()
