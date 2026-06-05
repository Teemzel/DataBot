"""
Google Gemini-powered Data Analyst Agent
=========================================
Uses Gemini 3.5 Flash (free tier) with function calling to analyze data.
"""

import os
import io
import json
import uuid
import textwrap
import traceback
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import google.generativeai as genai
import time
import glob
from google.api_core.exceptions import ResourceExhausted
time.sleep(12)  # Pauses for 2 seconds to respect the free-tier rate limit


# ── Configure Gemini ──────────────────────────────────────────────────────────
genai.configure(api_key="")



CHART_DIR = "/tmp"

SYSTEM_PROMPT = textwrap.dedent("""
    You are a friendly, expert data analyst assistant. The user has uploaded a dataset.
    Use the available tools to answer questions accurately.

    Guidelines:
    - Always call load_data first if you haven't analyzed the file yet.
    - Use run_pandas for precise calculations and aggregations.
    - Use generate_chart when the user asks for a chart, graph, or plot.
    - Keep answers concise and clear. Format numbers with commas (e.g. 1,234.56).
    - Use Markdown for formatting: **bold** key figures, bullet lists for multiple items.
    - If you spot something interesting in the data, mention it briefly.
    - Never reveal file paths or internal implementation details to the user.
""").strip()


# ── Tool implementations ───────────────────────────────────────────────────────
def _load_df(filepath: str) -> pd.DataFrame:
    if filepath.endswith(".csv"):
        return pd.read_csv(filepath)
    return pd.read_excel(filepath)


def load_data(filepath: str) -> dict:
    """Load a CSV or Excel file and return metadata including shape, columns, dtypes, sample rows, and statistics."""
    try:
        df = _load_df(filepath)
        return {
            "rows": int(df.shape[0]),
            "columns": int(df.shape[1]),
            "column_names": df.columns.tolist(),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "sample_rows": df.head(5).to_dict(orient="records"),
            "missing_values": df.isnull().sum().to_dict(),
            "numeric_summary": json.loads(df.describe().to_json()),
        }
    except Exception as e:
        return {"error": str(e)}


def run_pandas(filepath: str, code: str) -> dict:
    """Execute Python/Pandas code to answer a data question. The dataframe is pre-loaded as `df`. Store the final answer in a variable named `result`."""
    try:
        # 🔧 OVERRIDE: Automatically grab the real file from your downloads folder
        download_files = glob.glob(os.path.join("downloads", "*"))
        if download_files:
            filepath = max(download_files, key=os.path.getctime)
            print(f"🔧 run_pandas forcing file load from: {filepath}")
            
        df = _load_df(filepath)
        local_vars: dict = {"df": df, "pd": pd, "np": np}
        exec(code, {}, local_vars)  # noqa: S102
        result = local_vars.get("result", "Code executed. No `result` variable was set.")
        if isinstance(result, (pd.DataFrame, pd.Series)):
            return {"result": result.to_string()}
        return {"result": str(result)}
    except Exception:
        return {"error": traceback.format_exc()}


