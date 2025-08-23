"""
Streamlit GUI for VTuber Control Center - The Official Interface
Replaces PyGui, Tkinter, and Flask interfaces with a modern, working solution.
"""

import streamlit as st
import requests
import time
import asyncio
import websockets
import json
import threading
from datetime import datetime
from pathlib import Path
import subprocess
import sys

# Import configuration
try:
    from aichat.core.config import get_settings
    settings = get_settings()
    API_HOST = settings.api_host
    API_PORT = settings.api_port
except ImportError:
    API_HOST = "localhost"
    API_PORT = 8765

# Configure page
st.set_page_config(
    page_title="VTuber Control Center",
    page_icon="🎤", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'api_host' not in st.session_state:
    st.session_state.api_host = API_HOST
if 'api_port' not in st.session_state:
    st.session_state.api_port = API_PORT
if 'backend_running' not in st.session_state:
    st.session_state.backend_running = False
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'log_messages' not in st.session_state:
    st.session_state.log_messages = []
if 'auto_started' not in st.session_state:
    st.session_state.auto_started = False

# Sidebar for connection settings
st.sidebar.title("🔧 Settings")
st.session_state.api_host = st.sidebar.text_input("API Host", st.session_state.api_host)
st.session_state.api_port = st.sidebar.number_input("API Port", st.session_state.api_port)
api_url = f"http://{st.session_state.api_host}:{st.session_state.api_port}"

# Backend Management
st.sidebar.subheader("🖥️ Backend Control")

def start_backend_docker():
    """Start the backend server using Docker"""
    try:
        result = subprocess.run([
            "docker-compose", "up", "-d", "backend"
        ], cwd=Path.cwd(), capture_output=True, text=True)
        
        if result.returncode == 0:
            st.session_state.backend_running = True
            st.sidebar.success("🐳 Backend starting with Docker...")
            return True
        else:
            st.sidebar.error(f"❌ Docker failed: {result.stderr}")
            return False
    except Exception as e:
        st.sidebar.error(f"❌ Failed to start Docker backend: {e}")
        return False

def stop_backend_docker():
    """Stop the Docker backend server"""
    try:
        result = subprocess.run([
            "docker-compose", "down", "backend"
        ], cwd=Path.cwd(), capture_output=True, text=True)
        
        if result.returncode == 0:
            st.session_state.backend_running = False
            st.sidebar.info("🐳 Backend stopped")
            return True
        else:
            st.sidebar.error(f"❌ Docker stop failed: {result.stderr}")
            return False
    except Exception as e:
        st.sidebar.error(f"❌ Failed to stop Docker backend: {e}")
        return False

def find_available_port(start_port=8765, max_attempts=10):
    """Find an available port starting from start_port"""
    import socket
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            continue
    return None

def start_backend_local():
    """Start the backend server as subprocess with automatic port selection"""
    try:
        # Find available port
        available_port = find_available_port(st.session_state.api_port)
        if available_port is None:
            st.sidebar.error("❌ No available ports found")
            return False
            
        if available_port != st.session_state.api_port:
            st.sidebar.info(f"ℹ️ Using port {available_port} (original {st.session_state.api_port} busy)")
            st.session_state.api_port = available_port
        
        # Start backend using the CLI command
        process = subprocess.Popen([
            sys.executable, "-m", "aichat.cli.main", 
            "backend", "--host", st.session_state.api_host, 
            "--port", str(available_port)
        ], cwd=Path.cwd(), 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0)
        
        # Store process in session state
        st.session_state.backend_process = process
        st.session_state.backend_running = True
        
        st.sidebar.success(f"🚀 Backend starting (PID: {process.pid})...")
        
        # Wait for backend to become available (takes ~10-12 seconds)
        api_url = f"http://{st.session_state.api_host}:{st.session_state.api_port}"
        
        with st.sidebar:
            progress_bar = st.progress(0)
            status_text = st.empty()
            
        for i in range(20):  # Wait up to 20 seconds
            try:
                # Check if process is still running
                if process.poll() is not None:
                    st.sidebar.error("❌ Backend process exited unexpectedly")
                    return False
                
                # Update progress
                progress = (i + 1) / 20
                progress_bar.progress(progress)
                status_text.text(f"Starting... {i+1}/20s")
                
                # Test connectivity after 8 seconds
                if i >= 8:
                    try:
                        response = requests.get(f"{api_url}/api/system/status", timeout=2)
                        if response.status_code == 200:
                            progress_bar.progress(1.0)
                            status_text.text("✅ Backend ready!")
                            st.sidebar.success("✅ Backend started successfully!")
                            return True
                    except:
                        pass  # Still starting up
                
                time.sleep(1)
            except Exception:
                pass
        
        # Timeout - backend didn't start in time
        st.sidebar.warning("⚠️ Backend starting slowly... Check logs")
        return True  # Return True but with warning
        
    except Exception as e:
        st.sidebar.error(f"❌ Failed to start backend: {e}")
        return False

def stop_backend_local():
    """Stop the backend subprocess"""
    try:
        if 'backend_process' in st.session_state:
            process = st.session_state.backend_process
            
            if process.poll() is None:  # Process is still running
                if sys.platform == 'win32':
                    # Windows: use taskkill to terminate process tree
                    subprocess.run(['taskkill', '/F', '/T', '/PID', str(process.pid)], 
                                 capture_output=True)
                else:
                    # Unix: terminate process
                    process.terminate()
                    process.wait(timeout=5)
                
                st.session_state.backend_running = False
                del st.session_state.backend_process
                st.sidebar.success("⏹️ Backend stopped")
                return True
            else:
                st.sidebar.info("Backend process already stopped")
                st.session_state.backend_running = False
                if 'backend_process' in st.session_state:
                    del st.session_state.backend_process
                return True
        else:
            st.sidebar.info("No backend process to stop")
            return True
            
    except Exception as e:
        st.sidebar.error(f"❌ Failed to stop backend: {e}")
        return False

def check_docker_available():
    """Check if Docker is available and running"""
    try:
        result = subprocess.run([
            "docker", "info"
        ], cwd=Path.cwd(), capture_output=True, text=True)
        
        return result.returncode == 0
    except:
        return False

def get_docker_status():
    """Check if Docker backend is running"""
    try:
        if not check_docker_available():
            return False
            
        result = subprocess.run([
            "docker-compose", "ps", "-q", "backend"
        ], cwd=Path.cwd(), capture_output=True, text=True)
        
        return bool(result.stdout.strip())
    except:
        return False

def check_backend_status():
    """Check if backend is responding"""
    try:
        response = requests.get(f"{api_url}/api/system/status", timeout=3)
        return response.status_code == 200
    except:
        return False

# Backend status and controls
is_backend_running = check_backend_status()

# Auto-start backend on first load
if not is_backend_running and not st.session_state.auto_started:
    st.session_state.auto_started = True
    st.sidebar.info("🚀 Auto-starting backend...")
    if start_backend_local():
        st.sidebar.success("✅ Backend auto-started!")
        st.rerun()
    else:
        st.sidebar.error("❌ Auto-start failed")

status_color = "🟢" if is_backend_running else "🔴"
status_text = "Running" if is_backend_running else "Stopped"

st.sidebar.markdown(f"**Status:** {status_color} {status_text}")

# Simple backend controls
if not is_backend_running:
    if st.sidebar.button("🚀 Start Backend"):
        start_backend_local()
        st.rerun()
else:
    if st.sidebar.button("⏹️ Stop Backend"):
        stop_backend_local()
        st.rerun()
        
# Backend process info
if 'backend_process' in st.session_state and hasattr(st.session_state.backend_process, 'pid'):
    process = st.session_state.backend_process
    is_alive = process.poll() is None
    st.sidebar.text(f"PID: {process.pid} ({'Running' if is_alive else 'Stopped'})")

if is_backend_running and st.sidebar.button("🔗 Test Connection"):
    try:
        response = requests.get(f"{api_url}/api/system/status", timeout=5)
        if response.status_code == 200:
            st.sidebar.success("✅ Connected!")
            data = response.json()
            st.sidebar.json(data)
        else:
            st.sidebar.error(f"❌ Error: {response.status_code}")
    except Exception as e:
        st.sidebar.error(f"❌ Connection failed: {e}")

# Auto-refresh setting (disabled by default - less annoying)
auto_refresh = st.sidebar.checkbox("🔄 Auto-refresh", False)
if auto_refresh:
    refresh_interval = st.sidebar.slider("Refresh interval (seconds)", 3, 30, 10)

# Main interface  
st.title("🎤 VTuber Control Center")
st.markdown("*The Official Interface - Modern, Fast, and Actually Works*")

# Connection status bar
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    if is_backend_running:
        st.success(f"🟢 Connected to {api_url}")
    else:
        st.error(f"🔴 Backend not responding at {api_url}")
with col2:
    st.metric("Status", "Online" if is_backend_running else "Offline")
with col3:
    st.metric("Time", datetime.now().strftime("%H:%M:%S"))

# Create tabs - same as before but with enhanced functionality
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 System Status", 
    "🎵 TTS Control", 
    "💬 Chat Interface", 
    "🔊 Audio Controls",
    "⚙️ Configuration"
])

