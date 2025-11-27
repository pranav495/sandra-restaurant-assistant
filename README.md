# 👩‍🍳 Sandra - AI Restaurant Reservation Assistant

A conversational AI-powered restaurant reservation assistant for Mumbai, built with Streamlit and local LLM (Ollama).

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)
![Ollama](https://img.shields.io/badge/Ollama-Local%20LLM-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

---

## 🎬 Demo Video

[![Sandra Demo](https://img.shields.io/badge/▶️_Watch_Demo-Loom-blueviolet?style=for-the-badge&logo=loom)](https://www.loom.com/share/778e8cce90564504a565fa24793aced2)

> **📹 [Click here to watch the full demo video](https://www.loom.com/share/778e8cce90564504a565fa24793aced2)**
>
> The demo covers:
> - Mood-based restaurant discovery ("romantic anniversary dinner")
> - Filter-based search ("Italian in Bandra for 4")
> - Complete booking flow
> - Modifying and cancelling reservations
> - Phone number lookup

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔍 **Smart Search** | Find restaurants by location, cuisine, budget, party size |
| 🎯 **Semantic Recommendations** | AI understands mood/vibe ("romantic", "lively", "quiet business meeting") |
| 📅 **Real-time Availability** | Check table availability before booking |
| ✅ **Instant Booking** | Complete reservations through natural conversation |
| ✏️ **Easy Modifications** | Change time or party size on existing bookings |
| ❌ **Quick Cancellation** | Cancel reservations when plans change |
| 📱 **Phone Lookup** | Find your bookings using just your phone number |

---

## 🚀 Setup Instructions

### Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.10+ | [Download](https://www.python.org/downloads/) |
| Ollama | Latest | [Install Guide](https://ollama.ai/) |
| Git | Any | For cloning the repo |

### Step-by-Step Installation

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/sandra-restaurant-assistant.git
cd sandra-restaurant-assistant

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate      # Linux/Mac
# .venv\Scripts\activate       # Windows

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Install and start Ollama (if not already)
# Download from https://ollama.ai/ then:
ollama serve                   # Start Ollama server (in separate terminal)
ollama pull llama3.2:3b        # Download the model (~2GB, fast!)

# 5. Run the application
streamlit run run_app.py

# 6. Open browser
# Navigate to http://localhost:8501
```

### Verify Installation

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Check model is available
ollama list
# Should show: llama3.2:3b
```

### Configuration

Edit `goodfoods_app/config.py` if needed:

```python
DB_PATH = "goodfoods.db"                           # SQLite database
LLAMA_API_URL = "http://localhost:11434/api/chat"  # Ollama endpoint
LLM_MODEL = "llama3.2:3b"                          # Model name (fast & lightweight)
LLM_TEMPERATURE = 0.3                              # Lower = more focused
LLM_TIMEOUT = 180                                  # Request timeout (seconds)
```

---

## 🧠 Prompt Engineering Approach

### Design Philosophy

Sandra's personality and behavior are shaped by a carefully crafted system prompt that balances:

1. **Warmth** - Friendly, approachable tone (not robotic)
2. **Precision** - Strict rules about tool usage to prevent hallucination
3. **Flow Control** - Clear decision trees for when to use which tool

### System Prompt Structure

```
┌─────────────────────────────────────────────────────────────┐
│                    PERSONA DEFINITION                       │
│  "You are Sandra, a friendly restaurant concierge..."       │
├─────────────────────────────────────────────────────────────┤
│                    TASK ENUMERATION                         │
│  - Search restaurants                                       │
│  - Check availability                                       │
│  - Create/modify/cancel reservations                        │
│  - Look up by phone                                         │
├─────────────────────────────────────────────────────────────┤
│                 DECISION ROUTING RULES                      │
│  IF mood-based query → semantic_recommend                   │
│  IF filter-based query → search_restaurants                 │
│  IF booking request without restaurant → ASK first          │
├─────────────────────────────────────────────────────────────┤
│                   ANTI-HALLUCINATION                        │
│  "NEVER invent restaurant_ids"                              │
│  "Only use IDs from tool results or user input"             │
├─────────────────────────────────────────────────────────────┤
│                    OUTPUT FORMAT                            │
│  ISO 8601 dates, clear restaurant listings, confirm IDs     │
└─────────────────────────────────────────────────────────────┘
```

### Key Prompt Engineering Techniques

| Technique | Implementation | Why It Works |
|-----------|----------------|--------------|
| **Role Assignment** | "You are Sandra, a friendly concierge" | Creates consistent persona |
| **Explicit Tool Routing** | "IF mood → semantic_recommend, IF filters → search" | Reduces tool confusion |
| **Negative Instructions** | "NEVER invent IDs", "DO NOT call tools immediately" | Prevents common failures |
| **Output Scaffolding** | "Show name, area, cuisine, price, restaurant_id" | Consistent response format |
| **Conversation Flow** | Numbered steps for booking process | Guides multi-turn dialogue |
| **Error Handling** | "When a tool returns error, explain briefly..." | Graceful failure recovery |

### Semantic vs Filter Search Decision

```
User Query Analysis:
┌────────────────────────────────────────┐
│ "romantic dinner in Bandra"            │
│  ├─ "romantic" = mood descriptor       │
│  └─ Use: semantic_recommend            │
├────────────────────────────────────────┤
│ "Italian restaurant in Andheri, 7pm"   │
│  ├─ "Italian" = cuisine filter         │
│  ├─ "Andheri" = location filter        │
│  ├─ "7pm" = time filter                │
│  └─ Use: search_restaurants            │
├────────────────────────────────────────┤
│ "cozy place with good pasta in Bandra" │
│  ├─ "cozy" = mood descriptor           │
│  ├─ "pasta" = cuisine hint             │
│  └─ Use: semantic_recommend (mood wins)│
└────────────────────────────────────────┘
```

### Embedding Strategy for Semantic Search

```python
# Each restaurant is embedded as:
"{name}. Area: {location}. Cuisine: {cuisine}. Features: {features}."

# User query is embedded as:
"{mood}. Area: {location}. Cuisine: {cuisine}."

# Matching via cosine similarity finds restaurants 
# whose "vibe" matches user intent
```

---

## 💬 Example Conversations

### Journey 1: Mood-Based Discovery → Booking

```
👤 User: I'm looking for something romantic for our anniversary in Bandra, 
         budget around ₹800 per person

🤖 Sandra: How lovely! An anniversary calls for something special. Let me 
          find the perfect spots for you in Bandra...

          Here are my top picks:

          1. **The Romantic Terrace** (ID: 23)
             📍 Bandra | 🍝 Italian | 💰 ₹750/person
             ✨ rooftop, romantic, candlelit
             
          2. **Moonlight Bistro** (ID: 45)
             📍 Bandra | 🍷 Continental | 💰 ₹800/person
             ✨ romantic, private-dining, live-music

          3. **Garden of Flavors** (ID: 67)
             📍 Bandra | 🥗 Mediterranean | 💰 ₹700/person
             ✨ outdoor-seating, romantic, quiet

          Which one catches your eye? Just tell me the ID!

👤 User: Let's go with 45, for 2 people, tomorrow at 8pm

🤖 Sandra: Great choice! Moonlight Bistro is perfect for anniversaries. 
          Let me check if 8pm tomorrow works for 2...

          ✅ Good news! Table available!
          
          To confirm your booking, I just need:
          - Your name
          - Phone number

👤 User: Pranav, 9876543210

🤖 Sandra: All set! 🎉

          ┌─────────────────────────────────────┐
          │ RESERVATION CONFIRMED               │
          ├─────────────────────────────────────┤
          │ 📍 Moonlight Bistro, Bandra         │
          │ 📅 Tomorrow, 8:00 PM                │
          │ 👥 2 guests                         │
          │ 🎫 Reservation ID: #127             │
          │ 📱 Phone: 9876543210                │
          └─────────────────────────────────────┘

          Have an amazing anniversary! 💕
```

### Journey 2: Filter-Based Search

```
👤 User: Find me Chinese restaurants in Andheri for 6 people, 
         this Saturday at 7:30pm

🤖 Sandra: Looking for Chinese in Andheri for 6, Saturday 7:30pm...

          Found these options:

          1. **Dragon Palace** (ID: 12)
             📍 Andheri West | 💰 ₹600/person | 👥 80 seats
             ⏰ 11:00 - 23:00

          2. **Wok & Roll** (ID: 34)
             📍 Andheri East | 💰 ₹450/person | 👥 50 seats
             ⏰ 12:00 - 22:30

          3. **Golden Chopsticks** (ID: 56)
             📍 Andheri West | 💰 ₹700/person | 👥 100 seats
             ⏰ 11:30 - 23:30

          Want me to check availability at any of these?

👤 User: Check 12

🤖 Sandra: Checking Dragon Palace for 6 people, Saturday 7:30pm...

          ✅ Available! 12 seats open for that slot.
          
          Ready to book? Just give me a name and phone number!
```

### Journey 3: Modify Existing Booking

```
👤 User: I need to change my reservation

🤖 Sandra: No problem! I can help with that. 
          Do you have your reservation ID, or should I look it up 
          by your phone number?

👤 User: Phone is 9876543210

🤖 Sandra: Found it! Here's your booking:

          📍 Moonlight Bistro, Bandra
          📅 Nov 27, 2025 at 8:00 PM
          👥 2 guests
          🎫 Reservation #127

          What would you like to change?
          - Time/date
          - Party size
          - Or cancel entirely?

👤 User: Change it to 4 people

🤖 Sandra: Let me check if they can accommodate 4 at the same time...

          ✅ Done! Your reservation is now updated:
          
          📅 Nov 27, 2025 at 8:00 PM
          👥 4 guests (was 2)

          Anything else?
```

### Journey 4: Phone Lookup & Cancellation

```
👤 User: I need to cancel my booking, phone 9876543210

🤖 Sandra: Looking up your reservations...

          Found 1 active booking:

          📍 Moonlight Bistro, Bandra
          📅 Nov 27, 2025 at 8:00 PM
          👥 4 guests
          🎫 Reservation #127

          Are you sure you want to cancel this?

👤 User: Yes, cancel it

🤖 Sandra: Done. Reservation #127 has been cancelled.

          Sorry to see you go! Feel free to book again anytime. 
          Hope everything's okay! 💙
```

### Journey 5: No Results Handling

```
👤 User: I want Japanese food in Panvel for 20 people tonight at 6pm

🤖 Sandra: Let me search for Japanese restaurants in Panvel...

          😕 I couldn't find any Japanese restaurants in Panvel that 
          can seat 20 people.

          A few suggestions:
          - **Try a different cuisine** - I have several large 
            restaurants in Panvel
          - **Try nearby areas** - Vashi has great Japanese options
          - **Split the group** - Some places seat 10-15

          What would you like to do?
```

---

## 📈 Business Strategy Summary

### Value Proposition

| For Customers | For Restaurants |
|---------------|-----------------|
| 24/7 booking availability | Reduced phone call overhead |
| Natural language interface | Automated reservation management |
| Instant confirmation | Reduced no-shows (with future deposits) |
| Easy modifications | Customer data insights |

### Target Market

- **Primary**: Mumbai diners (25-45 age group) comfortable with chat interfaces
- **Secondary**: Tourists seeking local dining recommendations
- **Restaurant Partners**: Mid-to-upscale restaurants wanting digital booking

### Revenue Model (Future)

| Stream | Description |
|--------|-------------|
| **Commission** | 2-5% per booking from restaurants |
| **Premium Listings** | Featured placement in recommendations |
| **Subscription** | Monthly fee for restaurants with analytics |
| **White-label** | License Sandra to restaurant chains |

### Competitive Advantage

1. **Local LLM** - No cloud dependency, faster responses, data privacy
2. **Semantic Search** - Understands "vibe" not just filters
3. **Conversational UX** - More natural than form-based booking
4. **Mumbai-focused** - Deep local knowledge vs generic platforms

### Growth Roadmap

```
Q1 2026: Launch with 50 restaurants, web-only
Q2 2026: Add WhatsApp channel, 200 restaurants
Q3 2026: Payment integration, waitlist feature
Q4 2026: Expand to Pune & Bangalore
```

### Key Metrics to Track

| Metric | Target | Why It Matters |
|--------|--------|----------------|
| Booking Completion Rate | >80% | Core conversion |
| Avg. Turns to Book | <6 | UX efficiency |
| Restaurant Partner NPS | >50 | B2B satisfaction |
| User Retention (30-day) | >40% | Stickiness |
| Revenue per Booking | ₹30-50 | Unit economics |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      STREAMLIT UI                           │
│                    (ui_streamlit.py)                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      AGENT LOOP                             │
│                      (agent.py)                             │
│  1. Receive user message                                    │
│  2. Call LLM with tools                                     │
│  3. Execute tool calls                                      │
│  4. Return response                                         │
└─────────────────────────────────────────────────────────────┘
                    │                   │
                    ▼                   ▼
┌──────────────────────────┐  ┌────────────────────────────────┐
│       LLM CLIENT         │  │           TOOLS                │
│     (llm_client.py)      │  │         (tools.py)             │
│                          │  │                                │
│  - Ollama API calls      │  │  - search_restaurants          │
│  - System prompt         │  │  - semantic_recommend          │
│  - Response parsing      │  │  - check_availability          │
└──────────────────────────┘  │  - create_reservation          │
            │                 │  - modify_reservation          │
            ▼                 │  - cancel_reservation          │
┌──────────────────────────┐  │  - get_reservation_by_phone    │
│    OLLAMA (Local LLM)    │  └────────────────────────────────┘
│     llama3.1:latest      │                  │
└──────────────────────────┘                  ▼
                              ┌────────────────────────────────┐
                              │         DATABASE               │
                              │          (db.py)               │
                              │                                │
                              │  SQLite: goodfoods.db          │
                              │  - restaurants (75 seeded)     │
                              │  - reservations                │
                              └────────────────────────────────┘
```

### File Structure

```
sandra-restaurant-assistant/
├── goodfoods_app/
│   ├── __init__.py          # Package init
│   ├── config.py            # Settings (DB, API, model)
│   ├── db.py                # SQLite setup & seeding
│   ├── models.py            # Dataclasses
│   ├── tools.py             # 7 tool functions + schemas
│   ├── llm_client.py        # Ollama integration
│   ├── agent.py             # Conversation loop
│   └── ui_streamlit.py      # Chat interface
├── run_app.py               # Entry point
├── requirements.txt         # Dependencies
├── README.md                # This file
├── USE_CASE.md              # Detailed use case document
├── CONTRIBUTING.md          # Contribution guide
├── LICENSE                  # MIT License
└── goodfoods.db             # SQLite database (auto-created)
```

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Frontend** | Streamlit | Chat UI |
| **LLM** | Ollama + Llama 3.2 (3B) | Conversation & reasoning |
| **Embeddings** | Sentence Transformers | Semantic search |
| **Database** | SQLite | Data persistence |
| **Vector Math** | NumPy | Cosine similarity |

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

MIT License - see [LICENSE](LICENSE)

---

## 📚 Additional Documentation

- [USE_CASE.md](USE_CASE.md) - Detailed use case document with state diagrams
- [CONTRIBUTING.md](CONTRIBUTING.md) - How to contribute

---

Made with ❤️ by Pranav
