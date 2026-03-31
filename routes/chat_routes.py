from flask import Blueprint, request, jsonify, session, flash, redirect, url_for, render_template
import google.generativeai as genai

# -----------------------------
# Blueprint Setup
# -----------------------------
chat_bp = Blueprint('chat', __name__)

# -----------------------------
# Gemini AI Configuration
# -----------------------------
GEMINI_API_KEY = 'AIzaSyCjSx2psIH8fzL3JPCd0-Mb3Dvu_12Fy88'  # 🔒 Replace with your actual API key
MODEL_NAME = "models/gemini-2.5-flash"

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(MODEL_NAME)

# -----------------------------
# Session-based chat history
# -----------------------------
def get_chat_history():
    """Retrieve chat history from session."""
    return session.get('chat_history', [])

def save_chat_history(history):
    """Save chat history to session."""
    session['chat_history'] = history
    session.modified = True

# -----------------------------
# Chat Page Route
# -----------------------------
@chat_bp.route('/', methods=['GET'])
def chat_page():
    """Render chatbot interface page."""
    if 'user_id' not in session:
        flash("Please login to access the chatbot.", "warning")
        return redirect(url_for('auth.login'))

    print(f"DEBUG: User {session.get('user_name')} accessed chat page")
    return render_template('patient/chat.html')

# -----------------------------
# API: Get Chat History
# -----------------------------
@chat_bp.route('/api/chat_history', methods=['GET'])
def get_chat_history_api():
    """Return saved chat history as JSON."""
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    history = get_chat_history()
    return jsonify(history)

# -----------------------------
# API: Send Message to AI
# -----------------------------
@chat_bp.route('/api/chat', methods=['POST'])
def chat_api():
    """Handle chat message and get response from Gemini (medical domain + small talk)."""
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        data = request.get_json()
        user_query = data.get('query', '').strip().lower()

        if not user_query:
            return jsonify({'error': 'Query is required'}), 400

        # -----------------------------
        # Step 1: Allowed Small Talk & Domain Validation
        # -----------------------------
        # Some casual greetings or polite phrases we allow
        allowed_smalltalk = [
            "hi", "hello", "hey", "good morning", "good evening", "good afternoon",
            "how are you", "what’s up", "thank you", "thanks", "ok", "okay"
        ]

        # Medical/hospital-related keywords
        medical_keywords = [
            'doctor', 'hospital', 'patient', 'disease', 'symptom', 'medicine',
            'treatment', 'diagnosis', 'therapy', 'surgery', 'nurse', 'pharmacy',
            'appointment', 'clinic', 'report', 'blood', 'scan', 'x-ray', 'lab',
            'cardiology', 'neurology', 'infection', 'emergency', 'prescription',
            'fever', 'pain', 'cough', 'cold', 'fracture', 'covid', 'health'
        ]

        # Check domain or smalltalk validity
        is_medical_related = any(word in user_query for word in medical_keywords)
        is_smalltalk = any(user_query.startswith(word) for word in allowed_smalltalk)

        # If not related and not small talk → politely decline
        if not is_medical_related and not is_smalltalk:
            polite_response = (
                "I'm mainly trained to talk about healthcare, hospitals, and medical topics. "
                "Please ask something related to health or patient care."
            )
            return jsonify({'response': polite_response}), 200

        # -----------------------------
        # Step 2: Build Prompt for Gemini
        # -----------------------------
        chat_history = get_chat_history()
        history_str = '\n'.join([
            f"User: {msg['content']}" if msg['role'] == 'user' else f"Assistant: {msg['content']}"
            for msg in chat_history[-10:]
        ])

        system_prompt = (
            "You are a polite and knowledgeable medical and hospital assistant. "
            "You can respond to basic greetings politely (like 'hello', 'hi', 'how are you'), "
            "but your main focus is healthcare-related questions. "
            "If asked something unrelated, kindly tell the user that you can only discuss "
            "medical or hospital-related topics."
        )

        full_prompt = (
            f"{system_prompt}\n\n{history_str}\nUser: {user_query}\nAssistant:"
            if history_str else f"{system_prompt}\n\nUser: {user_query}\nAssistant:"
        )

        # -----------------------------
        # Step 3: Generate Response
        # -----------------------------
        response = model.generate_content(full_prompt)
        ai_response = response.text.strip() if response.text else "I'm sorry, I couldn't generate a response."

        # -----------------------------
        # Step 4: Save to Chat History
        # -----------------------------
        chat_history.append({'role': 'user', 'content': user_query})
        chat_history.append({'role': 'assistant', 'content': ai_response})
        save_chat_history(chat_history)

        print(f"DEBUG: Chat response for user {session.get('user_id')}: {ai_response[:80]}...")
        return jsonify({'response': ai_response})

    except Exception as e:
        print(f"DEBUG: Chat Error - {e}")
        return jsonify({'error': 'Failed to generate response. Please try again.'}), 500


# -----------------------------
# API: Clear Chat
# -----------------------------
@chat_bp.route('/api/clear_chat', methods=['POST'])
def clear_chat():
    """Clear chat history from session."""
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    session.pop('chat_history', None)
    flash("Chat history cleared.", "info")
    return jsonify({"message": "Chat history cleared"}), 200
