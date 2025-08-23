# 🎯 VTuber GUI Wireframe & Architecture Plan

**Generated:** 2025-08-23  
**Purpose:** Complete GUI layout design with proper service routing and backend integration

## 📊 Current GUI Analysis

### ✅ Existing Components (Well-Implemented)
- **ChatDisplayPanel**: Real-time chat with formatting, message types, export functionality
- **VoiceControlsPanel**: Push-to-talk, always-listening, volume monitoring, sensitivity
- **StatusPanel**: Backend connection monitoring, health checks, uptime tracking
- **BackendControlsPanel**: Start/stop backend services, process management
- **MenuBar**: Application-wide actions and settings

### ❌ Missing Components (Need Implementation)
- **CharacterManagerPanel**: Character switching, profile management, creation
- **AudioDevicesPanel**: Device selection, configuration, real-time monitoring
- **TrainingPanel**: Voice model training, progress tracking, dataset management
- **WebhooksPanel**: External integrations, event forwarding
- **SettingsPanel**: Persistent configuration, themes, preferences

## 🏗️ Proposed GUI Architecture

### Main Window Layout (1200x800 minimum)

```
┌────────────────────────────────────────────────────────────────┐
│ Menu Bar: File | Edit | View | Character | Audio | Help        │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌─────────────────┐ ┌─────────────────────────────────────────┐ │
│  │                 │ │                                         │ │
│  │   Character     │ │             Main Content Area           │ │
│  │   Manager       │ │                                         │ │
│  │   Sidebar       │ │          (Tabbed Interface)             │ │
│  │                 │ │                                         │ │
│  │ ┌─────────────┐ │ │ ┌─────┬─────┬─────┬─────┬─────┬─────┐   │ │
│  │ │ Hatsune Miku│●│ │ │💬   │🎤   │🔊   │🏋️   │📊   │⚙️   │   │ │
│  │ │ Assistant   │ │ │ │Chat │Voice│Audio│Train│Sys  │Set  │   │ │
│  │ │ Custom Bot  │ │ │ └─────┴─────┴─────┴─────┴─────┴─────┘   │ │
│  │ │             │ │ │                                         │ │
│  │ └─────────────┘ │ │          Active Tab Content             │ │
│  │                 │ │                                         │ │
│  │ [+ New Character]│ │                                         │ │
│  │                 │ │                                         │ │
│  │ Voice Preview   │ │                                         │ │
│  │ ┌─────────────┐ │ │                                         │ │
│  │ │ [▶] Play    │ │ │                                         │ │
│  │ │ Sample      │ │ │                                         │ │
│  │ └─────────────┘ │ │                                         │ │
│  └─────────────────┘ └─────────────────────────────────────────┘ │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│ Status Bar: 🟢 Backend: Connected | 🎤 Audio: Ready | Uptime: 00:42:15 │
└────────────────────────────────────────────────────────────────┘
```

## 🗂️ Detailed Tab Layouts

### 💬 Chat Studio Tab (Enhanced)
```
┌──────────────────────────────────────────────────────────────────┐
│  Chat Conversation Area (Scrollable)                            │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ [15:24] System: Welcome to VTuber Chat! 🎉                 │  │
│  │                                                            │  │
│  │ [15:25] You:                                               │  │
│  │     Hello! How are you today?                             │  │
│  │                                                            │  │
│  │                           [15:25] Miku (Happy):           │  │
│  │                    Hi there! I'm doing wonderful! ✨      │  │
│  │                    Ready to chat and sing with you! 🎵     │  │
│  │                                                            │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌─────────────────────────────────┬──────────────────────────┐  │
│  │ Type your message here...       │ [🎤 Voice] [📤 Send]   │  │
│  └─────────────────────────────────┴──────────────────────────┘  │
│                                                                  │
│  [🗑️ Clear] [💾 Export] [🔍 Search] [📊 Stats] [⚙️ Chat Settings] │
└──────────────────────────────────────────────────────────────────┘
```

