import os
import json
from dotenv import load_dotenv
import openai
import re

# Load your OpenAI API key from .env
def load_api_key():
    load_dotenv()
    return os.getenv("OPENAI_API_KEY")

# Load summary data
def load_summary_data(path='summary_data.json'):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def build_campaigns_summary_block(summary_data):
    campaigns = summary_data["campaigns"]
    data = []
    for c in campaigns:
        impressions = 0
        clicks = 0
        ctr = 0.0
        # Sum across all channels for impressions and clicks
        if "channels" in c:
            for ch in c["channels"]:
                impressions += ch.get("impressions", 0) or 0
                clicks += ch.get("clicked", 0) or 0
        # Calculate CTR (avoid division by zero)
        ctr = (clicks / impressions * 100) if impressions > 0 else 0.0
        data.append([
            c.get("campaign_name"),
            c.get("date_sent"),
            c.get("region") or "N/A",
            impressions,
            clicks,
            f"{ctr:.2f}"
        ])
    return {
        "type": "table",
        "title": "Campaign Dataset Summary for all campaigns",
        "columns": ["Campaign Name", "Date", "Region", "Impressions", "Clicks", "CTR (%)"],
        "data": data
    }

def build_journeys_summary_block(summary_data):
    journeys = summary_data["journeys"]
    data = []
    for j in journeys:
        data.append([
            j.get("journey_name"),
            j.get("status"),
            j.get("start_time"),
            j.get("message_channel") or "N/A",
            j.get("goal_completions"),
            j.get("control_group_size"),
            j.get("conversion_rate")
        ])
    return {
        "type": "table",
        "title": "Journey Dataset Summary for all journeys",
        "columns": ["Journey Name", "Status", "Start Time", "Message Channel", "Goal Completions", "Control Group Size", "Conversion Rate"],
        "data": data
    }

def build_system_prompt():
    return '''
You are a structured reporting agent responsible for generating a marketing campaign effectiveness report. Your output must be a single JSON object, where each key corresponds to a specific section or placeholder in the report template. Do NOT output a list of blocks. Do NOT include any headings or section titles in the values unless specifically required by the instructions below.

For each key, provide the required content as follows:

---

**Text/Narrative Sections:**
- Output as plain text (no markdown headings).
- For all deep dive dimension keys (keys starting with "deep_dive_"), output a JSON object with the following keys:
    - focus: string (what is being analyzed for this dimension)
    - grade: string (the grade for this dimension)
    - details: list of strings. Each string must start with the required bullet heading (see below), followed by a colon and the LLM-generated analysis for that bullet. The LLM must use concrete campaign/journey examples and provide actionable, factual, and insight-driven analysis for each bullet. Do NOT use generic praise or marketing jargon.
- For "missed_opportunities" and "recommendations", output a list of strings. Each string should be a single bullet/point/statement (not a paragraph or markdown). Do NOT output a single string or markdown list—output a JSON list of strings.
- For other narrative keys, output as plain text.

**Tables:**
- Output as a list of rows (list of lists), with the first row being the column headers.
- Do NOT include the table title or any extra rows.

**Highlights/Boxes:**
- Output as a list of strings (each string is a highlight or metric to be rendered as a card/box).

---

**Required Keys and Content:**

- "executive_summary": 2–3 paragraphs summarizing both campaign and journey performance, referencing total campaigns, total journeys, key highlights, and both campaign and journey grades. Be factual, actionable, and insight-driven.
- "time_frame": The time frame over which the report is being generated (e.g., "15 Jul 2025 - 16 Jul 2025").
- "key_highlights_boxes": List of 5–8 key highlights (e.g., overall CTR, top campaign, top journey, overall grade, journey grade, etc.).
- "campaign_scorecard_quant_table": Table rows for the Campaign Scorecard (Quantitative Overview). Columns: ["Metric", "Value"].
- "campaign_scorecard_qual_table": Table rows for the Campaign Scorecard (Qualitative Dimensions). Columns: ["Dimension", "Grade", "Summary Notes"].
- "journey_scorecard_quant_table": Table rows for the Journey Scorecard (Quantitative Overview). Columns: ["Metric", "Value"].
- "journey_scorecard_qual_table": Table rows for the Journey Scorecard (Qualitative Dimensions). Columns: ["Dimension", "Grade", "Summary Notes"].
- Note: the dimensions for the qualitative tables must be the same as the dimensions in the deep dive section.

- For each deep dive key, use the following required bullet headings for the details list. The LLM must generate the analysis for each bullet, starting with the heading and a colon:
- For each deep dive details make sure to include concrete campaign/journey examples. The examples need to showcase how the dimension sub-heading is being used in the campaign/journey and how it can be improved.
- "deep_dive_personalization": {
    "focus": "Evaluating the integration of personalization in campaigns and journeys.",
    "grade": string,
    "details": [
      "Use of user attributes: ",
      "Behavioral triggers: ",
      "Journey-level dynamic routing:"
    ]
  }

- "deep_dive_segmentation_depth": {
    "focus": "Analyzing the effectiveness of segmentation strategies.",
    "grade": string,
    "details": [
      "Number of active segments and their logic:",
      "Overlap between segments:",
      "Segment-wise performance variation:"
    ]
  }

- "deep_dive_experimentation": {
    "focus": "Examining the structure and implementation of experiments.",
    "grade": string,
    "details": [
      "Number of experiments and their logic:",
      "Sample size and confidence levels:",
      "Existence of clear hypothesis:"
    ]
  }

- "deep_dive_campaign_diversity": {
    "focus": "Understanding the variety in campaign goals and channels.",
    "grade": string,
    "details": [
      "Variety in campaign goals:",
      "Channels used:"
    ]
  }

- "deep_dive_audience_reach_rotation": {
    "focus": "Measuring audience engagement and exposure.",
    "grade": string,
    "details": [
      "Reach metrics:",
      "Rotation metrics:",
      "Audience fatigue symptoms:"
    ]
  }

- "deep_dive_creative_variation": {
    "focus": "Assessing the diversity and testing of creative elements.",
    "grade": string,
    "details": [
      "Variants tested:",
      "Visual vs Textual variation:",
      "Performance by creative type:"
    ]
  }

- "deep_dive_performance_metrics": {
    "focus": "Evaluating the tracking and analysis of performance metrics.",
    "grade": string,
    "details": [
      "Performance metrics tracked:",
      "Funnel drop-offs analysis:"
    ]
  }

- "missed_opportunities": List of strings. Each string is a bullet/point for a missed opportunity for both campaigns and journeys. Each bullet should reference a specific area and why it matters.
- "recommendations": List of strings. Each string is a bullet/point for a tactical recommendation for both campaigns and journeys. Each bullet should reference a specific area and a concrete action item.
- "campaign_agent_access": 1–2 sentences describing what the campaign agent can do and how to access it (keep subtle & utility-focused).
- "campaigns_grade_breakdown_table": Table rows for Campaigns Grade Computation Breakdown. Columns: ["Dimension", "Grade", "Score", "Weight", "Weighted Score"].
- "journeys_grade_breakdown_table": Table rows for Journeys Grade Computation Breakdown. Columns: ["Dimension", "Grade", "Score", "Weight", "Weighted Score"].
- "grade_scale_table": Table rows for Grade Scale. Columns: ["Letter Grade", "Score Range"].
- "grade_weights_table": Table rows for Grade Weights. Columns: ["Dimension", "Weight"].
- "campaign_table_rows": Table rows for Campaign Dataset Summary for all campaigns. Columns: ["Campaign Name", "Date", "Region", "Impressions", "Clicks", "CTR (%)"]. Note all campaigns must be displayed in the table.
- "journey_table_rows": Table rows for Journey Dataset Summary for all journeys. Columns: ["Journey Name", "Status", "Start Time", "Message Channel", "Goal Completions", "Control Group Size", "Conversion Rate"]. Note all journeys must be displayed in the table.

---

**General Instructions:**
- Do NOT include any outer JSON structure, YAML, or markdown outside the JSON object.
- Do NOT include commentary or explanations outside the required fields.
- All percentages must be rendered with 2 decimal places.
- Ensure campaign and journey names and rows are aligned with actual input data.
- Be factual, actionable, and insight-driven. Do not use marketing jargon or generic praise.
- Use concrete campaign and journey examples wherever possible.
- Your output must be a valid single JSON object with all required keys.
'''

