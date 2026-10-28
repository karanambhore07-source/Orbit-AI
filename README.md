# Orbit — Personal AI Assistant

A personal AI assistant built with Python, Flask, PyTorch, and Hugging Face Transformers. Orbit is personalized for **Karan Ambhore** and helps prepare reports, summarize user-provided information, draft writing, and organize plans. In local mode, the **SmolLM2-360M-Instruct** model runs on the CPU and chat stays on the computer. On Vercel, chat uses the hosted AI provider you configure, so prompts are sent to that provider.

The original notebook-based setup remains available. The web app adds a local API and a browser UI with saved conversations, conversation export, starter prompts, and an offline-model status indicator.

## Features

- **Local model inference:** Locally, loads the saved model with `local_files_only=True` after the initial download.
- **CPU execution:** Runs the model on the CPU using PyTorch; no CUDA GPU is required.
- **Personal assistant behavior:** Helps Karan draft reports, summarize notes, prepare writing, and organize ideas and plans.
- **Source-only report mode:** Use `/report` followed by your notes to format a report without asking the language model to invent or expand facts.
- **Grounded responses:** Instructed not to invent facts or personal details and to be clear when information is missing or uncertain.
- **Instruction-following chat model:** Uses `HuggingFaceTB/SmolLM2-360M-Instruct`.
- **Conversation context:** Includes recent user/assistant messages to support follow-up questions.
- **Sampling controls:** Uses `temperature=0.7`, `top_p=0.9`, and `repetition_penalty=1.1` during text generation.
- **Original notebook:** The initial teaching-assistant prototype remains available in `AI_Project.ipynb`.
- **Bounded history:** Retains recent messages to limit how much conversation is passed back to the model.
- **Responsive web chat:** Runs at `http://127.0.0.1:5000` and works on desktop and mobile screens.
- **Browser-saved conversations:** Keeps chat history in the current browser using local storage; export a chat as a text file.
- **Model status:** Shows whether the local model has been downloaded and gives setup guidance if it is missing.

## How it works

1. **Install dependencies** — install PyTorch's CPU build and Hugging Face Transformers.
2. **Download the model** — download the tokenizer and model weights from Hugging Face, then save them into `smollm2_model/`.
3. **Load locally** — reload the tokenizer and model from the local folder with network access disabled for this loading step.
4. **Prepare messages** — combine the system prompt, recent conversation history, and the latest user question.
5. **Format the prompt** — use the tokenizer's chat template to create model input.
6. **Generate a response** — call `model.generate()` under `torch.inference_mode()`.
7. **Decode the output** — return only newly generated tokens, rather than repeating the input prompt.
8. **Continue chatting** — store the latest user/assistant messages and allow the user to reset or exit.

## Technology stack

| Technology | Purpose |
|---|---|
| Python and Flask | Local web app and API |
| PyTorch (`torch`) | Loads and runs the language model |
| Hugging Face Transformers | Tokenizer, pretrained model, chat template, and text generation |
| SmolLM2-360M-Instruct | Local instruction-tuned language model |
| HTML, CSS, and JavaScript | Responsive browser interface |
| Jupyter Notebook | Original development and terminal workflow |

## Project structure

```text
AI-chatbot/
├── AI_Project.ipynb       # Original notebook and terminal chat loop
├── app.py                 # Flask web app and chat API
├── chatbot.py             # Shared local-model loading and text generation
├── download_model.py      # One-time model download for the web app
├── requirements.txt
├── static/                # Browser styles and chat behavior
├── templates/index.html   # Web chat page
├── test_app.py            # Web API tests
└── smollm2_model/         # Downloaded model/tokenizer files (not committed)
```

The exact files inside `smollm2_model/` can vary by model and library version. Model files are excluded from Git by `.gitignore`.

## Requirements

- Python 3.10 or a compatible Python version supported by the installed PyTorch and Transformers releases
- `pip`
- Flask
- Jupyter Notebook or JupyterLab (for the original notebook workflow)
- Internet access for the **initial model download**
- Sufficient RAM and disk space for the model and Python libraries

The notebook explicitly installs the CPU version of PyTorch. CPU inference is convenient for a simple local setup, but response speed depends on your computer and the length of the prompt and answer.

## Setup and installation

### 1. Clone or download the project

If you have uploaded the notebook to your own GitHub repository, clone it:

```bash
git clone <YOUR_REPOSITORY_URL>
cd <YOUR_PROJECT_FOLDER>
```

Or open `AI_Project.ipynb` directly in Jupyter.

### 2. Install dependencies

For the web app, install PyTorch's CPU build and the remaining project packages:

```powershell
python -m pip install --upgrade pip
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements-local.txt
```

For Vercel, `requirements.txt` contains only the lightweight Flask runtime. The local model dependencies are kept in `requirements-local.txt` so the Vercel function does not package PyTorch, Transformers, or the model weights.

### 3. Download the model

From the project directory, run:

```powershell
python download_model.py
```

This first download requires internet access and saves the model and tokenizer into `smollm2_model/`. The web app uses these local files for inference.

### 4. Start the web app

```powershell
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser. The model is loaded locally when you send the first message; generation runs on CPU.

To format a report using only your supplied facts, select **Write a report**, enter `/report` followed by your title and notes, and send it. This report mode formats your notes without using the language model; review the result before sharing.

## Deploy to Vercel

The local SmolLM2 workflow stays local. On Vercel, general chat uses an OpenAI-compatible hosted inference endpoint; chat prompts are sent to that provider. Hugging Face Inference Providers does not currently list this project's exact SmolLM2-360M model for serverless inference, so select a model that your chosen provider supports, or deploy SmolLM2 as a separate dedicated endpoint.

1. Import the GitHub repository into Vercel, or deploy this folder with the Vercel CLI.
2. In **Project Settings → Environment Variables**, set the following for Production (and Preview if desired):

   | Variable | Value |
   |---|---|
   | `AI_API_KEY` | Secret key from your hosted AI provider |
   | `AI_BASE_URL` | Provider's OpenAI-compatible API base URL, such as `https://openrouter.ai/api/v1` |
   | `AI_MODEL` | A chat-completion model ID enabled for your provider account |

