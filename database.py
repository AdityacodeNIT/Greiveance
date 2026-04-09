import random
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from faker import Faker

fake = Faker()

# In-memory database for now 

CUSTOMERS_DB: Dict[str, dict] = {}
ORDERS_DB: Dict[str, dict] = {}
COMPLAINTS_DB: Dict[str, dict] = {}
POLICIES_DB: Dict[str, dict] = {
    "P1": {"name": "Return Policy", "description": "Returns are allowed within 30 days of purchase. Items must be in original packaging."},
    "P2": {"name": "Refund Limits", "description": "Automated refunds cannot exceed $500. Anything above $500 must be escalated."},
    "P3": {"name": "Damage Claims", "description": "For damaged goods properly reported within 14 days, a full replacement or refund is granted."},
}

# generating the mock data

def generate_mock_data():
    """Populates the in-memory databases with synthetic data."""
    print("Generating mock data...")

    # Product categories for our furniture retail context
    products = [
        {"name": "Sofa", "price": 450.0},
        {"name": "Dining Table", "price": 600.0},
        {"name": "Bookshelf", "price": 120.0},
        {"name": "Luxury Bed Frame", "price": 850.0},
        {"name": "Office Chair", "price": 250.0},
        {"name": "Lamp", "price": 45.0}
    ]
    
    # Created 10 customers
    for _ in range(10):
        customer_id = f"CUST_{fake.unique.random_number(digits=5)}"
        CUSTOMERS_DB[customer_id] = {
            "customer_id": customer_id,
            "name": fake.name(),
            "email": fake.email(),
            "loyalty_tier": random.choice(["Bronze", "Silver", "Gold"]),
            "order_history": []
        }
        
        # Each customer has 1 to 3 orders
        for _ in range(random.randint(1, 3)):
            order_id = f"ORD_{fake.unique.random_number(digits=6)}"
            purchase_date = fake.date_between(start_date='-60d', end_date='today')
            
            # Select 1 to 4 random items for the order
            items = random.sample(products, k=random.randint(1, min(len(products), 4)))
            total_amount = sum(item["price"] for item in items)
            
            ORDERS_DB[order_id] = {
                "order_id": order_id,
                "customer_id": customer_id,
                "items": items,
                "total_amount": total_amount,
                "purchase_date": purchase_date.isoformat(),
                "delivery_status": random.choice(["Delivered", "In Transit", "Pending"]),
            }
            
            CUSTOMERS_DB[customer_id]["order_history"].append(order_id)
            
    print(f"Generated {len(CUSTOMERS_DB)} customers and {len(ORDERS_DB)} orders.")

# access tools

def get_order_details(order_id: str) -> Optional[dict]:
    """Retrieves order details by order_id."""
    return ORDERS_DB.get(order_id)

#  CUSTOMER DETAIL TOOL

def get_customer_details(customer_id: str) -> Optional[dict]:
    """Retrieves customer profile and order history by order_id."""
    return CUSTOMERS_DB.get(customer_id)

# customer complain tool

def get_customer_complaints(customer_id: str) -> List[dict]:
    """Retrieves all past complaints filed by a specific customer."""
    return [c for c in COMPLAINTS_DB.values() if c["customer_id"] == customer_id]

#policy

def get_policy(policy_category: str) -> str:
    """Returns business policy details. Allowed categories: 'Returns', 'Refunds', 'Damages'"""
    # Simple search mapping
    mapping = {
        "Returns": POLICIES_DB.get("P1"),
        "Refunds": POLICIES_DB.get("P2"),
        "Damages": POLICIES_DB.get("P3")
    }
    policy = mapping.get(policy_category)
    if policy:
        return f"{policy['name']}: {policy['description']}"
    return "Policy not found for this category."

def save_complaint(customer_id: str, order_id: str, issue_text: str, status: str, resolution_notes: str) -> str:
    """Saves a record of the complaint to the database."""
    complaint_id = f"COMP_{fake.unique.random_number(digits=6)}"
    COMPLAINTS_DB[complaint_id] = {
        "complaint_id": complaint_id,
        "customer_id": customer_id,
        "order_id": order_id,
        "issue": issue_text,
        "status": status,
        "resolution_notes": resolution_notes,
        "date_filed": datetime.now().isoformat()
    }
    return complaint_id

# refund tool

def process_refund(order_id: str, amount: float, reason: str) -> dict:
    """Processes a refund for a given order. Returns confirmation or denial."""
    order = ORDERS_DB.get(order_id)
    if not order:
        return {"success": False, "message": f"Order {order_id} not found."}
    
    # Business rule: cannot refund more than the order total
    if amount > order["total_amount"]:
        return {
            "success": False,
            "message": f"Refund amount ${amount} exceeds order total ${order['total_amount']}. Denied."
        }
    
    # Business rule: cannot auto-refund above $500
    if amount > 500:
        return {
            "success": False,
            "message": f"Refund amount ${amount} exceeds $500 auto-refund limit. Requires human approval."
        }
    
    # Simulate successful refund
    refund_id = f"REF_{fake.unique.random_number(digits=6)}"
    return {
        "success": True,
        "refund_id": refund_id,
        "message": f"Refund of ${amount} approved for order {order_id}. Reason: {reason}"
    }

def initiate_replacement(order_id: str, item_name: str, reason: str) -> dict:
    """Initiates a replacement for a specific item in an order."""
    order = ORDERS_DB.get(order_id)
    if not order:
        return {"success": False, "message": f"Order {order_id} not found."}
    
    # Check if the item actually exists in the order
    item_found = any(item["name"].lower() == item_name.lower() for item in order["items"])
    if not item_found:
        return {
            "success": False,
            "message": f"Item '{item_name}' not found in order {order_id}."
        }
    
    replacement_id = f"RPL_{fake.unique.random_number(digits=6)}"
    return {
        "success": True,
        "replacement_id": replacement_id,
        "message": f"Replacement for '{item_name}' initiated for order {order_id}. Reason: {reason}"
    }

generate_mock_data()
