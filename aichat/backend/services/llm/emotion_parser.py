"""
Intensity parsing utilities for LLM-first intensity streaming
Parses intensity markers from LLM output for Chatterbox TTS exaggeration control
"""

import re
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class IntensityParser:
    """Parse intensity markers from LLM streaming output for Chatterbox TTS"""
    
    def __init__(self):
        # Regex patterns for intensity detection
        self.intensity_patterns = [
            r'\[INTENSITY:\s*(\w+)\]',         # [INTENSITY: high]
            r'\[(\w+)\]',                      # [high]
            r'<intensity>(\w+)</intensity>',   # <intensity>high</intensity>
            r'intensity:\s*(\w+)',             # intensity: high
        ]
        
        # Valid intensity levels mapping to Chatterbox exaggeration (0.0-2.0)
        self.intensity_mapping = {
            'flat': 0.0,       # Completely monotone
            'low': 0.3,        # Subdued, minimal expression
            'minimal': 0.4,    # Very slight expression
            'neutral': 0.5,    # Balanced, natural baseline
            'normal': 0.7,     # Default Chatterbox setting
            'moderate': 0.9,   # Slightly more expressive
            'high': 1.2,       # Noticeably expressive
            'dramatic': 1.5,   # Clearly dramatic
            'extreme': 1.8,    # Highly theatrical
            'theatrical': 2.0, # Maximum exaggeration
        }
        
        # Intensity aliases for robustness
        self.intensity_aliases = {
            'none': 'flat',
            'zero': 'flat',
            'monotone': 'flat',
            'robotic': 'flat',
            'quiet': 'low',
            'subdued': 'low',
            'calm': 'minimal',
            'mild': 'minimal',
            'balanced': 'neutral',
            'natural': 'normal',
            'default': 'normal',
            'standard': 'normal',
            'medium': 'moderate',
            'strong': 'high',
            'intense': 'dramatic',
            'very': 'dramatic',
            'maximum': 'extreme',
            'max': 'extreme',
            'over': 'theatrical',
            'overboard': 'theatrical'
        }
    
    def extract_intensity_from_chunk(self, text_chunk: str) -> Optional[float]:
        """
        Extract intensity from a text chunk (typically the first LLM output chunk)
        
        Args:
            text_chunk: Text chunk from LLM streaming output
            
        Returns:
            Exaggeration value (0.0-2.0) if found, None otherwise
        """
        if not text_chunk:
            return None
            
        text_lower = text_chunk.lower().strip()
        
        # Try each pattern
        for pattern in self.intensity_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                intensity = match.group(1).lower().strip()
                
                # Validate and normalize intensity
                exaggeration_value = self._normalize_intensity(intensity)
                if exaggeration_value is not None:
                    logger.debug(f"Extracted intensity '{intensity}' -> {exaggeration_value:.2f} from chunk: {text_chunk[:50]}...")
                    return exaggeration_value
        
        return None
    
    def _normalize_intensity(self, intensity: str) -> Optional[float]:
        """
        Normalize intensity to valid Chatterbox exaggeration value
        
        Args:
            intensity: Raw intensity string
            
        Returns:
            Exaggeration value (0.0-2.0) or None if invalid
        """
        intensity = intensity.lower().strip()
        
        # Direct match
        if intensity in self.intensity_mapping:
            return self.intensity_mapping[intensity]
            
        # Alias match
        if intensity in self.intensity_aliases:
            normalized = self.intensity_aliases[intensity]
            return self.intensity_mapping[normalized]
            
        # Try numeric parsing (0.0-2.0)
        try:
            numeric_value = float(intensity)
            if 0.0 <= numeric_value <= 2.0:
                return numeric_value
        except ValueError:
            pass
            
        # Partial match (fuzzy matching for typos)
        for valid_intensity in self.intensity_mapping.keys():
            if intensity in valid_intensity or valid_intensity in intensity:
                return self.intensity_mapping[valid_intensity]
                
        logger.warning(f"Unknown intensity '{intensity}', falling back to normal (0.7)")
        return 0.7  # Default Chatterbox exaggeration
    
    def strip_intensity_marker(self, text: str) -> str:
        """
        Remove intensity markers from text to get clean content
        
        Args:
            text: Text with potential intensity markers
            
        Returns:
            Clean text without intensity markers
        """
        if not text:
            return text
            
        # Remove all intensity patterns
        cleaned_text = text
        for pattern in self.intensity_patterns:
            cleaned_text = re.sub(pattern, '', cleaned_text, flags=re.IGNORECASE)
            
        return cleaned_text.strip()
    
    def parse_intensity_and_text(self, full_text: str) -> Tuple[Optional[float], str]:
        """
        Parse both intensity and clean text from full LLM output
        
        Args:
            full_text: Complete LLM output text
            
        Returns:
            Tuple of (exaggeration_value, clean_text)
        """
        intensity = self.extract_intensity_from_chunk(full_text)
        clean_text = self.strip_intensity_marker(full_text)
        
        return intensity, clean_text


# Global parser instance
_intensity_parser = IntensityParser()

def extract_intensity(text_chunk: str) -> Optional[float]:
    """Convenience function to extract intensity from text chunk"""
    return _intensity_parser.extract_intensity_from_chunk(text_chunk)

def strip_intensity_markers(text: str) -> str:
    """Convenience function to remove intensity markers from text"""
    return _intensity_parser.strip_intensity_marker(text)

def parse_intensity_and_text(text: str) -> Tuple[Optional[float], str]:
    """Convenience function to parse intensity and clean text"""
    return _intensity_parser.parse_intensity_and_text(text)