# Video algorithms, models, and research decisions

[Back to Thea](../README.md) | [Configuration](configuration.md)

Research checked on **November 15, 2026**. Scope: selecting useful stock-footage
segments, understanding their content, and transforming existing source footage.
**Motion stability, visual quality, and caption accuracy are separate objectives.**

**Implemented** means present in Thea's source, not a measured quality guarantee.
**Candidate** means a research recommendation, not an installed integration or a
claim that alternatives have already been benchmarked. Hardware estimates use
the 12 GB RTX 4070 SUPER target described in the existing guides; actual device
availability and model performance have not been measured for this research.

## 1. What Thea currently uses

| Video task | Algorithm or model actually used | Evidence and important boundary |
|------------|----------------------------------|---------------------------------|
| Motion estimation | Classical dense Farneback optical flow, OpenCV CUDA or CPU | [Flow calculators](../src/motion_assessment/optical_flow.py#L42); no trained checkpoint or neural optical-flow model |
| Stable-segment selection | Mean flow magnitude, Gaussian temporal smoothing, thresholding, gap merging, minimum duration | [Scoring and windows](../src/motion_assessment/analyzer.py#L29); this is a motion heuristic, not learned aesthetic assessment |
| Motion labels | Seven hand-set magnitude ranges, scaled to a nominal 320-pixel width | [Classification](../src/motion_assessment/assessment.py#L38); `cut` is a threshold label, not a dedicated shot detector |
| Analysis copies | OpenCV area-resampled, normally `mp4v` video; optional standalone FFV1/LANCZOS4 mode | [Downscaling](../src/downscaler/downscaler.py#L22); the full pipeline explicitly chooses the normal lossy analysis copy |
| Clip extraction and joining | FFmpeg stream copy; optional OpenCV slice re-encoding | [Slicing](../src/slicer/slicer.py), [joining](../src/merger/merger.py#L68); transformations operate on original footage |
| Cropping and panning | Exact ratio geometry and a time-dependent FFmpeg crop rectangle | [Crop/pan](../src/cropandpan/cropandpan.py#L141); no object tracking or saliency model |
| Video description | Uniformly sampled contact sheet plus an injectable vision-language backend, exposed through CLI and MCP | [Sampling](../src/sampled_captioner/sampler.py#L25), [caption adapter](../src/sampled_captioner/captioner.py#L67); no default model ID is selected |
| Local caption model | Florence-2-large is a TODO, not an implemented backend | [Explicit TODO](../src/sampled_captioner/captioner.py#L136) |

The Qwen 3 models in the [editor setup guide](setup.local-llm-mcp.md) are coding
assistant examples. `Qwen/Qwen3-14B` is a text-generation model; it must not be
confused with a `Qwen3-VL` vision model or reported as Thea's video captioner.
See the [publisher's model card][qwen-text].

## 2. Motion and shot-boundary algorithms

### The central distinction: movement is not shake

Optical flow estimates apparent image displacement, which can come from camera
motion, moving subjects, or both. A smooth pan can therefore have greater flow
magnitude than an undesirable almost-static clip. A moving sea, crowd, or vehicle
can also raise the score without camera shake. This follows from the
[definition of optical flow][opencv-flow] and Thea's whole-frame averaging.

For Thea, keep separate assessments of **camera smoothness**, **subject motion**,
**shot continuity**, and **technical/aesthetic quality**. Replacing the flow
estimator alone does not solve the mismatch between mean motion and clip value.

| Approach | Salient features and tradeoffs | Fit for Thea / recommendation | Configuration and acceptance evidence |
|----------|--------------------------------|-------------------------------|---------------------------------------|
| **Farneback dense flow - implemented baseline** | Computes a displacement vector per pixel without downloaded weights. Existing CPU/CUDA implementations share parameters. Averaging discards spatial structure and direction | Retain as the low-dependency baseline; do not call it a stock-quality model | Compare clip decisions on smooth pans, subject motion and shake, not merely CPU/GPU numerical agreement. [OpenCV API][opencv-tracking] |
| **Sparse pyramidal Lucas-Kanade plus robust camera transform - candidate** | Tracks selected features; RANSAC fits a transform while rejecting inconsistent correspondences. Can separate dominant camera movement from some independently moving objects. Sparse texture, parallax and a foreground filling the frame can defeat the fit | Preferred first experiment for distinguishing smooth camera travel from jitter, before adopting a larger flow network. This is a proposed fit to Thea's objective, not a benchmark win | Start with translation/rotation/uniform scale using `estimateAffinePartial2D`. Measure inlier coverage and residuals; do not treat a failed fit as zero shake. [Tracking][opencv-flow], [robust transform][opencv-affine] |
| **RAFT - candidate learned flow comparator** | Uses learned pixel features, all-pairs correlation and recurrent flow refinement. Requires weights, preprocessing and an inference runtime; correspondence accuracy is not a camera-smoothness label | Evaluate only if dense-flow errors remain important after fixing the scoring objective. Do not select solely on published optical-flow leaderboards | Compare both flow failure cases and end-to-end accepted/rejected clips at the same analysis size. Record checkpoint, runtime, latency and peak memory. [Paper][raft-paper], [authors' implementation][raft-code] |
| **PySceneDetect AdaptiveDetector - candidate shot gate** | Compares HSV content changes against a rolling local baseline; intended to reduce some fast-camera-motion false cuts. Flashing lights and gradual transitions still need evaluation | Use a separate shot-boundary signal rather than assuming high flow means a cut; never merge a stable window across a confirmed cut | Compare with its fixed-threshold `ContentDetector` on pans, flashes, hard cuts and dissolves. Pin the evaluated package/config; published defaults are not validated Thea thresholds. [Official detectors][scene-detect] |

For the proposed camera estimator, fit correspondences as
`p_next ~= s * R(theta) * p_previous + translation`. Assess the time series of
translation, rotation and scale together with residual flow and fit confidence.
Smooth nonzero velocity should not automatically fail; abrupt changes and
unexplained residuals are separate evidence. Derivatives must use elapsed
timestamps rather than assume every source has the same FPS. This is an analysis
recommendation using the robust-transform tools above, **not current behavior**.

### Actual scoring, smoothing, and thresholds

Thea reduces each flow field to
`m[t] = mean(sqrt(u[t,x,y]^2 + v[t,x,y]^2))`, then runs
`gaussian_filter1d(m, sigma)` and thresholds that smoothed sequence.
Clip boundaries are formed by merging short gaps and filtering short spans.
Whole-video `motion_stats` instead summarize the **unsmoothed** scores.
Evidence: [flow reduction](../src/motion_assessment/optical_flow.py#L62) and
[temporal/window processing](../src/motion_assessment/analyzer.py#L29).

| Choice | Current configuration | Benefit / cost and research implication |
|--------|-----------------------|-----------------------------------------|
| Grayscale, reduced analysis frames | Width limited by preset; area interpolation | Fewer analyzed pixels; removes color evidence and fine movement. A 3840x2160 frame reduced to 320x180 has `8,294,400 / 57,600 = 144` times fewer pixels, **not a demonstrated 144x speedup**; original decoding and other costs remain |
| Gaussian temporal smoothing | Sigma 2-8 **flow samples**, depending on preset | Suppresses short variations but can blur an abrupt event in time. Sigma is not seconds; 5 samples corresponds to about `5 / 30 = 0.167 s` standard deviation at 30 FPS. SciPy supplies a centered filter with default reflected boundaries. [Filter definition][scipy-gaussian] |
| Threshold plus gap merging | Strict `< threshold`; gaps bounded by `int(gap_seconds * fps)` | Simple/interpretable, but merged windows can contain above-threshold intervals. A minimum-duration pass does not prove that every frame is stable |
| Resolution normalization | Motion-label classification multiplies by `320 / analysis_width`; window detection uses its raw preset threshold | Labels and extraction thresholds are not one calibrated metric. The action preset changes both resolution and thresholds; do not compare its raw score directly with the cinematic score |
| Frame-rate dependence | Flow is displacement between decoded adjacent frames | No explicit pixels-per-second normalization; equal physical motion sampled at different frame rates need not have equal scores |
| CUDA selection | Enabled presets request device 0; CPU used when disabled or no device is reported | GPU construction/driver failures are not comprehensively caught and converted to CPU execution. Frame uploads and full flow downloads also remain in the GPU path; no measured end-to-end speedup is implied |

These are consequences of the implemented calculations, not evidence that the
current thresholds are optimal. The smoothing and gap policy needs visual
validation around the precise bad frames it can hide.

### Checked-in presets

| Preset | Width | Sigma (samples) | Motion threshold | Minimum clip (s) | Merge gap (s) | Farneback levels / window / iterations | Polynomial neighborhood / sigma |
|--------|-------|-----------------|------------------|------------------|---------------|----------------------------------------|---------------------------------|
| [strict](../config/presets/strict.json) | 320 | 8 | 0.20 | 8.0 | 2.0 | 5 / 31 / 7 | 7 / 1.5 |
| [cinematic](../config/presets/cinematic.json) | 320 | 5 | 0.50 | 3.0 | 1.0 | 5 / 21 / 5 | 7 / 1.5 |
| [permissive](../config/presets/permissive.json) | 320 | 3 | 1.00 | 3.0 | 0.5 | 3 / 15 / 3 | 5 / 1.2 |
| [action](../config/presets/action.json) | 480 | 2 | 2.00 | 2.0 | 0.3 | 3 / 11 / 3 | 5 / 1.2 |

All four set pyramid scale `0.5`, flags `0`, output codec `mp4v`, and GPU device
`0` enabled. OpenCV documents larger averaging/polynomial neighborhoods as a
robustness-versus-flow-detail tradeoff and iterations as work at each pyramid
level. These settings are working choices, not a published comparative study.
[Parameter semantics][opencv-tracking].

The separate motion-label ranges at nominal width 320 are: static `[0,0.05)`,
very stable `[0.05,0.20)`, stable `[0.20,0.50)`, moderate `[0.50,1)`,
unstable `[1,2)`, very unstable `[2,5)`, and cut `[5,infinity)`.
The [source](../src/motion_assessment/assessment.py#L49) establishes those
boundaries; it does not establish that a score of 5 reliably detects an edit.

## 3. Technical and aesthetic video quality

A stability filter cannot establish sharpness, exposure, composition or
usefulness. These need independent evidence; a perfectly static blurred shot
should not outrank a clear, intentional pan simply because its flow is lower.

| Method | What it contributes | Limit / decision for Thea |
|--------|---------------------|--------------------------|
| Mean optical-flow magnitude | Motion amount | Keep for interpretable motion evidence, not an overall quality score |
| **DOVER / DOVER-Mobile - research candidate** | Published no-reference video-quality assessment separates aesthetic and technical perspectives; Mobile is the smaller variant | Evaluate Mobile as an optional ranking signal after temporal selection. Its UGC training/evaluation domain is not proof of stock-footage acceptability. Calibrate on Thea clips; do not interpret a normalized dataset rank as a universal quality percentage. [Authors' repository][dover] |
| Human clip judgments | Whether the segment is actually useful stock footage | Needed to establish the target for automated ranking; distinguish motion, defects and content usefulness rather than one unexplained label |

No DOVER checkpoint or learned aesthetic/technical-quality model is integrated
into the current selection path. Its inclusion here is a focused research
alternative, not a claim that inference or comparative accuracy has been tested.

## 4. Video understanding and caption-model selection

### Sampling policy matters before model size

The implemented sampler selects up to 12 unique, approximately evenly spaced
frame indices from 5%-95% of the clip. Each frame is letterboxed to 176x144 and
arranged chronologically in four columns: a full 12-frame sheet is
`4 * 176 = 704` by `3 * 144 = 432` pixels. The backend receives one image with
`detail: low`; timestamp metadata is returned to the caller but is not separately
sent as a temporal sequence. [Sampler](../src/sampled_captioner/sampler.py#L25),
[request construction](../src/sampled_captioner/captioner.py#L82).

| Representation | Advantages | Information loss / recommendation |
|----------------|------------|-----------------------------------|
| **Current single contact sheet** | One image request, chronological overview, can reuse an existing downscaled video | Small subjects/text and short events may disappear; first/last 5% is omitted; chronological ordering alone is not measured motion. Suitable baseline for scene/subject summaries, not evidence of complete event coverage |
| **Separate sampled frames with timestamps - candidate** | Makes frame order/time explicit; avoids treating every tile as one spatial scene | More input tokens and inference memory; compare against the montage using identical sampled times before increasing sample count |
| **Shot-aware/key-event sampling - candidate** | Can preserve content changes missed by uniform sampling | Requires an evaluated selection policy; scene changes and brief actions are different signals. Test selection misses independently from caption errors |

### Captioning models and decision

A vision-language model (VLM) accepts images/video plus instructions and produces
text. The current HTTP adapter is a transport contract, **not a model choice**.

| Model / option | Capabilities and salient tradeoffs | Thea status and recommendation |
|----------------|-----------------------------------|--------------------------------|
| **Caller-selected vision model via compatible endpoint** | Existing adapter sends one contact-sheet image and a short instruction prompt; model quality, image preprocessing and resource use depend on the selected server/checkpoint | **Implemented API, unspecified model.** Defaults are local endpoint port 1234, temperature 0.1, maximum 120 output tokens, timeout 120 s. A successful response is not a correctness benchmark |
| **`microsoft/Florence-2-large`** | Approximately 0.77B parameters; task-token image captioning, including `<CAPTION>` and detailed-caption tasks. Smaller research baseline, but image captions alone do not establish temporal action understanding | **TODO only.** Evaluate per-frame visual descriptions plus conservative aggregation, or explicitly test montage comprehension. The existing free-form chat request is not a native Florence implementation. [Model card][florence] |
| **`Qwen/Qwen3-VL-4B-Instruct`** | Publisher documents image/video understanding and timestamp-grounded temporal modeling. More capable input contract for a temporal-caption experiment, with greater model/context cost than Florence | **Research candidate, not configured.** Preferred second comparator when actions/order matter. Start with the same montage, then separately test timestamped frames/native video; verify the serving runtime actually supports that input. [Model card][qwen-vl], [official usage][qwen-vl-code] |
| **Plain Qwen3 text models** | Text generation, not a replacement for a visual encoder | Not a direct video-caption candidate; presence in editor documentation does not make them image-capable. [Publisher][qwen-text] |

**Selection recommendation:** compare Florence-2-large against
Qwen3-VL-4B-Instruct on the same grounded caption set. Prefer Florence if short
scene/subject captions meet the quality bar at lower measured cost; prefer
Qwen3-VL if its additional temporal/instruction capability materially improves
the required labels. No benchmark or hardware-fit result currently establishes
a winning checkpoint for Thea.

### Caption-model weight-memory estimates

For a nominal `P` billion parameters and `b` stored bits per parameter,
`weight_bytes ~= P * 10^9 * b / 8`. These estimates exclude quantization scales,
unquantized layers, activations, attention caches, input processing, workspaces
and runtime allocations. They do not establish full-model hardware fit.

| Model-scale example | Arithmetic | Approximate weights only |
|---------------------|------------|--------------------------|
| Florence 0.77B at 16 bits | `0.77e9 * 2` bytes | 1.54 GB / 1.43 GiB |
| Nominal 4B VLM at 16 bits | `4e9 * 2` bytes | 8 GB / 7.45 GiB |
| Nominal 4B VLM at ideal 4 bits | `4e9 * 0.5` bytes | 2 GB / 1.86 GiB; not a measured Qwen checkpoint footprint |

### Grounding and hallucination boundaries

The current prompt always requests activity/subject, suppresses location and
time-of-day text when corresponding metadata flags are set, and asks for generic
settings instead of unsupported place names. It also requires definitive wording
and disallows uncertainty phrases. These are instructions, not verification:
fluent certainty cannot establish factual accuracy.
[Prompt source](../src/sampled_captioner/captioner.py#L37).

Evaluate visible nouns/actions separately from inferred geography and time.
Use reliable embedded location/time metadata as evidence; do not promote a
generic beach or street to a specific city from a plausible caption. For actions
requiring motion, judge event order against frames/timestamps, not an attractive
sentence about a montage. Record unsupported claims and missed events explicitly;
neither low temperature nor one-sentence output eliminates them.

## 5. Preserving source-video fidelity

| Operation / choice | Why it fits | Limit and comparison criterion |
|--------------------|-------------|--------------------------------|
| **Low-resolution analysis, original-source extraction** | Reduces motion-analysis pixels without making the small analysis copy the deliverable | Lossy analysis copies can affect scores; compare against direct decoding at the same analysis size before changing codec/resolution. [Pipeline](../src/main.py) |
| **Stream-copy slicing versus re-encoding** | Copy avoids a new encoding pass; useful when preserving existing compressed streams is the priority | Input-side `-ss` seeks to an available earlier seek point; stream copy need not discard that lead-in. Measure decoded start/end error, not just container duration. Current OpenCV re-encoding writes video frames without an audio-copy path. [Thea slicer](../src/slicer/slicer.py), [FFmpeg seeking][ffmpeg-cli] |
| **Concat-demuxer stream-copy merging** | Preserves order/streams without another video encode when signatures match | Cannot treat arbitrary codecs, layouts or time bases as interchangeable. Thea checks compatibility and output duration before publication. [Thea merge](../src/merger/merger.py#L44), [demuxer contract][ffmpeg-concat] |
| **Exact crop ratio and linear pan** | Deterministic geometry, rational aspect ratio, chroma-compatible dimensions and explicit endpoint path; no need to hallucinate pixels | Pixel changes require filtering/re-encoding; retaining the codec name does not make the result lossless. The pan follows supplied coordinates, not a subject. [Geometry/rendering](../src/cropandpan/cropandpan.py#L141), [crop filter][ffmpeg-crop] |

For crop/pan, evaluate displayed dimensions after rotation, sample aspect ratio,
pixel format, audio preservation, timestamp alignment and real decoded duration.
For extraction, distinguish **the chosen algorithmic window** from **the actual
playable/keyframe-constrained clip**. A correct window list alone is not proof
that unwanted frames are absent from the exported footage.

## 6. Evidence needed to select algorithms and models

Existing unit/regression tests establish behavior, not comparative visual quality.
The [recorded motion fixture](../src/integration_tests/fixtures/reference_sample.json)
contains one 574-frame source, 573 adjacent-frame scores and three windows.
It is a useful regression reference, not a diverse footage-quality dataset or
a fresh speed benchmark.

| Research question | Comparison design | Acceptance evidence to record |
|-------------------|-------------------|-------------------------------|
| Does selection retain useful pans while rejecting shake? | Label static shots, smooth pans/tilts, handheld jitter, parallax, crowds, water, low texture and low light; separate camera from subject motion | Segment precision/recall, useful-duration retained and bad-duration accepted, stratified by motion class and camera/source rather than one aggregate score |
| Are shot boundaries safe? | Hard cuts, dissolves, exposure flashes and fast pans; compare flow-only labeling against a dedicated detector | Boundary precision/recall and absolute timing error; count any exported segment that bridges a true cut |
| Which flow/scoring configuration is worthwhile? | Same clips, analysis sizes and timestamp policy; compare current Farneback scoring, robust camera-motion features, and only then a learned-flow comparator | Visual decision quality plus complete decode/resize/flow/selection latency, CPU RAM and GPU peak memory; report actual backend/checkpoint |
| Which caption representation/model is sufficient? | Same labeled clips and prompts; compare montage versus timestamped frames, Florence versus Qwen3-VL; group related clips in one split to reduce near-duplicate leakage | Supported subject/action recall, unsupported-claim rate, location/time errors, missed short events, latency and memory; no accuracy claim from request-success tests |
| Does a quality ranker help stock selection? | Compare current motion-only ordering with DOVER-Mobile-assisted ordering on human-rated candidates | Pairwise agreement and retained/rejected useful footage; inspect domain-specific failures before calibrating a threshold |
| Are final files faithful? | Decode outputs and compare requested versus actual clip boundaries, geometry and stream properties | Measured boundary tolerance, A/V sync, duration, codec/pixel format and no unintended source modification |

These are proposed evaluation criteria, not invented pass percentages or claims
that comparative model inference has already run. Establish product-specific
quality thresholds from labeled footage before declaring one model or preset
the winner.

## References

Implementation evidence is linked at the relevant algorithm above. External
references are primary documentation, model cards or authors' papers/code.
Published benchmark and memory claims are not substituted for Thea measurements.

- [OpenCV optical-flow concepts and Lucas-Kanade][opencv-flow]
- [OpenCV Farneback API and parameter meanings][opencv-tracking]
- [OpenCV robust affine estimation][opencv-affine]
- [SciPy Gaussian temporal filtering][scipy-gaussian]
- [RAFT paper][raft-paper] and [official implementation][raft-code]
- [PySceneDetect detector definitions][scene-detect]
- [DOVER authors' model and evaluation repository][dover]
- [Florence-2-large model card][florence]
- [Qwen3-VL-4B-Instruct model card][qwen-vl] and [official usage][qwen-vl-code]
- [Qwen3-14B text-model card][qwen-text]
- [FFmpeg stream copy/seeking][ffmpeg-cli], [concat demuxer][ffmpeg-concat],
  and [crop filter][ffmpeg-crop]

[opencv-flow]: https://docs.opencv.org/4.13.0/d4/dee/tutorial_optical_flow.html
[opencv-tracking]: https://docs.opencv.org/4.13.0/dc/d6b/group__video__track.html
[opencv-affine]: https://docs.opencv.org/4.13.0/d9/d0c/group__calib3d.html
[scipy-gaussian]: https://docs.scipy.org/doc/scipy/reference/generated/scipy.ndimage.gaussian_filter1d.html
[raft-paper]: https://arxiv.org/abs/2003.12039
[raft-code]: https://github.com/princeton-vl/RAFT
[scene-detect]: https://www.scenedetect.com/docs/latest/api/detectors.html
[dover]: https://github.com/VQAssessment/DOVER
[florence]: https://huggingface.co/microsoft/Florence-2-large
[qwen-vl]: https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct
[qwen-vl-code]: https://github.com/QwenLM/Qwen3-VL
[qwen-text]: https://huggingface.co/Qwen/Qwen3-14B
[ffmpeg-cli]: https://ffmpeg.org/ffmpeg.html
[ffmpeg-concat]: https://ffmpeg.org/ffmpeg-formats.html#concat
[ffmpeg-crop]: https://ffmpeg.org/ffmpeg-filters.html#crop
