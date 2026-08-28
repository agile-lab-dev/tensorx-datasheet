# tensorx-datasheet

An always-up-to-date [Bifrost](https://getbifrost.ai) model datasheet that
includes [TensorX](https://tensorx.ai) pricing and model information, refreshed
daily and available as a raw file directly from GitHub:

```
https://raw.githubusercontent.com/agile-lab-dev/tensorx-datasheet/refs/heads/main/data.json
```

[Point your Bifrost data sheet URL](https://docs.getbifrost.ai/providers/custom-pricing)
there and TensorX-hosted models show up with correct costs, token limits, and
capabilities — no maintenance on your side.

## Sample entry

```json
{
  "deepseek/deepseek-v3.2": {
    "mode": "chat",
    "provider": "deepseek",
    "base_model": "deepseek-v3.2",
    "max_input_tokens": 163840,
    "max_output_tokens": 163840,
    "max_tokens": 163840,
    "input_cost_per_token": 3e-07,
    "output_cost_per_token": 5e-07,
    "cache_read_input_token_cost": 7.5e-08,
    "supports_function_calling": true,
    "supports_tool_choice": true,
    "supports_reasoning": true,
    "metadata": { "notes": "..." }
  }
}
```

## How it works

A single Python script (`tensorx-datasheet.py`) fetches the live TensorX models API,
rewrites each entry into the Bifrost datasheet schema, and concats it on top of the
official [Bifrost datasheet](https://getbifrost.ai/datasheet): all Bifrost models are
kept, and for models present in both, the TensorX entry wins (fields are merged
per-model, with TensorX values taking precedence). A daily job regenerates and commits
`data.json`. To run it manually (requires [uv](https://docs.astral.sh/uv/)):

```fish
uv run tensorx-datasheet.py --output data.json
```
