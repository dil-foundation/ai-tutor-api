# OpenAI Realtime WebSocket Workflow Diagram

## Complete System Workflow

```mermaid
sequenceDiagram
    participant Client
    participant WS_Endpoint as WebSocket Endpoint<br/>(/ws/openai-realtime)
    participant Bridge as OpenAIRealtimeBridge
    participant OpenAI as OpenAI Realtime API
    participant TTS_Worker as TTS Worker Thread
    participant ElevenLabs as ElevenLabs TTS API

    Note over Client,ElevenLabs: === INITIALIZATION PHASE ===
    
    Client->>WS_Endpoint: WebSocket Connect
    WS_Endpoint->>WS_Endpoint: Accept Connection
    WS_Endpoint->>Bridge: Initialize Bridge(client_ws)
    Bridge->>Bridge: Initialize State Variables<br/>(buffers, queues, flags)
    
    Bridge->>Bridge: Create HTTP Client for ElevenLabs
    Bridge->>OpenAI: Connect WebSocket<br/>(wss://api.openai.com/v1/realtime)
    OpenAI-->>Bridge: Connection Established
    
    Bridge->>OpenAI: Send session.update<br/>(modalities: audio/text,<br/>turn_detection: None,<br/>instructions: SYSTEM_PROMPT)
    OpenAI-->>Bridge: session.created
    OpenAI-->>Bridge: session.updated
    Bridge->>Bridge: Set session_ready = True
    
    Bridge->>Bridge: Start _listen_to_openai() task
    Bridge->>Bridge: Start _tts_worker() task
    
    WS_Endpoint->>Client: Send {"type": "connected"}

    Note over Client,ElevenLabs: === AUDIO STREAMING PHASE ===
    
    loop For Each Audio Chunk
        Client->>WS_Endpoint: Send Binary Audio Data
        WS_Endpoint->>Bridge: send_audio_to_openai(audio_bytes)
        
        alt Session Not Ready
            Bridge->>Bridge: Wait up to 5s for session_ready
        end
        
        Bridge->>Bridge: convert_audio_to_pcm16()<br/>(Convert to 24kHz, mono, 16-bit PCM)
        Bridge->>Bridge: Base64 Encode PCM16 Audio
        Bridge->>OpenAI: input_audio_buffer.append<br/>(audio: base64_encoded)
        
        OpenAI-->>Bridge: (No error response)
        Bridge->>Bridge: Track buffer_size_bytes<br/>Track audio_chunks_count
        Bridge->>Bridge: Wait 0.08s, check for errors
        
        alt Append Error Received
            Bridge->>Bridge: Track error in append_errors
            Bridge->>Bridge: Return False (don't track buffer)
        else Success
            Bridge->>Bridge: Increment buffer tracking
        end
    end

    Note over Client,ElevenLabs: === COMMIT & RESPONSE PHASE ===
    
    Client->>WS_Endpoint: Send {"type": "audio_commit"}
    WS_Endpoint->>Bridge: commit_audio_and_get_response()
    
    alt Response Already In Progress
        Bridge->>Client: Send Error: "response_in_progress"
    else Insufficient Audio (< 4800 bytes)
        Bridge->>Client: Send Error: "insufficient_audio"
    else Valid Commit
        Bridge->>Bridge: Reset response state<br/>(response_done = False,<br/>clear text buffers)
        
        Bridge->>OpenAI: input_audio_buffer.commit
        OpenAI-->>Bridge: input_audio_buffer.commit (confirmation)
        
        Bridge->>Bridge: Reset buffer tracking
        Bridge->>OpenAI: response.create<br/>(modalities: ["text"])
        
        Note over OpenAI: OpenAI processes audio<br/>and generates text response
        
        loop Text Delta Streaming
            OpenAI-->>Bridge: response.output_text.delta<br/>(or response.text.delta)
            Bridge->>Bridge: Append to response_text<br/>Append to partial_text_buffer
            Bridge->>Bridge: _try_flush_partial_segment()<br/>(Check for complete sentences)
            
            alt Complete Sentence Found (≥80 chars)
                Bridge->>Bridge: Extract sentence segment
                Bridge->>Bridge: _enqueue_tts_segment(segment)
                Bridge->>TTS_Worker: Queue.put_nowait(segment)
            end
            
            Bridge->>Client: Send {"type": "transcript_delta",<br/>"text": accumulated_text}
        end
        
        OpenAI-->>Bridge: response.output_text.done<br/>(or response.text.done)
        Bridge->>Bridge: Finalize response_text
        Bridge->>Client: Send {"type": "transcript_done",<br/>"text": final_text}
        Bridge->>Bridge: _finalize_tts_segments()<br/>(Flush remaining buffer)
        Bridge->>TTS_Worker: Queue.put_nowait("", is_final=True)
        
        OpenAI-->>Bridge: response.done
        
        Note over TTS_Worker,ElevenLabs: === TTS PROCESSING PHASE ===
        
        loop Process TTS Queue
            TTS_Worker->>TTS_Worker: Queue.get() - Wait for segment
            alt Text Segment Available
                TTS_Worker->>Bridge: _stream_elevenlabs_tts(text, is_final)
                
                Bridge->>ElevenLabs: POST /text-to-speech/{voice_id}/stream<br/>(JSON: text, model_id, voice_settings)
                
                loop Stream MP3 Audio
                    ElevenLabs-->>Bridge: Stream MP3 Chunks
                    Bridge->>Bridge: Buffer MP3 chunks in memory
                end
                
                Bridge->>Bridge: Convert MP3 to WAV<br/>(24kHz, mono, 16-bit)
                Bridge->>Client: Send Binary WAV Audio
                
                alt is_final = True
                    Bridge->>Bridge: Set response_done = True
                    Bridge->>Client: Send {"type": "response_done"}
                end
            else Empty Final Marker
                Bridge->>Bridge: Set response_done = True
                Bridge->>Client: Send {"type": "response_done"}
            end
        end
    end

    Note over Client,ElevenLabs: === ERROR HANDLING ===
    
    alt OpenAI Error
        OpenAI-->>Bridge: {"type": "error", "code": "...", "message": "..."}
        Bridge->>Bridge: Track error (if append-related)
        
        alt input_audio_buffer_commit_empty
            Bridge->>Bridge: Reset buffer tracking
        else conversation_already_has_active_response
            Bridge->>Bridge: Set response_done = False
        end
        
        Bridge->>Client: Send {"type": "error", "code": "...", "message": "..."}
    end
    
    alt ElevenLabs Error
        ElevenLabs-->>Bridge: HTTP Error Response
        Bridge->>Client: Send {"type": "error", "code": "elevenlabs_error"}
        Bridge->>Client: Send {"type": "response_done"}
    end

    Note over Client,ElevenLabs: === CLEANUP PHASE ===
    
    alt Client Disconnect or Close
        Client->>WS_Endpoint: WebSocket Disconnect<br/>(or {"type": "close"})
        WS_Endpoint->>Bridge: close()
        Bridge->>OpenAI: Close WebSocket
        Bridge->>Bridge: Close HTTP Client
        Bridge->>TTS_Worker: Cancel TTS Worker Task
        Bridge->>Bridge: Set is_connected = False
    end
```

