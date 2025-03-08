# TinyChat
## Very simple LLM chat frontend with Fastapi

Fork from https://github.com/tinygrad/tinygrad/tree/master/examples/tinychat

I wanted a very lightweight and simple chat interface to try several LLM.

There are several projects but non of them are very lightweight (hundreds of Mb to Gb):
* https://github.com/open-webui/open-webui
* https://github.com/jasonacox/TinyLLM/tree/main/chatbot
* https://github.com/fmaclen/hollama
* https://github.com/danny-avila/LibreChat
* ...

I wanted a very simple chat interface. The docker image size is 73 mo!

The UI is from [Tinygrad](https://github.com/tinygrad/tinygrad/tree/master/examples/tinychat) and tools have been added.

Features:
* needs a OpenAI compatible API endpoint. LiteLLM Proxy is recommended. Endpoint is env var `LITELLM_URL`
* Auto discover models (all that are available at /models)
* Simple history
* Use of tools:
    * Search on the internet and scrape pages: [Firecrawl](https://www.firecrawl.dev/) (it is self-hostable). env var : `FIRECRAWL_API_KEY`and `FIRECRAWL_API_URL`
    * Geocoding: https://open-meteo.com/
    * Weather forecast: https://open-meteo.com/
    * Execute python code: https://github.com/khoj-ai/terrarium `TERRARIUM_URL`
    * Generate charts: https://quickchart.io/  `QUICKCHART_URL`

  ![image](https://github.com/user-attachments/assets/f3c6a798-5172-428b-89ba-877d9129befc)
