import os
import json
import uuid
from pathlib import Path
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from groq import Groq

app = Flask(__name__)
CORS(app)  # Enables cross-origin requests from GitHub Pages

# ==============================================================================
# CONFIGURATION SETTINGS
# Paste your real Groq API key inside the quotes below:
# ==============================================================================
GROQ_API_KEY = "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"  # <-- PUT YOUR GSK_ KEY HERE
GROQ_MODEL = "qwen/qwen3.8-27b"  # Classic universally supported model ID
DATA_FILE = "chats.json"
PORT = 5000

# Base directory setup
base_dir = Path(__file__).resolve().parent

# Load personality from personality.txt if it exists
personality_path = base_dir / 'personality.txt'
if personality_path.exists():
    with open(personality_path, 'r', encoding='utf-8') as f:
        SYSTEM_PERSONA = f.read().strip()
else:
    SYSTEM_PERSONA = "You are ZeeDax Assistance, a helpful and intelligent AI assistant."

# Initialize Groq Client safely
groq_client = None
init_error_message = None

if not GROQ_API_KEY or GROQ_API_KEY == "gsk_your_actual_groq_key_here":
    init_error_message = "[Configuration Error]: Please paste your real Groq API key on line 15 of app.py!"
else:
    try:
        groq_client = Groq(api_key=GROQ_API_KEY)
    except Exception as err:
        init_error_message = f"[Groq Client Initialization Error]: {str(err)}"


# --- Data Storage Functions ---

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr

def get_or_create_profile(user_ip, profiles):
    if user_ip not in profiles:
        initial_chat_id = f"chat_{uuid.uuid4().hex[:6]}"
        profiles[user_ip] = {
            "profile_id": f"profile_{uuid.uuid4().hex[:8]}",
            "active_chat_id": initial_chat_id,
            "chats": [
                {
                    "id": initial_chat_id,
                    "title": "General Conversation",
                    "messages": [
                        {"role": "assistant", "content": "Hello! I am ZeeDax Assistance. How can I assist you today?"}
                    ]
                }
            ]
        }
        save_data(profiles)
    return profiles[user_ip]


# --- Web Routes & APIs ---

@app.route('/')
def index():
    user_ip = get_client_ip()
    profiles = load_data()
    get_or_create_profile(user_ip, profiles)
    return render_template('index.html')

@app.route('/api/profile', methods=['GET'])
def get_profile_data():
    user_ip = get_client_ip()
    profiles = load_data()
    profile = get_or_create_profile(user_ip, profiles)
    return jsonify({
        "ip": user_ip,
        "chats": profile["chats"],
        "active_chat_id": profile["active_chat_id"]
    })

@app.route('/api/chats/new', methods=['POST'])
def create_new_chat():
    user_ip = get_client_ip()
    profiles = load_data()
    profile = get_or_create_profile(user_ip, profiles)
    
    data = request.json or {}
    chat_title = data.get("title", "").strip() or f"New Chat {len(profile['chats']) + 1}"
    new_chat_id = f"chat_{uuid.uuid4().hex[:6]}"
    
    new_chat = {
        "id": new_chat_id,
        "title": chat_title,
        "messages": [
            {"role": "assistant", "content": f"Welcome to '{chat_title}'! How can I help?"}
        ]
    }
    
    profile["chats"].insert(0, new_chat)
    profile["active_chat_id"] = new_chat_id
    save_data(profiles)
    
    return jsonify(new_chat)

@app.route('/api/chats/reset', methods=['POST'])
def reset_chats():
    user_ip = get_client_ip()
    profiles = load_data()
    
    if user_ip in profiles:
        del profiles[user_ip]
        save_data(profiles)
        
    get_or_create_profile(user_ip, profiles)
    return jsonify({"status": "success", "message": "All chats reset successfully."})

@app.route('/api/message', methods=['POST'])
def send_message():
    user_ip = get_client_ip()
    profiles = load_data()
    profile = get_or_create_profile(user_ip, profiles)
    
    data = request.json or {}
    chat_id = data.get("chat_id")
    user_text = data.get("message", "").strip()
    
    if not user_text:
        return jsonify({"error": "Empty message"}), 400

    target_chat = next((c for c in profile["chats"] if c["id"] == chat_id), None)
    if not target_chat:
        return jsonify({"error": "Chat not found"}), 404

    target_chat["messages"].append({"role": "user", "content": user_text})

    if init_error_message or not groq_client:
        ai_reply = init_error_message or "[Configuration Error]: Groq client failed to initialize."
    else:
        groq_messages = [
            {"role": "system", "content": SYSTEM_PERSONA}
        ]
        for msg in target_chat["messages"]:
            groq_messages.append({"role": msg["role"], "content": msg["content"]})

        try:
            response = groq_client.chat.completions.create(
                messages=groq_messages,
                model=GROQ_MODEL
            )
            ai_reply = response.choices[0].message.content
        except Exception as e:
            ai_reply = f"[Groq API Error]: {str(e)}"

    target_chat["messages"].append({"role": "assistant", "content": ai_reply})
    profile["active_chat_id"] = chat_id
    save_data(profiles)

    return jsonify({"role": "assistant", "content": ai_reply})

if __name__ == '__main__':
    app.run(debug=True, port=PORT)
