# tensorx-datasheet

[Point your bifrost data sheet url](https://docs.getbifrost.ai/providers/custom-pricing) here:

```
https://raw.githubusercontent.com/agile-lab-dev/tensorx-datasheet/refs/heads/main/data.json
```

Convert the [TensorX](https://sys.tensorx.ai) models API into a
[Bifrost](https://getbifrost.ai/datasheet) pricing datasheet.

The script fetches the live model catalogue from `https://sys.tensorx.ai/api/models`
and rewrites each entry into the Bifrost datasheet schema: a flat JSON object keyed
by model id, with numeric token costs, `mode`, `provider`, `base_model`, token
limits, capability flags, and metadata notes.

## Requirements

[uv](https://docs.astral.sh/uv/getting-started/installation/) — dependencies
(`httpx`, `typer`, `rich`) are declared inline in the script and installed automatically.

## Usage

```fish
uv run tensorx-datasheet.py --output data.json
uv run tensorx-datasheet.py --output data.json --verbose
```

| Option | Description |
| --- | --- |
| `--output`, `-o` | Path of the JSON datasheet file to write. |
| `--verbose`, `-v` | Enable verbose (DEBUG) logging. |

## Output format

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

Only fields present in the API response are emitted; capability flags appear only
when `true`.
