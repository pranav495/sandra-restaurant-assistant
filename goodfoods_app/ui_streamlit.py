"""
Streamlit chat interface.
"""

import streamlit as st
from .db import init_db, seed_restaurants_if_empty
from .agent import run_agent


def main():
    st.set_page_config(
        page_title="Sandra - Your Dining Companion",
        page_icon="👩‍🍳",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': None,
            'Report a bug': None,
            'About': None
        }
    )

    # Custom styling
    st.markdown("""
        <style>
        /* Hide Streamlit UI */
        #MainMenu, footer, header, .stDeployButton {display: none !important; visibility: hidden !important;}
        
        /* Colors */
        :root {
            --warm-cream: #FDF6E3;
            --soft-coral: #FF8B7B;
            --deep-burgundy: #8B2635;
            --forest-green: #2D5A3D;
            --warm-gray: #6B6B6B;
            --soft-shadow: rgba(0,0,0,0.08);
        }
        
        /* Background */
        .stApp {
            background: linear-gradient(135deg, #1a1a2e 0%, #0f0f1a 100%);
        }
        
        /* Chat container */
        .main .block-container {
            max-width: 900px;
            padding: 1rem 2rem 3rem 2rem;
        }
        
        /* Assistant messages */
        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
            background: linear-gradient(135deg, rgba(255,139,123,0.15) 0%, rgba(139,38,53,0.1) 100%);
            border-radius: 20px 20px 20px 4px;
            border-left: 3px solid #FF8B7B;
            margin: 0.8rem 0;
            padding: 1rem;
        }
        
        /* User messages */
        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
            background: rgba(255,255,255,0.05);
            border-radius: 20px 20px 4px 20px;
            border-right: 3px solid #6C9BC4;
            margin: 0.8rem 0;
            padding: 1rem;
        }
        
        /* Message text */
        [data-testid="stChatMessageContent"] {
            font-size: 1.05rem;
            line-height: 1.7;
            font-family: 'Segoe UI', system-ui, sans-serif;
        }
        
        /* Input box */
        [data-testid="stChatInput"] {
            border-radius: 30px !important;
            border: 2px solid rgba(255,139,123,0.3) !important;
            background: rgba(255,255,255,0.05) !important;
            padding: 0.5rem 1rem !important;
        }
        
        [data-testid="stChatInput"]:focus-within {
            border-color: #FF8B7B !important;
            box-shadow: 0 0 20px rgba(255,139,123,0.2) !important;
        }
        
        /* Sidebar */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #1E1E2E 0%, #151520 100%);
            border-right: 1px solid rgba(255,255,255,0.05);
        }
        
        [data-testid="stSidebar"] > div {
            padding: 1.5rem 1rem;
        }
        
        /* Buttons */
        .stButton > button {
            background: linear-gradient(135deg, #FF8B7B 0%, #FF6B6B 100%);
            color: white;
            border: none;
            border-radius: 25px;
            padding: 0.6rem 1.5rem;
            font-weight: 600;
            font-size: 0.95rem;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(255,107,107,0.3);
        }
        
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 25px rgba(255,107,107,0.4);
        }
        
        /* Expanders */
        .streamlit-expanderHeader {
            background: rgba(255,255,255,0.03);
            border-radius: 12px;
            border: 1px solid rgba(255,255,255,0.05);
            font-weight: 500;
        }
        
        .streamlit-expanderHeader:hover {
            background: rgba(255,139,123,0.1);
            border-color: rgba(255,139,123,0.3);
        }
        
        /* Metrics */
        [data-testid="stMetricValue"] {
            font-size: 1.8rem;
            font-weight: 700;
            color: #FF8B7B;
        }
        
        [data-testid="stMetricLabel"] {
            font-size: 0.85rem;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        /* Slider */
        .stSlider > div > div > div {
            background: linear-gradient(90deg, #FF8B7B, #FF6B6B) !important;
        }
        
        /* Dividers */
        hr {
            border: none;
            height: 1px;
            background: linear-gradient(90deg, transparent, rgba(255,139,123,0.3), transparent);
            margin: 1.5rem 0;
        }
        
        /* Select boxes */
        .stSelectbox > div > div {
            background: rgba(255,255,255,0.05);
            border-radius: 10px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        
        /* Spinner */
        .stSpinner > div {
            border-top-color: #FF8B7B !important;
        }
        
        /* Links */
        a {
            color: #FF8B7B !important;
        }
        
        /* Code/ID tags */
        code {
            background: rgba(255,139,123,0.15);
            color: #FF8B7B;
            padding: 2px 8px;
            border-radius: 6px;
            font-size: 0.9em;
        }
        
        /* Table styling */
        table {
            border-collapse: separate;
            border-spacing: 0;
        }
        
        th {
            background: rgba(255,139,123,0.1);
            padding: 0.8rem;
            text-align: left;
            border-bottom: 2px solid rgba(255,139,123,0.3);
        }
        
        td {
            padding: 0.6rem 0.8rem;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        
        /* Typing indicator animation */
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .typing-indicator {
            animation: pulse 1.5s infinite;
        }
        </style>
    """, unsafe_allow_html=True)

    conn = init_db()
    seed_restaurants_if_empty(conn)

    st.markdown("""
        <div style="text-align: center; padding: 1rem 0 0.5rem 0;">
            <span style="font-size: 3.5rem;">👩‍🍳</span>
            <h1 style="font-size: 2.2rem; margin: 0.3rem 0; font-weight: 600; 
                       background: linear-gradient(135deg, #FF8B7B 0%, #FFB347 100%);
                       -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                Hey, I'm Sandra!
            </h1>
            <p style="color: #888; font-size: 1.1rem; margin: 0; font-weight: 300;">
                Your friendly neighborhood restaurant concierge 🌟
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)

    if "messages" not in st.session_state:
        st.session_state.messages = [{
            "role": "assistant",
            "content": """Hey there! 👋 So nice to meet you!

I'm **Sandra**, and I absolutely *love* helping people find amazing dining experiences in Mumbai. Think of me as that friend who always knows the best spots! 

**What I'm great at:**

🔍 Finding that perfect restaurant (romantic dinner? birthday bash? quick bite?)  
📅 Checking if your favorite place has room  
✅ Booking tables faster than you can say "butter chicken"  
✏️ Changing plans? No worries, I've got you  
📱 Lost your booking details? I'll find them!

**Just tell me what you're in the mood for!** Something like:

> *"I need a cozy Italian place in Bandra for date night tomorrow"*  
> *"What's good for a group of 8 in Andheri?"*  
> *"Find me something fancy for my anniversary!"*

So... what are we celebrating today? 🎉"""
        }]

    chat_container = st.container()
    
    with chat_container:
        for message in st.session_state.messages:
            avatar = "👩‍🍳" if message["role"] == "assistant" else "😊"
            with st.chat_message(message["role"], avatar=avatar):
                st.markdown(message["content"])

    if prompt := st.chat_input("Tell me what you're craving... 🍽️"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.spinner(""):
            thinking_placeholder = st.empty()
            thinking_placeholder.markdown("""
                <div style="text-align: center; padding: 1rem; color: #888;">
                    <span class="typing-indicator">👩‍🍳 Sandra is checking the best options for you...</span>
                </div>
            """, unsafe_allow_html=True)
            
            agent_messages = [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
                if m["role"] in ["user", "assistant"]
            ]
            response = run_agent(agent_messages, conn)
            thinking_placeholder.empty()

        st.session_state.messages.append(response)
        st.rerun()

    with st.sidebar:
        st.markdown("""
            <div style="text-align: center; padding: 1rem 0;">
                <span style="font-size: 2rem;">🍽️</span>
                <h3 style="margin: 0.5rem 0 0 0; font-weight: 500;">Browse Restaurants</h3>
                <p style="color: #666; font-size: 0.85rem; margin: 0;">Find your next favorite spot</p>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        cursor = conn.cursor()
        
        cursor.execute("SELECT DISTINCT location_area FROM restaurants ORDER BY location_area")
        areas = ["📍 Any Area"] + [row[0] for row in cursor.fetchall()]
        selected_area = st.selectbox("Location", areas, label_visibility="collapsed")
        
        cursor.execute("SELECT DISTINCT cuisine FROM restaurants ORDER BY cuisine")
        cuisines = ["🍴 Any Cuisine"] + [row[0] for row in cursor.fetchall()]
        selected_cuisine = st.selectbox("Cuisine", cuisines, label_visibility="collapsed")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        price_range = st.slider(
            "💰 Budget per person",
            min_value=300,
            max_value=1200,
            value=(300, 1200),
            format="₹%d"
        )
        
        st.divider()
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 New Chat", use_container_width=True):
                st.session_state.messages = [{
                    "role": "assistant",
                    "content": "Fresh start! 🌟 What kind of dining experience are you looking for today?"
                }]
                st.rerun()
        
        with col2:
            cursor.execute("SELECT COUNT(*) FROM reservations WHERE status = 'confirmed'")
            booking_count = cursor.fetchone()[0]
            st.metric("Bookings", booking_count, label_visibility="visible")
        
        st.divider()
        
        query = "SELECT * FROM restaurants WHERE average_price_per_person BETWEEN ? AND ?"
        params = [price_range[0], price_range[1]]
        
        if selected_area != "📍 Any Area":
            query += " AND location_area = ?"
            params.append(selected_area)
        if selected_cuisine != "🍴 Any Cuisine":
            query += " AND cuisine = ?"
            params.append(selected_cuisine)
        query += " ORDER BY name LIMIT 20"
        
        cursor.execute(query, params)
        restaurants = cursor.fetchall()
        
        st.markdown(f"**{len(restaurants)} restaurants found**")
        st.markdown("<br>", unsafe_allow_html=True)
        
        for rest in restaurants:
            with st.expander(f"{rest['name']}", expanded=False):
                features = rest['features'].split(',') if rest['features'] else []
                feature_tags = ' '.join([f"`{f.strip()}`" for f in features[:3]])
                
                st.markdown(f"""
**{rest['location_area']}** · {rest['cuisine']}

💰 ₹{rest['average_price_per_person']}/person · 👥 {rest['seating_capacity']} seats

⏰ {rest['opening_time']} - {rest['closing_time']}

{feature_tags}

---
*Tell Sandra:* "Book restaurant `{rest['id']}`"
""")


if __name__ == "__main__":
    main()
