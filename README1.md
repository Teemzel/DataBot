# 📊 Data Analyst Telegram Bot

A Telegram bot powered by Claude AI that lets you upload a CSV or Excel file
and ask questions about your data in plain English — including charts!

---

## Features

- Upload CSV or Excel files directly in Telegram
- Ask questions in plain English
- Get charts (bar, line, pie, scatter, histogram, box)
- Multi-turn conversation — the bot remembers context
- Powered by Claude claude-sonnet-4-20250514 with tool use

---

## Quick Start (Local)

### 1. Clone / download this project

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Set your API keys

```bash
cp .env.example .env
# Edit .env and fill in your keys
```

Or export them directly:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export TELEGRAM_BOT_TOKEN="1234567890:AA..."
```

### 4. Run the bot

```bash
python bot.py
```

### 5. Open Telegram, find your bot, and start chatting!

---

## Getting Your Keys

### Anthropic API Key
1. Go to https://console.anthropic.com
2. Sign up / log in
3. Navigate to **API Keys** → **Create Key**

### Telegram Bot Token
1. Open Telegram and search for **@BotFather**
2. Send `/newbot`
3. Follow the prompts — BotFather gives you a token like `1234567890:AAxxxxxxx`

---

## Example Conversation

```
You:   [uploads sales_data.csv]
Bot:   ✅ sales_data.csv loaded!
       Columns: date, product, revenue, region

You:   What is the total revenue by region?
Bot:   💰 Total Revenue by Region:
       • North: ₦4,200,000
       • South: ₦3,100,000
       • West:  ₦2,800,000

You:   Show me a bar chart of that
Bot:   [sends a bar chart image 📊]

You:   Which month had the highest sales?
Bot:   📅 March 2024 had the highest sales with ₦1,850,000 in total revenue.
```

---

## Deploy to Railway (Free)

1. Push this folder to a GitHub repo
2. Go to https://railway.app → **New Project** → **Deploy from GitHub**
3. Select your repo
4. Go to **Variables** and add:
   - `ANTHROPIC_API_KEY`
   - `TELEGRAM_BOT_TOKEN`
5. Railway auto-detects the `Procfile` and starts the bot

That's it — your bot runs 24/7 for free! 🚀

---

## Project Structure

```
data_analyst_bot/
├── bot.py            # Telegram bot handlers
├── agent.py          # Claude agent loop + tools
├── requirements.txt  # Python dependencies
├── Procfile          # For Railway/Render deployment
├── .env.example      # API key template
└── README.md         # This file
```

---

## Commands

| Command | Description |
|---------|-------------|
| /start  | Welcome message & instructions |
| /help   | Show help |
| /clear  | Clear loaded data and chat history |

---

## Customization Tips

- **Add more tools**: Edit the `TOOLS` list in `agent.py`
- **Change the persona**: Edit `SYSTEM_PROMPT` in `agent.py`
- **Support more file types**: Add handling in `_load_df()` in `agent.py`
- **Add user auth**: Check `update.effective_user.id` in `bot.py`
