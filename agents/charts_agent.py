import json
import re
import io
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for Streamlit
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from utils.llm_retry import invoke_with_fallback


CHART_EXTRACTION_PROMPT = """
You are a Data Visualization Expert. Your job is to analyze a text-based answer and extract structured data suitable for a chart.

### INPUT
User Query: {query}
Text Answer: {answer}

### TASK
1. Determine if the answer contains numerical/categorical data worth visualizing.
2. If YES, extract the data and decide the best chart type:
   - **line**: For time-series or trend data (e.g., prices over months/years)
   - **bar**: For comparisons between categories (e.g., commodity A vs B, counts per category)
   - **pie**: For distribution/proportion data (e.g., subscription plan breakdown, share percentages)
3. If NO chartable data exists, return chart_type as "none".

### OUTPUT FORMAT
Return ONLY valid JSON. No markdown, no explanation:
{{
  "chart_type": "line" | "bar" | "pie" | "none",
  "title": "A short descriptive chart title",
  "x_label": "X axis label (for line/bar only)",
  "y_label": "Y axis label (for line/bar only)",
  "data": [
    {{"label": "Category or Date", "value": 123.45}},
    ...
  ]
}}

### STRICT RULES
- "value" must always be a number (float or int). Never a string.
- "label" should be concise (e.g., "Jan 2024", "Gold", "Premium Plan")
- For line charts, labels should be ordered chronologically
- For pie charts, values should sum to a meaningful total (counts or percentages)
- If data has more than 20 points, sample the most significant ones (first, last, peaks)
- Return "none" if the answer is purely textual with no numerical data

### USER QUERY
{query}

### TEXT ANSWER
{answer}
"""


def extract_chart_data(query: str, answer: str) -> dict | None:
    """
    Calls LLM to extract chart-ready structured data from a text answer.
    Returns a dict or None if no chartable data.
    """
    if isinstance(answer, list):
        answer = "\n".join(str(item) for item in answer)
    elif not isinstance(answer, str):
        answer = str(answer) if answer else ""

    if not answer.strip():
        return None

    prompt = CHART_EXTRACTION_PROMPT.format(query=query, answer=answer)

    try:
        response = invoke_with_fallback(
            prompt,
            temperature=0.0
        )

        raw = response.content if hasattr(response, "content") else response

        match = re.search(r'\{.*\}', raw, re.DOTALL)
        json_str = match.group(0) if match else raw
        chart_data = json.loads(json_str)

        if chart_data.get("chart_type") == "none":
            return None

        if not chart_data.get("data"):
            return None

        cleaned_data = []

        for item in chart_data["data"]:
            try:
                cleaned_data.append({
                    "label": str(item["label"]),
                    "value": float(item["value"])
                })
            except (ValueError, KeyError):
                continue

        if not cleaned_data:
            return None

        # Skip chart generation if fewer than 3 data points
        if len(cleaned_data) < 3:
            print(f"[ChartAgent] Skipping chart: Only {len(cleaned_data)} data point(s), need at least 3")
            return None

        chart_data["data"] = cleaned_data
        return chart_data

    except Exception as e:
        print(f"[ChartAgent] Failed to extract chart data: {e}")
        return None


