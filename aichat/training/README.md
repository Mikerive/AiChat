# Voice Training Pipeline

This module contains the voice training pipeline for creating custom TTS models. It processes audio files through segmentation, transcription, and training to produce high-quality voice models.

Overview
- Purpose: convert long mp3/mp4 inputs into training-ready speech clips, transcribe clips with Whisper, produce a CSV manifest (clip_filename | transcript), generate Piper-compatible manifests, and run Piper finetuning with epoch-level checkpointing.
- Durable design: each major stage writes checkpoints and atomic metadata so long-running jobs can resume safely.

## Key Components
- **Audio processing**: `audio_processor.py` - Audio preprocessing and segmentation
- **Training orchestration**: `train_voice.py` - Training workflow management  
- **Scripts**: Various utilities for ingestion, preprocessing, and training
- **Services**: Training service runners and utilities

Pipeline summary
1. Ingest
   - Accept mp3/mp4 uploads or directory of files.
   - Extract audio via ffmpeg to WAV at target sample rate (default 22050 Hz).
   - Persist original in `training_data/raw/` with checksum and job-sidecar JSON.

2. Source separation (Spleeter)
   - Run Spleeter (2-stem) to extract vocal stem.
   - Save vocal stem to `training_data/vocals/`.
   - Mark separation complete in job checkpoint JSON.

3. Recursive silence-based segmentation
   - Compute RMS envelope.
   - Start with an initial silence factor and split on silence midpoints.
   - If segments exceed MAX_AUDIO_LENGTH, lower factor and recurse.
   - Save segments atomically to `training_data/audio/`.

4. Per-clip preprocessing
   - Resample, normalize, optional denoise, trim micro-silence.
   - Enforce min/max clip lengths and merge very short neighbors.
   - Save final processed WAV.

5. Whisper transcription
   - Worker pool transcribes clips as they finish.
   - Append rows to `training_data/metadata.csv` with atomic write: clip_filename|transcript|duration|speaker|quality
   - Save per-clip JSON with confidence and language.

6. Piper manifest generation
   - Convert `metadata.csv` to Piper's dataset layout (ljspeech or dataset.jsonl + .pt spectrograms) using `piper_train.preprocess`.
   - Validate audio (wav, 16-bit, mono, sample rate 22050 or 16000 as chosen).

7. Training orchestration
   - Run `python -m piper_train --dataset-dir <dir> ...` with checkpoint epochs configured.
   - Save model checkpoints per epoch and maintain resume info in job JSON.

Durability and resume strategy
- Job JSON (checkpoints/<job_id>.json) records stage booleans and counters:
  - ingested, separated, segments_saved, transcribed_count, manifest_created, training: { epoch, last_checkpoint }
- Atomic write pattern:
  - Write to temp file, fsync if possible, then rename to final path.
  - CSV appends should use per-clip temporary row files merged periodically or use file locks for append.

Mermaid dataflow (renderable)
graph LR
  A[Ingest mp3/mp4 -> extract WAV] --> B[Spleeter: vocals + accompaniment]
  B --> C[Compute RMS energy envelope]
  C --> D[Recursive silence-based splitter]
  D --> E[Per-clip preprocessing (resample, normalize, trim)]
  E --> F[Save clip WAV (atomic)]
  F --> G[Whisper transcription worker]
  G --> H[Append to CSV: clip_name | transcript]
  H --> I[Piper manifest generator]
  I --> J[Training orchestrator (epochs + checkpointing)]
  J --> K[Model checkpoints & logs]

Next actions performed by the project
- Copy existing preprocessing/training code here and continue development.
- Implement CLI wrappers and API endpoints that reference this new folder.
- Provide tests for splitting, transcription, CSV generation, and training flows.

## Development Notes

### Adding New Training Scripts
1. Create script in `aichat/training/scripts/`
2. Follow existing patterns for argument parsing
3. Add CLI integration if needed
4. Include proper logging and error handling

### Extending the Pipeline  
- All training data should use the `data/training/` directory structure
- Scripts should be idempotent and resumable
- Use atomic file operations for data integrity
- Log progress and checkpoints for long-running operations

## Usage

### CLI Commands
```bash
# Start training pipeline
aichat-training --mode serve

# Run specific training scripts
python -m aichat.training.scripts.ingest --input /path/to/audio
python -m aichat.training.scripts.preprocess_clips --input data/training/raw
```

### Data Directory Structure
```
data/training/
├── raw/                # Original audio files
├── processed/          # Processed audio clips
├── checkpoints/        # Training checkpoints
└── metadata.csv        # Training manifest
```

### Training Workflow
1. Place audio files in `data/training/raw/`
2. Run ingestion: `python -m aichat.training.scripts.ingest`
3. Process clips: `python -m aichat.training.scripts.preprocess_clips`
4. Generate transcripts: `python -m aichat.training.scripts.transcribe_worker`
5. Train model: `python -m aichat.training.scripts.train_orchestrator`