### 🎤 Voice Studio Tab (Enhanced)
```
┌──────────────────────────────────────────────────────────────────┐
│ ┌─────────────────────┐ ┌─────────────────────────────────────────┐ │
│ │   Voice Controls    │ │           Audio Waveform               │ │
│ │                     │ │  ┌───────────────────────────────────┐  │ │
│ │ Mode:               │ │  │ ∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿ │  │ │
│ │ ● Push to Talk      │ │  └───────────────────────────────────┘  │ │
│ │ ○ Always Listen     │ │                                         │ │
│ │                     │ │ Status: 🎤 Ready to Record             │ │
│ │ [🎤 Hold to Talk]   │ │                                         │ │
│ │                     │ │ Last Recording: 00:03.2 (95% confidence)│ │
│ │ Volume: ████████▒▒  │ │                                         │ │
│ │ 80%                 │ │ ┌─────────────────────────────────────┐ │ │
│ │                     │ │ │ Transcription:                      │ │ │
│ │ Sensitivity: 50     │ │ │ "Hello, can you hear me clearly?"  │ │ │
│ │ ▓▓▓▓▓▒▒▒▒▒          │ │ │                                     │ │ │
│ │                     │ │ │ [🔄 Retry] [✅ Accept] [❌ Discard] │ │ │
│ │ VAD Threshold: 0.3  │ │ └─────────────────────────────────────┘ │ │
│ │ ▓▓▓▒▒▒▒▒▒▒          │ │                                         │ │
│ └─────────────────────┘ └─────────────────────────────────────────┘ │
│                                                                  │
│ [🎵 Generate TTS] [▶️ Play Last] [💾 Save Recording] [⚙️ Settings] │
└──────────────────────────────────────────────────────────────────┘
```

### 🔊 Audio Devices Tab (NEW)
```
┌──────────────────────────────────────────────────────────────────┐
│ ┌─────────────────────────┐ ┌─────────────────────────────────────┐ │
│ │    Input Devices        │ │       Output Devices              │ │
│ │                         │ │                                     │ │
│ │ ● Microphone (USB)      │ │ ● Speakers (USB Headset)           │ │
│ │ ○ Built-in Microphone   │ │ ○ Built-in Speakers                 │ │
│ │ ○ Virtual Audio Cable  │ │ ○ Virtual Audio Cable               │ │
│ │ ○ VoiceMeeter Output    │ │ ○ VoiceMeeter Input                 │ │
│ │                         │ │                                     │ │
│ │ Sample Rate: 44.1kHz    │ │ Volume: ████████▒▒ 85%             │ │
│ │ Bit Depth: 16-bit       │ │ [🔇] [Test Audio]                   │ │
│ │ Channels: Mono          │ │                                     │ │
│ │                         │ │ Output Format: WAV 44.1kHz          │ │
│ │ [🎤 Test Mic]          │ │ Latency: 12ms (Low)                 │ │
│ └─────────────────────────┘ └─────────────────────────────────────┘ │
│                                                                  │
│ Real-time Audio Monitor:                                         │
│ Input Level:  ████████▒▒ Recording: 🔴                           │
│ Output Level: ██████▒▒▒▒ Playing: 🟢                             │
│                                                                  │
│ [🔄 Refresh Devices] [⚙️ Advanced Settings] [📊 Audio Diagnostics] │
└──────────────────────────────────────────────────────────────────┘
```

### 🏋️ Training Tab (NEW)
```
┌──────────────────────────────────────────────────────────────────┐
│ ┌─────────────────────┐ ┌─────────────────────────────────────────┐ │
│ │   Active Jobs       │ │         Training Progress              │ │
│ │                     │ │                                         │ │
│ │ 🟢 miku_voice_v2    │ │ Job: miku_voice_v2                     │ │
│ │ Epoch 45/100 (45%)  │ │ ████████████▒▒▒▒▒▒▒▒ 45%              │ │
│ │ ETA: 2h 15m         │ │                                         │ │
│ │                     │ │ Loss: 0.0234 (↓ improving)             │ │
│ │ ⏸️  assistant_bot   │ │ Learning Rate: 0.001                   │ │
│ │ Paused at 23%       │ │ Samples Processed: 12,450/27,600       │ │
│ │                     │ │                                         │ │
│ │ ✅ basic_voice_v1   │ │ ┌─────────────────────────────────────┐ │ │
│ │ Completed 100%      │ │ │ Recent Logs:                        │ │ │
│ │                     │ │ │ [14:23] Processing batch 245/552   │ │ │
│ │ [+ New Training]    │ │ │ [14:22] Validation loss: 0.0241    │ │ │
│ └─────────────────────┘ │ │ [14:21] Checkpoint saved           │ │ │
│                         │ │ [14:20] GPU memory: 6.2GB/8GB      │ │ │
│                         │ └─────────────────────────────────────┘ │ │
│                         │                                         │ │
│                         │ [⏸️ Pause] [⏹️ Stop] [💾 Save Checkpoint] │ │
│                         └─────────────────────────────────────────┘ │
│                                                                  │
│ Dataset Management:                                              │
│ Audio Files: 2,847 clips (3.2GB) | Transcripts: 100% complete    │
│ [📁 Browse] [🎵 Preview] [✏️ Edit Labels] [🔄 Rescan]           │
└──────────────────────────────────────────────────────────────────┘
```

