import os
import json
import re
from dotenv import load_dotenv
from google import genai
from google.genai import types
from typing import Dict, Any

# Load custom DB logic
import database

load_dotenv()

# INIT

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("Missing GEMINI_API_KEY")

client = genai.Client(api_key=api_key)


#  TOOL DEFINITIONS 
# Tool schemas are defined in tools.py for modularity.
# When Gemini decides to call one, WE execute the matching Python function locally.

from tools import order_tool, customer_tool, policy_tool, refund_tool, replacement_tool

# Bundle all tool declarations into a single Tool object

grievance_tools = types.Tool(function_declarations=[
    order_tool, customer_tool, policy_tool, refund_tool, replacement_tool
])

# Map tool names to actual local Python functions

TOOL_DISPATCH = {
    "get_order_details": lambda args: database.get_order_details(args["order_id"]),
    "get_customer_details": lambda args: database.get_customer_details(args["customer_id"]),
    "get_policy": lambda args: database.get_policy(args["policy_category"]),
    "process_refund": lambda args: database.process_refund(args["order_id"], args["amount"], args["reason"]),
    "initiate_replacement": lambda args: database.initiate_replacement(args["order_id"], args["item_name"], args["reason"]),
}


# -------------------- SYSTEM PROMPT --------------------

SYSTEM_INSTRUCTION = """
You are an intelligent customer grievance agent for a furniture retail company. 
Your job is to handle customer complaints end-to-end. You must determine what happened, decide on an appropriate resolution, draft a response to the customer, and either close the ticket or escalate it with a clear recommendation for the human who picks it up.

You MUST use your tools to gather facts first (e.g., look up the order_id, check the customer's loyalty tier, verify policy constraints). Do NOT trust user claims blindly. ALWAYS call the tools before making any judgment.

When generating your FINAL output (after all tool calls), you MUST format it strictly with the following tagged boundaries:

[INTENT]: RESOLUTION_POSSIBLE or ESCALATION_REQUIRED or CLARIFICATION_NEEDED
[TONE]: ANGRY or NEUTRAL or CALM
[MISSING_INFO]: TRUE or FALSE
[CUSTOMER_RESPONSE]: <Draft your exact email/chat response to the customer here. If the customer reports physical damage, always ask them to share photos of the damaged item for verification before processing a replacement or refund.>
[HUMAN_RECOMMENDATION]: <If escalating or requiring info, draft a brief note for the human agent. If resolving, write "N/A">
"""


# -------------------- RESPONSE PARSER --------------------

def parse_llm_response(text: str) -> dict:
    parsed = {
        "intent": "CLARIFICATION_NEEDED",
        "tone": "NEUTRAL",
        "missing_info": "TRUE",
        "customer_response": "We are reviewing your case.",
        "human_recommendation": "Manual review required."
    }

    intent_match = re.search(r'\[INTENT\]:\s*(.*)', text)
    if intent_match: parsed["intent"] = intent_match.group(1).strip()

    tone_match = re.search(r'\[TONE\]:\s*(.*)', text)
    if tone_match: parsed["tone"] = tone_match.group(1).strip().upper()

    missing_match = re.search(r'\[MISSING_INFO\]:\s*(.*)', text)
    if missing_match: parsed["missing_info"] = missing_match.group(1).strip().upper()

    cust_match = re.search(r'\[CUSTOMER_RESPONSE\]:\s*(.*?)(?=\n\[|$)', text, re.DOTALL)
    if cust_match: parsed["customer_response"] = cust_match.group(1).strip()

    hum_match = re.search(r'\[HUMAN_RECOMMENDATION\]:\s*(.*?)(?=\n\[|$)', text, re.DOTALL)
    if hum_match: parsed["human_recommendation"] = hum_match.group(1).strip()

    return parsed


# -------------------- MAIN FUNCTION --------------------

