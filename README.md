# AI Grievance Agent

This project is a customer grievance handling system built with FastAPI and Google Gemini.

The goal is simple: take a customer complaint, verify it against internal data, and decide whether to resolve it automatically or escalate it to a human. The key idea is that the system does **not** blindly trust user input—it checks everything before acting.

---

## What it does

### 1. Verifies complaints using internal tools

Our aagent uses Gemini function calling to access three backend functions:

- `get_order_details`  
- `get_customer_details`  
- `get_policy`  
- `process_refund`
- `initiate_replacement`

LLM is designed in a way that it dont blindly trust what the customer says, system validates it.

**For Example:**  
If a user claims they spent $5,000 and received a broken item, our llm agent looks up the actual order using `order_id` and checks:
- order amount  
- delivery status  
- purchase date  

All decisions are based on this data, not just the complaint text.

---

### 2. Generates both customer reply and internal note

For every complaint, the system produces two outputs:

- A response that goes to the customer  
- An internal note for the support team  

The internal note explains what happened and what action is recommended. This keeps things clear for whoever handles the ticket next.

---

### 3. Uses strict rules before final decision

The LLM suggests what to do, but it does **not** have the final say.

A rule-based layer sits on top and can override the model. Some key rules:

- **Angry users → always escalate**  
- **Orders above $500 → escalate**  
- **VIP customers → prioritize and escalate when needed**  
- **Repeat complaints → escalate for manual review**  
- **Missing details → ask for clarification instead of guessing**
- **If the user is reporting physical damage, always ask them to share photos of the damaged item for verification before processing a replacement or refund.**
- **If the user is reporting a refund, always ask them for the reason for the refund.**
- **If the user is reporting a replacement, always ask them for the reason for the replacement.**


This prevents bad automated decisions.

---

## Why this design?

- **Order Tool**: *Grounding the LLM in Reality.* We cannot trust the user's assertion of their order state. An LLM might logically deduce a refund is warranted based on a text prompt, but the database might show the item hasn't even shipped yet. Reaching into the DB guarantees decisions are based on truth.
- **Customer Tool**: *Predictive Issue Prevention.* Knowing a customer's lifetime value/loyalty tier allows us to bypass the standard queue for VIPs. Furthermore, a repeat complainer requires human scrutiny to prevent abuse.
- **Policy Tool**: *Decoupled Business Logic.* Hardcoding "returns are within 30 days" directly into the System Prompt makes the agent fragile and forces engineering redeploys every time a business policy shifts. Providing a tool lets the underlying DB update dynamically while the LLM remains stateless.

**"Why use action tools (process_refund, initiate_replacement) if a human still needs to approve them?"**

- **Decoupled Execution Pattern (Decision-Routing)**: The LLM acts as the triage and routing layer, not the final authority. By instructing it to use action tools to generate a *Pending Action Request* (which is intercepted by our local logic), we prevent the AI from blindly taking financial actions. 

- **Human-in-the-Loop (HITL) for Physical Goods**: For scenarios demanding evidence (like a broken chair leg), the AI can draft the email asking for photos and "initiate" the replacement in the database. But the actual shipping of a $5,000 couch stops at a HITL validation gate where a human agent quickly verifies the uploaded photos before final approval. This limits automated risk while retaining 95% of the efficiency.

---

## Issue discovered during testing

One thing i found while testing:

The model tries too hard to please angry users.

If a user aggressively claims something false (for example, inventing a policy), the model may skip verification and agree just to de-escalate the situation.

This is risky.

To fix this, i added a rule-based validation layer.This layer detects aggressive tone and forces escalation instead of allowing the model to auto-resolve incorrectly.

---


# Setup

Kindly clone this repo and  install the requirement.txt and set your **gemini api key** by making a .env file it can only take gemini api keys currently i have not implemented mechanism for the any other api key.
**GEMINI_API_KEY="your-api-key"**


## Summary

- Doesn't solely rely on the  user input 
- Verifies everything using internal tools  
- Uses LLM for reasoning, it does not have any authority
- Applies strict rules before taking action  
- Falls back to humans for risky cases  

- ThankYou for reading this.