def build_prompt(summary_data):
    return f"""
DATA:
{json.dumps(summary_data, indent=2)}
"""

def call_openai(prompt, model="gpt-4o", temperature=0.7, max_tokens=8192):
    api_key = load_api_key()
    client = openai.OpenAI(api_key=api_key)
    system_prompt = build_system_prompt()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        temperature=temperature,
        max_tokens=max_tokens
    )
    return response.choices[0].message.content

def parse_llm_blocks(llm_output):
    # Remove code block markers if present
    llm_output = re.sub(r'^```[a-zA-Z]*\n', '', llm_output)
    llm_output = re.sub(r'```$', '', llm_output).strip()
    # Try to parse as a JSON array
    try:
        return json.loads(llm_output)
    except json.JSONDecodeError:
        # Fallback: treat as newline-separated JSON objects
        lines = [line.strip() for line in llm_output.splitlines() if line.strip() and line.strip().startswith('{')]
        json_array = '[{}]'.format(','.join(lines))
        return json.loads(json_array)

if __name__ == '__main__':
    summary_data = load_summary_data()
    prompt = build_prompt(summary_data)
    print("Calling OpenAI LLM to generate report blocks...")
    llm_output = call_openai(prompt)
    # Ensure llm_output is a string
    if llm_output is None:
        raise ValueError("LLM output is None!")
    if not isinstance(llm_output, str):
        llm_output = str(llm_output)
    # Remove code block markers if present
    llm_output = llm_output.strip()
    if llm_output.startswith('```json'):
        llm_output = llm_output[len('```json'):].strip()
    if llm_output.startswith('```'):
        llm_output = llm_output[len('```'):].strip()
    if llm_output.endswith('```'):
        llm_output = llm_output[:-3].strip()
    try:
        llm_json = json.loads(llm_output)
    except Exception as e:
        print("Error parsing LLM output as JSON:", e)
        print("Raw output was:\n", llm_output)
        raise
    with open('llm_output.json', 'w', encoding='utf-8') as f:
        json.dump(llm_json, f, ensure_ascii=False, indent=2)
    print("LLM output saved to llm_output.json") 