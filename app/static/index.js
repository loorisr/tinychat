document.addEventListener("alpine:init", () => {
  Alpine.data("state", () => ({

    // current state
    cstate: {
      time: null,
      messages: [],
    },

    // historical state
    histories: JSON.parse(localStorage.getItem("histories")) || [],

    home: 0,
    generating: false,
    endpoint: `${window.location.origin}`,
    model_name: ``,

    gottenFirstChunk: false,
    prefill_start: 0,

    // performance tracking
    time_till_first: 0,
    tokens_per_second: 0,
    total_tokens: 0,

    start_time: 0,
    tokens: 0,

    models_list: 'ok',
    
    // Websocket variables and functions
    websocket: null,
    websocketStatus: "disconnected",

    connectWebSocket() {
      const wsUrl = `ws://${window.location.host}/chat`; // Replace with your WebSocket URL if different
      this.websocket = new WebSocket(wsUrl);

      this.websocket.addEventListener("open", (event) => {
        //console.log("WebSocket connection opened:", event);
        this.websocketStatus = "connected";
      });


      this.websocket.addEventListener("message", (event) => {
        const jsonData = JSON.parse(event.data);
        //console.log("WebSocket message received:", jsonData);

        if ('token' in jsonData) {
          this.total_tokens += -this.tokens + jsonData.token;
          this.tokens = jsonData.token;

          const diff = Date.now() - this.start_time;
          this.tokens_per_second = this.tokens / (diff / 1000);
          this.start_time = 0;
        }
        if ('event' in jsonData) {
          this.generating = false;
          //console.log("event:", "end");
        }
        if ('tool' in jsonData) {
          this.cstate.messages.push({ role: "tool", content: "" });
          this.cstate.messages[this.cstate.messages.length - 1].content += jsonData.tool;
          this.gottenFirstChunk = false;
        }
        
        if ('assistant' in jsonData) {
          if (!this.gottenFirstChunk) {
            this.cstate.messages.push({ role: "assistant", content: "" });
            this.gottenFirstChunk = true;
          }
          
          // add chunk to the last message
          this.cstate.messages[this.cstate.messages.length - 1].content += jsonData.assistant;

          // calculate performance tracking
          this.tokens += 1;
          this.total_tokens += 1;
          if (this.start_time === 0) { // calculate TTFT
            this.start_time = Date.now();
            this.time_till_first = this.start_time - this.prefill_start;
          } else {
            const diff = Date.now() - this.start_time;
            if (diff > 0) {
              this.tokens_per_second = this.tokens / (diff / 1000);
            }
          }

                // update the state in histories or add it if it doesn't exist
          const index = this.histories.findIndex((cstate) => {
            return cstate.time === this.cstate.time;
          });
          this.cstate.time = Date.now();
          if (index !== -1) {
            // update the time
            this.histories[index] = this.cstate;
          } else {
            this.histories.push(this.cstate);
          }
          // update in local storage
          localStorage.setItem("histories", JSON.stringify(this.histories));
      }

      });

      this.websocket.addEventListener("close", (event) => {
        console.log("WebSocket connection closed:", event);
        this.websocketStatus = "disconnected";
        // Attempt to reconnect after a delay
        setTimeout(() => {
          this.connectWebSocket();
        }, 5000); // Reconnect after 5 seconds
      });

      this.websocket.addEventListener("error", (error) => {
        console.error("WebSocket error:", error);
        this.websocketStatus = "error";
        // Clean up if connection errors
          if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
          }
      });
    },

    sendMessage(message) {
      if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
        this.websocket.send(message);
      } else {
        console.error("WebSocket not connected.");
      }
    },
    
    updateModelsListFromMessage(newModelList){
      this.models_list = newModelList.map(obj => obj.id).sort((a, b) => {return a.localeCompare(b); });
      this.model_name = localStorage.getItem("model_name") || this.models_list[0]
    },

    removeHistory(cstate) {
      const index = this.histories.findIndex((state) => {
        return state.time === cstate.time;
      });
      if (index !== -1) {
        this.histories.splice(index, 1);
        localStorage.setItem("histories", JSON.stringify(this.histories));
      }
    },


    async handleSend() {
      const el = document.getElementById("input-form");
      const value = el.value.trim();
      if (!value) return;

      if (this.generating) return;
      this.generating = true;
      if (this.home === 0) this.home = 1;

      // ensure that going back in history will go back to home
      window.history.pushState({}, "", "/");

      // add message to list
      this.cstate.messages.push({ role: "user", content: value });

      // clear textarea
      el.value = "";
      el.style.height = "auto";
      el.style.height = el.scrollHeight + "px";

      // reset performance tracking
      this.prefill_start = Date.now();
      this.tokens_per_second = 0;
      this.tokens = 0;
      this.gottenFirstChunk = false;

      this.websocket.send(JSON.stringify({ message: value, model: this.model_name }));
    },

    async handleEnter(event) {
      // if shift is not pressed
      if (!event.shiftKey) {
        event.preventDefault();
        await this.handleSend();
      }
    },

    updateModelsList() {
      fetch(`${this.endpoint}/models`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      }).then((response) => response.json()).then((data) => {
       this.models_list = data.data.map(obj => obj.id).sort((a, b) => {return a.localeCompare(b); });
       this.model_name = localStorage.getItem("model_name") || this.models_list[0]
      }).catch(console.error);
    },


    init(){
      //initialize websocket on load.
      this.connectWebSocket();
    }

  }));
});

const { markedHighlight } = globalThis.markedHighlight;
marked.use(markedHighlight({
  langPrefix: "hljs language-",
  highlight(code, lang, _info) {
    const language = hljs.getLanguage(lang) ? lang : "plaintext";
    return hljs.highlight(code, { language }).value;
  },
}));


const BOM = [239, 187, 191];
function hasBom(buffer) {
  return BOM.every((charCode, index) => buffer.charCodeAt(index) === charCode);
}
