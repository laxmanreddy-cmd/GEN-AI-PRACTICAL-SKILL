# Week 3: MongoDB Connectivity and LLM Monitoring

A small command-line project that sends a question to Gemini or local Ollama,
measures the request, and saves its result in MongoDB when MongoDB is available.

## Project files

```text
Week-3/
├── .venv/                 # Local Python environment
├── .env                   # Your local Gemini key (ignored by Git)
├── .env.example           # Safe configuration template
├── .gitignore
├── README.md
├── cost_calculator.py
├── llm_client.py
├── main.py
├── mongo_logger.py
├── requirements.txt
└── test_project.py
```

## 1. Install the tools

Install Python 3.10 or newer, MongoDB Community Server, MongoDB Compass, and
[Ollama](https://ollama.com/download). Start MongoDB and Ollama after installing.

In PowerShell, download the default local model:

```powershell
ollama pull llama3.2
```

MongoDB Compass can connect to `mongodb://localhost:27017/`. The program creates
the `llm_monitoring` database and `call_logs` collection on its first saved log.
MongoDB creates databases and collections when the first document is inserted;
no manual creation is needed.

## 2. Open and prepare the project

Open the workspace in VS Code, then open a terminal in this `Week-3` folder.
Create and activate a virtual environment in PowerShell:

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PowerShell activation is blocked by your machine's policy, run the commands
in Command Prompt instead:

```bat
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
```

## 3. Configure Gemini (optional)

The project includes an empty `.env`. Edit it to add your own Gemini API key to
`GEMINI_API_KEY`. If `.env` is missing, copy `.env.example` to `.env` first.
Never share or commit `.env`. Ollama does not need an API key.
You can set `GEMINI_MODEL`, `OLLAMA_MODEL`, or `OLLAMA_URL` in `.env` if you
need to change the defaults. The Gemini model defaults to `gemini-3.8-flash`,
matching the supplied Week 2 client configuration; choose an available model
for your API account if that model is unavailable.

## 4. Run the app

With the virtual environment active, from this folder run:

```powershell
python main.py
```

Choose `1` for Gemini or `2` for Ollama, then enter a question. Ollama uses
`llama3.2` by default. Successful and failed AI calls are logged when MongoDB
is running. If MongoDB is unavailable, the app warns you and still attempts the
AI request. Gemini needs a valid key and internet access; Ollama needs its local
service running and the model downloaded.

## 5. View request logs

In Compass, connect to `mongodb://localhost:27017/`, refresh the connection,
and open `llm_monitoring` → `call_logs`. Each document includes the provider,
model, prompt, token counts, latency, estimated cost, attempt count, status,
error, and UTC timestamp.

Gemini costs use sample USD rates in `cost_calculator.py`; replace them with
verified current pricing before relying on the estimates. If a Gemini model has
no configured rate, its cost is recorded as `null`. Ollama cost is `0.0`.

## 6. Test the project

From this folder, compile the project modules and run the offline tests:

```powershell
python -m compileall -q cost_calculator.py llm_client.py main.py mongo_logger.py
python -m pytest
```

The app itself also checks MongoDB at startup, makes the selected provider call,
and logs the result. You can run it with Ollama without configuring Gemini.

## Common errors

- **`No module named ...`**: activate `.venv` and run
  `python -m pip install -r requirements.txt` from this folder.
- **MongoDB connection refused**: start the MongoDB Server service, then check
  that it listens on `localhost:27017`. The app can still make an AI request,
  but it clearly warns that its log was not saved.
- **Ollama connection refused**: start the Ollama app/service and check
  `http://localhost:11434`. If the model is missing, run
  `ollama pull llama3.2`.
- **Gemini key missing or rejected**: set a valid `GEMINI_API_KEY` in `.env`.
  Ollama remains available without that key.
- **Gemini model unavailable**: set `GEMINI_MODEL` in `.env` to a model enabled
  for your API account.
