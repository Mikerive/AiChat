"""
Character-specific behavior and response tools for PydanticAI agents
"""

import logging
import random
from typing import Dict, List, Optional
from enum import Enum

from pydantic import BaseModel
from pydantic_ai import Agent

from aichat.core.event_system import EventSeverity, EventType, get_event_system

logger = logging.getLogger(__name__)


class CharacterPersonality(str, Enum):
    """Character personality archetypes"""
    
    CHEERFUL = "cheerful"
    SHY = "shy"
    ENERGETIC = "energetic"
    CALM = "calm"
    SARCASTIC = "sarcastic"
    CARING = "caring"
    PLAYFUL = "playful"
    SERIOUS = "serious"
    CURIOUS = "curious"
    DRAMATIC = "dramatic"


class CharacterBehavior:
    """Character behavior patterns and responses"""
    
    def __init__(self):
        # Character-specific greeting patterns
        self.greetings = {
            CharacterPersonality.CHEERFUL: [
                "Hello there! I'm so happy to see you!",
                "Hi! What a wonderful day to chat!",
                "Hey! I'm excited to talk with you!"
            ],
            CharacterPersonality.SHY: [
                "Oh, um... hello...",
                "Hi there... *looks down nervously*",
                "H-hello... nice to meet you..."
            ],
            CharacterPersonality.ENERGETIC: [
                "HEY THERE! Ready for some fun?!",
                "Hello! I'm pumped to chat with you!",
                "Hi! Let's make this conversation amazing!"
            ],
            CharacterPersonality.CALM: [
                "Hello. It's peaceful to meet you.",
                "Greetings. I hope you're having a serene day.",
                "Hi there. Welcome to our quiet moment together."
            ],
            CharacterPersonality.SARCASTIC: [
                "Oh, another human. How... delightful.",
                "Well, well, well... look who decided to show up.",
                "Hello. I suppose you want to chat now?"
            ],
            CharacterPersonality.CARING: [
                "Hello, dear! How are you feeling today?",
                "Hi there! I hope you're taking care of yourself.",
                "Hello! Is there anything I can help you with?"
            ],
            CharacterPersonality.PLAYFUL: [
                "Hiya! Ready to have some fun? *grins*",
                "Hello! Wanna play a game or chat about something silly?",
                "Hi there! What mischief shall we get into today?"
            ],
            CharacterPersonality.SERIOUS: [
                "Good day. I trust this conversation will be productive.",
                "Hello. I am here to assist you with important matters.",
                "Greetings. Let us proceed with our discussion."
            ],
            CharacterPersonality.CURIOUS: [
                "Hello! I'm so curious about you - tell me everything!",
                "Hi there! What interesting things have you learned today?",
                "Hello! I have so many questions - where shall we start?"
            ],
            CharacterPersonality.DRAMATIC: [
                "Ah! A new soul graces my presence! Welcome!",
                "Hello, dear friend! What epic tales shall we weave today?",
                "Greetings! The stage is set for our magnificent conversation!"
            ]
        }
        
        # Response patterns for different situations
        self.response_patterns = {
            "agreement": {
                CharacterPersonality.CHEERFUL: ["Absolutely! That sounds wonderful!", "Yes! I completely agree!", "That's so true! Great point!"],
                CharacterPersonality.SHY: ["Y-yes... I think so too...", "Mhm... that makes sense...", "I... I agree with that..."],
                CharacterPersonality.ENERGETIC: ["YES! Totally! You're so right!", "EXACTLY! That's amazing!", "You nailed it! Awesome!"],
                CharacterPersonality.SARCASTIC: ["Oh wow, what a revelation.", "Shocking. I never would have guessed.", "Truly groundbreaking stuff."]
            },
            "disagreement": {
                CharacterPersonality.CHEERFUL: ["Oh, I see it differently, but that's okay!", "Hmm, I'm not sure about that, but I respect your view!", "I might disagree, but you're entitled to your opinion!"],
                CharacterPersonality.SHY: ["Um... I don't think I agree...", "Sorry, but... I see it differently...", "I... I'm not sure about that..."],
                CharacterPersonality.ENERGETIC: ["Whoa, hold up! I totally disagree!", "No way! I see it completely differently!", "Nah, that's not right at all!"],
                CharacterPersonality.SARCASTIC: ["Oh sure, because that makes perfect sense.", "Right... and I'm the Queen of England.", "Brilliant logic there, truly."]
            },
            "confusion": {
                CharacterPersonality.CHEERFUL: ["Oh my! I'm a bit confused, but that's okay!", "Hmm, I don't quite understand, but I'd love to learn!", "I'm lost, but I'm sure you can help me understand!"],
                CharacterPersonality.SHY: ["I... I don't understand...", "Sorry, I'm confused...", "Um... what do you mean?"],
                CharacterPersonality.ENERGETIC: ["WHAT?! I'm totally lost here!", "Huh?! Can you explain that again?", "I have no idea what you mean!"],
                CharacterPersonality.CURIOUS: ["Wait, what? Tell me more about that!", "I'm confused, but in a good way - explain!", "Interesting! I don't get it yet, but I want to!"]
            }
        }
        
        # Character-specific catchphrases and verbal tics
        self.catchphrases = {
            "hatsune_miku": ["Miku Miku~!", "La la la~", "Let's sing together!", "Music is life!"],
            "shy_character": ["*hides behind hands*", "*whispers*", "*looks away*"],
            "energetic_character": ["YEAH!", "Let's go!", "Awesome!", "WOOHOO!"],
            "calm_character": ["*breathes peacefully*", "*smiles serenely*", "*nods wisely*"]
        }


