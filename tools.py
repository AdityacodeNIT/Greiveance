from google.genai import types


# ORDER TOOL 

order_tool = types.FunctionDeclaration(
    name="get_order_details",
    description="Retrieves order details including items, total_amount, purchase_date, and delivery_status for a given order_id.",
    parameters=types.Schema(
        type="OBJECT",
        properties={
            "order_id": types.Schema(type="STRING", description="The order ID to look up, e.g. 'ORD_123456'.")
        },
        required=["order_id"]
    )
)

# CUSTOMER TOOL 

customer_tool = types.FunctionDeclaration(
    name="get_customer_details",
    description="Retrieves customer profile including name, email, loyalty_tier, and order_history for a given customer_id.",
    parameters=types.Schema(
        type="OBJECT",
        properties={
            "customer_id": types.Schema(type="STRING", description="The customer ID, e.g. 'CUST_12345'.")
        },
        required=["customer_id"]
    )
)

# POLICY TOOL 

policy_tool = types.FunctionDeclaration(
    name="get_policy",
    description="Retrieves business policy details. Use this to check return windows, refund limits, and damage claim rules.",
    parameters=types.Schema(
        type="OBJECT",
        properties={
            "policy_category": types.Schema(type="STRING", description="One of: 'Returns', 'Refunds', 'Damages'.")
        },
        required=["policy_category"]
    )
)

# REFUND ACTION TOOL

refund_tool = types.FunctionDeclaration(
    name="process_refund",
    description="Initiates a refund for a specific order. Call this tool INSTEAD of just saying you are refunding. You must call this to actually process a refund.",
    parameters=types.Schema(
        type="OBJECT",
        properties={
            "order_id": types.Schema(type="STRING", description="The order ID to refund."),
            "amount": types.Schema(type="NUMBER", description="The refund amount in dollars."),
            "reason": types.Schema(type="STRING", description="Brief reason for the refund.")
        },
        required=["order_id", "amount", "reason"]
    )
)

# replacement tool

replacement_tool = types.FunctionDeclaration(
    name="initiate_replacement",
    description="Initiates a product replacement for a specific order. Call this tool INSTEAD of just saying you are sending a replacement. You must call this to actually start the replacement process.",
    parameters=types.Schema(
        type="OBJECT",
        properties={
            "order_id": types.Schema(type="STRING", description="The order ID for the replacement."),
            "item_name": types.Schema(type="STRING", description="Name of the item to replace."),
            "reason": types.Schema(type="STRING", description="Brief reason for the replacement.")
        },
        required=["order_id", "item_name", "reason"]
    )
)