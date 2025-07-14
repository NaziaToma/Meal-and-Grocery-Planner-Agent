import os
import re
import asyncio
from dotenv import load_dotenv
# Import custom agent modules (make sure these are installed and available)
from agents import Agent, Runner, WebSearchTool, function_tool
import logging
from judgeval.tracer import Tracer

judgment = Tracer(project_name="meal_planner_assessment")



# --- Setup Environment and Logging ---
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Helper Functions ---
@judgment.observe(span_type="function")
def _parse_price(text: str) -> float:
    """
    Extracts a float price from a string (e.g., '$4.99' -> 4.99).
    
    Args:
        text (str): Text that may contain a price.
    Returns:
        float: Extracted price, or 0.0 if not found.
    """
    if not isinstance(text, str):
        return 0.0
    match = re.search(r'\$?(\d+\.\d{2})', text)
    if match:
        return float(match.group(1))
    return 0.0

@judgment.observe(span_type="function")
def _extract_item_name(item_with_quantity: str) -> str:
    """
    Removes the quantity/notes in parentheses from a grocery item string.
    
    Args:
        item_with_quantity (str): String like "Milk (1 gallon)"
    Returns:
        str: Clean item name ("Milk")
    """
    return re.sub(r'\s*\([^)]*\)', '', item_with_quantity).strip()

# --- Agents ---

# Meal Planner Agent - generates meal plans with efficiency and budget in mind.
meal_planner_agent = Agent(
    name="Meal Planner Agent",
    model="gpt-4o-mini",
    instructions=(
        "You are an expert meal planning assistant focused on efficiency and budget-friendliness. "
        "**EFFICIENCY RULE**: To reduce cooking and waste, the 7-day plan **MUST** repeat some meals. At least 2 meals in the week should be leftovers or repeated recipes. However, **do not** schedule the same meal two days in a row. "
        "**GROCERY LIST RULES**: Every item **MUST** have a quantity (e.g., '- Milk (1 gallon)'). If the user specifies a maximum number of grocery items, the list must not exceed that number. The list section **MUST** begin with a line that says exactly '### Grocery List'. "
        "If asked to revise a plan, create a cheaper version while following all efficiency and formatting rules."
    ),
)

# Web Search Agent - for fetching real-time grocery prices.
web_search_agent = Agent(
    name="Web Search Agent",
    tools=[WebSearchTool()],
)

# --- Orchestrator Tool ---
@function_tool
@judgment.observe(span_type="tool")
async def orchestrator_tool(user_input: str):
    """
    Coordinates meal planning and pricing logic.
    1. Gets a meal plan from the planner agent.
    2. Extracts and prices the grocery list using the web agent.
    3. Revises the plan if over budget, with up to 3 attempts.

    Args:
        user_input (str): The user's request prompt.

    Returns:
        str: Final meal plan and priced grocery list, or error message.
    """
    max_retries = 3
    budget_match = re.search(r'Budget: \$?(\d+)', user_input)
    budget = float(budget_match.group(1)) if budget_match else 100.0
    logging.info(f"🎯 Budget set to: ${budget:.2f}")

    current_prompt = f"User's request: {user_input}."
    
    for attempt in range(max_retries):
        logging.info(f"--- Attempt {attempt + 1} of {max_retries} ---")
        
        @judgment.observe(span_type="agent", name="Meal Planner Agent Run")
        async def run_meal_planner(prompt):
            return await Runner.run(meal_planner_agent, prompt)
        
        # Get meal plan from planner agent
        logging.info("🤖 Asking Meal Planner for a new plan...")
        mealplan_result = await run_meal_planner(current_prompt)
        mealplan_text = mealplan_result.final_output

        # Parse grocery list from meal planner output
        match = re.search(r"#+\s*Grocery List:?[\r\n]+((?:- .+\n?)+)", mealplan_text, re.IGNORECASE)
        if not match:
            # Retry if list not found or formatted wrong
            if attempt < max_retries - 1:
                logging.warning("Could not find a correctly formatted grocery list. Retrying...")
                current_prompt = (
                    "Your previous response was not formatted correctly. Please try again, "
                    "ensuring the grocery list starts with '### Grocery List' and that all items have quantities. "
                    f"Original request: {user_input}"
                )
                continue
            # After final retry, return error
            return mealplan_text + "\n\n⚠️ **Error: Could not extract a grocery list to check prices after several attempts.**"
        
        grocery_list_items = re.findall(r"- ([^\n]+)", match.group(1))
        logging.info(f"🛒 Found {len(grocery_list_items)} items. Looking up prices...")

        # Look up prices asynchronously for all grocery items
        
        async def get_price(item_text):
            
            @judgment.observe(span_type="agent", name="Web Search Agent Run")
            async def run_web_search(prompt):
                return await Runner.run(web_search_agent, prompt)
            query_full = f"Price of {item_text} at Walmart in Watertown, Connecticut"
            result_full = await run_web_search(query_full)
            price = _parse_price(result_full.final_output)

            # Fallback to just the core item name if full search fails
            if price == 0.0:
                item_name_only = _extract_item_name(item_text)
                if item_name_only != item_text:
                    logging.info(f"  -> Fallback search for '{item_name_only}'")
                    query_fallback = f"Price of {item_name_only} at Walmart in Watertown, Connecticut"
                    result_fallback = await run_web_search(query_fallback)
                    price = _parse_price(result_fallback.final_output)

            logging.info(f"  - {item_text}: ${price:.2f}")
            return price

        prices_found = await asyncio.gather(*[get_price(item) for item in grocery_list_items])
        total_cost = sum(prices_found)
        logging.info(f"💵 Calculated Total Cost: ${total_cost:.2f}")

        # Prepare priced grocery list text for output
        priced_list_text = "\n".join([f"- {item}: ${price:.2f}" for item, price in zip(grocery_list_items, prices_found)])
        final_report_text = re.sub(r"#+\s*Grocery List:?[\r\n]+((?:- .+\n?)+)", "", mealplan_text, flags=re.IGNORECASE).strip()

        # Success: Plan is within budget
        if total_cost <= budget:
            logging.info("✅ Budget met! Compiling final report.")
            return f"{final_report_text}\n\n---\n\n## 🛒 Priced Grocery List (Total: ${total_cost:.2f})\n\n{priced_list_text}"
        
        # Otherwise, request a revision (try up to max_retries)
        if attempt < max_retries - 1:
            logging.warning(f"❌ Plan is over budget. Asking for a revision...")
            current_prompt = (
                f"Your last plan was too expensive at ${total_cost:.2f}. The grocery list was:\n{priced_list_text}\n"
                "Please generate a NEW, cheaper meal plan. Remember to follow all rules about meal repetition and item limits. "
                f"Original request was: {user_input}"
            )
        else:
            # After final attempt, return best effort
            return (
                f"⚠️ **Failed to create a plan within the ${budget:.2f} budget after {max_retries} attempts.**\n"
                f"The cheapest plan generated had a cost of ${total_cost:.2f}.\n\n"
                f"Here is the final meal plan and its priced list:\n{final_report_text}\n\n"
                f"## 🛒 Priced Grocery List (Total: ${total_cost:.2f})\n\n{priced_list_text}"
            )

