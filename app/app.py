from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
import asyncio
import base64
import json
import httpx
import requests
import yaml
from urllib.parse import quote_plus
import re
import os
from openai import AsyncOpenAI
from pathlib import Path
from datetime import datetime
from firecrawl.firecrawl import FirecrawlApp

FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "my-api-key")
FIRECRAWL_API_URL = os.getenv("FIRECRAWL_API_URL", "https://api.firecrawl.dev")
QUICKCHART_URL = os.getenv("QUICKCHART_URL", "https://quickchart.io/")
TERRARIUM_URL = os.getenv("TERRARIUM_URL")

firecrawl_client = FirecrawlApp(api_key=FIRECRAWL_API_KEY, api_url=FIRECRAWL_API_URL)

system_prompt = f"""
You are a helpful assistant.
Your name is Tiny Chat. Today is {datetime.now().isoformat()}
You can use Markdown.
You can make search on internet using the command: "/search $QUERY$". Return a message with only this command.
You can read a page on internet using the command: "/scrape $page_adresse$". Return a message with only this command. One per line. Try to access only to the necessary pages.
"""

system_prompt = f"""
You are a helpful assistant.
Your name is Tiny Chat. Today is {datetime.now().isoformat()}
You can use Markdown.""" + """
You can use functions. You can use several in a row but only one at a time. To use a function, use this format, and return only this: {"function": "function_name", "arguments":{"argument_name": "argument_value"}}
The following functions are available to you:
* internet_search: search on the internet. argument : query, a string/
* internet_scrape: scrape a page from the internet. argument : urls, an array of urls   
* geocoding: get the latitude, longitude and altitude of a place. argument : name, a string   
* weather: get the current and forecast weather of a place. argument : latitude and longitude. return temperature (°C), precipirations (mm)
* python: execute python code. argument : code. You cannot use plt.show but plt.savefig() is allowed. It if returns an image name, use ![image](/tmp/{imagename})  to display it
* chartjs: You can use ChartJS v4 to generate chart. argument : chart: Chart.js v4 configuration object to render. It returns an image name, use ![image](/chart?c={imagename}) to display it. 
"""

app = FastAPI()


# Mount static files for mobile-friendly CSS
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# for sandbox generated file
app.mount("/tmp", StaticFiles(directory="tmp"), name="tmp")


LITELLM_URL = os.environ.get("LITELLM_URL")
# Default value: It's better to keep the default value out of the env for security,
# you could override it with the env if needed.

if not LITELLM_URL:
    print(
        "Warning: LITELLM_URL environment variable and default not set. /models endpoint will not work."
    )
    

openai_client = AsyncOpenAI(
    api_key="my key",  
    base_url=LITELLM_URL
)

@app.get("/chart")  # Use POST to accept JSON in the request body
async def get_chart(c: str = Query(..., description="A JSON-encoded string")):
    quickchart_api_url = QUICKCHART_URL
        
    format = "png"
    w = 200
    h = 200
    json_string = json.dumps(c)

    try:
        # Make a POST request to the external API with the JSON payload using httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(quickchart_api_url, params={'c': c, 'w': w, 'h': h, 'format': format})
            response.raise_for_status()  # Raise an exception for HTTP errors
            
            # Determine the content type from the response headers
            content_type = response.headers.get("content-type", "image/png")
            print(content_type)
            
            # Return the image as a response with the appropriate media type
            return Response(content=response.content, media_type=content_type)
    except httpx.HTTPStatusError as e:
        # Handle HTTP errors (e.g., 404, 500)
        raise HTTPException(status_code=e.response.status_code, detail="External API request failed")
    except Exception as e:
        # Handle other exceptions
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    with open("app/static/index.html", "r") as file:
        HTML_CONTENT = file.read()

    return HTML_CONTENT


def chartjs_quickchart(chart):
    print(f"Generating chart : {chart}")
           
    #chart_json = json.load(chart)
    json_string = json.dumps(chart).rstrip('"').lstrip('"')

    # Step 2: URL-encode the JSON string
    url_encoded_json = quote_plus(json_string)

    #print("JSON String:", json_string)
    print("URL-Encoded JSON:", url_encoded_json)
    
    return json.dumps({'imagename': url_encoded_json})
   
    
