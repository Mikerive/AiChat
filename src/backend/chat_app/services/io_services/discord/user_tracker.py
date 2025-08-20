"""
Discord user tracking and management
"""

import asyncio
import logging
import time
from typing import Dict, Set, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum

try:
    import discord
    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False
    discord = None

logger = logging.getLogger(__name__)


class UserStatus(Enum):
    """User status in voice channels"""
    OFFLINE = "offline"
    ONLINE = "online"
    SPEAKING = "speaking"
    MUTED = "muted"
    DEAFENED = "deafened"


@dataclass
class DiscordUser:
    """Discord user information and state"""
    id: int
    name: str
    display_name: str
    discriminator: str
    is_bot: bool = False
    
    # Voice state
    voice_channel_id: Optional[int] = None
    is_speaking: bool = False
    is_muted: bool = False
    is_deafened: bool = False
    status: UserStatus = UserStatus.OFFLINE
    
    # Activity tracking
    join_time: Optional[float] = None
    last_activity: Optional[float] = None
    total_speak_time: float = 0.0
    speak_session_start: Optional[float] = None
    
    # Consent and permissions
    has_consent: bool = False
    consent_timestamp: Optional[float] = None
    recording_enabled: bool = False
    
    # Audio processing state
    audio_buffer_id: Optional[str] = None
    last_audio_frame: Optional[float] = None
    
    def __post_init__(self):
        if self.join_time is None:
            self.join_time = time.time()
    
    def start_speaking(self):
        """Mark user as speaking"""
        if not self.is_speaking:
            self.is_speaking = True
            self.speak_session_start = time.time()
            self.last_activity = time.time()
            self.status = UserStatus.SPEAKING
    
    def stop_speaking(self):
        """Mark user as stopped speaking"""
        if self.is_speaking:
            self.is_speaking = False
            if self.speak_session_start:
                session_duration = time.time() - self.speak_session_start
                self.total_speak_time += session_duration
                self.speak_session_start = None
            self.status = UserStatus.ONLINE if not self.is_muted else UserStatus.MUTED
    
    def update_voice_state(self, voice_state):
        """Update user state from Discord voice state"""
        if voice_state:
            self.is_muted = voice_state.self_mute or voice_state.mute
            self.is_deafened = voice_state.self_deaf or voice_state.deaf
            self.voice_channel_id = voice_state.channel.id if voice_state.channel else None
            
            # Update status based on voice state
            if self.is_deafened:
                self.status = UserStatus.DEAFENED
            elif self.is_muted:
                self.status = UserStatus.MUTED
            elif self.is_speaking:
                self.status = UserStatus.SPEAKING
            else:
                self.status = UserStatus.ONLINE
        else:
            self.voice_channel_id = None
            self.status = UserStatus.OFFLINE
            self.stop_speaking()  # Stop speaking if left channel
    
    def grant_consent(self):
        """Grant recording consent"""
        self.has_consent = True
        self.consent_timestamp = time.time()
        self.recording_enabled = True
    
    def revoke_consent(self):
        """Revoke recording consent"""
        self.has_consent = False
        self.consent_timestamp = None
        self.recording_enabled = False
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "discriminator": self.discriminator,
            "is_bot": self.is_bot,
            "voice_channel_id": self.voice_channel_id,
            "is_speaking": self.is_speaking,
            "is_muted": self.is_muted,
            "is_deafened": self.is_deafened,
            "status": self.status.value,
            "join_time": self.join_time,
            "last_activity": self.last_activity,
            "total_speak_time": self.total_speak_time,
            "has_consent": self.has_consent,
            "recording_enabled": self.recording_enabled
        }


