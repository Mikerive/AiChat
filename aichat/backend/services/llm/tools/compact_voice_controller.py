"""
Compact Voice Parameter Controller
Efficient emotion-to-voice mapping with N-dimensional emotion space
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class EmotionDimension(Enum):
    """N-dimensional emotion space dimensions"""
    VALENCE = "valence"          # Positive (1.0) to Negative (-1.0)
    AROUSAL = "arousal"          # High Energy (1.0) to Low Energy (-1.0)
    DOMINANCE = "dominance"      # Confident (1.0) to Submissive (-1.0)
    INTENSITY = "intensity"      # Strong (1.0) to Mild (-1.0)


@dataclass
class EmotionVector:
    """N-dimensional emotion representation"""
    valence: float      # -1.0 (negative) to 1.0 (positive)
    arousal: float      # -1.0 (low energy) to 1.0 (high energy)
    dominance: float    # -1.0 (submissive) to 1.0 (dominant)
    intensity: float    # -1.0 (mild) to 1.0 (intense)
    
    def to_array(self) -> np.ndarray:
        """Convert to numpy array for calculations"""
        return np.array([self.valence, self.arousal, self.dominance, self.intensity])
    
    @classmethod
    def from_array(cls, arr: np.ndarray) -> 'EmotionVector':
        """Create from numpy array"""
        return cls(valence=arr[0], arousal=arr[1], dominance=arr[2], intensity=arr[3])


@dataclass
class VoiceMapping:
    """Compact voice parameter mapping"""
    speed_base: float = 1.0
    speed_valence_factor: float = 0.1    # Positive emotions slightly faster
    speed_arousal_factor: float = 0.2    # High arousal = faster speech
    speed_intensity_factor: float = 0.05  # Intensity affects speed
    
    pitch_base: float = 1.0
    pitch_valence_factor: float = 0.08   # Positive emotions slightly higher pitch
    pitch_arousal_factor: float = 0.1    # High arousal = higher pitch
    pitch_dominance_factor: float = 0.05  # Confidence affects pitch
    
    # Constraints
    speed_min: float = 0.7
    speed_max: float = 1.3
    pitch_min: float = 0.8
    pitch_max: float = 1.2


class CompactVoiceController:
    """
    Efficient voice parameter controller using N-dimensional emotion space.
    Maps emotions to voice parameters through mathematical functions rather than lookup tables.
    """
    
    def __init__(self):
        # N-dimensional emotion space mapping (more accurate than discrete categories)
        self.emotion_vectors = {
            # Positive emotions
            "happy": EmotionVector(valence=0.8, arousal=0.6, dominance=0.3, intensity=0.7),
            "excited": EmotionVector(valence=0.9, arousal=0.9, dominance=0.5, intensity=0.8),
            "joyful": EmotionVector(valence=0.9, arousal=0.5, dominance=0.4, intensity=0.8),
            "enthusiastic": EmotionVector(valence=0.8, arousal=0.8, dominance=0.6, intensity=0.9),
            "elated": EmotionVector(valence=1.0, arousal=0.7, dominance=0.5, intensity=0.9),
            "content": EmotionVector(valence=0.6, arousal=-0.2, dominance=0.2, intensity=0.4),
            "peaceful": EmotionVector(valence=0.5, arousal=-0.6, dominance=0.0, intensity=0.3),
            "serene": EmotionVector(valence=0.7, arousal=-0.8, dominance=0.1, intensity=0.4),
            
            # Negative emotions
            "sad": EmotionVector(valence=-0.7, arousal=-0.5, dominance=-0.3, intensity=0.6),
            "disappointed": EmotionVector(valence=-0.6, arousal=-0.3, dominance=-0.2, intensity=0.5),
            "melancholy": EmotionVector(valence=-0.8, arousal=-0.7, dominance=-0.4, intensity=0.7),
            "dejected": EmotionVector(valence=-0.9, arousal=-0.8, dominance=-0.6, intensity=0.8),
            "gloomy": EmotionVector(valence=-0.7, arousal=-0.6, dominance=-0.5, intensity=0.6),
            
            # Anger spectrum
            "angry": EmotionVector(valence=-0.8, arousal=0.7, dominance=0.6, intensity=0.9),
            "frustrated": EmotionVector(valence=-0.6, arousal=0.4, dominance=0.2, intensity=0.7),
            "irritated": EmotionVector(valence=-0.5, arousal=0.3, dominance=0.1, intensity=0.5),
            "furious": EmotionVector(valence=-1.0, arousal=1.0, dominance=0.8, intensity=1.0),
            "annoyed": EmotionVector(valence=-0.4, arousal=0.2, dominance=0.0, intensity=0.4),
            
            # Anxiety spectrum
            "worried": EmotionVector(valence=-0.4, arousal=0.5, dominance=-0.3, intensity=0.6),
            "anxious": EmotionVector(valence=-0.6, arousal=0.7, dominance=-0.5, intensity=0.8),
            "nervous": EmotionVector(valence=-0.5, arousal=0.6, dominance=-0.4, intensity=0.6),
            "concerned": EmotionVector(valence=-0.3, arousal=0.3, dominance=-0.1, intensity=0.5),
            "stressed": EmotionVector(valence=-0.7, arousal=0.8, dominance=-0.2, intensity=0.8),
            
            # Curiosity spectrum
            "curious": EmotionVector(valence=0.3, arousal=0.4, dominance=0.2, intensity=0.5),
            "interested": EmotionVector(valence=0.4, arousal=0.3, dominance=0.3, intensity=0.4),
            "intrigued": EmotionVector(valence=0.2, arousal=0.2, dominance=0.1, intensity=0.4),
            "fascinated": EmotionVector(valence=0.6, arousal=0.5, dominance=0.4, intensity=0.7),
            "wondering": EmotionVector(valence=0.1, arousal=-0.1, dominance=0.0, intensity=0.3),
            
            # Confusion spectrum
            "confused": EmotionVector(valence=-0.2, arousal=0.1, dominance=-0.4, intensity=0.4),
            "puzzled": EmotionVector(valence=-0.1, arousal=0.0, dominance=-0.3, intensity=0.3),
            "uncertain": EmotionVector(valence=-0.3, arousal=-0.1, dominance=-0.5, intensity=0.4),
            "bewildered": EmotionVector(valence=-0.4, arousal=0.2, dominance=-0.6, intensity=0.6),
            "perplexed": EmotionVector(valence=-0.2, arousal=0.1, dominance=-0.4, intensity=0.4),
            
            # Surprise spectrum
            "surprised": EmotionVector(valence=0.2, arousal=0.8, dominance=0.0, intensity=0.7),
            "amazed": EmotionVector(valence=0.6, arousal=0.7, dominance=0.2, intensity=0.8),
            "astonished": EmotionVector(valence=0.4, arousal=0.9, dominance=0.1, intensity=0.9),
            "startled": EmotionVector(valence=-0.1, arousal=1.0, dominance=-0.2, intensity=0.8),
            "shocked": EmotionVector(valence=-0.2, arousal=0.6, dominance=-0.1, intensity=0.7),
            
            # Neutral spectrum
            "neutral": EmotionVector(valence=0.0, arousal=0.0, dominance=0.0, intensity=0.0),
            "indifferent": EmotionVector(valence=0.0, arousal=-0.3, dominance=-0.1, intensity=0.1),
            "apathetic": EmotionVector(valence=-0.2, arousal=-0.5, dominance=-0.3, intensity=0.2),
            "detached": EmotionVector(valence=-0.1, arousal=-0.4, dominance=-0.2, intensity=0.2),
            "bland": EmotionVector(valence=0.0, arousal=-0.2, dominance=-0.1, intensity=0.1),
        }
        
        # Voice mapping configuration
        self.voice_mapping = VoiceMapping()
        
        # Performance cache
        self.parameter_cache: Dict[str, Tuple[float, float]] = {}
        
        # Statistics
        self.stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "calculations_performed": 0,
            "unknown_emotions": set()
        }
    
    def get_voice_parameters(self, emotion: str) -> Tuple[float, float]:
        """
        Calculate voice parameters from emotion using N-dimensional space
        
        Args:
            emotion: Single emotion word
            
        Returns:
            Tuple of (speed, pitch)
        """
        # Check cache first
        if emotion in self.parameter_cache:
            self.stats["cache_hits"] += 1
            return self.parameter_cache[emotion]
        
        self.stats["cache_misses"] += 1
        
        # Get emotion vector
        if emotion not in self.emotion_vectors:
            logger.warning(f"Unknown emotion '{emotion}', using neutral")
            self.stats["unknown_emotions"].add(emotion)
            emotion_vector = self.emotion_vectors["neutral"]
        else:
            emotion_vector = self.emotion_vectors[emotion]
        
        # Calculate voice parameters using mathematical mapping
        speed, pitch = self._calculate_voice_parameters(emotion_vector)
        
        # Cache result
        self.parameter_cache[emotion] = (speed, pitch)
        self.stats["calculations_performed"] += 1
        
        return speed, pitch
    
    def _calculate_voice_parameters(self, emotion_vector: EmotionVector) -> Tuple[float, float]:
        """
        Calculate voice parameters from emotion vector using mathematical functions
        
        Args:
            emotion_vector: N-dimensional emotion representation
            
        Returns:
            Tuple of (speed, pitch)
        """
        mapping = self.voice_mapping
        
        # Calculate speed: base + valence*factor + arousal*factor + intensity*factor
        speed = (
            mapping.speed_base +
            (emotion_vector.valence * mapping.speed_valence_factor) +
            (emotion_vector.arousal * mapping.speed_arousal_factor) +
            (emotion_vector.intensity * mapping.speed_intensity_factor)
        )
        
        # Calculate pitch: base + valence*factor + arousal*factor + dominance*factor
        pitch = (
            mapping.pitch_base +
            (emotion_vector.valence * mapping.pitch_valence_factor) +
            (emotion_vector.arousal * mapping.pitch_arousal_factor) +
            (emotion_vector.dominance * mapping.pitch_dominance_factor)
        )
        
        # Apply constraints
        speed = np.clip(speed, mapping.speed_min, mapping.speed_max)
        pitch = np.clip(pitch, mapping.pitch_min, mapping.pitch_max)
        
        return float(speed), float(pitch)
    
    def get_emotion_vector(self, emotion: str) -> Optional[EmotionVector]:
        """Get the N-dimensional vector for an emotion"""
        return self.emotion_vectors.get(emotion)
    
    def add_custom_emotion(self, emotion: str, vector: EmotionVector):
        """Add a custom emotion to the system"""
        self.emotion_vectors[emotion] = vector
        logger.info(f"Added custom emotion '{emotion}' with vector {vector}")
    
    def find_similar_emotions(self, emotion: str, limit: int = 5) -> List[Tuple[str, float]]:
        """
        Find emotions similar to the given emotion using vector distance
        
        Args:
            emotion: Target emotion
            limit: Maximum number of similar emotions to return
            
        Returns:
            List of (emotion_name, similarity_score) tuples
        """
        if emotion not in self.emotion_vectors:
            return []
        
        target_vector = self.emotion_vectors[emotion].to_array()
        similarities = []
        
        for other_emotion, other_vector in self.emotion_vectors.items():
            if other_emotion == emotion:
                continue
            
            # Calculate cosine similarity
            other_array = other_vector.to_array()
            similarity = np.dot(target_vector, other_array) / (
                np.linalg.norm(target_vector) * np.linalg.norm(other_array)
            )
            similarities.append((other_emotion, float(similarity)))
        
        # Sort by similarity and return top results
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:limit]
    
    def get_emotion_space_info(self) -> Dict[str, Any]:
        """Get information about the N-dimensional emotion space"""
        vectors = [v.to_array() for v in self.emotion_vectors.values()]
        vectors_array = np.array(vectors)
        
        return {
            "total_emotions": len(self.emotion_vectors),
            "dimensions": 4,
            "dimension_names": [d.value for d in EmotionDimension],
            "space_statistics": {
                "valence_range": [float(vectors_array[:, 0].min()), float(vectors_array[:, 0].max())],
                "arousal_range": [float(vectors_array[:, 1].min()), float(vectors_array[:, 1].max())],
                "dominance_range": [float(vectors_array[:, 2].min()), float(vectors_array[:, 2].max())],
                "intensity_range": [float(vectors_array[:, 3].min()), float(vectors_array[:, 3].max())],
            },
            "voice_mapping": {
                "speed_range": [self.voice_mapping.speed_min, self.voice_mapping.speed_max],
                "pitch_range": [self.voice_mapping.pitch_min, self.voice_mapping.pitch_max],
                "base_values": {"speed": self.voice_mapping.speed_base, "pitch": self.voice_mapping.pitch_base}
            }
        }
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        total_requests = self.stats["cache_hits"] + self.stats["cache_misses"]
        cache_hit_rate = self.stats["cache_hits"] / total_requests if total_requests > 0 else 0
        
        return {
            "cache_performance": {
                "total_requests": total_requests,
                "cache_hits": self.stats["cache_hits"],
                "cache_misses": self.stats["cache_misses"],
                "hit_rate": cache_hit_rate,
                "cache_size": len(self.parameter_cache)
            },
            "calculation_stats": {
                "calculations_performed": self.stats["calculations_performed"],
                "unknown_emotions_encountered": len(self.stats["unknown_emotions"]),
                "unknown_emotions": list(self.stats["unknown_emotions"])
            }
        }
    
    def calibrate_voice_mapping(self, speed_sensitivity: float = 1.0, pitch_sensitivity: float = 1.0):
        """
        Calibrate voice mapping sensitivity
        
        Args:
            speed_sensitivity: Multiplier for speed sensitivity (1.0 = default)
            pitch_sensitivity: Multiplier for pitch sensitivity (1.0 = default)
        """
        self.voice_mapping.speed_arousal_factor *= speed_sensitivity
        self.voice_mapping.speed_valence_factor *= speed_sensitivity
        self.voice_mapping.speed_intensity_factor *= speed_sensitivity
        
        self.voice_mapping.pitch_arousal_factor *= pitch_sensitivity
        self.voice_mapping.pitch_valence_factor *= pitch_sensitivity
        self.voice_mapping.pitch_dominance_factor *= pitch_sensitivity
        
        # Clear cache to force recalculation
        self.parameter_cache.clear()
        
        logger.info(f"Voice mapping calibrated: speed_sensitivity={speed_sensitivity}, pitch_sensitivity={pitch_sensitivity}")
    
    def clear_cache(self):
        """Clear the parameter cache"""
        self.parameter_cache.clear()
        self.stats["cache_hits"] = 0
        self.stats["cache_misses"] = 0
        logger.info("Voice parameter cache cleared")