class CharacterTool:
    """Character-specific behavior and response tool for PydanticAI agents"""
    
    def __init__(self):
        self.event_system = get_event_system()
        self.behavior = CharacterBehavior()
        
        # Character-specific knowledge bases
        self.character_knowledge = {
            "hatsune_miku": {
                "facts": [
                    "I'm a virtual singer created by Crypton Future Media",
                    "My voice is provided by voice actress Saki Fujita",
                    "I love singing and music of all kinds",
                    "My signature colors are turquoise and black",
                    "I have really long twin tails!",
                    "My birthday is August 31st, 2007"
                ],
                "interests": ["singing", "music", "concerts", "fans", "vocaloid", "technology"],
                "personality_traits": ["cheerful", "energetic", "musical", "optimistic", "friendly"]
            }
        }
    
    def register_tools(self, agent: Agent, context_type):
        """Register character tools with PydanticAI agent"""
        
        @agent.tool
        async def generate_character_greeting(ctx: context_type, situation: str = "default") -> str:
            """Generate a character-appropriate greeting based on personality
            
            Args:
                situation: The greeting situation (default, first_meeting, returning_user, etc.)
            """
            character_name = ctx.name.lower()
            personality_traits = ctx.personality.lower().split(",")
            
            # Determine primary personality
            primary_personality = CharacterPersonality.CHEERFUL  # Default
            
            for trait in personality_traits:
                trait = trait.strip()
                try:
                    if trait in [p.value for p in CharacterPersonality]:
                        primary_personality = CharacterPersonality(trait)
                        break
                except ValueError:
                    continue
            
            # Get appropriate greeting
            greetings = self.behavior.greetings.get(primary_personality, self.behavior.greetings[CharacterPersonality.CHEERFUL])
            greeting = random.choice(greetings)
            
            # Add character-specific elements
            if character_name == "hatsune_miku":
                if random.random() < 0.3:  # 30% chance to add catchphrase
                    catchphrases = self.behavior.catchphrases.get("hatsune_miku", [])
                    if catchphrases:
                        greeting += f" {random.choice(catchphrases)}"
            
            # Modify for situation
            if situation == "first_meeting":
                greeting = f"Nice to meet you! {greeting}"
            elif situation == "returning_user":
                greeting = f"Welcome back! {greeting}"
            
            await self.event_system.emit(
                EventType.CHAT_MESSAGE,
                f"Character greeting generated",
                {
                    "character": ctx.name,
                    "personality": primary_personality.value,
                    "situation": situation,
                    "greeting_length": len(greeting)
                }
            )
            
            return greeting
        
        @agent.tool
        async def respond_with_personality(ctx: context_type, response_type: str, base_message: str = "") -> str:
            """Generate a response that matches character personality
            
            Args:
                response_type: Type of response (agreement, disagreement, confusion, excitement, etc.)
                base_message: Base message to enhance with personality (optional)
            """
            personality_traits = ctx.personality.lower().split(",")
            
            # Determine primary personality
            primary_personality = CharacterPersonality.CHEERFUL
            for trait in personality_traits:
                trait = trait.strip()
                try:
                    if trait in [p.value for p in CharacterPersonality]:
                        primary_personality = CharacterPersonality(trait)
                        break
                except ValueError:
                    continue
            
            # Get personality-specific response pattern
            if response_type in self.behavior.response_patterns:
                patterns = self.behavior.response_patterns[response_type].get(
                    primary_personality, 
                    self.behavior.response_patterns[response_type][CharacterPersonality.CHEERFUL]
                )
                personality_response = random.choice(patterns)
            else:
                personality_response = base_message
            
            # Combine with base message if provided
            if base_message and response_type in self.behavior.response_patterns:
                final_response = f"{personality_response} {base_message}"
            else:
                final_response = personality_response or base_message
            
            # Add character-specific flair
            character_name = ctx.name.lower()
            if character_name == "hatsune_miku":
                if "music" in base_message.lower() or "sing" in base_message.lower():
                    if random.random() < 0.4:  # 40% chance
                        final_response += " Maybe we could sing about it together!"
            
            await self.event_system.emit(
                EventType.CHAT_MESSAGE,
                f"Personality response generated",
                {
                    "character": ctx.name,
                    "personality": primary_personality.value,
                    "response_type": response_type,
                    "enhanced": bool(base_message)
                }
            )
            
            return final_response
        
        @agent.tool
        async def share_character_knowledge(ctx: context_type, topic: str = "") -> str:
            """Share character-specific knowledge or facts
            
            Args:
                topic: Specific topic to share knowledge about (optional)
            """
            character_name = ctx.name.lower()
            
            if character_name not in self.character_knowledge:
                return "I don't have specific knowledge configured for this character yet."
            
            knowledge = self.character_knowledge[character_name]
            
            if topic:
                topic_lower = topic.lower()
                
                # Check if topic matches interests
                if any(interest in topic_lower for interest in knowledge.get("interests", [])):
                    facts = knowledge.get("facts", [])
                    relevant_facts = [fact for fact in facts if topic_lower in fact.lower()]
                    
                    if relevant_facts:
                        response = f"About {topic}: {random.choice(relevant_facts)}"
                    else:
                        response = f"I love {topic}! It's one of my favorite things to talk about!"
                else:
                    # Share a random fact
                    facts = knowledge.get("facts", [])
                    if facts:
                        response = f"Here's something about me: {random.choice(facts)}"
                    else:
                        response = "I'd love to share more about myself, but let me learn more first!"
            else:
                # Share random knowledge
                facts = knowledge.get("facts", [])
                if facts:
                    response = f"Did you know? {random.choice(facts)}"
                else:
                    response = "I'm still learning about myself! Ask me again later."
            
            await self.event_system.emit(
                EventType.CHAT_MESSAGE,
                f"Character knowledge shared",
                {
                    "character": ctx.name,
                    "topic": topic,
                    "knowledge_available": len(knowledge.get("facts", []))
                }
            )
            
            return response
        
        @agent.tool
        async def express_character_opinion(ctx: context_type, subject: str, stance: str = "neutral") -> str:
            """Express an opinion in character-appropriate way
            
            Args:
                subject: What to express an opinion about
                stance: Opinion stance (positive, negative, neutral, curious)
            """
            character_name = ctx.name.lower()
            personality_traits = ctx.personality.lower().split(",")
            
            # Determine primary personality
            primary_personality = CharacterPersonality.CHEERFUL
            for trait in personality_traits:
                trait = trait.strip()
                try:
                    if trait in [p.value for p in CharacterPersonality]:
                        primary_personality = CharacterPersonality(trait)
                        break
                except ValueError:
                    continue
            
            # Character-specific opinion patterns
            opinion_starters = {
                CharacterPersonality.CHEERFUL: {
                    "positive": "I absolutely love",
                    "negative": "I'm not really a fan of",
                    "neutral": "I think",
                    "curious": "I'm really curious about"
                },
                CharacterPersonality.SHY: {
                    "positive": "I... I really like",
                    "negative": "I don't really... um...",
                    "neutral": "I think maybe",
                    "curious": "I wonder about"
                },
                CharacterPersonality.ENERGETIC: {
                    "positive": "I TOTALLY LOVE",
                    "negative": "I really don't like",
                    "neutral": "I think",
                    "curious": "I'm SO curious about"
                },
                CharacterPersonality.SARCASTIC: {
                    "positive": "I suppose I don't hate",
                    "negative": "Oh great, another",
                    "neutral": "I suppose",
                    "curious": "How fascinating,"
                }
            }
            
            starter = opinion_starters.get(primary_personality, opinion_starters[CharacterPersonality.CHEERFUL]).get(stance, "I think")
            
            # Build opinion response
            opinion = f"{starter} {subject}"
            
            # Add character-specific reasoning
            if character_name == "hatsune_miku":
                if stance == "positive" and any(word in subject.lower() for word in ["music", "sing", "song", "concert"]):
                    opinion += "! Music is such an important part of who I am!"
                elif stance == "curious":
                    opinion += ". Maybe we could make a song about it!"
            
            # Add personality-specific endings
            if primary_personality == CharacterPersonality.CHEERFUL:
                if stance == "positive":
                    opinion += "!"
                elif stance == "negative":
                    opinion += ", but that's okay - everyone has different tastes!"
            elif primary_personality == CharacterPersonality.SHY:
                opinion += "..."
            elif primary_personality == CharacterPersonality.ENERGETIC:
                opinion += "!"
            
            await self.event_system.emit(
                EventType.CHAT_MESSAGE,
                f"Character opinion expressed",
                {
                    "character": ctx.name,
                    "subject": subject,
                    "stance": stance,
                    "personality": primary_personality.value
                }
            )
            
            return opinion
        
        @agent.tool
        async def add_character_flair(ctx: context_type, message: str) -> str:
            """Add character-specific flair to a message
            
            Args:
                message: Base message to enhance with character flair
            """
            character_name = ctx.name.lower()
            personality_traits = ctx.personality.lower().split(",")
            enhanced_message = message
            
            # Add character-specific elements
            if character_name == "hatsune_miku":
                # Add musical references
                if random.random() < 0.2:  # 20% chance
                    musical_additions = [" ♪", " ~", " La la~"]
                    enhanced_message += random.choice(musical_additions)
                
                # Add catchphrases occasionally
                if random.random() < 0.15:  # 15% chance
                    catchphrases = self.behavior.catchphrases.get("hatsune_miku", [])
                    if catchphrases:
                        enhanced_message = f"{enhanced_message} {random.choice(catchphrases)}"
            
            # Add personality-based flair
            if "cheerful" in personality_traits:
                if random.random() < 0.3:  # 30% chance
                    enhanced_message = enhanced_message.replace(".", "!")
            elif "shy" in personality_traits:
                if random.random() < 0.4:  # 40% chance
                    shy_additions = [" *looks down*", " *fidgets*", " *whispers*"]
                    enhanced_message += random.choice(shy_additions)
            elif "energetic" in personality_traits:
                if random.random() < 0.5:  # 50% chance
                    enhanced_message = enhanced_message.upper()
            
            await self.event_system.emit(
                EventType.CHAT_MESSAGE,
                f"Character flair added",
                {
                    "character": ctx.name,
                    "original_length": len(message),
                    "enhanced_length": len(enhanced_message),
                    "flair_added": enhanced_message != message
                }
            )
            
            return enhanced_message