## Component Architecture

```mermaid
graph TB
    subgraph "Client Application"
        Client[Client WebSocket]
    end
    
    subgraph "FastAPI Server"
        WS[WebSocket Endpoint<br/>/ws/openai-realtime]
        Bridge[OpenAIRealtimeBridge]
        
        subgraph "Bridge Components"
            AudioConverter[Audio Converter<br/>convert_audio_to_pcm16]
            BufferTracker[Audio Buffer Tracker<br/>audio_buffer_size_bytes<br/>audio_chunks_count]
            TextBuffer[Text Buffer<br/>response_text<br/>partial_text_buffer]
            TTSQueue[asyncio.Queue<br/>TTS Segments Queue]
        end
        
        subgraph "Background Tasks"
            ListenerTask[_listen_to_openai<br/>Async Task]
            TTSWorkerTask[_tts_worker<br/>Async Task]
        end
    end
    
    subgraph "External Services"
        OpenAI[OpenAI Realtime API<br/>WebSocket Connection]
        ElevenLabs[ElevenLabs TTS API<br/>HTTP Streaming]
    end
    
    Client <-->|WebSocket| WS
    WS <-->|Manages| Bridge
    Bridge -->|Uses| AudioConverter
    Bridge -->|Tracks| BufferTracker
    Bridge -->|Buffers| TextBuffer
    Bridge -->|Enqueues| TTSQueue
    Bridge -->|Spawns| ListenerTask
    Bridge -->|Spawns| TTSWorkerTask
    
    ListenerTask <-->|WebSocket Messages| OpenAI
    TTSWorkerTask -->|Reads from| TTSQueue
    TTSWorkerTask -->|HTTP Stream| ElevenLabs
    
    Bridge -->|Sends Audio| OpenAI
    OpenAI -->|Text Deltas| ListenerTask
    ListenerTask -->|Updates| TextBuffer
    TextBuffer -->|Flushes Segments| TTSQueue
    ElevenLabs -->|MP3 Audio| TTSWorkerTask
    TTSWorkerTask -->|WAV Audio| Bridge
    Bridge -->|Sends Audio| Client
```

