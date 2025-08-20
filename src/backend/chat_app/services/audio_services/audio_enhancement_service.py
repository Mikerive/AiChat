"""
Audio Enhancement Service

Provides audio preprocessing and enhancement capabilities for improving
audio quality before VAD and transcription processing.
"""

import asyncio
import logging
import numpy as np
from typing import Optional, Dict, Any
from pathlib import Path

try:
    import scipy.signal
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    scipy = None

logger = logging.getLogger(__name__)


class AudioEnhancementService:
    """Service for audio preprocessing and enhancement"""
    
    def __init__(self):
        self.sample_rate = 16000
        self.enabled = True
        
        # Simple noise gate parameters
        self.noise_gate_threshold = -50.0  # dB
        self.noise_gate_ratio = 0.1
        
        logger.info("Audio Enhancement Service initialized")
    
    async def enhance_audio(self, audio_data: bytes, sample_rate: int = None) -> bytes:
        """Enhance audio data (placeholder implementation)"""
        try:
            if not self.enabled:
                return audio_data
            
            # Convert to numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            
            if len(audio_array) == 0:
                return audio_data
            
            # Simple noise gate
            audio_array = self._apply_noise_gate(audio_array)
            
            # Normalize
            audio_array = self._normalize_audio(audio_array)
            
            return audio_array.tobytes()
            
        except Exception as e:
            logger.debug(f"Error enhancing audio: {e}")
            return audio_data  # Return original on error
    
    def _apply_noise_gate(self, audio_array: np.ndarray) -> np.ndarray:
        """Apply simple noise gate"""
        try:
            # Calculate RMS level
            rms = np.sqrt(np.mean(audio_array.astype(np.float64) ** 2))
            if rms > 0:
                db_level = 20 * np.log10(rms / 32768.0)
                
                # Apply gate
                if db_level < self.noise_gate_threshold:
                    return (audio_array * self.noise_gate_ratio).astype(np.int16)
            
            return audio_array
            
        except Exception as e:
            logger.debug(f"Error applying noise gate: {e}")
            return audio_array
    
    def _normalize_audio(self, audio_array: np.ndarray) -> np.ndarray:
        """Normalize audio levels"""
        try:
            # Simple normalization to prevent clipping
            max_val = np.max(np.abs(audio_array))
            if max_val > 0:
                scale_factor = min(1.0, 32767.0 / max_val)
                return (audio_array * scale_factor).astype(np.int16)
            
            return audio_array
            
        except Exception as e:
            logger.debug(f"Error normalizing audio: {e}")
            return audio_array
    
    def set_enabled(self, enabled: bool):
        """Enable or disable audio enhancement"""
        self.enabled = enabled
        logger.info(f"Audio enhancement {'enabled' if enabled else 'disabled'}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get enhancement service statistics"""
        return {
            "enabled": self.enabled,
            "scipy_available": SCIPY_AVAILABLE,
            "noise_gate_threshold": self.noise_gate_threshold
        }