def python_sandbox(code):
    print(f"Executing python code : {code}")
    
    base_url = TERRARIUM_URL
    
    json_data = {
        'code': code,
    }

    response = requests.post(base_url, json=json_data)

    if response.status_code == 200:
        response = response.json()
        
        if response['success']:
            files = response['output_files']
            for file in files:
                #print(file['b64_data'])
                imgdata = base64.b64decode(file['b64_data'], validate=True)
                #print(imgdata)
                with open(f"tmp/{file['filename']}", "wb") as fh:
                    fh.write(imgdata)
                del file['b64_data']
        
        print(json.dumps(response))
        return json.dumps(response)
    else:
        print("python code executing error")
        return {"error"}    
    
def openmeteo_geocoding(name):
    print(f"Geocoding search : {name}")
    
    
    base_url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {
        "name": name,
        "count": 1,
    }

    response = requests.get(base_url, params=params)

    if response.status_code == 200:
        #print(response.json())
        results = response.json()["results"][0]
        #print(results)

        geocoding_result = {
                "latitude": results["latitude"],
                "longitude": results["longitude"],
                "altitude": results["elevation"],
            }
                
        #print(response.json())
        
        #print(yaml.dump(geocoding_result))
        #return yaml.dump(geocoding_result)
        print(json.dumps(geocoding_result))
        return json.dumps(geocoding_result)
    else:
        print("geocoding error")
        return {"error"}    

    
def openmeteo_weather(latitude, longitude):
    weather_dict = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Depositing rime fog",
        51: "Drizzle: Light intensity",
        53: "Drizzle: Moderate intensity",
        55: "Drizzle: Dense intensity",
        56: "Freezing Drizzle: Light intensity",
        57: "Freezing Drizzle: Dense intensity",
        61: "Rain: Slight intensity",
        63: "Rain: Moderate intensity",
        65: "Rain: Heavy intensity",
        66: "Freezing Rain: Light intensity",
        67: "Freezing Rain: Heavy intensity",
        71: "Snow fall: Slight intensity",
        73: "Snow fall: Moderate intensity",
        75: "Snow fall: Heavy intensity",
        77: "Snow grains",
        80: "Rain showers: Slight",
        81: "Rain showers: Moderate",
        82: "Rain showers: Violent",
        85: "Snow showers: Slight",
        86: "Snow showers: Heavy",
        95: "Thunderstorm: Slight or moderate",
        96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail"
    }
    
    print(f"Weather for : {latitude}, {longitude}")
    
    
    base_url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "timezone": "auto",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code",
    }

    response = requests.get(base_url, params=params)

    if response.status_code == 200:
        #print(response.json())
        results = response.json()
        #print(results)

        weather_result = results['daily']
        
        for i, code in enumerate(weather_result['weather_code']):
            weather_result['weather_code'][i] = weather_dict.get(code, "Unknown code")
        
        #print(response.json())
        
        #print(yaml.dump(geocoding_result))
        #return yaml.dump(geocoding_result)
        print(json.dumps(weather_result))
        return json.dumps(weather_result)
    else:
        print("weather error")
        return {"error"}    
    
    

def firecrawl_search(query):
    print(f"Firecrawl search query: {query}")
    results = firecrawl_client.search(query)
    
    search_results = [
            {
                "title": result["title"],
                "snippet": result["description"],
                "url": result["url"],
            }
            for result in results['data']]
                
    print(yaml.dump(search_results))
    return yaml.dump(search_results)

def firecrawl_scrape(urls):
    print(f"Firecrawl scraping urls : {urls}")
    results = firecrawl_client.batch_scrape_urls(urls, params={"formats": ["markdown"]})
    # markdown_results = ""
    # for page in scrape_results['data']:
    #     markdown_results += page['markdown']
    # return markdown_results


    scrape_results = [
            {
                "content": page["markdown"],
            }
            for page in results['data']]
                
    print(yaml.dump(scrape_results))
    return yaml.dump(scrape_results)

@app.get('/favicon.svg', include_in_schema=False)
async def favicon():
    return FileResponse('app/static/favicon.svg')