### 📊 System Tab (Enhanced)
```
┌──────────────────────────────────────────────────────────────────┐
│ ┌─────────────────────────┐ ┌─────────────────────────────────────┐ │
│ │    System Status        │ │        Resource Monitor            │ │
│ │                         │ │                                     │ │
│ │ Backend: 🟢 Running     │ │ CPU Usage: ████████▒▒ 83%          │ │
│ │ Uptime: 2h 42m 15s      │ │ Memory: ██████▒▒▒▒ 62% (4.8GB)     │ │
│ │                         │ │ GPU: ████████████ 98% (Training)   │ │
│ │ Audio: 🟢 Ready         │ │ Disk: ███▒▒▒▒▒▒▒ 34% (125GB free)  │ │
│ │ Devices: 46 detected    │ │                                     │ │
│ │                         │ │ Network: ↑ 12KB/s ↓ 45KB/s         │ │
│ │ WebSocket: 🟢 Connected │ │ Temperature: CPU 67°C GPU 82°C      │ │
│ │ Events: 1,247 logged    │ │                                     │ │
│ │                         │ │ ┌─────────────────────────────────┐ │ │
│ │ [🔄 Refresh]           │ │ │ Active Processes:               │ │ │
│ │ [🔗 Test Connection]   │ │ │ aichat-backend    PID: 12455    │ │ │
│ │                         │ │ │ python (training) PID: 12889    │ │ │
│ │                         │ │ │ GPU Process       PID: 13021    │ │ │
│ │                         │ │ └─────────────────────────────────┘ │ │
│ └─────────────────────────┘ └─────────────────────────────────────┘ │
│                                                                  │
│ Event Log (Recent):                                              │
│ [15:42] INFO: Chat message processed (2.3ms)                     │
│ [15:41] SUCCESS: TTS generated for character 'miku' (1.2s)       │
│ [15:40] WARNING: High GPU usage detected (98%)                   │
│ [📊 View All Events] [🗑️ Clear Log] [💾 Export] [⚙️ Log Settings] │
└──────────────────────────────────────────────────────────────────┘
```

### ⚙️ Settings Tab (NEW)
```
┌──────────────────────────────────────────────────────────────────┐
│ ┌─────────────────────┐ ┌─────────────────────────────────────────┐ │
│ │   Setting Groups    │ │           Configuration                │ │
│ │                     │ │                                         │ │
│ │ ● General           │ │ General Settings:                       │ │
│ │   Audio             │ │                                         │ │
│ │   Voice             │ │ ☑ Start backend on app launch           │ │
│ │   Training          │ │ ☑ Auto-save chat history                │ │
│ │   Appearance        │ │ ☑ Show system notifications             │ │
│ │   Advanced          │ │ ☐ Start minimized to tray               │ │
│ │                     │ │                                         │ │
│ │                     │ │ Default Character: [Hatsune Miku    ▼]  │ │
│ │                     │ │ Auto-clear chat after: [100 messages▼] │ │
│ │                     │ │ Backup frequency: [Daily          ▼]   │ │
│ │                     │ │                                         │ │
│ │                     │ │ Backend Settings:                       │ │
│ │                     │ │ Host: [localhost        ]               │ │
│ │                     │ │ Port: [8765            ]                │ │
│ │                     │ │ Timeout: [10s          ]                │ │
│ │                     │ │                                         │ │
│ │                     │ │ [🔑 API Keys] [🌐 Webhooks] [📁 Paths] │ │
│ └─────────────────────┘ └─────────────────────────────────────────┘ │
│                                                                  │
│ [💾 Save Settings] [🔄 Reset to Defaults] [📤 Export Config]      │
└──────────────────────────────────────────────────────────────────┘
```

## 🔗 Backend Service Integration Map

### Current API Routing (✅ Implemented & Tested)
```
GUI Component              → Backend Route                    → Service
─────────────────────────────────────────────────────────────────────────
ChatDisplayPanel           → /api/chat/chat                  → ChatService
                           → /api/chat/characters            → ChatService
                           → /api/chat/switch_character      → ChatService  
                           → /api/chat/chat/history          → DatabaseOps

VoiceControlsPanel         → /api/voice/audio/record         → AudioIOService
                           → /api/voice/audio/play           → AudioIOService
                           → /api/chat/stt                   → WhisperService

StatusPanel                → /api/system/status              → SystemService
                           → /api/system/info                → SystemService

BackendControlsPanel       → Process Management (Local)      → subprocess

VTuberAPIClient           → All above routes                 → All Services
```

