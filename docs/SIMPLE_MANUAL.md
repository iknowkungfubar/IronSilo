# Simple User Manual: IronSilo

## Welcome to Your AI Team
This setup is designed to run on almost any computer (Windows, macOS, or Linux). It keeps your memory databases and research agents in a lightweight background "Sandbox", leaving your main computer free to run your AI models (like Qwen) and your daily applications.

## Step 0: The First-Time Setup
If you have a brand-new computer, you must install four standard tools before starting:
1. **Git:** Download and install from [git-scm.com](https://git-scm.com/).
2. **Python:** Required for standard CLI tools (`pip install aider-chat`).
3. **Docker Desktop:** Download from [docker.com](https://www.docker.com/products/docker-desktop/). Open it and make sure it is running in your taskbar.
4. **LM Studio:** Download from [lmstudio.ai](https://lmstudio.ai/). This is the easiest tool for downloading and running AI models locally.

## Step 1: Start Your Host AI
Open LM Studio (or Ollama/Lemonade) on your computer and start your model. **Nothing else works unless your local AI is running.**

* **LM Studio Users:** Go to the "Local Server" tab on the left. Change the port on the right side of the screen from `1234` to `8000`. Click the green "Start" button.
* **Ollama Users:** Create a file named `.env` in the root folder of this workspace (next to `docker-compose.yml`) and add this exact line: `LLM_ENDPOINT="http://host.docker.internal:11434/v1/chat/completions"`

## Step 2: Start the Background Sandbox
* **Windows:** Double-click `Start_Workspace.bat` in the project folder.
* **Mac / Linux:** Open your terminal, navigate to the folder, and run `./Start_Workspace.sh`
*(Note: The very first time you do this, it will take a few minutes to download the files).*

## Step 3: Connect Your Tools
Your tools are now natively waiting for you:
* **To Code (Aider):** Aider runs natively in your terminal. Open your terminal in your project directory and run:
  ```bash
  export OPENAI_API_BASE="[http://127.0.0.1:8001/api/v1](http://127.0.0.1:8001/api/v1)"
  export OPENAI_API_KEY="local-sandbox"
  aider
  ```
* **To Research (Khoj):** Open your web browser and go to `http://127.0.0.1:42110`. You can upload PDFs and chat with your private documents here.
* **To Automate (IronClaw):** Open your web browser and go to `http://127.0.0.1:8080`.

## Step 4: Shutting Down
When you are done for the day:
* **Windows:** Double-click `Stop_Workspace.bat`
* **Mac / Linux:** Run `./Stop_Workspace.sh`

Your computer instantly gets its RAM back, and your files wait safely for next time.

## Common Troubleshooting
* **Aider says "Not a Git Repository":** Aider requires version control to keep your code safe. Open a terminal in your project folder and type `git init` before asking Aider to code.
* **The "First Prompt" Delay:** The very first time you ask Aider a question, it might freeze for 60 seconds. *Do not panic.* The system is downloading a compression file in the background. Wait a minute, try again, and it will be lightning-fast.
* **"Model Not Found":** Make sure the model name you type in Aider *exactly* matches the name displayed in LM Studio/Lemonade (including capitalization and dashes).