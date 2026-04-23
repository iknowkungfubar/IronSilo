# 🚀 Universal Local AI Workspace

A completely local, cross-platform (Windows, macOS, Linux) AI development sandbox optimized for low-to-mid spec machines. 

This stack runs a memory layer, a wiki RAG engine, and a token-compression proxy in an isolated Docker network. It is strictly capped to ~4GB of RAM to leave plenty of room for your host-level LLM and VS Code.

## 🛠 Prerequisites
1. **Docker Desktop** (Make sure it is open and running!)
2. **Local AI Host**: You must have LM Studio, Ollama, or Lemonade running locally, hosting a model, and serving an API on port `8000`.
3. **VS Code** you can also use VSCodium or Code-OSS

## 🟢 How to Use
1. **Double-click** `Start_Workspace` (use the `.bat` for Windows or `.command` for Mac).
2. Open this folder in **VS Code**. 
3. Click "Install Recommended Extensions" when prompted.
   *(VS Code will automatically wire your extensions directly to the running Sandbox).*
4. Start chatting with Aider and Khoj!

## 🔴 Shutting Down
When you are done, **double-click** `Stop_Workspace`. This safely turns off the background containers and instantly frees up your computer's RAM. Your data is safely saved for next time.
