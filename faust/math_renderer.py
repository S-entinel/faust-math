
import re
from typing import Dict, Tuple, List

class MathRenderer:
    """Convert LaTeX math expressions to Unicode for terminal display"""
    
    def __init__(self):
        # Unicode character mappings
        self.greek_letters = {
            'alpha': 'α', 'beta': 'β', 'gamma': 'γ', 'delta': 'δ', 'epsilon': 'ε',
            'zeta': 'ζ', 'eta': 'η', 'theta': 'θ', 'iota': 'ι', 'kappa': 'κ',
            'lambda': 'λ', 'mu': 'μ', 'nu': 'ν', 'xi': 'ξ', 'pi': 'π',
            'rho': 'ρ', 'sigma': 'σ', 'tau': 'τ', 'upsilon': 'υ', 'phi': 'φ',
            'chi': 'χ', 'psi': 'ψ', 'omega': 'ω',
            'Alpha': 'Α', 'Beta': 'Β', 'Gamma': 'Γ', 'Delta': 'Δ', 'Epsilon': 'Ε',
            'Zeta': 'Ζ', 'Eta': 'Η', 'Theta': 'Θ', 'Iota': 'Ι', 'Kappa': 'Κ',
            'Lambda': 'Λ', 'Mu': 'Μ', 'Nu': 'Ν', 'Xi': 'Ξ', 'Pi': 'Π',
            'Rho': 'Ρ', 'Sigma': 'Σ', 'Tau': 'Τ', 'Upsilon': 'Υ', 'Phi': 'Φ',
            'Chi': 'Χ', 'Psi': 'Ψ', 'Omega': 'Ω'
        }
        
        self.operators = {
            'pm': '±', 'mp': '∓', 'times': '×', 'div': '÷', 'cdot': '·',
            'neq': '≠', 'leq': '≤', 'geq': '≥', 'll': '≪', 'gg': '≫',
            'approx': '≈', 'equiv': '≡', 'propto': '∝', 'sim': '∼',
            'simeq': '≃', 'cong': '≅', 'not': '¬', 'neg': '¬',
            'partial': '∂', 'nabla': '∇', 'infty': '∞',
            'int': '∫', 'iint': '∬', 'iiint': '∭', 'oint': '∮',
            'sum': '∑', 'prod': '∏', 'coprod': '∐',
            'sqrt': '√', 'cbrt': '∛', 'fourthroot': '∜',
            'angle': '∠', 'measuredangle': '∡', 'sphericalangle': '∢',
            'perp': '⊥', 'parallel': '∥', 'nparallel': '∦',
            'in': '∈', 'notin': '∉', 'ni': '∋', 'notni': '∌',
            'subset': '⊂', 'supset': '⊃', 'subseteq': '⊆', 'supseteq': '⊇',
            'subsetneq': '⊊', 'supsetneq': '⊋', 'cup': '∪', 'cap': '∩',
            'setminus': '∖', 'emptyset': '∅', 'varnothing': '∅',
            'forall': '∀', 'exists': '∃', 'nexists': '∄',
            'therefore': '∴', 'because': '∵',
            'wedge': '∧', 'vee': '∨', 'oplus': '⊕', 'ominus': '⊖',
            'otimes': '⊗', 'oslash': '⊘', 'odot': '⊙',
            'to': '→', 'rightarrow': '→', 'leftarrow': '←',
            'leftrightarrow': '↔', 'uparrow': '↑', 'downarrow': '↓',
            'Rightarrow': '⇒', 'Leftarrow': '⇐', 'Leftrightarrow': '⇔',
            'mapsto': '↦', 'longmapsto': '⟼',
            'deg': '°', 'prime': '′', 'dprime': '″', 'tprime': '‴'
        }
        
        self.sets = {
            'mathbb{N}': 'ℕ', 'mathbb{Z}': 'ℤ', 'mathbb{Q}': 'ℚ',
            'mathbb{R}': 'ℝ', 'mathbb{C}': 'ℂ', 'mathbb{H}': 'ℍ',
            'mathbb{P}': 'ℙ', 'mathbb{E}': 'ℝ'
        }
        
        # Superscript and subscript mappings
        self.superscripts = {
            '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴', '5': '⁵',
            '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹', '+': '⁺', '-': '⁻',
            '=': '⁼', '(': '⁽', ')': '⁾', 'n': 'ⁿ', 'i': 'ⁱ', 'x': 'ˣ'
        }
        
        self.subscripts = {
            '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄', '5': '₅',
            '6': '₆', '7': '₇', '8': '₈', '9': '₉', '+': '₊', '-': '₋',
            '=': '₌', '(': '₍', ')': '₎', 'a': 'ₐ', 'e': 'ₑ', 'h': 'ₕ',
            'i': 'ᵢ', 'j': 'ⱼ', 'k': 'ₖ', 'l': 'ₗ', 'm': 'ₘ', 'n': 'ₙ',
            'o': 'ₒ', 'p': 'ₚ', 'r': 'ᵣ', 's': 'ₛ', 't': 'ₜ', 'u': 'ᵤ',
            'v': 'ᵥ', 'x': 'ₓ'
        }
    
    def render(self, text: str) -> str:
        """Convert LaTeX math expressions to Unicode"""
        if not text:
            return text
        
        # Handle inline math: $...$
        text = re.sub(r'\$([^$]+)\$', lambda m: self._convert_math(m.group(1)), text)
        
        # Handle display math: $$...$$
        text = re.sub(r'\$\$([^$]+)\$\$', lambda m: '\n' + self._convert_math(m.group(1)) + '\n', text)
        
        # Handle LaTeX math environments
        text = re.sub(r'\\begin\{equation\}(.*?)\\end\{equation\}', 
                     lambda m: '\n' + self._convert_math(m.group(1)) + '\n', text, flags=re.DOTALL)
        
        return text
    
    def _convert_math(self, math_expr: str) -> str:
        """Convert a single math expression"""
        # Remove extra whitespace
        expr = math_expr.strip()
        
        # Convert fractions
        expr = self._convert_fractions(expr)
        
        # Convert superscripts and subscripts
        expr = self._convert_scripts(expr)
        
        # Convert Greek letters
        expr = self._convert_greek(expr)
        
        # Convert operators
        expr = self._convert_operators(expr)
        
        # Convert number sets
        expr = self._convert_sets(expr)
        
        # Convert roots
        expr = self._convert_roots(expr)
        
        # Convert limits
        expr = self._convert_limits(expr)
        
        # Clean up remaining LaTeX commands
        expr = self._cleanup_latex(expr)
        
        return expr
    
    def _convert_fractions(self, expr: str) -> str:
        """Convert \\frac{num}{den} to num/den or Unicode fraction if simple"""
        def replace_frac(match):
            num = match.group(1)
            den = match.group(2)
            
            # Simple fraction mappings
            fraction_map = {
                ('1', '2'): '½', ('1', '3'): '⅓', ('2', '3'): '⅔',
                ('1', '4'): '¼', ('3', '4'): '¾', ('1', '5'): '⅕',
                ('2', '5'): '⅖', ('3', '5'): '⅗', ('4', '5'): '⅘',
                ('1', '6'): '⅙', ('5', '6'): '⅚', ('1', '7'): '⅐',
                ('1', '8'): '⅛', ('3', '8'): '⅜', ('5', '8'): '⅝',
                ('7', '8'): '⅞', ('1', '9'): '⅑', ('1', '10'): '⅒'
            }
            
            if (num, den) in fraction_map:
                return fraction_map[(num, den)]
            else:
                return f"({num})/({den})"
        
        return re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', replace_frac, expr)
    
    def _convert_scripts(self, expr: str) -> str:
        """Convert superscripts and subscripts"""
        # Superscripts: ^{...} or ^single_char
        def replace_super(match):
            content = match.group(1) or match.group(2)
            return ''.join(self.superscripts.get(c, c) for c in content)
        
        expr = re.sub(r'\^\{([^}]+)\}|\^(.)', replace_super, expr)
        
        # Subscripts: _{...} or _single_char
        def replace_sub(match):
            content = match.group(1) or match.group(2)
            return ''.join(self.subscripts.get(c, c) for c in content)
        
        expr = re.sub(r'_\{([^}]+)\}|_(.)', replace_sub, expr)
        
        return expr
    
    def _convert_greek(self, expr: str) -> str:
        """Convert Greek letters"""
        for latex, unicode_char in self.greek_letters.items():
            expr = expr.replace(f'\\{latex}', unicode_char)
        
        return expr
    
    def _convert_operators(self, expr: str) -> str:
        """Convert mathematical operators"""
        for latex, unicode_char in self.operators.items():
            expr = expr.replace(f'\\{latex}', unicode_char)
        
        return expr
    
    def _convert_sets(self, expr: str) -> str:
        """Convert number sets"""
        for latex, unicode_char in self.sets.items():
            expr = expr.replace(f'\\{latex}', unicode_char)
        
        return expr
    
    def _convert_roots(self, expr: str) -> str:
        """Convert roots"""
        # Square root: \\sqrt{...}
        expr = re.sub(r'\\sqrt\{([^}]+)\}', r'√(\1)', expr)
        
        # Nth root: \\sqrt[n]{...}
        def replace_nroot(match):
            n = match.group(1)
            content = match.group(2)
            root_symbols = {'3': '∛', '4': '∜'}
            if n in root_symbols:
                return f"{root_symbols[n]}({content})"
            else:
                return f"ⁿ√({content})"  # Fallback for other roots
        
        expr = re.sub(r'\\sqrt\[([^]]+)\]\{([^}]+)\}', replace_nroot, expr)
        
        return expr
    
    def _convert_limits(self, expr: str) -> str:
        """Convert limits"""
        # \\lim_{x \\to a} -> lim[x→a]
        def replace_limit(match):
            var_to_val = match.group(1)
            var_to_val = var_to_val.replace('\\to', '→')
            return f"lim[{var_to_val}]"
        
        expr = re.sub(r'\\lim_\{([^}]+)\}', replace_limit, expr)
        
        # Handle other limit-like expressions
        expr = re.sub(r'\\max_\{([^}]+)\}', r'max[\1]', expr)
        expr = re.sub(r'\\min_\{([^}]+)\}', r'min[\1]', expr)
        expr = re.sub(r'\\sup_\{([^}]+)\}', r'sup[\1]', expr)
        expr = re.sub(r'\\inf_\{([^}]+)\}', r'inf[\1]', expr)
        
        return expr
    
    def _cleanup_latex(self, expr: str) -> str:
        """Clean up remaining LaTeX commands"""
        # Remove common LaTeX commands that don't have Unicode equivalents
        cleanup_patterns = [
            (r'\\left\(', '('),
            (r'\\right\)', ')'),
            (r'\\left\[', '['),
            (r'\\right\]', ']'),
            (r'\\left\{', '{'),
            (r'\\right\}', '}'),
            (r'\\left\|', '|'),
            (r'\\right\|', '|'),
            (r'\\text\{([^}]+)\}', r'\1'),
            (r'\\mathrm\{([^}]+)\}', r'\1'),
            (r'\\mathit\{([^}]+)\}', r'\1'),
            (r'\\mathbf\{([^}]+)\}', r'\1'),
            (r'\\,', ' '),  # Small space
            (r'\\;', '  '), # Medium space
            (r'\\quad', '    '), # Quad space
            (r'\\qquad', '        '), # Double quad space
        ]
        
        for pattern, replacement in cleanup_patterns:
            expr = re.sub(pattern, replacement, expr)
        
        # Remove any remaining backslashes that might be LaTeX artifacts
        expr = re.sub(r'\\([a-zA-Z]+)', r'\1', expr)
        
        return expr
    
    def format_equation(self, equation: str, title: str = None) -> str:
        """Format an equation with optional title for display"""
        rendered = self.render(equation)
        
        if title:
            return f"\n[bold cyan]{title}:[/bold cyan]\n{rendered}\n"
        else:
            return f"\n{rendered}\n"
    
    def format_step_by_step(self, steps: List[Tuple[str, str]]) -> str:
        """Format step-by-step solution"""
        result = "\n[bold cyan]Step-by-step solution:[/bold cyan]\n"
        
        for i, (description, equation) in enumerate(steps, 1):
            result += f"\n[dim]Step {i}:[/dim] {description}\n"
            result += f"{self.render(equation)}\n"
        
        return result

# Global renderer instance
_renderer = None

def get_math_renderer() -> MathRenderer:
    """Get global math renderer instance"""
    global _renderer
    if _renderer is None:
        _renderer = MathRenderer()
    return _renderer