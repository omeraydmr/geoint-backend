I have successfully migrated all AI services from OpenAI to **Claude (Anthropic)**.

**Changes:**

1.  **AI Chatbot (`backend/app/services/ai/chatbot.py`):**
    *   Removed OpenAI integration.
    *   The chatbot now exclusively uses the Anthropic API for generating responses.

2.  **Strategy Generator (`backend/app/services/strategy/generator.py`):**
    *   Removed OpenAI integration.
    *   Strategy generation logic now defaults to Claude if the API key is present, falling back to a template otherwise.

**Action Required:**
*   Ensure that `ANTHROPIC_API_KEY` is correctly defined in your `backend/.env` file.
*   You can remove `OPENAI_API_KEY` from your configuration if you wish.

The platform is now fully powered by Claude.