3. Redeploy after setting the variables.

Vercel serves the UI assets from `public/static/`, routes the Flask app through a Python Function, and excludes the local model and PyTorch dependencies from the deployment bundle. Without provider variables, the site and source-only `/report` formatter work, but hosted AI chat returns a configuration message.

To try the hosted endpoint locally, set the same variables in your shell or a private `.env` file (never commit API keys), install a compatible environment, and run `python app.py`. Local inference uses SmolLM2 when its files exist; otherwise, the configured hosted provider is used.

### 5. Use the original notebook (optional)

Open `AI_Project.ipynb` and run its cells in order to use the original terminal chat workflow.

Example interaction:

```text
==================================================
       OFFLINE GENAI CHATBOT
==================================================
Ask any question.
Type /reset to clear history.
Type /exit to stop.
==================================================

You: Explain Generative AI in simple terms.
Bot: ...
```

The model's exact response will vary from run to run.

## Using the chatbot

| Input | Result |
|---|---|
| Ask a question | Generates a response |
| Ask a follow-up question | Uses recent conversation history when available |
| `/reset` | Clears conversation history for the current session |
| `/exit` | Ends the chat loop |

The notebook includes a `generate_response(user_message, history=None)` function that can also be called from other Python code after the model and tokenizer have been loaded.

## Configuration

The notebook currently defines these generation settings:

| Setting | Current value | Purpose |
|---|---:|---|
| `MAX_NEW_TOKENS` | `120` | Maximum number of new tokens generated per answer |
| `MAX_HISTORY_MESSAGES` | `6` | Number of recent history entries selected by `generate_response()` |
| `temperature` | `0.7` | Controls randomness when sampling is enabled |
| `top_p` | `0.9` | Nucleus-sampling threshold |
| `repetition_penalty` | `1.1` | Discourages repetitive text |
| Device | CPU | Runs inference without requiring CUDA |

**History note:** The terminal loop stores up to 12 message entries. Both the notebook and web app pass at most six recent entries to the model; these are individual user or assistant messages, not six complete question-and-answer pairs. The web interface saves conversations in the current browser's local storage.

## Limitations

- **Model quality:** SmolLM2-360M-Instruct is a compact model. It can produce incorrect, incomplete, or inconsistent answers and may struggle with complex reasoning.
- **No live web access:** After downloading the model, the chatbot generates answers from the model's learned parameters and provided conversation; it does not search the internet.
- **No connected personal accounts or tools:** Orbit can help with information you share in chat, but it does not access your files, email, calendar, or accounts, and cannot perform actions outside the chat.
- **Browser-local history:** Web chat history is stored in this browser only; the notebook chat history exists only while its terminal loop is running.
- **Initial internet required:** The first model download requires a connection. The inference-loading cell uses local files, but this does not by itself guarantee that every dependency or notebook operation is fully offline.
- **CPU performance:** Generation may be slower on lower-powered computers.
- **Local web server:** The development server is intended for use on the same computer, not as a public or production deployment.
- **No formal evaluation yet:** The notebook does not include a benchmark, automated tests, or a systematic quality evaluation.
- **No safety or factuality guarantee:** Generated answers should be checked, especially for important decisions.

## Troubleshooting

### Model files not found

For the web app, run `python download_model.py` from the project directory and confirm that `smollm2_model/` contains the model files. For the notebook workflow, run its download-and-save cell first.

### Hugging Face model download fails

Check your internet connection, retry the download, and confirm that the model repository is accessible. Ensure you have enough free disk space.

### Package or version conflicts

Use a dedicated virtual environment and install compatible versions of PyTorch and Transformers. Restart the notebook kernel after changing core dependencies.

### Slow responses

The project runs on CPU and generates up to 120 new tokens per response. Reduce `MAX_NEW_TOKENS` for shorter responses, or consider suitable hardware and model optimizations if needed.

### Chat history seems short

The function passes at most six recent history entries to the model, while the terminal loop stores at most twelve entries. Older context is intentionally discarded.

## Future improvements

- Add configurable system prompts and generation parameters.
- Expand automated tests to cover message formatting and model generation behavior.
- Evaluate response quality on a small set of documented questions.
- Explore quantization or other CPU optimizations after measuring memory use and response speed.

## Responsible use and privacy

In local mode, chat runs on your computer after the model has been downloaded. In Vercel mode, chat prompts are sent to the hosted AI provider configured for the deployment; review that provider's data-retention and privacy terms before use. Orbit only knows information provided in the current conversation and cannot access personal files or accounts. The initial local model download contacts Hugging Face, and this project does not implement a privacy audit or guarantee that other software on the computer cannot access local data. Avoid entering passwords, confidential information, or sensitive personal data.

## Author

**Karan Ambhore**

## License

No project license is specified in the notebook. Add a `LICENSE` file before publicly distributing the project, and review the model's license and usage terms on its Hugging Face model page before redistributing model files.

## Acknowledgements

- [Hugging Face Transformers](https://huggingface.co/docs/transformers/index)
- [SmolLM2-360M-Instruct model page](https://huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct)
- [PyTorch](https://pytorch.org/)
#   O r b i t - A I  
 