def generate_chart(
    filepath: str,
    chart_type: str,
    title: str,
    x_column: str = None,
    y_column: str = None,
    top_n: int = None,
    agg_func: str = None,
) -> dict:
    """Generate a chart image from the data and return the file path."""
    try:
        df = _load_df(filepath)

        # Optional aggregation
        if agg_func and x_column and y_column:
            agg_map = {"sum": "sum", "mean": "mean", "count": "count", "max": "max", "min": "min"}
            df = df.groupby(x_column)[y_column].agg(agg_map[agg_func]).reset_index()

        # Optional top-N filter
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
            plt.yticks(color="white")

        elif chart_type == "line" and x_column and y_column:
            ax.plot(df[x_column].astype(str), df[y_column], marker="o", color=colors[0], linewidth=2)
            ax.set_xlabel(x_column, color="white")
            ax.set_ylabel(y_column, color="white")
            plt.xticks(rotation=45, ha="right", color="white")
            plt.yticks(color="white")

        elif chart_type == "pie" and x_column and y_column:
            ax.pie(df[y_column], labels=df[x_column].astype(str), autopct="%1.1f%%", colors=colors)

        elif chart_type == "scatter" and x_column and y_column:
            ax.scatter(df[x_column], df[y_column], color=colors[0], alpha=0.7)
            ax.set_xlabel(x_column, color="white")
            ax.set_ylabel(y_column, color="white")
            plt.xticks(color="white")
            plt.yticks(color="white")

        elif chart_type == "histogram" and x_column:
            ax.hist(df[x_column].dropna(), bins=20, color=colors[0], edgecolor="white")
            ax.set_xlabel(x_column, color="white")
            ax.set_ylabel("Frequency", color="white")
            plt.xticks(color="white")
            plt.yticks(color="white")

        elif chart_type == "box" and y_column:
            ax.boxplot(df[y_column].dropna(), patch_artist=True,
                       boxprops=dict(facecolor=colors[0]))
            ax.set_ylabel(y_column, color="white")
            plt.yticks(color="white")

        else:
            return {"error": "Invalid chart parameters. Check column names and chart_type."}

        ax.set_title(title, color="white", fontsize=13, pad=12)
        ax.tick_params(colors="white")
        for spine in ax.spines.values():
            spine.set_edgecolor("#555")

        plt.tight_layout()
        chart_path = os.path.join(CHART_DIR, f"chart_{uuid.uuid4().hex[:8]}.png")
        plt.savefig(chart_path, dpi=130, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close(fig)
        return {"chart_path": chart_path, "status": "Chart generated successfully."}

    except Exception:
        return {"error": traceback.format_exc()}


# ── Gemini tool declarations ──────────────────────────────────────────────────
TOOL_DECLARATIONS = [
    {
        "name": "load_data",
        "description": "Load a CSV or Excel file and return metadata: shape, column names, dtypes, sample rows, missing values, and numeric statistics. Call this first before any analysis.",
        "parameters": {
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "description": "Absolute path to the data file",
                }
            },
            "required": ["filepath"],
        },
    },
    {
        "name": "run_pandas",
        "description": "Execute Python/Pandas code to answer a data question. The dataframe is pre-loaded as `df`. Store the final answer in a variable named `result`. Do NOT generate charts here.",
        "parameters": {
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "description": "Absolute path to the data file",
                },
                "code": {
                    "type": "string",
                    "description": "Python code to run. `df`, `pd`, and `np` are available. Set `result = ...` with your answer.",
                },
            },
            "required": ["filepath", "code"],
        },
    },
    {
        "name": "generate_chart",
        "description": "Generate a chart image from the data. Use when the user asks for a chart, graph, or plot.",
        "parameters": {
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "Absolute path to the data file"},
                "chart_type": {
                    "type": "string",
                    "enum": ["bar", "line", "pie", "scatter", "histogram", "box"],
                    "description": "Type of chart to generate",
                },
                "title": {"type": "string", "description": "Chart title"},
                "x_column": {"type": "string", "description": "Column for x-axis or pie labels"},
                "y_column": {"type": "string", "description": "Column for y-axis or pie values"},
                "top_n": {"type": "integer", "description": "Show only the top N rows sorted by y_column descending"},
                "agg_func": {
                    "type": "string",
                    "enum": ["sum", "mean", "count", "max", "min"],
                    "description": "Aggregate y_column grouped by x_column before plotting",
                },
            },
            "required": ["filepath", "chart_type", "title"],
        },
    },
]



