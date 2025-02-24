from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import litellm
import asyncio
import json
import yaml
import time
import os
from pathlib import Path
from datetime import datetime
from firecrawl.firecrawl import FirecrawlApp

FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "my-api-key")
FIRECRAWL_API_URL = os.getenv("FIRECRAWL_API_URL", "https://api.firecrawl.dev")

firecrawl_client = FirecrawlApp(api_key=FIRECRAWL_API_KEY, api_url=FIRECRAWL_API_URL)

system_prompt = f"""
You are a helpful assistant.
Your name is Tiny Chat. Today is {datetime.now().isoformat()}
You can use Markdown.
You can make search on internet using the command: "/search $QUERY$". Return a message with only this command.
You can read a page on internet using the command: "/scrape $page_adresse$". Return a message with only this command. One per line. Try to access only to the necessary pages.
"""

app = FastAPI()

# Mount static files for mobile-friendly CSS
app.mount("/static", StaticFiles(directory="static"), name="static")

# Load LLM configurations from YAML file
CONFIG_FILE = "../models.yaml"
if not Path(CONFIG_FILE).exists():
    raise FileNotFoundError(f"Config file {CONFIG_FILE} not found.")

with open(CONFIG_FILE, "r") as file:
    LLM_CONFIGS = yaml.safe_load(file)

# Validate YAML structure
if not isinstance(LLM_CONFIGS, dict):
    raise ValueError("YAML file must contain a dictionary of LLM configurations.")


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    with open("static/index.html", "r") as file:
        HTML_CONTENT = file.read()

    content=HTML_CONTENT.replace(
            "{% for llm_name in llm_names %}",
            "".join(
                [f"<option value='{llm_name}'>{llm_name}</option>" for llm_name in LLM_CONFIGS]
            ),
        )

    return content

async def send_LLM_message(message_session, llm_config):
    return True



@app.websocket("/chat")
async def chat_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        message_session = []
        message_session.append({"role": "system", "content": system_prompt})
        while True:
            data = await websocket.receive_json()
            user_message = data.get("message", "")
            llm_name = data.get("llm", "")

            if not user_message or not llm_name:
                await websocket.send_json(
                    {"status": "error", "message": "Empty message or LLM selection"}
                )
                continue

            if llm_name not in LLM_CONFIGS:
                await websocket.send_json({"status": "error", "message": "LLM not found"})
                continue

            llm_config = LLM_CONFIGS[llm_name]
            message_session.append( {"role": "user", "content": user_message})

            assistant_message = ""

            #start_time = time.time()
            user_ip = websocket.client.host
            print(f"Model {llm_config['model_name']}, message {user_message}, IP: {user_ip}")
            response = await litellm.acompletion(
                model=llm_config["model_name"],
                #messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}],
                messages=message_session,
                temperature=0.7,
                api_key=llm_config.get("api_key"),
                api_base=llm_config.get("endpoint"),
                stream=True,
                stream_options={"include_usage": True},
            )

            total_tokens = 0
            async for chunk in response:
                if chunk.choices[0].delta.content is not None:
                    content_chunk = chunk.choices[0].delta.content
                    assistant_message += content_chunk
                    await websocket.send_text(content_chunk)
                    if "usage" in chunk:
                        total_tokens = chunk.usage.total_tokens

            message_session.append( {"role": "assistant", "content": assistant_message})

            if "/search" in assistant_message:
                query = assistant_message[len("/search "):]
                assistant_message = ""
                print(f"Searching for {query}")
                await websocket.send_text(f"<br />Searching for *{query}* <br/><br/>")

                search_results = firecrawl_client.search(query)
                #print(json.dumps(search_results['data']))
                
                message_session.append( {"role": "user", "content": json.dumps(search_results['data'])})
                response = await litellm.acompletion(
                    model=llm_config["model_name"],
                    #messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}],
                    messages=message_session,
                    temperature=0.7,
                    api_key=llm_config.get("api_key"),
                    api_base=llm_config.get("endpoint"),
                    stream=True,
                    stream_options={"include_usage": True},
                )

                async for chunk in response:
                    if chunk.choices[0].delta.content is not None:
                        content_chunk = chunk.choices[0].delta.content
                        assistant_message += content_chunk
                        await websocket.send_text(content_chunk)

                message_session.append( {"role": "assistant", "content": assistant_message})

            
            if "/scrape" in assistant_message:
                lines = assistant_message.split()
                assistant_message = ""
                #url = lines[len("/scrape "):]
                urls = [line for line in lines if line != "/scrape"]
                print(f"Scraping pages {urls}")
                await websocket.send_text(f"<br />Scraping pages {urls}<br />")

                scrape_results = firecrawl_client.batch_scrape_urls(urls, params={"formats": ["markdown"]})
                for page in scrape_results["data"]:
                    del page["metadata"]
                
                message_session.append( {"role": "user", "content": json.dumps(scrape_results["data"])})
                response = await litellm.acompletion(
                    model=llm_config["model_name"],
                    #messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}],
                    messages=message_session,
                    temperature=0.7,
                    api_key=llm_config.get("api_key"),
                    api_base=llm_config.get("endpoint"),
                    stream=True,
                    stream_options={"include_usage": True},
                )

                async for chunk in response:
                    if chunk.choices[0].delta.content is not None:
                        content_chunk = chunk.choices[0].delta.content
                        assistant_message += content_chunk
                        await websocket.send_text(content_chunk)

                message_session.append( {"role": "assistant", "content": assistant_message})
    
            #end_time = time.time()
            #duration = end_time - start_time
            #tokens_per_second = total_tokens / duration if duration > 0 else 0
            #await websocket.send_json(
            #    {"total_tokens": total_tokens, "tokens_per_second": f"{tokens_per_second:.2f}"}
            #)  # send as json

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        await websocket.send_json({"status": "error", "message": str(e)})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