class UserTracker:
    """Tracks and manages Discord users in voice channels"""
    
    def __init__(self, config):
        self.config = config
        self.users: Dict[int, DiscordUser] = {}
        self.speaking_users: Set[int] = set()
        self.consented_users: Set[int] = set()
        
        # Callbacks
        self.on_user_join: Optional[Callable] = None
        self.on_user_leave: Optional[Callable] = None
        self.on_user_start_speaking: Optional[Callable] = None
        self.on_user_stop_speaking: Optional[Callable] = None
        self.on_user_consent_granted: Optional[Callable] = None
        self.on_user_consent_revoked: Optional[Callable] = None
        
        # Consent management
        self._consent_requests: Dict[int, asyncio.Task] = {}
        
        logger.info("User tracker initialized")
    
    def add_user(self, member, voice_state=None) -> DiscordUser:
        """Add or update a user"""
        user_id = member.id
        
        # Create or update user
        if user_id in self.users:
            user = self.users[user_id]
            # Update existing user info
            user.name = str(member)
            user.display_name = member.display_name
            user.discriminator = member.discriminator
        else:
            user = DiscordUser(
                id=user_id,
                name=str(member),
                display_name=member.display_name,
                discriminator=member.discriminator,
                is_bot=member.bot
            )
            self.users[user_id] = user
        
        # Update voice state
        user.update_voice_state(voice_state)
        
        # Check if user should be tracked
        if self._should_track_user(user):
            if self.config.require_user_consent and not user.has_consent:
                asyncio.create_task(self._request_user_consent(user))
        
        logger.debug(f"Added/updated user: {user.display_name}")
        return user
    
    def remove_user(self, user_id: int) -> Optional[DiscordUser]:
        """Remove a user"""
        user = self.users.pop(user_id, None)
        if user:
            self.speaking_users.discard(user_id)
            self.consented_users.discard(user_id)
            
            # Cancel any pending consent request
            if user_id in self._consent_requests:
                self._consent_requests[user_id].cancel()
                del self._consent_requests[user_id]
            
            logger.debug(f"Removed user: {user.display_name}")
        
        return user
    
    async def handle_voice_state_update(self, member, before, after):
        """Handle Discord voice state updates"""
        user_id = member.id
        
        try:
            # User left voice channels entirely
            if before.channel and not after.channel:
                user = self.remove_user(user_id)
                if user and self.on_user_leave:
                    await self.on_user_leave(user)
                return
            
            # User joined or moved channels
            if after.channel:
                user = self.add_user(member, after)
                
                # If this is a new join (not a move)
                if not before.channel and self.on_user_join:
                    await self.on_user_join(user)
            
            # Update speaking state based on mute status
            if user_id in self.users:
                user = self.users[user_id]
                was_speaking = user.is_speaking
                
                # User can speak if not muted or deafened
                can_speak = not (after.self_mute or after.mute or after.self_deaf or after.deaf)
                
                if can_speak and not was_speaking:
                    await self._user_start_speaking(user)
                elif not can_speak and was_speaking:
                    await self._user_stop_speaking(user)
        
        except Exception as e:
            logger.error(f"Error handling voice state update: {e}")
    
    async def _user_start_speaking(self, user: DiscordUser):
        """Handle user starting to speak"""
        user.start_speaking()
        self.speaking_users.add(user.id)
        
        if self.on_user_start_speaking:
            await self.on_user_start_speaking(user)
        
        logger.debug(f"User started speaking: {user.display_name}")
    
    async def _user_stop_speaking(self, user: DiscordUser):
        """Handle user stopping to speak"""
        user.stop_speaking()
        self.speaking_users.discard(user.id)
        
        if self.on_user_stop_speaking:
            await self.on_user_stop_speaking(user)
        
        logger.debug(f"User stopped speaking: {user.display_name}")
    
    def _should_track_user(self, user: DiscordUser) -> bool:
        """Check if user should be tracked"""
        # Skip bots if configured
        if self.config.ignore_bots and user.is_bot:
            return False
        
        # Check allowed users list
        if self.config.allowed_users and user.id not in self.config.allowed_users:
            return False
        
        return True
    
    async def _request_user_consent(self, user: DiscordUser):
        """Request recording consent from user"""
        try:
            # This would typically send a DM or channel message
            # For now, we'll simulate consent after a timeout
            logger.info(f"Requesting recording consent from {user.display_name}")
            
            # Wait for consent timeout
            await asyncio.sleep(self.config.consent_timeout)
            
            # Auto-grant consent for testing (in real implementation, this would wait for user response)
            user.grant_consent()
            self.consented_users.add(user.id)
            
            if self.on_user_consent_granted:
                await self.on_user_consent_granted(user)
            
            logger.info(f"Consent granted for {user.display_name}")
        
        except asyncio.CancelledError:
            logger.debug(f"Consent request cancelled for {user.display_name}")
        except Exception as e:
            logger.error(f"Error requesting consent: {e}")
    
    def grant_user_consent(self, user_id: int) -> bool:
        """Grant consent for a specific user"""
        if user_id in self.users:
            user = self.users[user_id]
            user.grant_consent()
            self.consented_users.add(user_id)
            
            # Cancel pending consent request
            if user_id in self._consent_requests:
                self._consent_requests[user_id].cancel()
                del self._consent_requests[user_id]
            
            return True
        return False
    
    def revoke_user_consent(self, user_id: int) -> bool:
        """Revoke consent for a specific user"""
        if user_id in self.users:
            user = self.users[user_id]
            user.revoke_consent()
            self.consented_users.discard(user_id)
            return True
        return False
    
    def get_user(self, user_id: int) -> Optional[DiscordUser]:
        """Get user by ID"""
        return self.users.get(user_id)
    
    def get_all_users(self) -> List[DiscordUser]:
        """Get all tracked users"""
        return list(self.users.values())
    
    def get_speaking_users(self) -> List[DiscordUser]:
        """Get currently speaking users"""
        return [self.users[uid] for uid in self.speaking_users if uid in self.users]
    
    def get_consented_users(self) -> List[DiscordUser]:
        """Get users who have granted recording consent"""
        return [self.users[uid] for uid in self.consented_users if uid in self.users]
    
    def get_recordable_users(self) -> List[DiscordUser]:
        """Get users who can be recorded (consented and speaking)"""
        recordable = []
        for user_id in self.speaking_users:
            if user_id in self.users and user_id in self.consented_users:
                user = self.users[user_id]
                if user.recording_enabled:
                    recordable.append(user)
        return recordable
    
    def get_stats(self) -> Dict:
        """Get tracking statistics"""
        total_users = len(self.users)
        speaking_count = len(self.speaking_users)
        consented_count = len(self.consented_users)
        recordable_count = len(self.get_recordable_users())
        
        # Calculate average speak time
        total_speak_time = sum(user.total_speak_time for user in self.users.values())
        avg_speak_time = total_speak_time / total_users if total_users > 0 else 0
        
        return {
            "total_users": total_users,
            "speaking_users": speaking_count,
            "consented_users": consented_count,
            "recordable_users": recordable_count,
            "average_speak_time": avg_speak_time,
            "total_speak_time": total_speak_time
        }
    
    def set_callbacks(self, **callbacks):
        """Set callback functions"""
        for name, callback in callbacks.items():
            if hasattr(self, f"on_{name}"):
                setattr(self, f"on_{name}", callback)
    
    async def cleanup(self):
        """Cleanup resources"""
        # Cancel all pending consent requests
        for task in self._consent_requests.values():
            task.cancel()
        
        # Wait for tasks to complete
        if self._consent_requests:
            await asyncio.gather(*self._consent_requests.values(), return_exceptions=True)
        
        self._consent_requests.clear()
        logger.info("User tracker cleaned up")