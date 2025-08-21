"""
Memory management and conversation context tools for PydanticAI agents
"""

import logging
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from pydantic import BaseModel
from pydantic_ai import Agent

from aichat.core.event_system import EventSeverity, EventType, get_event_system
from aichat.models.schemas import ConversationMemory

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    """Enhanced memory entry with metadata"""
    
    topic: str
    details: str
    timestamp: str
    importance: float
    emotion_context: str
    tags: List[str]
    related_memories: List[str]


class MemoryManager:
    """Advanced memory management system"""
    
    def __init__(self, max_memories: int = 50):
        self.max_memories = max_memories
        self.importance_threshold = 0.3  # Minimum importance to keep memories
        
        # Memory categories for better organization
        self.memory_categories = {
            "personal": ["name", "age", "family", "background", "preferences"],
            "conversational": ["topic", "discussion", "question", "answer"],
            "emotional": ["feeling", "emotion", "mood", "reaction"],
            "factual": ["fact", "information", "data", "knowledge"],
            "behavioral": ["habit", "pattern", "tendency", "style"]
        }
    
    def categorize_memory(self, topic: str, details: str) -> List[str]:
        """Categorize memory based on content"""
        categories = []
        content = f"{topic} {details}".lower()
        
        for category, keywords in self.memory_categories.items():
            if any(keyword in content for keyword in keywords):
                categories.append(category)
        
        return categories if categories else ["general"]
    
    def calculate_importance(self, topic: str, details: str, emotion_context: str) -> float:
        """Calculate memory importance score"""
        importance = 0.5  # Base importance
        
        # Boost importance for certain keywords
        high_importance_keywords = ["name", "birthday", "important", "remember", "never forget"]
        medium_importance_keywords = ["like", "dislike", "prefer", "enjoy", "hate"]
        
        content = f"{topic} {details}".lower()
        
        for keyword in high_importance_keywords:
            if keyword in content:
                importance += 0.3
        
        for keyword in medium_importance_keywords:
            if keyword in content:
                importance += 0.2
        
        # Boost for emotional context
        if emotion_context and emotion_context != "neutral":
            importance += 0.1
        
        # Boost for longer, more detailed memories
        if len(details) > 100:
            importance += 0.1
        
        return min(importance, 1.0)
    
    def find_related_memories(self, memory_list: List[Dict], topic: str, details: str) -> List[str]:
        """Find memories related to the new memory"""
        related = []
        content_words = set(f"{topic} {details}".lower().split())
        
        for memory in memory_list:
            existing_words = set(f"{memory.get('topic', '')} {memory.get('details', '')}".lower().split())
            
            # Check for word overlap
            overlap = len(content_words.intersection(existing_words))
            if overlap >= 2:  # At least 2 words in common
                related.append(memory.get('topic', 'Unknown'))
        
        return related[:3]  # Limit to 3 related memories
    
    def consolidate_memories(self, memory_list: List[Dict]) -> List[Dict]:
        """Consolidate and clean up memory list"""
        if len(memory_list) <= self.max_memories:
            return memory_list
        
        # Sort by importance and recency
        def memory_score(memory):
            importance = memory.get('importance', 0.5)
            # Recent memories get a slight boost
            timestamp = memory.get('timestamp', '')
            recency_bonus = 0.1 if timestamp else 0.0
            return importance + recency_bonus
        
        sorted_memories = sorted(memory_list, key=memory_score, reverse=True)
        
        # Keep only the most important memories
        filtered_memories = [
            mem for mem in sorted_memories 
            if mem.get('importance', 0.5) >= self.importance_threshold
        ]
        
        return filtered_memories[:self.max_memories]


