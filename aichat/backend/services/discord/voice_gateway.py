"""
Discord Voice Gateway Protocol Handler

Implements Discord's voice protocol for receiving audio data from voice channels.
This is the core component that enables actual audio capture from Discord calls.
"""

import asyncio
import json
import logging
import socket
import struct
import time
from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Callable, Dict, Optional

try:
    import discord
    import nacl.secret
    import nacl.utils
    from discord.gateway import DiscordWebSocket

    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False
    discord = None
    nacl = None

logger = logging.getLogger(__name__)


class VoiceOpCode(IntEnum):
    """Discord Voice Gateway opcodes"""

    IDENTIFY = 0
    SELECT_PROTOCOL = 1
    READY = 2
    HEARTBEAT = 3
    SESSION_DESCRIPTION = 4
    SPEAKING = 5
    HEARTBEAT_ACK = 6
    RESUME = 7
    HELLO = 8
    RESUMED = 9
    CLIENT_DISCONNECT = 13


@dataclass
class VoicePacket:
    """Represents a voice packet from Discord"""

    sequence: int
    timestamp: int
    ssrc: int
    data: bytes
    user_id: Optional[int] = None
    decrypted_data: Optional[bytes] = None


class VoiceGateway:
    """Handles Discord Voice Gateway connection and audio receiving"""

    def __init__(self, session_id: str, token: str, endpoint: str, user_id: int):
        self.session_id = session_id
        self.token = token
        self.endpoint = endpoint.replace(":80", "")  # Remove port if present
        self.user_id = user_id

        # Connection state
        self.ws: Optional[DiscordWebSocket] = None
        self.udp_socket: Optional[socket.socket] = None
        self.secret_key: Optional[bytes] = None
        self.ssrc: Optional[int] = None
        self.ip: Optional[str] = None
        self.port: Optional[int] = None

        # Audio receiving
        self.audio_callback: Optional[Callable] = None
        self.user_ssrc_map: Dict[int, int] = {}  # Maps SSRC to user_id
        self.sequence_numbers: Dict[int, int] = {}  # Track sequence numbers per SSRC

        # Connection management
        self._running = False
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._receive_task: Optional[asyncio.Task] = None
        self._heartbeat_interval = 41.25  # Default Discord heartbeat interval

        logger.info("Voice Gateway initialized")

    async def connect(self) -> bool:
        """Connect to Discord Voice Gateway"""
        if not VOICE_AVAILABLE:
            logger.error(
                "Voice dependencies not available. Install with: pip install PyNaCl"
            )
            return False

        try:
            # Connect to voice gateway WebSocket
            gateway_url = f"wss://{self.endpoint}/?v=4"
            self.ws = await DiscordWebSocket.from_client(
                None,  # client
                gateway=gateway_url,
                session_id=self.session_id,
                token=self.token,
            )

            # Start receiving messages
            self._running = True
            asyncio.create_task(self._handle_gateway_messages())

            # Send IDENTIFY
            await self._send_identify()

            logger.info(f"Connected to voice gateway: {self.endpoint}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to voice gateway: {e}")
            return False

    async def disconnect(self):
        """Disconnect from voice gateway"""
        self._running = False

        # Cancel tasks
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        if self._receive_task:
            self._receive_task.cancel()

        # Close connections
        if self.udp_socket:
            self.udp_socket.close()
            self.udp_socket = None

        if self.ws:
            await self.ws.close()
            self.ws = None

        logger.info("Disconnected from voice gateway")

    async def _send_identify(self):
        """Send IDENTIFY payload to voice gateway"""
        payload = {
            "op": VoiceOpCode.IDENTIFY,
            "d": {
                "server_id": self.session_id,
                "user_id": str(self.user_id),
                "session_id": self.session_id,
                "token": self.token,
            },
        }
        await self.ws.send(json.dumps(payload))
        logger.debug("Sent IDENTIFY to voice gateway")

    async def _handle_gateway_messages(self):
        """Handle incoming gateway messages"""
        try:
            async for message in self.ws:
                if not self._running:
                    break

                if message.type == discord.WSMsgType.TEXT:
                    try:
                        data = json.loads(message.data)
                        await self._handle_voice_message(data)
                    except Exception as e:
                        logger.error(f"Error handling voice message: {e}")
                elif message.type == discord.WSMsgType.ERROR:
                    logger.error(f"Voice gateway error: {message.data}")
                elif message.type == discord.WSMsgType.CLOSE:
                    logger.warning("Voice gateway connection closed")
                    break

        except Exception as e:
            logger.error(f"Error in gateway message handler: {e}")
        finally:
            self._running = False

    async def _handle_voice_message(self, data: Dict[str, Any]):
        """Handle voice gateway message"""
        op = data.get("op")
        payload = data.get("d", {})

        if op == VoiceOpCode.HELLO:
            await self._handle_hello(payload)
        elif op == VoiceOpCode.READY:
            await self._handle_ready(payload)
        elif op == VoiceOpCode.SESSION_DESCRIPTION:
            await self._handle_session_description(payload)
        elif op == VoiceOpCode.SPEAKING:
            await self._handle_speaking(payload)
        elif op == VoiceOpCode.CLIENT_DISCONNECT:
            await self._handle_client_disconnect(payload)
        elif op == VoiceOpCode.HEARTBEAT_ACK:
            logger.debug("Received heartbeat ACK")
        else:
            logger.debug(f"Unhandled voice opcode: {op}")

    async def _handle_hello(self, payload: Dict[str, Any]):
        """Handle HELLO message"""
        self._heartbeat_interval = payload.get("heartbeat_interval", 41250) / 1000.0

        # Start heartbeat
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        logger.debug(
            f"Voice gateway HELLO received, heartbeat interval: {self._heartbeat_interval}s"
        )

    async def _handle_ready(self, payload: Dict[str, Any]):
        """Handle READY message"""
        self.ssrc = payload.get("ssrc")
        self.ip = payload.get("ip")
        self.port = payload.get("port")

        logger.info(f"Voice gateway READY: IP={self.ip}:{self.port}, SSRC={self.ssrc}")

        # Perform IP discovery
        await self._perform_ip_discovery()

    async def _perform_ip_discovery(self):
        """Perform IP discovery for UDP connection"""
        try:
            # Create UDP socket
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.setblocking(False)

            # Send IP discovery packet
            packet = bytearray(74)
            struct.pack_into(">H", packet, 0, 1)  # Request type
            struct.pack_into(">H", packet, 2, 70)  # Length
            struct.pack_into(">I", packet, 4, self.ssrc)  # SSRC

            await asyncio.get_event_loop().sock_sendto(
                self.udp_socket, packet, (self.ip, self.port)
            )

            # Receive response
            data, addr = await asyncio.get_event_loop().sock_recvfrom(
                self.udp_socket, 74
            )

            # Parse response to get our external IP and port
            ip_start = 8
            ip_end = data.find(b"\x00", ip_start)
            external_ip = data[ip_start:ip_end].decode("ascii")
            external_port = struct.unpack(">H", data[72:74])[0]

            logger.info(f"IP discovery complete: {external_ip}:{external_port}")

            # Send SELECT_PROTOCOL
            await self._send_select_protocol(external_ip, external_port)

        except Exception as e:
            logger.error(f"IP discovery failed: {e}")

    async def _send_select_protocol(self, ip: str, port: int):
        """Send SELECT_PROTOCOL message"""
        payload = {
            "op": VoiceOpCode.SELECT_PROTOCOL,
            "d": {
                "protocol": "udp",
                "data": {"address": ip, "port": port, "mode": "xsalsa20_poly1305"},
            },
        }
        await self.ws.send(json.dumps(payload))
        logger.debug("Sent SELECT_PROTOCOL")

    async def _handle_session_description(self, payload: Dict[str, Any]):
        """Handle SESSION_DESCRIPTION message"""
        mode = payload.get("mode")
        secret_key = payload.get("secret_key")

        if mode == "xsalsa20_poly1305" and secret_key:
            self.secret_key = bytes(secret_key)
            logger.info("Voice session established, starting audio reception")

            # Start receiving audio
            self._receive_task = asyncio.create_task(self._receive_audio())
        else:
            logger.error(f"Unsupported encryption mode or missing secret key: {mode}")

    async def _handle_speaking(self, payload: Dict[str, Any]):
        """Handle SPEAKING event"""
        user_id = int(payload.get("user_id", 0))
        ssrc = payload.get("ssrc")
        speaking = payload.get("speaking", 0)

        if ssrc and user_id:
            self.user_ssrc_map[ssrc] = user_id
            logger.debug(f"User {user_id} speaking state: {speaking} (SSRC: {ssrc})")

    async def _handle_client_disconnect(self, payload: Dict[str, Any]):
        """Handle CLIENT_DISCONNECT event"""
        user_id = int(payload.get("user_id", 0))

        # Remove user from SSRC mapping
        ssrc_to_remove = None
        for ssrc, uid in self.user_ssrc_map.items():
            if uid == user_id:
                ssrc_to_remove = ssrc
                break

        if ssrc_to_remove:
            del self.user_ssrc_map[ssrc_to_remove]
            logger.debug(f"User {user_id} disconnected")

    async def _heartbeat_loop(self):
        """Send heartbeat messages"""
        try:
            while self._running:
                await asyncio.sleep(self._heartbeat_interval)
                if self._running and self.ws:
                    payload = {
                        "op": VoiceOpCode.HEARTBEAT,
                        "d": int(time.time() * 1000),
                    }
                    await self.ws.send(json.dumps(payload))
                    logger.debug("Sent voice heartbeat")
        except asyncio.CancelledError:
            logger.debug("Voice heartbeat cancelled")
        except Exception as e:
            logger.error(f"Error in voice heartbeat: {e}")

    async def _receive_audio(self):
        """Receive and process audio packets"""
        try:
            while self._running and self.udp_socket:
                try:
                    # Receive UDP packet
                    data, addr = await asyncio.get_event_loop().sock_recvfrom(
                        self.udp_socket, 2048
                    )

                    # Process audio packet
                    await self._process_audio_packet(data)

                except Exception as e:
                    if self._running:
                        logger.error(f"Error receiving audio: {e}")
                    break

        except asyncio.CancelledError:
            logger.debug("Audio reception cancelled")
        except Exception as e:
            logger.error(f"Error in audio reception: {e}")

    async def _process_audio_packet(self, data: bytes):
        """Process received audio packet"""
        if len(data) < 12:
            return  # Invalid packet

        try:
            # Parse RTP header
            header = struct.unpack(">BBHII", data[:12])
            version = (header[0] >> 6) & 0x3
            header[1] & 0x7F
            sequence = header[2]
            timestamp = header[3]
            ssrc = header[4]

            if version != 2:
                return  # Invalid RTP version

            # Get user ID from SSRC mapping
            user_id = self.user_ssrc_map.get(ssrc)
            if not user_id:
                return  # Unknown user

            # Check for packet loss
            if ssrc in self.sequence_numbers:
                expected_seq = (self.sequence_numbers[ssrc] + 1) & 0xFFFF
                if sequence != expected_seq:
                    logger.debug(
                        f"Packet loss detected for SSRC {ssrc}: expected {expected_seq}, got {sequence}"
                    )

            self.sequence_numbers[ssrc] = sequence

            # Decrypt audio data if we have the secret key
            encrypted_audio = data[12:]
            if self.secret_key and len(encrypted_audio) > 0:
                try:
                    # Decrypt using XSalsa20-Poly1305
                    box = nacl.secret.SecretBox(self.secret_key)

                    # Create nonce from RTP header
                    nonce = bytearray(24)
                    nonce[:12] = data[:12]

                    decrypted_audio = box.decrypt(encrypted_audio, bytes(nonce))

                    # Create voice packet
                    packet = VoicePacket(
                        sequence=sequence,
                        timestamp=timestamp,
                        ssrc=ssrc,
                        data=encrypted_audio,
                        user_id=user_id,
                        decrypted_data=decrypted_audio,
                    )

                    # Call audio callback
                    if self.audio_callback:
                        await self.audio_callback(packet)

                except Exception as e:
                    logger.debug(f"Failed to decrypt audio packet: {e}")

        except Exception as e:
            logger.error(f"Error processing audio packet: {e}")

    def set_audio_callback(self, callback: Callable):
        """Set callback for received audio packets"""
        self.audio_callback = callback
        logger.debug("Audio callback set")

    def get_connected_users(self) -> Dict[int, int]:
        """Get mapping of SSRC to user IDs"""
        return {ssrc: user_id for ssrc, user_id in self.user_ssrc_map.items()}

    async def send_speaking_state(self, speaking: bool):
        """Send speaking state to voice gateway"""
        if not self.ws:
            return

        payload = {
            "op": VoiceOpCode.SPEAKING,
            "d": {"speaking": 1 if speaking else 0, "delay": 0, "ssrc": self.ssrc},
        }
        await self.ws.send(json.dumps(payload))
        logger.debug(f"Sent speaking state: {speaking}")

    def is_connected(self) -> bool:
        """Check if gateway is connected"""
        return self._running and self.ws is not None and not self.ws.closed

    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        return {
            "connected": self.is_connected(),
            "endpoint": self.endpoint,
            "ssrc": self.ssrc,
            "connected_users": len(self.user_ssrc_map),
            "packets_received": sum(self.sequence_numbers.values()),
            "has_secret_key": self.secret_key is not None,
        }