### Missing GUI Integrations (❌ Need Implementation)
```
Component Needed           → Backend Route Available         → Service Ready
─────────────────────────────────────────────────────────────────────────
CharacterManagerPanel     → /api/chat/characters (CRUD)     → ✅ ChatService
                           → /api/chat/characters/{id}       → ✅ ChatService

AudioDevicesPanel         → /api/voice/audio/devices        → ✅ AudioIOService
                           → /api/voice/audio/input-device  → ✅ AudioIOService
                           → /api/voice/audio/output-device → ✅ AudioIOService
                           → /api/voice/audio/status        → ✅ AudioIOService

TrainingPanel             → /api/voice/jobs/{id}/checkpoint → ✅ Training Jobs
                           → /api/voice/jobs/{id}/logs      → ✅ Training Jobs
                           
WebhooksPanel             → /api/system/webhooks            → ✅ EventSystem
                           → /api/system/webhooks (POST)    → ✅ EventSystem
                           → /api/system/webhooks/test      → ✅ EventSystem

SettingsPanel             → Local Configuration Files       → ❌ Need Config Service
```

## 📱 Responsive Design Considerations

### Window Sizing & Scaling
- **Minimum Size**: 1000x700 (all components visible)
- **Recommended**: 1200x800 (optimal layout)
- **Maximum**: Unlimited (components scale proportionally)
- **DPI Scaling**: Support high-DPI displays with theme scaling

### Layout Adaptations
- **Narrow Windows**: Character sidebar collapses to dropdown
- **Tall Windows**: Chat area expands, more message history visible
- **Ultra-wide**: Additional panels can be shown side-by-side

## 🎨 Visual Design System

### Color Scheme (Dark Theme)
```
Primary Background:   #1a1a1a
Secondary Background: #2d2d2d  
Accent Color:         #00d4aa (Teal/Cyan - VTuber theme)
Success:              #4CAF50
Warning:              #FF9800
Error:                #f44336
Text Primary:         #ffffff
Text Secondary:       #b0b0b0
Text Muted:           #666666
```

### Typography
```
Headers:    Segoe UI Bold, 16px
Subheaders: Segoe UI Semibold, 14px
Body Text:  Segoe UI Regular, 12px
Monospace:  Consolas, 11px (for logs/code)
```

### Component Styling
- **Rounded corners**: 8px for panels, 4px for buttons
- **Shadows**: Subtle drop shadows for depth
- **Borders**: 1px solid with accent color for focus
- **Animations**: Smooth transitions (200ms ease)

## 🔧 Implementation Priority

### Phase 1: Complete Core Features (High Priority)
1. **CharacterManagerPanel** - Character switching is critical for user experience
2. **AudioDevicesPanel** - Device management essential for voice functionality
3. **Enhanced Chat Features** - Search, statistics, advanced formatting

### Phase 2: Advanced Features (Medium Priority)  
1. **TrainingPanel** - Voice model training interface
2. **SettingsPanel** - Persistent configuration management
3. **WebhooksPanel** - External integrations

### Phase 3: Polish & Optimization (Low Priority)
1. **Responsive design refinements**
2. **Keyboard shortcuts** 
3. **Advanced theming system**
4. **Plugin architecture**

## 🚀 Technical Implementation Notes

### Component Architecture
- **Base Class**: All panels inherit from `PanelComponent`
- **Event System**: Use existing event-driven architecture for component communication
- **Dependency Injection**: Integrate with existing DI container for service access
- **Theme System**: Extend existing theme system for consistent styling

### Backend Integration
- **API Client**: Extend `VTuberAPIClient` with new endpoint methods
- **Error Handling**: Consistent error handling with user-friendly messages  
- **Real-time Updates**: Use WebSocket events for live status updates
- **Caching**: Implement intelligent caching for frequently accessed data

### Performance Considerations
- **Lazy Loading**: Load tabs/components only when accessed
- **Virtualization**: For large lists (chat history, training logs)
- **Background Processing**: Non-blocking operations for API calls
- **Memory Management**: Proper cleanup of event handlers and timers

## 📋 User Experience Flow

### Primary User Journeys
1. **Quick Chat**: Select character → Type/speak → Get AI response → Generate TTS
2. **Voice Training**: Upload audio → Review transcripts → Start training → Monitor progress
3. **System Management**: Check status → Adjust settings → Monitor resources → Export logs

### Accessibility Features
- **Keyboard Navigation**: Full tab-based navigation support
- **Screen Reader**: ARIA labels and semantic HTML structure
- **High Contrast**: Alternative color scheme for visibility
- **Font Scaling**: Respect system font size preferences

This comprehensive wireframe ensures all backend services are properly utilized and provides a complete, user-friendly interface for the VTuber AI system.