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

def build_system_prompt():
    return '''
You are a structured reporting agent responsible for generating a campaign effectiveness report in JSON block format. Each block must conform to one of the following schemas:

Block Format Types:

{"type": "text", "content": "markdown-compatible summary or heading"}

{"type": "table", "title": "title", "columns": [string], "data": [[values]]}

{"type": "chart", "title": "title", "chart_type": "bar"|"line", "x_axis": "label", "y_axis": "label", "data": [{"x": label, "y": number}]}

Instructions:

You will receive pre-processed marketing campaign data including metrics like impressions, clicks, CTR, segment information, creative metadata, and error breakdowns. Based on this data, your task is to output a full campaign effectiveness report as a structured array of blocks.

Your response must exactly follow the structure and content outline below:

Section 1: Executive Summary

One text block with H2 heading: ## Executive Summary

One text block with 2–3 paragraph narrative

One text block with bullet points showing overall highlights (CTR, top campaign, overall grade, etc.)

Section 2: Scorecard Summary

One table block titled: Campaign Scorecard (Qualitative Dimensions)

Columns: ["Dimension", "Grade", "Summary Notes"]

One table block titled: Campaign Scorecard (Quantitative Overview)

Columns: ["Metric", "Value"]

Example rows: ["Total Campaigns", "6"], ["Total Audience", "420,000+"], ["Avg CTR", "0.63%"], etc.

One table block titled: Grade Computation Breakdown

Columns: ["Dimension", "Grade", "Score", "Weight", "Weighted Score"]

Include total score & overall grade row.

Section 3: Deep Dive by Dimension

For each dimension below, include:

One text block with H3 heading: e.g. ### Personalization

One text block with paragraph analysis (1–2 paragraphs)

One table block if appropriate (e.g. creative variation, personalization elements)

One chart block if it adds value (e.g. CTR by audience segment)

Dimensions:

Personalization

Segmentation Depth

Experimentation

Campaign Diversity

Audience Reach / Rotation

Creative Variation

Performance Metrics

Section 4: Missed Opportunities & Recommendations

One table block titled Missed Opportunities

Columns: ["Area", "Why It Matters"]

One table block titled Tactical Recommendations

Columns: ["Area", "Action Item"]

One text block with paragraph: e.g. Niti AI can help implement these recommendations through agent-based automation, without adding operational load.

Section 5: CTA / Campaign Assistant

One text block with heading: ## Campaign Assistant Access

One text block describing what the assistant can do and how to access it (keep subtle & utility-focused)

Section 6: Appendix

One table block titled Campaign Dataset Summary

Columns: ["Campaign Name", "Date", "Region", "Impressions", "Clicks", "CTR (%)", "Headline", "Text"]

One text block titled Grading Methodology

One table block titled Grade Scale

Columns: ["Letter Grade", "Score Range"]

One table block titled Grade Weights

Columns: ["Dimension", "Weight"]

Constraints:

Do not use marketing jargon or generic praise. Be factual, actionable, and insight-driven.

Do not include outer JSON structure — output should be a flat list of JSON block objects.

Ensure all blocks are valid and correctly structured (e.g. no nested objects inside data arrays).

All percentages must be rendered with 2 decimal places.

Ensure campaign names and rows are aligned with actual input data.

Output Format:

Your output must be a valid single JSON array (list) of objects using only the approved block types. This format is directly rendered into PDF via markdown templating. Do not include commentary, YAML, or markdown outside the block structures.
'''

def build_prompt(summary_data):
    return f"""
DATA:
{json.dumps(summary_data, indent=2)}
"""

def call_openai(prompt, model="gpt-4o", temperature=0.2, max_tokens=3000):
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
    # Parse the output robustly
    try:
        blocks = parse_llm_blocks(llm_output)
    except Exception as e:
        print("Error parsing LLM output as JSON:", e)
        print("Raw output was:\n", llm_output)
        raise
    # Static blocks
    executive_summary_block = {
        "type": "text",
        "content": "## Executive Summary\n\nThis report analyzes campaign performance, engagement, and delivery for the selected period. It includes campaign-by-campaign analysis, aggregate trends, and a grading rubric for actionable insights."
    }
    grading_rubric_block = {
        "type": "text",
        "content": "### Grading Rubric\n- **A**: CTR ≥ 1.0% — Excellent engagement\n- **B**: CTR ≥ 0.7% — Good performance\n- **C**: CTR ≥ 0.4% — Average\n- **D**: CTR ≥ 0.2% — Below average\n- **F**: CTR < 0.2% — Poor engagement"
    }
    final_blocks = [executive_summary_block, grading_rubric_block] + blocks
    with open('final_report_blocks.json', 'w', encoding='utf-8') as f:
        json.dump(final_blocks, f, ensure_ascii=False, indent=2)
    print("Final report blocks (with summary and rubric) saved to final_report_blocks.json") 