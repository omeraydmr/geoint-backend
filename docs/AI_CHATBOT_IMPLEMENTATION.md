I have implemented the **Real AI Chatbot** integration.

**Changes:**

1.  **Backend:**
    *   Created `ChatbotService` (`backend/app/services/ai/chatbot.py`) to manage conversations with OpenAI/Claude. It includes a specialized system prompt for the STRATYON platform context.
    *   Added `/api/v1/ai/chat` endpoint (`backend/app/api/v1/endpoints/ai.py`) to handle chat requests.

2.  **Frontend:**
    *   Updated `ChatbotContext.tsx` to remove mock responses and instead call the real backend API.

**How to test:**
1.  Ensure your `backend/.env` file has a valid `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`.
2.  Restart the backend server if needed.
3.  Open the "AI Assistant" sidebar in the frontend.
4.  Send a message (e.g., "GEOINT nedir?" or "Bana bir pazarlama stratejisi öner").
5.  The chatbot should now respond with generated content from the LLM.