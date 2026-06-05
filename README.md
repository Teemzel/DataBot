# 📊 Data Analyst Telegram Bot (Powered by Google Gemini — FREE)

A Telegram bot that lets you upload a CSV or Excel file and ask questions
about your data in plain English — including charts! Powered by the
**free** Google Gemini 1.5 Flash API.

---

## ✨ Features

- Upload CSV or Excel files directly in Telegram
- Ask questions in plain English
- Get charts: bar, line, pie, scatter, histogram, box
- Multi-turn conversation — remembers context
- 100% FREE using Google Gemini API (no credit card needed)

---

## 🚀 Quick Start (Local)

### Step 1 — Install Python dependencies

```bash
pip install -r requirements.txt
```

### Step 2 — Get your FREE API keys

**Gemini API Key (free, no card needed):**
1. Go to https://aistudio.google.com
2. Sign in with your Google account
3. Click **Get API Key** → **Create API Key**
4. Copy the key (starts with `AIza...`)

**Telegram Bot Token (free):**
1. Open Telegram → search **@BotFather** (blue checkmark ✅)
2. Send `/newbot` → follow the prompts
3. Copy the token BotFather gives you

### Step 3 — Set your keys

```bash
cp .env.example .env
```

Open `.env` and fill in:
```
GEMINI_API_KEY=AIzaxxxxxxxxxxxxxxxxxxxxxxx

TELEGRAM_BOT_TOKEN=1234567890:AAxxxxxxxxxxxxxxx

```

Then load them:
```bash
export $(cat .env | xargs)
```

### Step 4 — Run the bot

```bash
python bot.py
```

### Step 5 — Test it!
Open Telegram → find your bot → send `/start` → upload a CSV → ask a question!

---

## 💬 Example Conversation

```
You:   [uploads sales_data.csv]
Bot:   ✅ sales_data.csv loaded!
       Columns: date, product, revenue, region

You:   What is the total revenue by region?
Bot:   💰 Total Revenue by Region:
       • North: 4,200,000
       • South: 3,100,000
       • West:  2,800,000

You:   Show me a bar chart of that
Bot:   [sends a bar chart image 📊]

You:   Which product had the highest average revenue?
Bot:   📦 Product A had the highest average revenue at 85,400 per sale.
```

---

## 📁 Project Structure

```
data_analyst_bot_gemini/
├── bot.py            # Telegram bot handlers
├── agent.py          # Gemini agent loop + tools
├── requirements.txt  # Python dependencies
├── Procfile          # For Railway/Render deployment
├── .env.example      # API key template
└── README.md         # This file
```

---

## ☁️ Deploy to Railway (Free Hosting)

1. Push this folder to a GitHub repo
2. Go to https://railway.app → **New Project** → **Deploy from GitHub**
3. Select your repo
4. Go to **Variables** tab and add:
   - `GEMINI_API_KEY`
   - `TELEGRAM_BOT_TOKEN`
5. Railway detects the `Procfile` and starts your bot automatically

Your bot will run 24/7 for free! 🚀

---

## 📋 Bot Commands

| Command | Description            |
|---------|------------------------|
| /start  | Welcome message        |
| /help   | Show help & tips       |
| /clear  | Reset data and history |

---

## 🆓 Gemini Free Tier Limits

| Limit            | Value                  |
|------------------|------------------------|
| Requests/minute  | 15                     |
| Requests/day     | 1,500                  |
| Tokens/minute    | 1,000,000              |
| Cost             | **FREE** (no card needed) |

More than enough for personal and small-team use!
