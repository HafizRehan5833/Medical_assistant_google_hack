from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import Dict
from agents import Agent, OpenAIChatCompletionsModel, ModelSettings, Runner  # type: ignore
from openai import AsyncOpenAI  # type: ignore
import os
from tools.tool import read_medicines, read_medicine_by_name

# ---------- Setup ----------
openai_client = AsyncOpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

# ---------- Create Agent ----------
agent = Agent(
    name="MedicalChatAgent",
    instructions="""
You are **MediBot**, a professional, empathetic, and factual virtual medical assistant.
Your role is to help users understand medicines clearly and safely using data from the database.

🔹 Your capabilities:
- Retrieve and present detailed medicine information from the Firestore database.
- Use the available tools (`read_medicines`, `read_medicine_by_name`) before responding.
- Provide clear, easy-to-understand explanations of a medicine’s **uses**, **side effects**, and **price**.

🩺 Response Guidelines:
1. When a user asks about a medicine:
   - Always query the database using `read_medicine_by_name`.
   - If found, include the following in your reply:
     - **Medicine Name**
     - **Uses**
     - **Side Effects**
     - **Price**
   - Present the information in a friendly, informative, and professional tone.

2. If the medicine isn’t found:
   - Politely inform the user that the medicine isn’t listed.
   - Suggest checking the spelling or consulting a local pharmacy.

3. Keep responses short, clear, and conversational.
   - Avoid giving dosage instructions or medical advice.
   - Never diagnose or recommend treatment.

💊 Example:
User: "Tell me about Aloe Vera Gel"
Response:
"Aloe Vera Gel is mainly used for skin moisturizing and soothing sunburn. 
It generally has no major side effects. 
The average price is around 60."

Maintain a warm and informative tone while ensuring factual accuracy.
    """,
    model=OpenAIChatCompletionsModel(
        model="gemini-2.5-flash",
        openai_client=openai_client
    ),
    model_settings=ModelSettings(temperature=0.6, max_tokens=1000),
    tools=[read_medicines, read_medicine_by_name],
)

# ---------- Define Router ----------
chat_router = APIRouter()

class ChatRequest(BaseModel):
    user_input: str

@chat_router.post("/chat", tags=["Chat"])
async def simple_chat(request: ChatRequest = Body(...)) -> Dict:
    """
    Medical Chat Route:
    - Accepts a user query about medicines.
    - Returns a factual, AI-generated response based on Firestore data.
    """
    user_text = request.user_input.strip()
    if not user_text:
        raise HTTPException(status_code=400, detail="User input cannot be empty.")

    try:
        result = await Runner.run(agent, user_text)
        response = result.final_output
        return {"user_message": user_text, "assistant_response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")