# --- CLI (User Interaction Loop) ---
@judgment.observe(span_type="chain") 
async def chat_cli():
    """
    CLI: Prompts user for preferences and runs the orchestrator tool to generate the meal plan.
    Gathers nutrition, cultural, dietary, pantry, budget, and grocery item limit info.
    """
    print("\nWelcome to the Efficient Meal Planner! Let's create your plan.")
    print("Please answer the following questions. You can press Enter to leave any field blank.")

    # Gather all user inputs
    nutrition_goals = input("🥗 What are your nutrition goals (e.g., high protein, low carb)?\n> ")
    cultural_preferences = input("🌮 Any cultural preferences for food (e.g., Mexican, Italian)?\n> ")
    dietary_restrictions = input("🥜 Any dietary restrictions (e.g., gluten-free, vegetarian)?\n> ")
    pantry_leftovers = input("🥫 What's in your pantry to use (comma-separated)?\n> ")
    budget_input = input("💰 What is your weekly budget for new groceries (e.g., 100)?\n> ")
    item_limit_input = input("🛒 Any limit on the number of new grocery items (e.g., 10, or leave blank)?\n> ")
    
    # Build user prompt for orchestrator agent
    prompt_details = [
        "## User Inputs:",
        f"- **Nutrition Goals**: {nutrition_goals or 'None'}",
        f"- **Cultural Preferences**: {cultural_preferences or 'None'}",
        f"- **Dietary Restrictions**: {dietary_restrictions or 'None'}",
        f"- **Pantry Leftovers**: {pantry_leftovers or 'None'}",
        f"- **Budget**: ${budget_input or '100'}"
    ]
    if item_limit_input.isdigit():
        prompt_details.append(f"- **Max Grocery Items**: {item_limit_input}")
        
    user_prompt = "\n".join(prompt_details)
    
    print("\n✅ Great! Based on your answers, I'm creating an efficient plan. This may take a moment...")
    print("------------------------------------------------------------------")
    
    # Orchestrator Agent runs the workflow using the tool
    orchestrator_agent = Agent(
        name="Orchestrator Agent",
        tools=[orchestrator_tool],
        model="gpt-4o",
        instructions="You are a master coordinator. Use your tool to fulfill the user's meal planning request, including adhering to their budget and efficiency goals."
    )
    
    @judgment.observe(span_type="agent", name="Orchestrator Agent Run")
    async def run_orchestrator(prompt):
        return await Runner.run(orchestrator_agent, prompt)
    result = await run_orchestrator(user_prompt)
    
    print("\n## 📄 Your Meal Plan & Priced Grocery List\n" + result.final_output)

# --- Script Entrypoint ---
if __name__ == "__main__":
    # Ensure API key exists before running
    if not os.getenv("OPENAI_API_KEY"):
        print("FATAL ERROR: OPENAI_API_KEY not found in .env file.")
    else:
        try:
            asyncio.run(chat_cli())
        except KeyboardInterrupt:
            print("\nExiting program. Goodbye!")
