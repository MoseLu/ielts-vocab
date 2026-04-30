# 2026-04-30 Local Word Image Preprocessing TODO

Last updated: 2026-04-30

## Goal

Prepare a development-machine preprocessing workflow for AI-generated associative vocabulary images, so production only serves already-generated image metadata and OSS objects. Production must not run local image generation because the current cloud server is a 2-core, 4 GB baseline host.

## Scope

### Local Preprocessing

- Pull and evaluate three local Ollama image-generation models:
  - `x/flux2-klein`
  - `x/flux2-klein:9b`
  - `x/z-image-turbo`
- Use `x/flux2-klein` as the default batch candidate unless pilot output shows weak semantic alignment.
- Reserve `x/flux2-klein:9b` for hard-word reruns and quality comparison.
- Reserve `x/z-image-turbo` for cases where photorealism, Chinese visual cues, or text-like visual composition is actually useful.
- Run a small golden-set pilot before any 9000+ full batch.

### Project Integration Boundary

- Keep generation off the production server.
- Reuse the existing `ai_word_image_assets` concept where possible: stable `sense_key`, prompt version, style version, status, provider/model metadata, and OSS object key.
- Store final images under the existing project OSS namespace pattern, not inside the frontend bundle.
- Production should only resolve ready assets and signed/public URLs; queued or failed images should continue to degrade gracefully in the game UI.

## Task Breakdown

1. Finish local model downloads and record the installed versions with `ollama list`.
2. Build a 50-100 word golden set covering concrete nouns, abstract nouns, verbs, adjectives, academic words, and confusing IELTS senses.
3. Generate the golden set with `x/flux2-klein` at square output size and the current semantic-memory-card prompt.
4. Rerun weak samples with `x/flux2-klein:9b` and `x/z-image-turbo`, then compare semantic clarity, style consistency, generation time, and retry rate.
5. Choose one default model and one fallback model for batch preprocessing.
6. Decide whether to add a local-only `ollama` provider to the existing worker path or keep a separate preprocessing/export script.
7. Generate images in resumable batches, upload/store outputs under the game-word-images namespace, and keep a manifest or database import path for generated metadata.
8. Verify frontend behavior with ready, queued, and failed image states before deploying metadata consumption changes.

## Risks

- Full 9000+ image generation can take many hours locally even on Apple Silicon.
- 1024x1024 PNGs may create a large OSS footprint; consider WebP conversion if frontend quality remains acceptable.
- Abstract words may produce decorative but semantically weak images unless the prompt includes a concrete consequence or visual metaphor.
- Local Ollama output and cloud API output may differ enough that prompt versions should encode the provider/model choice.
- Generating one asset per sense rather than one per spelling can multiply the final count when definitions differ across books.

## Verification

1. Confirm all three local models appear in `ollama list`.
2. Confirm the golden-set output directory or OSS namespace has one image per selected `sense_key`.
3. Review at least 30 generated images manually for semantic fit before full batch.
4. Confirm generated metadata can round-trip through the existing game word image shape: `status`, `senseKey`, `url`, `alt`, `styleVersion`, `model`, and `generatedAt`.
5. Confirm production remains free of local image-generation runtime requirements.
