# Efficient Meal & Grocery Planner Agent

---

## Motivation

Meal planning can be overwhelming, especially when you’re trying to balance nutrition, taste, budget, and pantry leftovers. Most people spend too much time figuring out what to cook, often overspend on groceries, and still waste food. This project uses AI agents to automate meal planning and budget tracking, so you can focus on enjoying your meals, not planning them.

---

## Features

- **Automated Meal Planning:** Generates efficient 7-day meal plans, with smart recipe repeats to minimize effort and reduce food waste.
- **Real-Time Grocery Pricing:** Checks web-sourced grocery prices for each item on your list (configurable by store/location).
- **Budget Awareness:** Revises the plan up to three times if it exceeds your set budget, ensuring affordability.
- **Customizable Preferences:** Supports nutrition goals, dietary restrictions, cultural cuisines, pantry leftovers, and item limits.
- **Agent-Based & Modular:** Clean, extensible agent/tool design—easy to add features or connect new data sources.
- **Traceable & Debuggable:** Built-in tracing with [Judgeval](https://github.com/judgeval/judgeval) for seamless debugging and workflow insights.

---

## File Structure

```
Meal-and-Grocery-Planner-Agent/
├── src/
│   ├── modeling/
│   ├── services/
│   ├── __init__.py
│   ├── config.py
│   ├── dataset.py
│   ├── features.py
│   ├── meal_planner.py    # Main CLI
│   └── plots.py
├── .env.example
├── requirements.txt
├── README.md
└── ...
```

---

## Setup

1. **Clone the repository:**

   ```bash
   git clone <repo-url>
   cd Meal-and-Grocery-Planner-Agent
   ```

2. **Set up a virtual environment:**

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure API keys:**

   - Copy `.env.example` to `.env`.
   - Fill in your `OPENAI_API_KEY` (get one [here](https://platform.openai.com/account/api-keys)).
   - Add JUDGMENT_API_KEY, JUDGMENT_ORG_ID (create your account [here](https://app.judgmentlabs.ai/register))

---

## Usage

Run the CLI meal planner:

```bash
python src/meal_planner.py
```

You’ll be prompted for:

- Nutrition goals (e.g., high protein, low carb)
- Cultural cuisine preferences (e.g., Mexican, Italian)
- Dietary restrictions (e.g., vegetarian, gluten-free)
- Pantry leftovers (comma-separated)
- Grocery budget for the week
- Maximum number of new grocery items (optional)

The system will generate a complete meal plan and a priced grocery list, retrying with cheaper options if over budget.

---

## Example Output

![Sample Output](D:\Coding\GitHub Repos\Meal-and-Grocery-Planner-Agent\assests\screenshots\Screenshot01.png)
![Sample Output](D:\Coding\GitHub Repos\Meal-and-Grocery-Planner-Agent\assests\screenshots\Screenshot02.png)
![Sample Output](D:\Coding\GitHub Repos\Meal-and-Grocery-Planner-Agent\assests\screenshots\Screenshot03.png)
![Sample Output](D:\Coding\GitHub Repos\Meal-and-Grocery-Planner-Agent\assests\screenshots\Screenshot04.png)

---

## Tracing & Debugging with Judgeval

This project uses [Judgeval](https://github.com/judgeval/judgeval) for **automatic tracing** of agent workflows.

**How does it work?**

- Key functions and agent/tool calls are instrumented with the `@judgment.observe` decorator from Judgeval.
- Every time you run the CLI, a trace of the workflow (including agent reasoning, tool calls, and results) is recorded.
- Tracing helps with debugging, understanding agent behavior, and performance optimization.

To view or analyze traces, see the [Judgeval documentation](https://github.com/judgeval/judgeval) for dashboard or export options.

---

## Troubleshooting

- **Missing API Key:**
  Make sure you set `OPENAI_API_KEY` in your `.env` file.
- **Dependencies not found:**
  Double-check your virtual environment is active and all packages are installed.
- **Web search or pricing issues:**
  Ensure your internet connection is active and you have API quota remaining.
- **Trace issues:**
  If you don’t see traces, verify the Judgeval integration and check the documentation for advanced setup.

---

## License

MIT License