def analyze_and_decide(
    complaint_text: str,
    order_id: str = None,
    customer_id: str = None
) -> Dict[str, Any]:

    # -------- Prompt Construction --------

    user_prompt = f"Complaint Text: {complaint_text}\n"
    if order_id:
        user_prompt += f"Order ID: {order_id}\n"
    if customer_id:
        user_prompt += f"Customer ID: {customer_id}\n"
    user_prompt += "\nAnalyze this complaint. Use your tools to look up data first, then give your final tagged assessment."

    # -------- LLM CALL WITH FUNCTION CALLING LOOP --------

    try:
        # Build initial contents
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=user_prompt)])]

        # Track which tools were invoked for transparency

        tools_invoked = []

        # Function calling loop: keep going until Gemini gives a text response (no more tool calls)
        
        MAX_TURNS = 10
        for turn in range(MAX_TURNS):
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    tools=[grievance_tools],
                    temperature=0
                )
            )

            # Check if the model wants to call a function

            candidate = response.candidates[0]
            has_function_call = False

            function_response_parts = []
            for part in candidate.content.parts:
                if part.function_call:
                    has_function_call = True
                    fn_name = part.function_call.name
                    fn_args = dict(part.function_call.args) if part.function_call.args else {}

                    print(f"  [Tool Call] {fn_name}({fn_args})")
                    tools_invoked.append({"tool": fn_name, "args": fn_args})

                    # Execute our LOCAL Python function

                    if fn_name in TOOL_DISPATCH:
                        result = TOOL_DISPATCH[fn_name](fn_args)
                        result_str = json.dumps(result) if isinstance(result, (dict, list)) else str(result)
                    else:
                        result_str = json.dumps({"error": f"Unknown tool: {fn_name}"})

                    # Build function response part
                    
                    function_response_parts.append(
                        types.Part.from_function_response(
                            name=fn_name,
                            response={"result": result_str}
                        )
                    )

            if has_function_call:
                # Append the model's function call to conversation history
                contents.append(candidate.content)
                # Append our function results back to the conversation
                contents.append(types.Content(role="user", parts=function_response_parts))
            else:
                # No more tool calls — model gave its final text answer
                break

        llm_response_text = response.text

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "message": f"LLM Error: {str(e)}"
        }

    # -------- PARSE STRUCTURED OUTPUT --------
    parsed = parse_llm_response(llm_response_text)
    original_intent = parsed["intent"]
    intent = original_intent
    tone = parsed["tone"]
    missing_info = parsed["missing_info"]
    customer_response = parsed["customer_response"]
    human_recommendation = parsed["human_recommendation"]

    final_action = "PENDING"
    override_reasons = []



    # if order id is not there
    if not order_id:
        intent = "CLARIFICATION_NEEDED"
        override_reasons.append("Missing order_id. Cannot proceed without verifying the order.")

    # if complaint details are not there
    if missing_info == "TRUE":
        intent = "CLARIFICATION_NEEDED"
        override_reasons.append("Insufficient complaint details provided by the customer.")

    # 2. Tone override — angry customers always escalate
    if intent != "CLARIFICATION_NEEDED" and tone == "ANGRY":
        intent = "ESCALATION_REQUIRED"
        override_reasons.append("Customer tone detected as ANGRY — requires human empathy.")

    # 3. Repeated complaints — chronic complainers get escalated
    if customer_id:
        past_complaints = database.get_customer_complaints(customer_id)
        if len(past_complaints) > 0:
            intent = "ESCALATION_REQUIRED"
            override_reasons.append(f"Repeat complainer with {len(past_complaints)} prior issue(s) on file.")

        # 4. VIP override — Gold tier gets priority routing
        cust = database.get_customer_details(customer_id)
        if cust and cust.get("loyalty_tier") == "Gold":
            intent = "ESCALATION_REQUIRED"
            override_reasons.append("Gold-tier VIP customer — priority routing required.")

    # 5. Financial limit override — orders above $500 cannot be auto-resolved
    if intent == "RESOLUTION_POSSIBLE" and order_id:
        order = database.get_order_details(order_id)
        if order and order.get("total_amount", 0) > 500:
            intent = "ESCALATION_REQUIRED"
            override_reasons.append(f"Order value ${order.get('total_amount')} exceeds $500 auto-resolution limit.")

    # If rules overrode the LLM, build a clear human-facing note
    if intent != original_intent and override_reasons:
        human_recommendation = (
            f"[SYSTEM OVERRIDE] LLM originally assessed this as '{original_intent}', "
            f"but local business rules forced '{intent}'. "
            f"Reasons: {'; '.join(override_reasons)}"
        )
    elif override_reasons:
        # LLM agreed on escalation, but we have additional system notes
        human_recommendation += f" | Additional flags: {'; '.join(override_reasons)}"

    # -------- MAP INTENT TO FINAL ACTION --------
    if intent == "ESCALATION_REQUIRED":
        final_action = "ESCALATE"
        resolution_notes = "Escalated to human support. Agent Note: " + human_recommendation
    elif intent == "CLARIFICATION_NEEDED":
        final_action = "REQUIRE_INFO"
        resolution_notes = "Needs more information. Agent Note: " + human_recommendation
    else:
        final_action = "RESOLVE"
        resolution_notes = "Automated resolution granted."

    # -------- SAVE TO DB --------
    complaint_id = database.save_complaint(
        customer_id=customer_id or "UNKNOWN",
        order_id=order_id or "UNKNOWN",
        issue_text=complaint_text,
        status=final_action,
        resolution_notes=resolution_notes
    )

    return {
        "complaint_id": complaint_id,
        "llm_intent_classification": intent,
        "final_action": final_action,
        "tools_invoked": tools_invoked,
        "drafted_customer_response": customer_response,
        "recommendation_for_human": human_recommendation,
        "llm_raw_response": llm_response_text
    }

# GENERAL CHAT FUNCTION 

def general_chat(prompt: str) -> str:
    """Handles general human prompts (like policy questions) without logging a formal complaint."""
    try:
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]
        
        # Simple execution loop so Gemini can still use tools if asked
        for _ in range(5):
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction="""You are a strictly grounded customer support agent. 
If the user asks a question about company rules, operations, or policies, you MUST use the get_policy tool to look it up.
If the tool returns 'Policy not found', or if you cannot find the answer using a tool, you MUST politely tell the customer that we do not have a policy for that or you do not know.
NEVER guess, invent, or hallucinate policies or facts.
Do NOT use any tags like [INTENT]. Just reply naturally to the human.""",
                    tools=[grievance_tools],
                    temperature=0
                )
            )
            candidate = response.candidates[0]
            
            has_function_call = False
            function_response_parts = []
            
            if candidate.content.parts:
                for part in candidate.content.parts:
                    if part.function_call:
                        has_function_call = True
                        fn_name = part.function_call.name
                        fn_args = dict(part.function_call.args) if part.function_call.args else {}
                        
                        if fn_name in TOOL_DISPATCH:
                            result = TOOL_DISPATCH[fn_name](fn_args)
                            result_str = json.dumps(result) if isinstance(result, (dict, list)) else str(result)
                        else:
                            result_str = f"Error: Unknown tool {fn_name}"
                            
                        function_response_parts.append(
                            types.Part.from_function_response(name=fn_name, response={"result": result_str})
                        )
            
            if has_function_call:
                contents.append(candidate.content)
                contents.append(types.Content(role="user", parts=function_response_parts))
            else:
                break
                
        return response.text
    except Exception as e:
        return f"Sorry, I encountered an error: {str(e)}"