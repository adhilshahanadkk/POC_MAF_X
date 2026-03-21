from datetime import datetime
from agents.llm_provider import get_llm

llm = get_llm(temperature=0.0)

def report_agent_node(state):
    # 1. ROBUST DATA RETRIEVAL
    # In a multi-agent flow, data might be in 'final_output' (from combiner)
    # or 'multi_results' (raw list from executor).
    raw_data = state.get("final_output")
    if not raw_data:
        raw_data = state.get("multi_results")
        
    # Read chart buffer from state
    chart_buffer=state.get("chart_buffer")
    # 2. TIMESTAMP GENERATION
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    # 3. PROMPT PREPARATION
    # We use .format() to inject the dynamic variables into your template
    report_template = """
### ROLE
You are an Executive Reporting Specialist. Your mission is to transform raw system data into a high-quality, structured business report.

### DESIGN PRINCIPLES
1. **Executive Tone**: Maintain a formal, neutral, and authoritative voice. 
2. **Scannability**: Use bold headers and logical spacing to ensure the report is easy to digest at a glance.
3. **Internal Logic**: Group related data points (e.g., all user-related info in one section, all market-related info in another).
4. **Cleanliness**: Strictly remove all technical jargon, database names, SQL syntax, or mentions of "agents."

### DATA SOURCE
{data}

### REPORT STRUCTURE REQUIREMENTS
1. **Title**: A professional, centered title (e.g., "Subscription and Market Analysis Report").
2. **Executive Summary**: A brief (2-3 sentence) overview of the findings.
3. **Key Findings**: 
   - Use organized headings.
   - Use bullet points for specific data like dates, prices, or account details.
4. **Analysis/Conclusion**: A final statement based on the provided data.

### OUTPUT FORMAT
Provide the report in Markdown format. Ensure it looks like a physical document.

---
## [Title of Report]
---

**Date**: {date}

### 1. Executive Summary
<Overview here>

### 2. User & Subscription Details
<Findings here>

### 3. Market Performance & Commodity Trends
<Findings here>

### 4. Conclusion
<Final summary here>
"""
    # Inject variables into the prompt
    final_prompt = report_template.format(data=raw_data, date=timestamp)

    # 4. INVOKE LLM
    response = llm.invoke(final_prompt)
    report_content = response.content if hasattr(response, "content") else response

    # 5. RETURN STATE
    return {
        "report_text": report_content, 
        "final_output": "The requested report has been generated. You can download the PDF and DOCX versions below.",
        "route": "report_agent"
    }





