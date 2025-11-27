# How I Built Sandra's Brain: A Prompt Engineering Deep Dive

When I started building Sandra, I quickly realized that getting an LLM to reliably handle restaurant reservations is *way* harder than it sounds. Here's what I learned along the way.

## The Problem

I needed Sandra to:
- Understand vague requests like "somewhere nice for a date"
- Handle specific queries like "Italian in Bandra, 7pm, 4 people"
- Never make up restaurant IDs (this was a big one)
- Guide users through a multi-step booking flow
- Know when to ask questions vs when to act

Sounds simple, right? It wasn't.

## My First Attempt (It Failed)

My initial prompt was basically:

```
You are a restaurant reservation assistant. Help users book tables.
```

What happened:
- Sandra would invent restaurant names that didn't exist
- She'd try to book without asking for phone numbers
- She'd hallucinate reservation IDs
- Sometimes she'd just... make stuff up

Not great for a booking system where accuracy matters.

## What Actually Worked

### 1. Give Her a Personality, But Keep Her Focused

Instead of a generic assistant, I made Sandra a specific character:

```
You are Sandra, a friendly and helpful restaurant reservation assistant for Mumbai.
```

Why "Sandra"? Honestly, I just liked the name. But giving the bot a name and personality made the conversations feel more natural. Users responded better to "Hey, I'm Sandra!" than "Welcome to the reservation system."

### 2. List Out Tasks Explicitly

I learned that LLMs work better when you spell things out:

```
Your main tasks:
- Help users search for restaurants
- Recommend restaurants based on mood, occasion, or vibe
- Check availability
- Create, modify, and cancel reservations
- Look up existing reservations by phone
```

This seems obvious in hindsight, but it really helped Sandra stay on track.

### 3. The Decision Tree That Changed Everything

My biggest breakthrough was creating clear routing rules. The LLM needs to know *which tool to use when*:

```
SEMANTIC RECOMMENDATIONS (mood-based queries):
- If the user describes preferences using "soft" terms like:
  - Mood: romantic, cozy, lively, quiet, casual, upscale
  - Occasion: anniversary, birthday, date night, business meeting
  - Atmosphere: rooftop, outdoor, family-friendly, live music
- Then use the `semantic_recommend` tool

STRUCTURED SEARCH (filter-based queries):
- If the user gives strict filters like specific cuisine, date/time, party size
- Use `search_restaurants` tool
```

This routing logic was crucial. Without it, Sandra would randomly pick tools.

### 4. The Anti-Hallucination Rules

This is where I spent the most time. LLMs love to make things up. For a reservation system, that's a disaster.

My solution was aggressive negative instructions:

```
NEVER invent restaurant_ids.
- Only use restaurant_ids that:
  - Came from a previous tool result, or
  - Were explicitly provided by the user
- If you do not know the restaurant_id, ask the user to pick one from the list you just showed.
```

I also added:

```
When a user says they want to make a reservation but has not chosen a restaurant yet:
- DO NOT call any tools immediately
- First, ask for: date/time, party size, location, cuisine preference
```

The "DO NOT" and "NEVER" instructions are important. LLMs pay attention to strong negative language.

### 5. Output Format Matters

I noticed Sandra's responses were inconsistent. Sometimes she'd list restaurants nicely, sometimes it was a mess. I added explicit formatting:

```
After calling semantic_recommend, present the top 3-5 recommendations clearly:
- Restaurant name
- Area
- Cuisine
- Price per person
- The restaurant_id
- A short sentence explaining WHY it fits their mood
```

Now her responses are predictable and useful.

### 6. Error Handling (The Forgotten Step)

Early on, when a tool returned an error, Sandra would just dump the raw error message. Not a good user experience.

```
When a tool returns an error:
- Briefly explain the issue in natural language
- Guide the user with a specific next question or suggestion
- Do not repeat low-level technical error messages
```

This made failures feel like conversations, not crashes.

## The Two-Prompt Strategy

I actually use two prompts in the codebase:

**SYSTEM_PROMPT (in llm_client.py)**: The big one with all the rules. This sets up Sandra's behavior.

**Tool Descriptions (in tools.py)**: Each tool has a clear description that helps the LLM understand when to use it.

For example:
```python
{
    "name": "semantic_recommend",
    "description": "Recommend restaurants based on user mood, occasion, or vibe 
                    using semantic similarity. Use this when the user describes 
                    their preferences in terms of mood (romantic, casual, lively), 
                    occasion (anniversary, birthday), or atmosphere rather than 
                    strict filters."
}
```

The description is almost as important as the function itself.

## Things I Tried That Didn't Work

1. **Few-shot examples in the prompt**: Made the prompt too long, and the LLM would sometimes copy the examples verbatim instead of adapting.

2. **Strict JSON output formatting**: The LLM would get confused and output malformed JSON. Better to let it respond naturally and parse what we need.

3. **Temperature = 0**: Made Sandra sound robotic. 0.3 is the sweet spot - consistent but not boring.

4. **One giant prompt**: Breaking it into sections with clear headers (CONVERSATION FLOW, ANTI-HALLUCINATION, etc.) worked much better.

## Lessons Learned

1. **Be specific about what NOT to do** - LLMs respond well to "NEVER" and "DO NOT"

2. **Give clear routing logic** - "If X, then use tool Y" works better than "use the appropriate tool"

3. **Personality helps** - A named character feels more natural than a generic assistant

4. **Format your outputs** - Tell the LLM exactly how you want responses structured

5. **Test with weird inputs** - Users will say things like "tmrw 8ish for me and my gf" and your bot needs to handle it

6. **Iterate constantly** - My prompt went through probably 20+ versions before I was happy with it

## The Current Prompt Structure

```
┌─────────────────────────────────┐
│        PERSONA                  │  Who is Sandra?
├─────────────────────────────────┤
│        TASKS                    │  What can she do?
├─────────────────────────────────┤
│     DECISION ROUTING            │  Which tool when?
├─────────────────────────────────┤
│   ANTI-HALLUCINATION            │  What to never do
├─────────────────────────────────┤
│     OUTPUT FORMAT               │  How to respond
├─────────────────────────────────┤
│    ERROR HANDLING               │  What if things fail?
└─────────────────────────────────┘
```

## What's Next

I'm still tweaking things. Some ideas I want to try:
- Adding memory of user preferences across sessions
- Better date/time parsing (currently struggles with "next Saturday")
- Handling multiple languages (Hindi would be huge for Mumbai)

## Final Thoughts

Prompt engineering is less about finding magic words and more about thinking clearly about what you want the LLM to do. The clearer your instructions, the better the results.

If you're building something similar, start simple, test a lot, and don't be afraid to be very explicit. LLMs are smart but they're not mind readers.

---

*Built by Pranav as part of the Sandra Restaurant Assistant project.*
