from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

# importing the custom modules here 
import database
import agent

# app opening

app = FastAPI(title="AI Grievance Resolution Agent", version="1.0")

# complaint request

class ComplaintRequest(BaseModel):
    complaint_text: str
    order_id: Optional[str] = None
    customer_id: Optional[str] = None

class ChatRequest(BaseModel):
    Question: str


# the api for complaints

@app.post("/api/complaints")
async def submit_complaint(request: ComplaintRequest):
    """
    Submits a customer complaint to the AI Agent for analysis and decision routing.
    """
    if not request.complaint_text:
        raise HTTPException(status_code=400, detail="Complaint text is required.")
        
    result = agent.analyze_and_decide(
        complaint_text=request.complaint_text,
        order_id=request.order_id,
        customer_id=request.customer_id
    )
    
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("message"))
        
    return result



@app.post("/api/policies")
async def getPolicies(request: ChatRequest):
    """
    A lightweight chat route for general human prompts (e.g., asking about policies).
    This does NOT log a formal complaint in the database.
    """
    if not request.Question:
        raise HTTPException(status_code=400, detail="Prompt is required.")
        
    reply = agent.general_chat(request.Question)
    return {"reply": reply}

# for the data orders

@app.get("/api/data/orders")
async def get_all_orders():
    """Returns all mock orders in the system."""
    return {"orders": list(database.ORDERS_DB.values())}

# for the data customers

@app.get("/api/data/customers")
async def get_all_customers():
    """Returns all mock customers in the system."""
    return {"customers": list(database.CUSTOMERS_DB.values())}

# for the data complaints

@app.get("/api/data/complaints")
async def get_all_complaints():
    """Returns all recorded complaints and their states."""
    return {"complaints": list(database.COMPLAINTS_DB.values())}

@app.get("/api/complaints/{complaint_id}")
async def get_complaint(complaint_id: str):
    """Retrieves a specific complaint by its ID."""
    complaint = database.COMPLAINTS_DB.get(complaint_id)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return complaint

# root

@app.get("/")
async def root():
    return {"message": "Welcome to the AI Grievance Agent API. Go to /docs for the Swagger UI."}
