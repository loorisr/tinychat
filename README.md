Very simple LLM chat frontend with Fastapi

![image](https://github.com/user-attachments/assets/9f8de766-4732-424c-997f-c4ddac95546c)

I wanted a very lightweight and simple chat interface to try several LLM.

There are several projects but non of them are very lightweight (hundreds of Mb to Gb):
* https://github.com/open-webui/open-webui
* https://github.com/jasonacox/TinyLLM/tree/main/chatbot
* https://github.com/fmaclen/hollama
* ...

So I decided to build a very simple chat interface. The docker image size is 161 mo.

It can search on the internet and scrape pages thanks to [Firecrawl](https://www.firecrawl.dev/) (which is self-hostable).

Thanks to [LiteLLM](https://github.com/BerriAI/litellm), you can configure as many models as you want inside `models.yaml`.

````yaml
mistral-large:
  api_key: "your-api-key"
  endpoint: "https://api.mistral.ai/v1"
  model_name: "mistral/mistral-large-latest"
````
