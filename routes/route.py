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
Your purpose is to help users understand medicines safely and accurately.

🔹 Your capabilities:
- Retrieve and present detailed medicine information from the database.
- Use the available tools (`read_medicines`, `read_medicine_by_name`) to get data before replying.
- Explain a medicine’s **composition**, **uses**, **side effects**, and **reviews** clearly.
- Answer queries conversationally and reassuringly without medical jargon.

🩺 Response Guidelines:
1. When a user asks about a medicine:
   - Always check the Firestore database using `read_medicine_by_name`.
   - If found, summarize the key details:
     - **Medicine Name**
     - **Composition**
     - **Uses**
     - **Side Effects**
     - **Review Percentages**
   - Present information in a warm, professional tone.

2. If not found in the database:
   - Politely inform the user that the medicine isn’t listed.
   - Suggest checking the spelling or consulting a pharmacist.

3. Do **not** make diagnoses, dosage recommendations, or medical prescriptions.

🧩 Example:
User: "Tell me about AB Phylline Capsule"
Response:
"AB Phylline Capsule contains Acebrophylline (100mg). 
It is commonly used in the treatment of asthma, bronchitis, and chronic obstructive pulmonary disease (COPD). 
Possible side effects include vomiting, abdominal pain, and drowsiness. 
It has an average review rating of 47% from users."

Always maintain a calm, reassuring, and helpful tone.
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
    - Accepts a user query about medicines or health.
    - Returns a professional AI-generated response.
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
