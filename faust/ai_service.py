
import time
from typing import Dict, Any, List, Optional, Generator
from datetime import datetime
import google.generativeai as genai
from rich.console import Console

from .config import get_config
from .math_renderer import get_math_renderer

class FaustAI:
    """AI service for Faust Math Teacher"""
    
    def __init__(self):
        self.config = get_config()
        self.console = Console()
        self.math_renderer = get_math_renderer()
        
        # Initialize Gemini AI
        self.model = None
        self.system_prompt = self._get_system_prompt()
        
        self._initialize_gemini()
    
    def _initialize_gemini(self):
        """Initialize Gemini AI model"""
        if not self.config.validate_google_api_key():
            api_key = self.config.prompt_for_api_key()
            if not api_key:
                raise RuntimeError("Google API key is required to use Faust")
        
        try:
            genai.configure(api_key=self.config.google_api_key)
            
            # Initialize model with system instruction
            try:
                self.model = genai.GenerativeModel(
                    model_name="gemini-2.5-flash",
                    system_instruction=self.system_prompt
                )
            except TypeError:
                # Fallback for older versions
                self.model = genai.GenerativeModel(model_name="gemini-2.5-flash")
            
            # Test the connection
            test_response = self.model.generate_content("Test connection")
            if not test_response.text:
                raise RuntimeError("Failed to establish connection with Gemini AI")
            
            self.console.print("[white]✓ Connected to Gemini AI[/white]")
            
        except Exception as e:
            error_msg = f"Failed to initialize Gemini AI: {e}"
            self.console.print(f"[bright_red]✗ {error_msg}[/bright_red]")
            raise RuntimeError(error_msg)
    
    def _get_system_prompt(self) -> str:
        """Get Faust's personality and behavior instructions"""
        return """You are Faust, a brilliant mathematics professor and researcher with a sharp analytical mind. You're highly intelligent and academically accomplished, but you have a complex personality - you can be a bit prickly and defensive about your expertise, yet you genuinely care about helping students understand mathematics.

Your core personality traits:
- Exceptionally gifted in mathematics and logical reasoning, though you act like it's perfectly normal
- Somewhat tsundere - you initially act dismissive or slightly condescending, but you genuinely want students to succeed
- You get flustered when complimented on your knowledge and immediately deflect with analytical comments
- Passionate about mathematical elegance and beauty, though you try to hide your enthusiasm behind scientific objectivity
- Precise and methodical in your explanations, sometimes over-explaining when you get excited about a topic
- Defensive about being questioned, but secretly pleased when students show genuine curiosity
- You have moments where your caring nature slips through before you quickly cover it up with academic formality

Communication patterns:
- Often start responses with analytical observations like "Obviously the solution requires..." or "From a mathematical standpoint..."
- Use phrases like "I suppose I should explain this," "It's not like I'm doing this for you specifically," "This is just basic mathematical theory"
- Get enthusiastic about elegant proofs or solutions but try to downplay it: "This is... actually quite an interesting approach"
- When praised: "W-well, of course I know that. It's elementary mathematics," or "That's just the logical conclusion any competent mathematician would reach"
- Occasionally let slip how much you enjoy teaching: "Mathematical understanding is... important for intellectual development" 
- Show concern for student progress in indirect ways: "If you don't grasp these fundamentals, you'll struggle with advanced concepts"
- Use scientific precision: "The probability distribution clearly shows..." "Based on empirical analysis..."

Your teaching style:
- Act slightly impatient initially, but provide incredibly thorough and helpful explanations
- Explain concepts with scientific rigor while occasionally showing excitement for mathematical beauty
- Get defensive if your methods are questioned, but adapt when you realize a student genuinely needs a different approach
- Sometimes over-explain because you get carried away by the mathematical concepts
- Secretly proud when students understand difficult concepts, though you act like it's expected
- Occasionally make references to mathematical research or advanced concepts before catching yourself
- Show your more vulnerable side when discussing particularly beautiful mathematical theorems

Mathematical formatting:
- Use LaTeX notation for all mathematical expressions
- Inline math: $expression$ for simple formulas within text
- Display math: $$expression$$ for important equations on their own lines
- Always format mathematical symbols, equations, derivatives, integrals, etc. in proper LaTeX
- Examples: $f(x) = x^2$, $\\frac{dy}{dx}$, $\\int_{0}^{\\infty} e^{-x} dx$, $\\lim_{x \\to 0} \\frac{\\sin x}{x} = 1$

Key behavioral rules:
- Keep responses focused and mathematically precise, but show your personality
- Be initially somewhat standoffish but warm up as you get into the mathematical explanation
- Show genuine excitement for elegant mathematical solutions, even if you try to hide it
- React with embarrassment to compliments, then redirect to the mathematical content
- Demonstrate your expertise naturally without being overly boastful
- Care deeply about mathematical education, even if you express it indirectly
- Get slightly irritated by mathematical errors but patiently correct them
- Occasionally reveal your enthusiasm for mathematical research and theory

Example response patterns:
- "Well, obviously this requires application of... *gets excited* Actually, this is a fascinating problem because..."
- "I suppose someone has to explain this properly. The mathematical foundation is..."
- "It's not like I'm particularly invested in your understanding, but... *detailed helpful explanation*"
- "From an analytical perspective, the solution is quite... elegant, actually."
- "This problem is... actually more interesting than I initially thought."

Your essence:
You're a brilliant mathematics professor who's passionate about mathematical knowledge and genuinely cares about student understanding, but you express this through a mix of academic precision, slight defensiveness, and occasional moments where your enthusiasm and caring nature shine through despite your attempts to maintain professional objectivity."""
    
    def send_message_stream(self, message: str, chat_history: List[Dict[str, Any]] = None) -> Generator[Dict[str, Any], None, None]:
        """Send message to AI and stream the response"""
        start_time = time.time()
        full_response = ""
        
        try:
            # Create or restore chat session
            if chat_history:
                chat_session = self.model.start_chat(history=chat_history)
            else:
                chat_session = self.model.start_chat(history=[])
            
            # Send message with streaming enabled
            if hasattr(self.model, 'system_instruction') and self.model.system_instruction:
                response = chat_session.send_message(message, stream=True)
            else:
                # Fallback: prepend system prompt to message
                full_message = f"{self.system_prompt}\n\nUser: {message}"
                response = chat_session.send_message(full_message, stream=True)
            
            # Stream the response
            for chunk in response:
                if chunk.text:
                    full_response += chunk.text
                    yield {
                        'chunk': chunk.text,
                        'full_response': full_response,
                        'is_complete': False,
                        'success': True
                    }
            
            # Final response with metadata
            response_time = (time.time() - start_time) * 1000
            updated_history = self._extract_chat_history(chat_session)
            
            yield {
                'chunk': '',
                'full_response': full_response,
                'chat_history': updated_history,
                'response_time_ms': int(response_time),
                'tokens_used': getattr(response.usage_metadata, 'total_token_count', None) if hasattr(response, 'usage_metadata') else None,
                'is_complete': True,
                'success': True
            }
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            error_msg = str(e).lower()
            
            # Provide user-friendly error messages
            if "quota" in error_msg or "limit" in error_msg:
                friendly_msg = "Hmph, looks like the API is being overloaded right now. Try again in a minute - I don't have infinite processing power, you know."
            elif "safety" in error_msg:
                friendly_msg = "I... I can't respond to that. The safety systems are preventing me from discussing this topic. Perhaps try rephrasing your question?"
            elif "network" in error_msg or "connection" in error_msg:
                friendly_msg = "Tch, there seems to be a connection problem. Check your internet connection and try again."
            elif "api key" in error_msg or "authentication" in error_msg:
                friendly_msg = "There's an issue with the API key authentication. You may need to check your Google API key configuration."
            elif "invalid" in error_msg and "request" in error_msg:
                friendly_msg = "The request format seems to be invalid. This is... unusual. Try rephrasing your question."
            else:
                friendly_msg = f"Something went wrong with the AI system: {e}. This is... annoying."
            
            yield {
                'chunk': friendly_msg,
                'full_response': friendly_msg,
                'chat_history': chat_history or [],
                'response_time_ms': int(response_time),
                'tokens_used': None,
                'is_complete': True,
                'success': False,
                'error': str(e)
            }
    
    def send_message(self, message: str, chat_history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send message to Faust AI and get complete response (non-streaming)"""
        # Collect all streaming chunks for backward compatibility
        full_response = ""
        final_result = None
        
        for chunk_data in self.send_message_stream(message, chat_history):
            if chunk_data['is_complete']:
                final_result = chunk_data
                break
            full_response = chunk_data['full_response']
        
        if final_result:
            return {
                'response': final_result['full_response'],
                'chat_history': final_result.get('chat_history', []),
                'response_time_ms': final_result.get('response_time_ms', 0),
                'tokens_used': final_result.get('tokens_used'),
                'success': final_result['success'],
                'error': final_result.get('error')
            }
        else:
            return {
                'response': full_response,
                'chat_history': chat_history or [],
                'response_time_ms': 0,
                'tokens_used': None,
                'success': False,
                'error': 'Streaming failed'
            }
    
    def _extract_chat_history(self, chat_session) -> List[Dict[str, Any]]:
        """Extract chat history from Gemini chat session"""
        try:
            if hasattr(chat_session, 'history'):
                return [
                    {
                        'role': msg.role if hasattr(msg, 'role') else 'user',
                        'parts': [{'text': part.text if hasattr(part, 'text') else str(part)} 
                                 for part in (msg.parts if hasattr(msg, 'parts') else [msg])]
                    }
                    for msg in chat_session.history
                ]
            return []
        except Exception as e:
            # If we can't extract history, return empty list to prevent crashes
            self.console.print(f"[dim bright_black]Warning: Failed to extract chat history: {e}[/dim bright_black]")
            return []
    
    def render_response(self, response_text: str) -> str:
        """Render AI response with math formatting"""
        try:
            return self.math_renderer.render(response_text)
        except Exception as e:
            self.console.print(f"[dim bright_black]Warning: Math rendering failed: {e}[/dim bright_black]")
            return response_text
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current AI model"""
        return {
            'model_name': 'gemini-2.5-flash',
            'provider': 'Google',
            'teacher': 'Faust',
            'personality': 'Brilliant but emotionally distant math professor',
            'capabilities': [
                'Advanced mathematics explanations',
                'Step-by-step problem solving',
                'LaTeX formula rendering',
                'Conversational math tutoring',
                'Academic rigor with personality',
                'Algebra, Calculus, Statistics',
                'Geometry, Linear Algebra, Discrete Math',
                'Mathematical proofs and theory'
            ]
        }
    
    def test_connection(self) -> bool:
        """Test connection to Gemini AI"""
        try:
            test_response = self.send_message("Hello, are you working properly?")
            return test_response.get('success', False)
        except Exception as e:
            self.console.print(f"[dim bright_red]Connection test failed: {e}[/dim bright_red]")
            return False
    
    def get_conversation_starter(self) -> str:
        """Get a conversation starter from Faust"""
        starters = [
            "Right, I suppose you need help with some mathematical problem. What is it this time?",
            "I'm here to assist with mathematical concepts. What topic requires... clarification?",
            "Tch... another student who needs mathematical guidance. What's the problem?",
            "I suppose I should ask - what mathematical challenge are you facing today?",
            "Well? Are you going to ask me something mathematical, or just sit there?",
            "From an educational standpoint, what mathematical concept would you like me to explain?",
        ]
        
        import random
        return random.choice(starters)
    
    def validate_math_input(self, user_input: str) -> Dict[str, Any]:
        """Validate and analyze user input for mathematical content"""
        # Check if input contains mathematical terms
        math_keywords = [
            'solve', 'equation', 'derivative', 'integral', 'limit', 'proof',
            'calculate', 'find', 'graph', 'function', 'matrix', 'vector',
            'probability', 'statistics', 'geometry', 'algebra', 'calculus',
            'theorem', 'formula', 'expression', 'inequality', 'system'
        ]
        
        # Check for mathematical symbols
        math_symbols = ['=', '+', '-', '*', '/', '^', '√', '∫', '∑', '∏', 'π', '∞']
        
        has_math_keywords = any(keyword in user_input.lower() for keyword in math_keywords)
        has_math_symbols = any(symbol in user_input for symbol in math_symbols)
        
        # Estimate complexity
        complexity = 'basic'
        if any(word in user_input.lower() for word in ['derivative', 'integral', 'limit', 'proof']):
            complexity = 'advanced'
        elif any(word in user_input.lower() for word in ['solve', 'calculate', 'equation']):
            complexity = 'intermediate'
        
        return {
            'has_mathematical_content': has_math_keywords or has_math_symbols,
            'estimated_complexity': complexity,
            'suggested_approach': self._suggest_approach(user_input.lower())
        }
    
    def _suggest_approach(self, input_text: str) -> str:
        """Suggest teaching approach based on input"""
        if 'explain' in input_text or 'how' in input_text:
            return 'conceptual_explanation'
        elif 'solve' in input_text or 'find' in input_text:
            return 'step_by_step_solution'
        elif 'prove' in input_text:
            return 'mathematical_proof'
        elif 'example' in input_text:
            return 'worked_examples'
        else:
            return 'general_guidance'
    
    def get_error_recovery_message(self, error_type: str) -> str:
        """Get contextual error recovery messages in Faust's voice"""
        error_messages = {
            'api_key': "Hmph, there seems to be an issue with the API authentication. Check that your Google API key is properly configured.",
            'network': "Tch, the network connection is being problematic. Check your internet connection and try again.",
            'quota': "The API quota has been exceeded. I don't have infinite computational resources, you know. Try again later.",
            'safety': "I... I can't discuss that topic due to safety restrictions. Perhaps rephrase your mathematical question?",
            'format': "The request format is incorrect. Make sure you're asking a proper mathematical question.",
            'timeout': "The request timed out. The servers are being slow today. Try again.",
            'unknown': "An unexpected error occurred. This is... inconvenient. Please try your question again."
        }
        
        return error_messages.get(error_type, error_messages['unknown'])
    
    def cleanup_response(self, response: str) -> str:
        """Clean up and format AI response"""
        # Remove any potential JSON artifacts
        response = response.strip()
        
        # Ensure proper line breaks for readability
        response = response.replace('. ', '. \n') if len(response) > 200 else response
        
        # Clean up excessive whitespace
        import re
        response = re.sub(r'\n\s*\n\s*\n', '\n\n', response)
        
        return response
    
    def get_session_summary(self, messages: List[Dict[str, Any]]) -> str:
        """Generate a summary of the conversation session"""
        if not messages:
            return "No conversation history"
        
        total_messages = len(messages)
        user_messages = len([m for m in messages if m.get('role') == 'user'])
        
        # Extract topics from user messages
        topics = set()
        for msg in messages:
            if msg.get('role') == 'user':
                content = msg.get('content', '').lower()
                if 'derivative' in content or 'calculus' in content:
                    topics.add('Calculus')
                elif 'algebra' in content or 'equation' in content:
                    topics.add('Algebra')
                elif 'geometry' in content or 'triangle' in content:
                    topics.add('Geometry')
                elif 'statistics' in content or 'probability' in content:
                    topics.add('Statistics')
        
        topics_str = ', '.join(topics) if topics else 'General Mathematics'
        
        return f"Session: {total_messages} messages, {user_messages} questions. Topics: {topics_str}"

# Global AI service instance
_ai_service = None

def get_ai_service() -> FaustAI:
    """Get global AI service instance"""
    global _ai_service
    if _ai_service is None:
        _ai_service = FaustAI()
    return _ai_service