class MemoryTool:
    """Memory management tool for PydanticAI agents"""
    
    def __init__(self):
        self.event_system = get_event_system()
        self.memory_manager = MemoryManager()
    
    def register_tools(self, agent: Agent, context_type):
        """Register memory tools with PydanticAI agent"""
        
        @agent.tool
        async def remember_conversation(ctx: context_type, topic: str, details: str, importance: float = None) -> str:
            """Store important conversation details in memory with enhanced metadata
            
            Args:
                topic: Topic or subject of the memory
                details: Specific details to remember
                importance: Memory importance (0.0 to 1.0, auto-calculated if not provided)
            """
            # Auto-calculate importance if not provided
            if importance is None:
                importance = self.memory_manager.calculate_importance(
                    topic, details, ctx.emotion_state.emotion
                )
            else:
                importance = max(0.0, min(1.0, importance))
            
            # Categorize memory
            categories = self.memory_manager.categorize_memory(topic, details)
            
            # Find related memories
            related = self.memory_manager.find_related_memories(
                ctx.conversation_history, topic, details
            )
            
            # Create enhanced memory entry
            memory_entry = {
                "topic": topic,
                "details": details,
                "timestamp": datetime.now().isoformat(),
                "importance": importance,
                "emotion_context": ctx.emotion_state.emotion,
                "categories": categories,
                "related_memories": related
            }
            
            ctx.conversation_history.append(memory_entry)
            
            # Consolidate memories if needed
            ctx.conversation_history = self.memory_manager.consolidate_memories(
                ctx.conversation_history
            )
            
            await self.event_system.emit(
                EventType.CHAT_MESSAGE,
                f"Memory stored: {topic}",
                {
                    "character": ctx.name,
                    "topic": topic,
                    "importance": importance,
                    "categories": categories,
                    "memory_count": len(ctx.conversation_history),
                    "related_count": len(related)
                }
            )
            
            return f"Remembered: {topic} - {details} (Importance: {importance:.2f}, Categories: {', '.join(categories)})"
        
        @agent.tool
        async def get_memory(ctx: context_type, topic: str = None, category: str = None, limit: int = 5) -> str:
            """Retrieve past conversation memories with advanced filtering
            
            Args:
                topic: Specific topic to search for (optional)
                category: Memory category to filter by (personal, conversational, emotional, factual, behavioral)
                limit: Maximum number of memories to return (1-20)
            """
            if not ctx.conversation_history:
                return "No memories stored yet."
            
            limit = max(1, min(20, limit))
            memories = ctx.conversation_history
            
            # Filter by category
            if category:
                memories = [
                    mem for mem in memories 
                    if category in mem.get("categories", [])
                ]
                if not memories:
                    available_categories = set()
                    for mem in ctx.conversation_history:
                        available_categories.update(mem.get("categories", []))
                    return f"No memories found in category '{category}'. Available categories: {', '.join(available_categories)}"
            
            # Filter by topic
            if topic:
                topic_lower = topic.lower()
                relevant_memories = [
                    mem for mem in memories
                    if topic_lower in mem.get("topic", "").lower() 
                    or topic_lower in mem.get("details", "").lower()
                ]
                memories = relevant_memories if relevant_memories else memories
            
            # Sort by importance and recency
            memories = sorted(
                memories, 
                key=lambda x: (x.get("importance", 0.5), x.get("timestamp", "")), 
                reverse=True
            )
            
            # Format results
            if not memories:
                return f"No memories found matching your criteria."
            
            result_memories = memories[:limit]
            result_text = f"Retrieved {len(result_memories)} memories"
            
            if topic:
                result_text += f" about '{topic}'"
            if category:
                result_text += f" in category '{category}'"
            
            result_text += ":\n\n"
            
            for i, mem in enumerate(result_memories, 1):
                timestamp = mem.get("timestamp", "Unknown time")
                importance = mem.get("importance", 0.5)
                emotion = mem.get("emotion_context", "neutral")
                categories = ", ".join(mem.get("categories", ["general"]))
                
                result_text += f"{i}. {mem.get('topic', 'Unknown')}: {mem.get('details', 'No details')}\n"
                result_text += f"   ↳ Importance: {importance:.2f} | Emotion: {emotion} | Categories: {categories}\n"
                
                if i < len(result_memories):
                    result_text += "\n"
            
            await self.event_system.emit(
                EventType.CHAT_MESSAGE,
                f"Memory retrieval completed",
                {
                    "character": ctx.name,
                    "query_topic": topic,
                    "query_category": category,
                    "memories_found": len(result_memories),
                    "total_memories": len(ctx.conversation_history)
                }
            )
            
            return result_text
        
        @agent.tool
        async def analyze_memory_patterns(ctx: context_type) -> str:
            """Analyze patterns in stored memories to provide insights
            """
            if not ctx.conversation_history:
                return "No memories available for pattern analysis."
            
            memories = ctx.conversation_history
            
            # Analyze categories
            category_counts = {}
            emotion_counts = {}
            importance_levels = {"high": 0, "medium": 0, "low": 0}
            
            for memory in memories:
                # Count categories
                for category in memory.get("categories", ["general"]):
                    category_counts[category] = category_counts.get(category, 0) + 1
                
                # Count emotions
                emotion = memory.get("emotion_context", "neutral")
                emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
                
                # Classify importance
                importance = memory.get("importance", 0.5)
                if importance >= 0.7:
                    importance_levels["high"] += 1
                elif importance >= 0.4:
                    importance_levels["medium"] += 1
                else:
                    importance_levels["low"] += 1
            
            # Generate analysis
            analysis = f"Memory Pattern Analysis ({len(memories)} total memories):\n\n"
            
            # Most common categories
            if category_counts:
                top_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:3]
                analysis += f"Top memory categories: {', '.join([f'{cat} ({count})' for cat, count in top_categories])}\n"
            
            # Emotional patterns
            if emotion_counts:
                top_emotions = sorted(emotion_counts.items(), key=lambda x: x[1], reverse=True)[:3]
                analysis += f"Most common emotions: {', '.join([f'{emo} ({count})' for emo, count in top_emotions])}\n"
            
            # Importance distribution
            analysis += f"Importance levels: High: {importance_levels['high']}, Medium: {importance_levels['medium']}, Low: {importance_levels['low']}\n"
            
            # Recent activity
            recent_memories = [mem for mem in memories if mem.get("timestamp")]
            if recent_memories:
                analysis += f"\nRecent memory activity: {len(recent_memories)} memories have timestamps"
            
            await self.event_system.emit(
                EventType.CHAT_MESSAGE,
                f"Memory pattern analysis completed",
                {
                    "character": ctx.name,
                    "total_memories": len(memories),
                    "categories": list(category_counts.keys()),
                    "emotions": list(emotion_counts.keys()),
                    "high_importance": importance_levels["high"]
                }
            )
            
            return analysis
        
        @agent.tool
        async def update_memory(ctx: context_type, topic: str, new_details: str = None, new_importance: float = None) -> str:
            """Update an existing memory with new information
            
            Args:
                topic: Topic of the memory to update
                new_details: New details to add or replace (optional)
                new_importance: New importance level (optional)
            """
            if not ctx.conversation_history:
                return "No memories available to update."
            
            # Find memory to update
            memory_to_update = None
            memory_index = -1
            
            for i, memory in enumerate(ctx.conversation_history):
                if topic.lower() in memory.get("topic", "").lower():
                    memory_to_update = memory
                    memory_index = i
                    break
            
            if not memory_to_update:
                return f"No memory found with topic containing '{topic}'. Use remember_conversation to create a new memory."
            
            # Update memory
            old_details = memory_to_update.get("details", "")
            old_importance = memory_to_update.get("importance", 0.5)
            
            if new_details:
                memory_to_update["details"] = new_details
                # Recategorize with new details
                memory_to_update["categories"] = self.memory_manager.categorize_memory(
                    memory_to_update["topic"], new_details
                )
            
            if new_importance is not None:
                memory_to_update["importance"] = max(0.0, min(1.0, new_importance))
            
            memory_to_update["timestamp"] = datetime.now().isoformat()  # Update timestamp
            
            ctx.conversation_history[memory_index] = memory_to_update
            
            await self.event_system.emit(
                EventType.CHAT_MESSAGE,
                f"Memory updated: {topic}",
                {
                    "character": ctx.name,
                    "topic": topic,
                    "details_changed": new_details is not None,
                    "importance_changed": new_importance is not None,
                    "old_importance": old_importance,
                    "new_importance": memory_to_update.get("importance", old_importance)
                }
            )
            
            return f"Updated memory for '{topic}'. " + \
                   (f"Details updated. " if new_details else "") + \
                   (f"Importance changed from {old_importance:.2f} to {memory_to_update['importance']:.2f}." if new_importance is not None else "")
        
        @agent.tool
        async def forget_memory(ctx: context_type, topic: str) -> str:
            """Remove a specific memory from storage
            
            Args:
                topic: Topic of the memory to forget
            """
            if not ctx.conversation_history:
                return "No memories available to forget."
            
            # Find and remove memory
            original_count = len(ctx.conversation_history)
            ctx.conversation_history = [
                mem for mem in ctx.conversation_history
                if topic.lower() not in mem.get("topic", "").lower()
            ]
            
            removed_count = original_count - len(ctx.conversation_history)
            
            if removed_count == 0:
                return f"No memory found with topic containing '{topic}'."
            
            await self.event_system.emit(
                EventType.CHAT_MESSAGE,
                f"Memory forgotten: {topic}",
                {
                    "character": ctx.name,
                    "topic": topic,
                    "memories_removed": removed_count,
                    "remaining_memories": len(ctx.conversation_history)
                }
            )
            
            return f"Forgot {removed_count} memory(ies) about '{topic}'. {len(ctx.conversation_history)} memories remaining."