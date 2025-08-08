# Faust

A brilliant AI math tutor that runs in your terminal. Faust adapts her explanations to your academic level and provides personalized mathematical guidance.

## Features

- **Adaptive Academic Levels**: Child, Normal, and Academic modes
- **Math Rendering**: LaTeX expressions displayed as Unicode in terminal
- **Persistent Sessions**: Continue conversations across sessions
- **Streaming AI Responses**: Real-time responses from Google Gemini
- **User Accounts**: Secure login with conversation history

## Installation

```bash
pip install git+https://github.com/S-entinel/faust-math.git
```

## Setup

1. Get a free Google Gemini API key at [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Set your API key:
   ```bash
   export GOOGLE_API_KEY="your_api_key_here"
   ```
3. Run Faust:
   ```bash
   faust
   ```

## Usage

```bash
# Basic commands
/help                    # Show all commands
/level set academic      # Set academic level
/new Calculus Help      # Start new session
/quit                   # Exit

# Just type math questions
You: How do I solve x² + 2x - 8 = 0?
Faust: Obviously, you use the quadratic formula...
```

## Academic Levels

- **Child**: Elementary/Middle school explanations
- **Normal**: High school level (default) 
- **Academic**: College/graduate level

## Requirements

- Python 3.8+
- Google Gemini API key (free tier available)

## License

MIT