def build_matplotlib_chart(chart_data: dict) -> io.BytesIO | None:
    """
    Builds a matplotlib chart from chart_data dict.
    Returns a BytesIO PNG buffer or None.
    """
    chart_type = chart_data.get("chart_type", "none")
    title = chart_data.get("title", "Data Visualization")
    x_label = chart_data.get("x_label", "")
    y_label = chart_data.get("y_label", "")
    data = chart_data.get("data", [])

    if not data or chart_type == "none":
        return None

    labels = [d["label"] for d in data]
    values = [d["value"] for d in data]

    COLORS = [
        "#1E88E5", "#00ACC1", "#43A047", "#FB8C00", "#E53935",
        "#8E24AA", "#3949AB", "#00897B", "#F4511E", "#6D4C41"
    ]

    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#f9f9f9")

    if chart_type == "bar":
        bars = ax.bar(
            labels,
            values,
            color=COLORS[:len(labels)],
            edgecolor="white",
            linewidth=0.8,
            zorder=3
        )

        ax.set_xlabel(x_label, fontsize=11, color="#555")
        ax.set_ylabel(y_label, fontsize=11, color="#555")
        ax.yaxis.grid(True, linestyle="--", alpha=0.5, zorder=0)
        ax.set_axisbelow(True)
        plt.xticks(rotation=30, ha="right", fontsize=9)

        val_min, val_max = min(values), max(values)
        val_range = val_max - val_min

        if val_max > 0 and val_range < val_max * 0.05:
            padding = max(val_range * 2, val_max * 0.01)
            ax.set_ylim(val_min - padding, val_max + padding)

        if val_range > 0:
            import math
            needed_decimals = max(2, -int(math.floor(math.log10(val_range))) + 2)
            fmt = f"{{:,.{needed_decimals}f}}"
        else:
            fmt = "{:,.2f}"

        for bar in bars:
            height = bar.get_height()

            ax.annotate(
                fmt.format(height),
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 5),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=8,
                color="#333"
            )

    elif chart_type == "line":
        ax.plot(
            labels,
            values,
            marker="o",
            linewidth=2.5,
            color="#1E88E5",
            markersize=7,
            markerfacecolor="white",
            markeredgewidth=2,
            zorder=3
        )

        ax.fill_between(
            range(len(labels)),
            values,
            alpha=0.08,
            color="#1E88E5"
        )

        ax.set_xlabel(x_label, fontsize=11, color="#555")
        ax.set_ylabel(y_label, fontsize=11, color="#555")
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=9)
        ax.yaxis.grid(True, linestyle="--", alpha=0.5, zorder=0)
        ax.set_axisbelow(True)

        val_min, val_max = min(values), max(values)
        val_range = val_max - val_min

        if val_max > 0 and val_range < val_max * 0.05:
            padding = max(val_range * 2, val_max * 0.01)
            ax.set_ylim(val_min - padding, val_max + padding)

    elif chart_type == "pie":
        wedges, texts, autotexts = ax.pie(
            values,
            labels=labels,
            colors=COLORS[:len(labels)],
            autopct="%1.1f%%",
            startangle=140,
            wedgeprops=dict(edgecolor="white", linewidth=2),
            pctdistance=0.82
        )

        for text in autotexts:
            text.set_fontsize(9)
            text.set_color("white")

        centre_circle = plt.Circle((0, 0), 0.60, fc="white")
        fig.gca().add_artist(centre_circle)
        ax.axis("equal")

    else:
        plt.close(fig)
        return None

    ax.set_title(title, fontsize=14, fontweight="bold", color="#2c3e50", pad=15)

    for spine in ax.spines.values():
        spine.set_visible(False)

    plt.tight_layout()

    buffer = io.BytesIO()
    plt.savefig(
        buffer,
        format="png",
        dpi=150,
        bbox_inches="tight",
        facecolor=fig.get_facecolor()
    )

    buffer.seek(0)
    plt.close(fig)

    return buffer


def graph_agent_node(state):
    """
    LangGraph node for chart generation.
    IMPORTANT: Does NOT modify final_output — only adds chart_buffer to state.
    """
    query = state.get("query", "")
    final_output = state.get("final_output", "")

    if isinstance(final_output, list):
        output_str = "\n".join(str(item) for item in final_output)
    elif not isinstance(final_output, str):
        output_str = str(final_output) if final_output else ""
    else:
        output_str = final_output

    if not output_str.strip():
        print("[GraphAgent] No final_output to visualize.")
        return {"chart_buffer": None}

    print(f"[GraphAgent] Extracting chart for: {query[:60]}...")

    chart_data = extract_chart_data(query, output_str)

    if not chart_data:
        print("[GraphAgent] No chartable data found.")
        return {"chart_buffer": None}

    chart_buffer = build_matplotlib_chart(chart_data)

    if chart_buffer:
        print(
            f"[GraphAgent] ✅ Chart built: "
            f"type={chart_data.get('chart_type')}, "
            f"points={len(chart_data.get('data', []))}"
        )
    else:
        print("[GraphAgent] Chart build failed.")

    return {"chart_buffer": chart_buffer}