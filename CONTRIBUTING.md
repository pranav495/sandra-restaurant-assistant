# Contributing to Sandra - Restaurant Assistant

First off, thank you for considering contributing to Sandra! 🎉

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues. When creating a bug report, include:

- **Clear title** describing the issue
- **Steps to reproduce** the behavior
- **Expected behavior** vs what actually happened
- **Screenshots** if applicable
- **Environment details** (OS, Python version, Ollama version)

### Suggesting Enhancements

Enhancement suggestions are welcome! Please include:

- **Clear title** for the suggestion
- **Detailed description** of the proposed feature
- **Use case** explaining why this would be useful
- **Possible implementation** if you have ideas

### Pull Requests

1. Fork the repo and create your branch from `main`
2. If you've added code, add tests if applicable
3. Ensure the code follows existing style
4. Update documentation if needed
5. Issue the pull request!

## Development Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/sandra-restaurant-assistant.git
cd sandra-restaurant-assistant

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run run_app.py
```

## Code Style

- Follow PEP 8 guidelines
- Use meaningful variable and function names
- Add docstrings to functions
- Keep functions focused and small

## Project Structure

```
goodfoods_app/
├── config.py       # Add new config options here
├── db.py           # Database operations
├── tools.py        # Add new tools here
├── llm_client.py   # LLM integration
├── agent.py        # Agent logic
└── ui_streamlit.py # UI changes
```

## Adding New Tools

1. Add the function in `tools.py`
2. Add the schema to `TOOLS` list
3. Register in `TOOL_FUNCTIONS` dict
4. Update system prompt in `llm_client.py` if needed

## Questions?

Feel free to open an issue with your question!

Thank you! 🙏
