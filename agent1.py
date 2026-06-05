"""
Claude-powered Data Analyst Agent
===================================
Defines the tools Claude can call and runs the agentic loop.
"""

import os
import io
import json
import uuid
import traceback
import textwrap
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import anthropic

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

CHART_DIR = "/tmp"

# ── Tool definitions ──────────────────────────────────────────────────────────
TOOLS = [
    {
        "name": "load_data",
        "description": (
            "Load a CSV or Excel file and return metadata: shape, column names, "
            "dtypes, sample rows, and basic statistics. Call this first before "
            "any analysis."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "Absolute path to the file"},
            },
            "required": ["filepath"],
        },
    },
    {
        "name": "run_pandas",
        "description": (
            "Execute a Python/Pandas snippet to answer a data question. "
            "The dataframe is pre-loaded as `df`. Store your final answer in a "
            "variable named `result` (string, number, or dict). "
            "Do NOT call plt.show(); charts are handled by generate_chart."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code. `df` is available. Set `result = ...`.",
                },
                "filepath": {"type": "string", "description": "Path to data file"},
            },
            "required": ["code", "filepath"],
        },
    },
    {
        "name": "generate_chart",
        "description": (
            "Generate a chart image from the data. Returns a path to the PNG. "
            "Supported chart_types: bar, line, pie, scatter, histogram, box."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "filepath": {"type": "string"},
                "chart_type": {
                    "type": "string",
                    "enum": ["bar", "line", "pie", "scatter", "histogram", "box"],
                },
                "x_column": {"type": "string", "description": "Column for x-axis (or labels)"},
                "y_column": {"type": "string", "description": "Column for y-axis (or values)"},
                "title": {"type": "string"},
                "top_n": {
                    "type": "integer",
                    "description": "If set, use only the top N rows (sorted by y_column desc)",
                },
                "agg_func": {
                    "type": "string",
                    "enum": ["sum", "mean", "count", "max", "min"],
                    "description": "Aggregation to apply before plotting (groups by x_column)",
                },
            },
            "required": ["filepath", "chart_type", "title"],
        },
    },
]

SYSTEM_PROMPT = textwrap.dedent("""
    You are a friendly, expert data analyst assistant. The user has uploaded a dataset.
    Use the available tools to answer questions accurately.

    Guidelines:
    - Always call load_data first if you haven't seen the data yet.
    - Prefer run_pandas for precise calculations.
    - Use generate_chart when the user asks for a chart, graph, or plot.
    - Keep answers concise and clear. Format numbers nicely (e.g. 1,234.56).
    - If you find something interesting in the data, mention it briefly.
    - Use Markdown for formatting (bold key figures, bullet lists for multiple items).
    - Never reveal file paths or internal implementation details.
""").strip()


# ── Tool implementations ───────────────────────────────────────────────────────
def _load_df(filepath: str) -> pd.DataFrame:
    if filepath.endswith(".csv"):
        return pd.read_csv(filepath)
    return pd.read_excel(filepath)


def tool_load_data(filepath: str) -> str:
    try:
        df = _load_df(filepath)
        info = {
            "rows": int(df.shape[0]),
            "columns": int(df.shape[1]),
            "column_names": df.columns.tolist(),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "sample_rows": df.head(5).to_dict(orient="records"),
            "missing_values": df.isnull().sum().to_dict(),
            "numeric_summary": json.loads(df.describe().to_json()),
        }
        return json.dumps(info, default=str)
    except Exception as e:
        return f"ERROR: {e}"


def tool_run_pandas(code: str, filepath: str) -> str:
    try:
        df = _load_df(filepath)
        local_vars: dict = {"df": df, "pd": pd, "np": np}
        exec(code, {}, local_vars)  # noqa: S102
        result = local_vars.get("result", "Code executed (no `result` variable set).")
        if isinstance(result, (pd.DataFrame, pd.Series)):
            return result.to_string()
        return str(result)
    except Exception:
        return f"ERROR:\n{traceback.format_exc()}"