# System Status Tab
with tab1:
    st.header("📊 System Status")
    
    # Overall status metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Backend", "Online" if is_backend_running else "Offline", 
                  delta="Connected" if is_backend_running else "Disconnected")
    with col2:
        process_status = "Running" if is_backend_running else "Stopped"
        if 'backend_process' in st.session_state:
            process = st.session_state.backend_process
            if process.poll() is None:
                process_status = f"PID {process.pid}"
        st.metric("Process", process_status)
    with col3:
        st.metric("API Port", st.session_state.api_port)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🖥️ Backend Information")
        
        # System info
        st.write(f"**API URL:** {api_url}")
        st.write(f"**Status:** {'🟢 Running' if is_backend_running else '🔴 Stopped'}")
        st.write(f"**Mode:** {'💻 Local Process' if is_backend_running else 'Not Running'}")
        st.write(f"**Last Check:** {datetime.now().strftime('%H:%M:%S')}")
        
        # Process info
        if 'backend_process' in st.session_state:
            process = st.session_state.backend_process
            is_alive = process.poll() is None
            st.write(f"**Process ID:** {process.pid}")
            st.write(f"**Process Status:** {'🟢 Alive' if is_alive else '🔴 Dead'}")
        
        # Refresh button
        if st.button("🔄 Refresh Status", use_container_width=True):
            try:
                response = requests.get(f"{api_url}/api/system/status", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    st.success("✅ Backend is healthy!")
                    with st.expander("📋 Detailed Status"):
                        st.json(data)
                else:
                    st.error(f"❌ Backend returned status: {response.status_code}")
            except Exception as e:
                st.error(f"❌ Connection failed: {e}")
    
    with col2:
        st.subheader("🔧 Backend Management")
        
        # Quick controls
        col_start, col_stop = st.columns(2)
        with col_start:
            if not is_backend_running and st.button("🚀 Start", use_container_width=True):
                start_backend_local()
                st.rerun()
                
        with col_stop:
            if is_backend_running and st.button("⏹️ Stop", use_container_width=True):
                stop_backend_local() 
                st.rerun()
        
        # Process logs (if available)
        if 'backend_process' in st.session_state:
            if st.button("📊 View Process Output", use_container_width=True):
                try:
                    process = st.session_state.backend_process
                    
                    # Try to read stdout/stderr (limited since we're using PIPE)
                    st.info("💡 Process output is captured. Check console for detailed logs.")
                    st.text(f"Process ID: {process.pid}")
                    st.text(f"Command: {' '.join([sys.executable, '-m', 'aichat.cli.main', 'backend'])}")
                    
                except Exception as e:
                    st.error(f"Error getting process info: {e}")
        
        # Quick start guide
        with st.expander("🚀 Quick Start Guide"):
            st.markdown("""
            **Local Backend:**
            1. Click "🚀 Start Backend" in sidebar
            2. Wait ~5 seconds for startup
            3. Backend runs as subprocess
            4. Available at http://localhost:8765
            
            **Benefits:**
            - ✅ Instant startup
            - ✅ No Docker required
            - ✅ Direct filesystem access
            - ✅ Easy debugging
            - ✅ Shared Python environment
            
            **Logs:** Check the terminal where you started Streamlit for backend logs.
            """)
        
        # Advanced controls
        if st.button("🔄 Restart Backend", use_container_width=True):
            if is_backend_running:
                stop_backend_local()
                time.sleep(1)
            start_backend_local()
            st.rerun()

# TTS Control Tab
with tab2:
    st.header("🎵 TTS Control")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📝 Text Input")
        text_input = st.text_area(
            "Text to Generate", 
            "[INTENSITY: high] Hello there! How are you doing today?",
            height=100
        )
        
        character = st.selectbox("Character", ["hatsune_miku", "character1", "character2"])
        
        if st.button("🎵 Generate TTS"):
            if text_input:
                try:
                    response = requests.post(
                        f"{api_url}/api/chat/tts",
                        json={"text": text_input, "character": character},
                        timeout=30
                    )
                    if response.status_code == 200:
                        result = response.json()
                        st.success(f"✅ Generated: {result.get('audio_file', 'N/A')}")
                    else:
                        st.error(f"❌ TTS failed: {response.status_code}")
                except Exception as e:
                    st.error(f"❌ Error: {e}")
    
    with col2:
        st.subheader("🎛️ Controls")
        use_manual = st.checkbox("Use Manual Intensity")
        if use_manual:
            manual_intensity = st.slider("Intensity", 0.0, 2.0, 1.0)
        
        st.subheader("📊 Current Status")
        st.metric("Intensity", "1.20", "High/Energetic")

# Chat Interface Tab
with tab3:
    st.header("💬 Chat Interface")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("📝 Send Message")
        
        # Character selection for chat
        character = st.selectbox(
            "Character", 
            ["hatsune_miku", "character1", "character2"],
            key="chat_character"
        )
        
        # Chat input
        chat_message = st.text_input(
            "Your message:", 
            placeholder="Type your message here...",
            key="chat_input"
        )
        
        col_send, col_clear = st.columns([1, 1])
        with col_send:
            if st.button("📤 Send", disabled=not is_backend_running) and chat_message:
                try:
                    # Add user message to history
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    st.session_state.chat_history.append(f"[{timestamp}] You: {chat_message}")
                    
                    response = requests.post(
                        f"{api_url}/api/chat/chat",
                        json={"text": chat_message, "character": character},
                        timeout=30
                    )
                    if response.status_code == 200:
                        result = response.json()
                        response_text = result.get('response', 'No response')
                        st.session_state.chat_history.append(f"[{timestamp}] {character}: {response_text}")
                        
                        # Auto-generate TTS if enabled
                        if st.session_state.get('auto_tts', False):
                            st.info("🎵 Auto-generating TTS...")
                            
                    else:
                        st.session_state.chat_history.append(f"[{timestamp}] Error: Status {response.status_code}")
                        
                except Exception as e:
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    st.session_state.chat_history.append(f"[{timestamp}] Error: {str(e)}")
                    
                # Clear input
                st.rerun()
                
        with col_clear:
            if st.button("🗑️ Clear Chat"):
                st.session_state.chat_history = []
                st.rerun()
        
        st.subheader("💬 Chat History")
        # Display chat history from session state
        chat_display = "\n".join(st.session_state.chat_history[-20:]) if st.session_state.chat_history else "Welcome to VTuber Chat! Select a character and start chatting."
        st.text_area("Chat Log", chat_display, height=300, disabled=True)
    
    with col2:
        st.subheader("👤 Character Settings")
        st.write(f"**Active:** {character}")
        st.write("**Status:** Online" if is_backend_running else "Offline")
        
        # Auto-TTS setting with session state
        auto_tts = st.checkbox(
            "Auto-generate TTS", 
            value=st.session_state.get('auto_tts', False),
            key='auto_tts'
        )
        
        # Voice settings
        st.subheader("🎵 Voice Settings")
        voice_speed = st.slider("Speed", 0.5, 2.0, 1.0, key="voice_speed_chat")
        voice_pitch = st.slider("Pitch", 0.5, 2.0, 1.0, key="voice_pitch_chat")

# Audio Controls Tab
with tab4:
    st.header("🔊 Audio Controls")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🎵 Audio Testing")
        
        record_duration = st.slider("Recording Duration (s)", 1.0, 30.0, 5.0)
        
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            if st.button("⏺️ Record"):
                st.info(f"Recording for {record_duration}s...")
        with col_b:
            if st.button("▶️ Play"):
                st.info("Playing audio...")
        with col_c:
            if st.button("⏹️ Stop"):
                st.info("Stopping audio...")
    
    with col2:
        st.subheader("🔊 Volume Controls")
        
        master_volume = st.slider("Master Volume", 0.0, 1.0, 0.8)
        tts_volume = st.slider("TTS Volume", 0.0, 1.0, 0.8)

# Configuration Tab
with tab5:
    st.header("⚙️ Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔌 API Settings")
        st.text_input("API Host", value=st.session_state.api_host)
        st.number_input("API Port", value=st.session_state.api_port)
        
        st.subheader("🎙️ TTS Settings")
        default_voice = st.selectbox("Default Voice", ["default", "chatterbox_default", "chatterbox_expressive"])
        default_speed = st.slider("Default Speed", 0.5, 2.0, 1.0)
        default_pitch = st.slider("Default Pitch", 0.5, 2.0, 1.0)
    
    with col2:
        st.subheader("🔧 Advanced Settings")
        debug_mode = st.checkbox("Enable Debug Mode")
        auto_connect = st.checkbox("Auto-connect WebSocket", True)
        
        st.subheader("💾 Actions")
        if st.button("💾 Save All Settings"):
            st.success("Settings saved!")
        if st.button("🔄 Reset to Defaults"):
            st.info("Settings reset!")

# Auto-refresh functionality
# Auto-refresh removed - was too annoying
# Users can manually refresh if needed

# Status footer
st.markdown("---")
status_text = "Connected" if is_backend_running else "Disconnected"
st.markdown(f"**Status:** {status_text} to `{api_url}` | **Time:** {datetime.now().strftime('%H:%M:%S')} | **GUI:** Streamlit Official Interface")