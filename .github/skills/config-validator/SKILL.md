---
name: config-validator
description: Validate Thea's implemented preset and settings contracts without hardware or media execution.
user-invocable: true
disable-model-invocation: false
---

# Configuration validation

Follow `AGENTS.md` and the parent workspace policy.

1. Read `src\utils\config_loader.py`, `src\utils\settings.py`, the changed JSON,
   and `docs\configuration.md`. Treat code as the implemented schema.
2. Presets require `analysis`, `optical_flow`, `window_detection`, `output`, and
   `gpu`. Use `validate_config`; do not invent quality, memory, or codec fields.
3. Settings merge tracked defaults and ignored `settings.local.json`.
   Validate string `data_dir` and boolean `data_collection`/`reencode`.
4. Run the focused configuration/settings tests:

   ```powershell
   python -m pytest src\utils\tests\test_config_loader.py src\utils\tests\test_settings.py -q
   ```

5. Report concrete errors and tested paths. Do not launch encoders or GPU
   compatibility probes without an explicit request.
