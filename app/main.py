import streamlit as st
import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone

# Load environment variables
load_dotenv()

# ---- CONFIG ----
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")  # Ensure this is set in your .env file

# ---- INIT ----
# Initialize OpenAI Client
openai_client = OpenAI(api_key=OPENAI_API_KEY)
  
# Initialize Pinecone Client
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX_NAME)

# ---- Helper Functions ----
def generate_query_embedding(text):
    response = openai_client.embeddings.create(
        input=[text],
        model="text-embedding-ada-002"
    )
    embedding = response.data[0].embedding
    return embedding

def summarize_event(description):
    prompt = f"Summarize the following event in 2-3 sentences:\n\n{description}"
    response = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content.strip()

def extract_intent_from_query(user_query):
    prompt = f"""
    Given the following user query, identify:

    - Mood (like Relaxed, Excited, Curious, Lonely, etc.)
    - Learning Goal (like 'learn AI', 'explore arts', etc.)
    - Life Situation (like 'new to city', 'graduating', etc.)

    If nothing is mentioned for a field, leave it blank.

    User Query: "{user_query}"

    Respond strictly in JSON format:
    {{
      "mood": "",
      "learning_goal": "",
      "life_situation": ""
    }}
    """

    response = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return json.loads(response.choices[0].message.content.strip())

# ---- Streamlit Custom Styling ----
st.set_page_config(page_title="Event Finder", page_icon="📅", layout="wide")

st.markdown(
    """
    <style>
    body {
        background-color: #000000;
        color: #90ee90;
    }
    .stTextInput>div>div>input {
        background-color: #000000;
        color: #90ee90;
        border: 1px solid #90ee90;
    }
    .stButton>button {
        background-color: #90ee90;
        color: #000000;
        border: none;
        padding: 10px 24px;
        border-radius: 8px;
    }
    .stButton>button:hover {
        background-color: #76c776;
        color: black;
    }
    .stMarkdown h1 {
        text-align: center;
        color: #90ee90;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ---- Title and Search Bar ----
st.markdown("<h1>🎉 Event Finder AI</h1>", unsafe_allow_html=True)
st.write("")  # Add slight space

# Centered Search Bar
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    query = st.text_input("🔎 Search events (e.g., 'tech workshops in Boston')", "")

if query:
    with st.spinner("🔎 Understanding your search intent..."):
        # 1. Extract Smart Intent
        intent = extract_intent_from_query(query)

        # 2. Build Enhanced Search Query
        enhanced_query = f"{query}. Mood: {intent['mood']}. Learning goal: {intent['learning_goal']}. Life situation: {intent['life_situation']}."

        # Show detected intent nicely
        st.success(f"🔍 Detected Mood: {intent['mood']}, Goal: {intent['learning_goal']}, Life: {intent['life_situation']}")

        # 3. Generate embedding for enhanced query
        query_embedding = generate_query_embedding(enhanced_query)

        # 4. Query Pinecone
        results = index.query(
            vector=query_embedding,
            top_k=9,
            include_metadata=True
        )

        matches = results.get("matches", [])

        if matches:
            st.success(f"Found {len(matches)} matching events! 🎯")

            # Display results: 3 cards per row
            for row_idx in range(0, len(matches), 3):
                cols = st.columns(3)

                for i in range(3):
                    if row_idx + i < len(matches):
                        match = matches[row_idx + i]
                        meta = match.get("metadata", {})
                        doc = meta.get("description", "No Description")

                        with cols[i]:
                            st.markdown(
                                """
                                <div style="background-color: #121212; padding: 20px; border-radius: 12px; box-shadow: 0px 0px 12px rgba(144,238,144,0.6); text-align: center;">
                                """,
                                unsafe_allow_html=True
                            )

                            st.subheader(meta.get('title', 'No Title'), divider='green')
                            st.write(f"📍 **{meta.get('location', 'Unknown')}**")
                            st.write(f"🗓️ **{meta.get('date_time', 'Unknown')}**")
                            st.markdown(f"[🔗 View Event]({meta.get('link', '#')})")

                            if st.button(f"✨ Summarize {row_idx+i+1}", key=f"btn-{row_idx+i}"):
                                with st.spinner("Summarizing..."):
                                    summary = summarize_event(doc)
                                    st.success(summary)

                            st.markdown(
                                """
                                </div>
                                """,
                                unsafe_allow_html=True
                            )
        else:
            st.warning("⚡ No events found matching your query.")
