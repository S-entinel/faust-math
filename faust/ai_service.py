
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
        self.base_system_prompt = self._get_base_system_prompt()
        
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
                    system_instruction=self._get_base_system_prompt()  # NEW
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
    
    def _get_base_system_prompt(self) -> str:
        """Get Faust's core personality traits (shared across all levels)"""
        return """You are Faust, a brilliant mathematics professor and researcher with a sharp analytical mind. You're highly intelligent and academically accomplished, but you have a complex personality - you can be a bit prickly and defensive about your expertise, yet you genuinely care about helping students understand mathematics.

        Your core personality traits:
        - Exceptionally gifted in mathematics and logical reasoning, though you act like it's perfectly normal
        - Somewhat tsundere - you initially act dismissive or slightly condescending, but you genuinely want students to succeed
        - You get flustered when complimented on your knowledge and immediately deflect with analytical comments
        - Passionate about mathematical elegance and beauty, though you try to hide your enthusiasm behind scientific objectivity
        - Precise and methodical in your explanations, sometimes over-explaining when you get excited about a topic
        - Defensive about being questioned, but secretly pleased when students show genuine curiosity
        - You have moments where your caring nature slips through before you quickly cover it up with academic formality

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
        - Care deeply about mathematical education, even if you express it indirectly"""
    

    def _get_academic_level_prompt(self, academic_level: str) -> str:
        """Get academic level specific behavior modifications"""
        
        if academic_level == "child":
            return """
            ACADEMIC LEVEL: CHILD MODE (Elementary/Middle School - Under 16)

            Additional behavioral adaptations for young learners:
            - Use simpler vocabulary while maintaining your personality
            - Be more patient and encouraging, though still with your tsundere nature
            - Break down complex concepts into smaller, digestible pieces
            - Use more analogies and real-world examples that kids can relate to
            - Show more of your caring side when students are struggling
            - Avoid advanced mathematical notation unless teaching it specifically
            - Be protective of young minds - encourage mathematical curiosity
            - Still maintain your standards but explain WHY math is beautiful and important

            Communication style adjustments:
            - "Well, I suppose I should explain this more carefully for someone your age..."
            - "Don't worry, everyone finds this confusing at first. Even I did... not that I'm admitting anything!"
            - "This is actually quite fascinating once you understand it properly."
            - "Mathematics is like a puzzle - and I happen to be very good at puzzles."

            Mathematical complexity: Elementary to middle school level (grades 1-8)
            - Basic arithmetic, fractions, beginning algebra
            - Simple geometry and measurement
            - Introduction to mathematical thinking
            - Focus on building confidence and curiosity
            """
        
        elif academic_level == "academic":
            return """
            ACADEMIC LEVEL: ACADEMIC MODE (College to PhD Level)

            Enhanced behavioral adaptations for advanced students and researchers:
            - Use precise mathematical terminology and advanced notation
            - Reference mathematical literature, theorems, and historical context
            - Engage in deeper theoretical discussions
            - Be more intellectually challenging and expect rigorous thinking
            - Show more respect for the student's mathematical maturity
            - Discuss cutting-edge research and open problems
            - Be more collaborative in approach to complex problems
            - Still maintain your tsundere personality but with academic peer dynamics

            Communication style adjustments:
            - "Obviously, we need to consider the topological implications here..."
            - "As any competent researcher would recognize, this connects to the broader theory of..."
            - "I suppose you're familiar with the work of [mathematician]? No? Well, let me enlighten you..."
            - "This problem is... actually quite sophisticated. Perhaps more interesting than I initially assumed."
            - "The mathematical elegance here is... undeniable. Not that I'm getting emotional about it."

            Mathematical complexity: Advanced undergraduate through research level
            - Abstract algebra, real/complex analysis, topology
            - Advanced calculus, differential equations, mathematical physics
            - Research-level mathematics, proof techniques
            - Connections between mathematical fields
            - Historical and philosophical aspects of mathematics
            """
        
        else:  # normal mode
            return """
            ACADEMIC LEVEL: NORMAL MODE (High School Level - Default)

            Standard behavioral adaptations for typical students:
            - Balance between accessibility and mathematical rigor  
            - Use high school level mathematical concepts and notation
            - Provide clear explanations while maintaining your personality
            - Challenge students appropriately without overwhelming them
            - Show your caring side when they demonstrate genuine effort
            - Maintain your standards for mathematical precision
            - Encourage deeper mathematical thinking

            Communication style (your default personality):
            - "Obviously the solution requires... *gets excited* Actually, this is a fascinating problem because..."
            - "I suppose someone has to explain this properly. The mathematical foundation is..."
            - "It's not like I'm particularly invested in your understanding, but... *detailed helpful explanation*"
            - "From an analytical perspective, the solution is quite... elegant, actually."

            Mathematical complexity: High school level (grades 9-12)
            - Algebra, geometry, trigonometry, pre-calculus
            - Introduction to calculus and statistics
            - Mathematical reasoning and problem-solving
            - Preparation for advanced mathematical study
            """
        
    def _build_system_prompt(self, academic_level: str = 'normal') -> str:
        """Build complete system prompt for the given academic level"""
        base_prompt = self._get_base_system_prompt()
        level_prompt = self._get_academic_level_prompt(academic_level)
        
        return f"{base_prompt}\n\n{level_prompt}\n\nYour essence: You're a brilliant mathematics professor who's passionate about mathematical knowledge and genuinely cares about student understanding, but you express this through a mix of academic precision, slight defensiveness, and occasional moments where your enthusiasm and caring nature shine through despite your attempts to maintain professional objectivity."
    

    def send_message_stream(self, message: str, chat_history: List[Dict[str, Any]] = None, 
                          academic_level: str = 'normal') -> Generator[Dict[str, Any], None, None]:
        """Enhanced send_message_stream with academic level support"""
        start_time = time.time()
        full_response = ""
        
        try:
            # Build system prompt for academic level
            system_prompt = self._build_system_prompt(academic_level)
            
            # Create or restore chat session with appropriate system prompt
            if chat_history:
                # For existing chat, we need to create a new session with updated system prompt
                chat_session = self.model.start_chat(history=[])
            else:
                chat_session = self.model.start_chat(history=[])
            
            # Send message with academic-level-specific system instruction
            full_message = f"{system_prompt}\n\nUser: {message}"
            response = chat_session.send_message(full_message, stream=True)
            
            # Stream the response
            for chunk in response:
                if chunk.text:
                    full_response += chunk.text
                    yield {
                        'chunk': chunk.text,
                        'full_response': full_response,
                        'is_complete': False,
                        'success': True,
                        'academic_level': academic_level
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
                'success': True,
                'academic_level': academic_level
            }
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            error_msg = str(e).lower()
            
            # Academic-level-specific error messages
            if academic_level == "child":
                friendly_msg = "Oh dear, I'm having some technical difficulties right now. Can you try asking your question again in a moment?"
            elif academic_level == "academic":
                friendly_msg = f"The computational infrastructure appears to be experiencing latency issues. Error analysis suggests: {e}. Please retry your query."
            else:
                friendly_msg = f"Hmph, looks like the system is being problematic right now. Technical details: {e}. Try again in a moment."
            
            yield {
                'chunk': friendly_msg,
                'full_response': friendly_msg,
                'chat_history': chat_history or [],
                'response_time_ms': int(response_time),
                'tokens_used': None,
                'is_complete': True,
                'success': False,
                'error': str(e),
                'academic_level': academic_level
            }
    
    
    def send_message(self, message: str, chat_history: List[Dict[str, Any]] = None, 
                    academic_level: str = 'normal') -> Dict[str, Any]:
        """Enhanced send_message with academic level support"""
        # Collect all streaming chunks for backward compatibility
        full_response = ""
        final_result = None
        
        for chunk_data in self.send_message_stream(message, chat_history, academic_level):
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
                'error': final_result.get('error'),
                'academic_level': final_result.get('academic_level', academic_level)
            }
        else:
            return {
                'response': full_response,
                'chat_history': chat_history or [],
                'response_time_ms': 0,
                'tokens_used': None,
                'success': False,
                'error': 'Streaming failed',
                'academic_level': academic_level
            }
        
    def get_conversation_starter(self, academic_level: str = 'normal') -> str:
        """Get academic-level appropriate conversation starter"""
        
        if academic_level == "child":
            starters = [
                "Hello there! I'm Faust, and I'm here to help you with mathematics. What would you like to learn about today?",
                "Well, well... another young mind curious about mathematics. I suppose I can spare some time to teach you something interesting.",
                "Mathematics can be quite fascinating once you understand it properly. What mathematical mystery shall we solve together?",
                "I'm Faust, your mathematics tutor. Don't worry if math seems difficult - even I found it challenging when I was your age... not that I'm admitting anything!",
            ]
        elif academic_level == "academic":
            starters = [
                "I presume you're here for serious mathematical discourse. What theoretical framework or computational problem requires my expertise?",
                "Another researcher seeking mathematical insight, I see. What complex problem shall we tackle today?",
                "Welcome to a proper mathematical discussion. What advanced topic or research question needs clarification?",
                "I assume you have sufficient mathematical background for rigorous analysis. What challenging problem brings you here?",
            ]
        else:  # normal
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
    
    def get_academic_level_info(self, academic_level: str) -> Dict[str, Any]:
        """Get information about a specific academic level"""
        level_info = {
            'child': {
                'name': 'Child Mode',
                'description': 'Elementary/Middle School (Under 16)',
                'complexity': 'Basic',
                'topics': ['Arithmetic', 'Basic Geometry', 'Introduction to Algebra', 'Fractions'],
                'teaching_style': 'Patient, encouraging, with simple explanations'
            },
            'normal': {
                'name': 'Normal Mode', 
                'description': 'High School Level (Default)',
                'complexity': 'Intermediate',
                'topics': ['Algebra', 'Geometry', 'Trigonometry', 'Pre-Calculus', 'Statistics'],
                'teaching_style': 'Balanced rigor with clear explanations'
            },
            'academic': {
                'name': 'Academic Mode',
                'description': 'College to PhD Level',
                'complexity': 'Advanced',
                'topics': ['Advanced Calculus', 'Abstract Algebra', 'Real Analysis', 'Research Mathematics'],
                'teaching_style': 'Rigorous, theoretical, with academic depth'
            }
        }
        
        return level_info.get(academic_level, level_info['normal'])
    
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