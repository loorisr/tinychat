from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import litellm
import asyncio
import yaml
import os
from pathlib import Path
import time

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


@app.websocket("/chat")
async def chat_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
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

            start_time = time.time()
            user_ip = websocket.client.host
            print(f"Model {llm_config['model_name']}, message {user_message}, IP: {user_ip}")
            response = await litellm.acompletion(
                model=llm_config["model_name"],
                messages=[{"content": user_message, "role": "user"}],
                temperature=0.7,
                api_key=llm_config.get("api_key"),
                api_base=llm_config.get("endpoint"),
                stream=True,
            )

            total_tokens = 0
            async for chunk in response:
                if chunk.choices[0].delta.content is not None:
                    content_chunk = chunk.choices[0].delta.content
                    await websocket.send_text(content_chunk)
                    if "usage" in chunk:
                        total_tokens = chunk.usage.total_tokens

            end_time = time.time()
            duration = end_time - start_time
            tokens_per_second = total_tokens / duration if duration > 0 else 0
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