def tool_generate_chart(
    filepath: str,
    chart_type: str,
    title: str,
    x_column: str | None = None,
    y_column: str | None = None,
    top_n: int | None = None,
    agg_func: str | None = None,
) -> str:
    try:
        df = _load_df(filepath)

        # Optional aggregation
        if agg_func and x_column and y_column:
            agg_map = {"sum": "sum", "mean": "mean", "count": "count", "max": "max", "min": "min"}
            df = df.groupby(x_column)[y_column].agg(agg_map[agg_func]).reset_index()

        # Optional top-N
        if top_n and y_column:
            df = df.nlargest(top_n, y_column)

        fig, ax = plt.subplots(figsize=(9, 5))
        fig.patch.set_facecolor("#1e1e2e")
        ax.set_facecolor("#2a2a3e")

        colors = ["#7c83d6", "#f28b82", "#81c995", "#ffb74d", "#80cbc4", "#ce93d8"]

        if chart_type == "bar" and x_column and y_column:
            ax.bar(df[x_column].astype(str), df[y_column], color=colors[: len(df)])
            ax.set_xlabel(x_column, color="white")
            ax.set_ylabel(y_column, color="white")
            plt.xticks(rotation=45, ha="right", color="white")
        elif chart_type == "line" and x_column and y_column:
            ax.plot(df[x_column].astype(str), df[y_column], marker="o", color=colors[0], linewidth=2)
            ax.set_xlabel(x_column, color="white")
            ax.set_ylabel(y_column, color="white")
            plt.xticks(rotation=45, ha="right", color="white")
        elif chart_type == "pie" and x_column and y_column:
            ax.pie(df[y_column], labels=df[x_column].astype(str), autopct="%1.1f%%", colors=colors)
        elif chart_type == "scatter" and x_column and y_column:
            ax.scatter(df[x_column], df[y_column], color=colors[0], alpha=0.7)
            ax.set_xlabel(x_column, color="white")
            ax.set_ylabel(y_column, color="white")
        elif chart_type == "histogram" and x_column:
            ax.hist(df[x_column].dropna(), bins=20, color=colors[0], edgecolor="white")
            ax.set_xlabel(x_column, color="white")
            ax.set_ylabel("Frequency", color="white")
        elif chart_type == "box" and y_column:
            ax.boxplot(df[y_column].dropna(), patch_artist=True,
                       boxprops=dict(facecolor=colors[0]))
            ax.set_ylabel(y_column, color="white")
        else:
            return "ERROR: Invalid chart parameters. Check column names and chart_type."

        ax.set_title(title, color="white", fontsize=13, pad=12)
        ax.tick_params(colors="white")
        for spine in ax.spines.values():
            spine.set_edgecolor("#555")

        plt.tight_layout()
        chart_path = os.path.join(CHART_DIR, f"chart_{uuid.uuid4().hex[:8]}.png")
        plt.savefig(chart_path, dpi=130, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close(fig)
        return json.dumps({"chart_path": chart_path})
    except Exception:
        return f"ERROR:\n{traceback.format_exc()}"


def dispatch_tool(name: str, inputs: dict) -> str:
    if name == "load_data":
        return tool_load_data(**inputs)
    if name == "run_pandas":
        return tool_run_pandas(**inputs)
    if name == "generate_chart":
        return tool_generate_chart(**inputs)
    return f"Unknown tool: {name}"


# ── Agent loop ────────────────────────────────────────────────────────────────
async def run_agent(
    user_message: str,
    filepath: str,
    history: list[dict],
) -> tuple[str, str | None]:
    """
    Run the agentic loop.
    Returns (answer_text, chart_path_or_None).
    """
    # Build message list: history + current user turn
    messages = list(history) + [{"role": "user", "content": user_message}]

    chart_path = None
    MAX_TURNS = 8

    for _ in range(MAX_TURNS):
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            # Extract final text
            text_parts = [b.text for b in response.content if hasattr(b, "text")]
            return "\n".join(text_parts).strip(), chart_path

        if response.stop_reason != "tool_use":
            break

        # Handle tool calls
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            raw = dispatch_tool(block.name, block.input)

            # Check if a chart was generated
            if block.name == "generate_chart":
                try:
                    data = json.loads(raw)
                    if "chart_path" in data:
                        chart_path = data["chart_path"]
                        raw = json.dumps({"status": "Chart generated successfully."})
                except Exception:
                    pass

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": raw,
            })

        # Append assistant turn + tool results
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

    return "⚠️ I couldn't complete the analysis. Please rephrase your question.", chart_path
