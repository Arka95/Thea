# Open work

[Back to Thea](../../README.md) | [Developer guide](../dev.readme.md)

| Item | Evidence / next acceptance |
|------|----------------------------|
| Existing lint backlog | Ruff reports pre-existing findings. Fix in a dedicated change without disabling inherited rules; structural migration must not introduce new diagnostic messages |
| Standalone distribution | Editable install works, but config remains checkout-relative; choose/package resources and test an isolated wheel before claiming wheel/executable deployment |
| Processing integration validation | Media/GPU reference suites were relocated, not run; explicitly validate the selected backend before changing its compatibility claims |
| Legacy slice output safety | `src\slicer\slicer.py` still uses FFmpeg `-y`; choose overwrite/failure policy before modifying behavior |
| Downscaled cache identity | Pipeline still reuses an existing file by pathname; design identity/invalidation separately, preserving current behavior meanwhile |
| Isolated downscaler/slicer coverage | Current suites use real media; add focused mocked units alongside a requested behavior change, not by moving real integrations into unit collection |
| Historical roadmap reconciliation | [Optimization](optimize.todo.md) and [packaging](productionize.todo.md) are historical proposals, not verified current feature lists or measured gains |

## Structural migration acceptance

The source/test moves, installed CLI imports, preset/codecs discovery, settings
precedence, unit collection, editor references and Markdown links are checked
as part of this migration. Existing user edits and the selected CUDA environment
are preserved. Historical roadmap items remain open until their behavior is
independently verified.
