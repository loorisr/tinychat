from openai import OpenAI
import streamlit as st
import time
from dotenv import load_dotenv
import os

load_dotenv()  # take environment variables from .env.

BASE_URL = os.getenv("BASE_URL")
MODEL = os.getenv("MODEL")
API_KEY = os.getenv("API_KEY")

st.title("TinyChat")

client = OpenAI(
    base_url = BASE_URL,
    api_key = API_KEY,
)

if "openai_model" not in st.session_state:
    st.session_state["openai_model"] = MODEL

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("What is up?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    startTime = time.time()
    with st.chat_message("assistant"):
        stream = client.chat.completions.create(
            model=st.session_state["openai_model"],
            messages=[
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ],
            stream=True,
            #stream_options={"include_usage": True} # not working
        )
        # Stream the response and accumulate it
        response = st.write_stream(stream)    

    st.session_state.messages.append({"role": "assistant", "content": response})
    endTime = time.time()
    with st.chat_message("assistant"):
        last_respoonse = st.session_state.messages[-1]["content"]
        number_words = len(last_respoonse.split())
        st.markdown( f"\n *{number_words} mots, temps: {endTime-startTime:.2f}s, {number_words/(endTime-startTime):.0f} mots/s*")