## WIP
async def handle_tools(message_session, assistant_message, model_name, websocket):
    try:
        #print(assistant_message)
        json_start = assistant_message.find('{')  # Find the start of the JSON
        json_end = assistant_message.rfind('}') + 1  # Find the end of the JSON
        json_str = assistant_message[json_start:json_end]  # Extract the JSON string

        #print(json_str)
        if json_str:
            json_response = json.loads(json_str)
        else:
            return message_session, ""
        
        #print(json_response)
            
        if 'function' in json_response:
            print(json_response)
            # Step 3: call the function
            # Note: the JSON response may not always be valid; be sure to handle errors
            available_functions = {
                "internet_search": firecrawl_search,
                "internet_scrape": firecrawl_scrape,
                "geocoding": openmeteo_geocoding,
                "weather": openmeteo_weather,
                "python": python_sandbox,
                "chartjs": chartjs_quickchart,
            }  

            function_name = json_response['function']
            function_to_call = available_functions[function_name]
            print(f"function_name {function_name}")
            await websocket.send_json({"tool": f"Using tool *{function_name}* with arguments *{json.dumps(json_response['arguments'])}*"})
            function_args = json_response['arguments']
            print(f"function_args {function_args}")

            function_response = function_to_call(
                    **function_args,
            )
            #print(f"function_response {function_response}")
            message_session.append( {"role": "user", "content": function_response})
            
            message_session, assistant_message = await send_stream_message(message_session, model_name, websocket)
            return message_session, assistant_message 
        else:
            return message_session, ""
    except ValueError as e:
        print(f"ValueError: {e}")
        return message_session, ""
    return message_session, ""

    

@app.get("/models")
async def get_models():
    """
    Fetches the list of models from the LITELLM_URL/models endpoint.
    """
    if not LITELLM_URL:
        raise HTTPException(
            status_code=500, detail="LITELLM_URL environment variable not set."
        )
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{LITELLM_URL}/models")
            response.raise_for_status()  # Raise an exception for bad status codes
            return response.json()
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=e.response.status_code if e.response is not None else 500,
            detail=f"Error communicating with LITELLM_URL: {e}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {e}"
        )
        
        
async def send_stream_message(message_session, model_name, websocket):
    print(f"Model {model_name}, IP:  {websocket.client.host}")
    #print(f"Model {model_name}")
    #print(f"message_session {message_session}")
    response = await openai_client.chat.completions.create(
        model=model_name,
        messages=message_session,
        temperature=0.7,
        stream=True,
        stream_options={"include_usage": True},
    )
    
    assistant_message = ""
    async for chunk in response:
        if chunk.choices[0].delta.content is not None:
            content_chunk = chunk.choices[0].delta.content
            assistant_message += content_chunk
            await websocket.send_json({"assistant": content_chunk})
        if chunk.usage and chunk.usage.completion_tokens:
            completion_tokens = chunk.usage.completion_tokens
            await websocket.send_json({"token": completion_tokens})
            break #### hack with groq, otherwise it never stops

    await websocket.send_json({"event": "END"})
    message_session.append( {"role": "assistant", "content": assistant_message})
    
    return message_session, assistant_message

@app.websocket("/chat")
async def chat_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        message_session = []
        message_session.append({"role": "system", "content": system_prompt})
        while True:
            data = await websocket.receive_json()
            user_message = data.get("message", "")
            model_name = data.get("model", "")

            message_session.append( {"role": "user", "content": user_message})

            message_session, assistant_message = await send_stream_message(message_session, model_name, websocket)

            # handle the tools, up to 4 times in a row
            message_session, assistant_message = await handle_tools(message_session, assistant_message, model_name, websocket)

            if assistant_message:
                message_session, assistant_message = await handle_tools(message_session, assistant_message, model_name, websocket)
            
            if assistant_message:
                message_session, assistant_message = await handle_tools(message_session, assistant_message, model_name, websocket)

            if assistant_message:
                message_session, assistant_message = await handle_tools(message_session, assistant_message, model_name, websocket)
            

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        await websocket.send_json({"status": "error", "message": str(e)})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