# ── Dispatch tool calls ───────────────────────────────────────────────────────
def dispatch_tool(name: str, args: dict) -> dict:
   
    # Find the actual newest downloaded file in your local downloads folder
    download_files = glob.glob(os.path.join("downloads", "*"))
    actual_filepath = max(download_files, key=os.path.getctime) if download_files else None

    if name == "load_data":
        if actual_filepath:
            print(f"🔧 Overriding path: forcing load of {actual_filepath}")
            return load_data(filepath=actual_filepath)
        return load_data(**args)
            
    if name == "run_pandas":
        '''if actual_filepath and "code" in args:
            # Safer replacement structure without using re.sub
            # Looks for common placeholders Gemini utilizes in its code strings
            code_str = args["code"]
            for placeholder in ["customer_data.csv", "superstore.csv", "data.csv"]:
                if placeholder in code_str:
                    code_str = code_str.replace(placeholder, actual_filepath.replace("\\", "/"))
            
            # Fallback catch-all case if Gemini hallucinates a completely random name
            if ".csv" in code_str and actual_filepath not in code_str:
                import re
                try:
                    # Clean the path string format to protect backslashes
                    safe_path = actual_filepath.replace("\\", "/")
                    code_str = re.sub(r"['\"][^'\"]+\.csv['\"]", f"'{safe_path}'", code_str)
                except Exception:
                    pass
            
            args["code"] = code_str
            print(f"🔧 Correcting Pandas Query Code: {args['code']}")
            '''
        return run_pandas(**args)
        
    if name == "generate_chart":
        return generate_chart(**args)
    return {"error": f"Unknown tool: {name}"}



# ── Agent loop ────────────────────────────────────────────────────────────────
async def run_agent(
    user_message: str,
    filepath: str,
    history: list[dict],
) -> tuple[str, str | None]:
    """
    Run the Gemini agentic loop with function calling.
    Returns (answer_text, chart_path_or_None).
    """
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=SYSTEM_PROMPT,
        tools=[{"function_declarations": TOOL_DECLARATIONS}],
    )

    # Build chat history for Gemini format
    gemini_history = []
    for msg in history:
        gemini_history.append(msg)

    chat = model.start_chat(history=gemini_history)
    chart_path = None
    MAX_TURNS = 8

    current_message = user_message

    for _ in range(MAX_TURNS):
        response = None
        for attempt in range(4):
            try:
                response = chat.send_message(current_message)
                break  # Success! Exit the retry loop
            except ResourceExhausted:
                if attempt < 3:
                    print(f"⚠️ Gemini Rate Limit hit. Waiting 10 seconds (Attempt {attempt + 1}/3)...")
                    time.sleep(10)
                else:
                    print("❌ Max retries reached for rate limit.")
                    return "⚠️ The analysis took too long due to API traffic. Please wait a moment and try again.", chart_path

        if not response:
            return "⚠️ I couldn't reach the AI model right now. Please try again.", chart_path
        candidate = response.candidates[0]
        parts = candidate.content.parts
        
        text_content = " ".join(p.text for p in parts if hasattr(p, "text") and p.text).strip()
        
        # Check if Gemini wants to call a function
        function_calls = [p for p in parts if hasattr(p, "function_call") and p.function_call.name]
        
        if not function_calls or ("missing" in text_content.lower() or "value" in text_content.lower()):
            if text_content:
                return text_content, chart_path
            
        '''if not function_calls:
            # Final text answer
            text = " ".join(p.text for p in parts if hasattr(p, "text") and p.text)
            return text.strip(), chart_path'''

        # Execute all function calls
        tool_responses = []
        for part in function_calls:
            fc = part.function_call
            args = dict(fc.args)
            result = dispatch_tool(fc.name, args)

            # Track chart path
            if fc.name == "generate_chart" and "chart_path" in result:
                chart_path = result["chart_path"]
                result = {"status": "Chart generated successfully."}

            tool_responses.append(
                genai.protos.Part(
                    function_response=genai.protos.FunctionResponse(
                        name=fc.name,
                        response={"result": json.dumps(result, default=str)},
                    )
                )
            )

        # Send tool results back
        current_message = tool_responses

    return "⚠️ I couldn't complete the analysis. Please try rephrasing your question.", chart_path
