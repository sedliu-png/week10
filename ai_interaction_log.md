# AI Interaction Log

## Task 1A: Page Setup & API Connection
- Prompt: Implement Part A with `st.set_page_config`, token from `st.secrets`, test message to HF API, and graceful errors.
- AI help: Added page config, token check with user-visible error, HF router request, and error handling for HTTP/network issues.
- Result: App shows model reply for a test prompt when token exists; shows error otherwise.

## Task 1B: Multi-Turn Conversation UI
- Prompt: Replace hardcoded message with chat UI and session history.
- AI help: Added `st.chat_message`, `st.chat_input`, and `st.session_state` history; full history sent with each request.
- Result: Multi-turn chat works with context and fixed input bar.

## Task 1C: Chat Management
- Prompt: Add sidebar chat list, new chat, switching, highlight active, delete.
- AI help: Implemented sidebar UI, new chat creation, active indicator, switching, and delete handling.
- Result: Multiple chats can be created, switched, and deleted independently.

## Task 1D: Chat Persistence
- Prompt: Persist each chat in `chats/` and load on startup.
- AI help: Added JSON save/load per chat, delete removes file, startup loads all chats.
- Result: Chats persist across app restarts.

## Task 2: Response Streaming
- Prompt: Stream model replies token-by-token.
- AI help: Enabled SSE streaming from HF router, incremental UI updates, small delay for visibility, save full reply at end.
- Result: Replies render progressively and are stored in history.

## Task 3: User Memory
- Prompt: Extract user traits to `memory.json` and personalize responses.
- AI help: Added memory load/save/merge, extraction API call after responses, sidebar display and clear control, memory injected into system prompt.
- Result: Memory persists and personalizes future replies.

## Git/GitHub Setup
- Prompt: Initialize git, add .gitignore for secrets, create commits.
- AI help: Initialized repo, committed initial setup, added `.gitignore` for `.venv/` and `.streamlit/secrets.toml`, removed secrets from tracking.
- Result: Repo ready for public GitHub without exposing secrets.