## State Machine Diagram

```mermaid
stateDiagram-v2
    [*] --> Initializing: Client Connects
    
    Initializing --> Connecting: Create Bridge
    Connecting --> Configuring: Connect to OpenAI
    Configuring --> Ready: Session Updated
    
    Ready --> Streaming: Receive Audio Chunk
    Streaming --> Converting: Audio Received
    Converting --> Appending: Convert to PCM16
    Appending --> Streaming: Append to Buffer
    
    Streaming --> Committing: Client Sends audio_commit
    Committing --> Validating: Check Buffer Size
    Validating --> WaitingResponse: Valid Commit
    Validating --> Ready: Invalid (Error)
    
    WaitingResponse --> ReceivingText: OpenAI Starts Response
    ReceivingText --> BufferingText: Text Delta Received
    BufferingText --> EnqueueingTTS: Complete Sentence Found
    EnqueueingTTS --> ReceivingText: More Deltas Expected
    ReceivingText --> TextComplete: response.text.done
    
    TextComplete --> ProcessingTTS: Finalize Segments
    ProcessingTTS --> StreamingTTS: TTS Worker Processes Queue
    StreamingTTS --> SendingAudio: ElevenLabs Streams MP3
    SendingAudio --> ConvertingAudio: Buffer MP3 Chunks
    ConvertingAudio --> SendingWAV: Convert to WAV
    SendingWAV --> ProcessingTTS: More Segments?
    ProcessingTTS --> ResponseComplete: All Segments Done
    
    ResponseComplete --> Ready: response_done = True
    
    Ready --> [*]: Client Disconnects
    Streaming --> [*]: Client Disconnects
    WaitingResponse --> [*]: Client Disconnects
    ProcessingTTS --> [*]: Client Disconnects
    
    note right of Validating
        Minimum: 4800 bytes (~100ms)
        Check: response_done flag
    end note
    
    note right of EnqueueingTTS
        Minimum: 80 characters
        Sentence end: . ! ?
    end note
```

## Data Flow Diagram

```mermaid
flowchart LR
    subgraph "Input Flow"
        A1[Client Audio<br/>Any Format] --> A2[convert_audio_to_pcm16]
        A2 --> A3[PCM16 Audio<br/>24kHz, mono, 16-bit]
        A3 --> A4[Base64 Encode]
        A4 --> A5[OpenAI Buffer]
    end
    
    subgraph "Processing Flow"
        B1[OpenAI Processes Audio] --> B2[Text Deltas]
        B2 --> B3[Accumulate Text]
        B3 --> B4{Complete<br/>Sentence?}
        B4 -->|Yes ≥80 chars| B5[Enqueue TTS Segment]
        B4 -->|No| B3
        B5 --> B6[TTS Queue]
    end
    
    subgraph "Output Flow"
        C1[TTS Queue] --> C2[ElevenLabs API]
        C2 --> C3[MP3 Stream]
        C3 --> C4[Buffer MP3]
        C4 --> C5[Convert to WAV<br/>24kHz, mono, 16-bit]
        C5 --> C6[Client Audio]
    end
    
    A5 --> B1
    B6 --> C1
```

## Key Workflow Steps Summary

1. **Initialization**: Client connects → Bridge created → OpenAI WebSocket established → Session configured → Background tasks started
2. **Audio Input**: Client sends audio chunks → Convert to PCM16 → Append to OpenAI buffer → Track buffer size
3. **Commit**: Client sends commit → Validate buffer → Commit to OpenAI → Request text-only response
4. **Text Streaming**: OpenAI streams text deltas → Accumulate text → Detect complete sentences → Enqueue to TTS
5. **TTS Processing**: Worker processes queue → Send to ElevenLabs → Stream MP3 → Convert to WAV → Send to client
6. **Completion**: Final transcript sent → All TTS segments processed → Response done flag set
7. **Cleanup**: Close connections → Cancel tasks → Reset state

