import json
import base64
from io import BytesIO
import pandas as pd
import matplotlib.pyplot as plt
import markdown
from weasyprint import HTML, CSS
import uuid
import re
import os
import openai
from dotenv import load_dotenv

load_dotenv()

# --- Renderers ---
def render_chart_base64(chart_block, block_id):
    plt.style.use('bmh')
    plt.figure(figsize=(10, 6), facecolor='#ffffff')
    block = chart_block.get('content', chart_block)
    chart_type = block.get('chart_type') or block.get('type') or 'bar'
    if 'x' in block and 'y' in block:
        x = block['x']
        y = block['y']
    elif 'data' in block and isinstance(block['data'], list):
        data = block['data']
        if data and isinstance(data[0], dict):
            keys = list(data[0].keys())
            if len(keys) >= 2:
                x_key, y_key = keys[0], keys[1]
                x = [d[x_key] for d in data]
                y = [d[y_key] for d in data]
            else:
                raise ValueError("Chart data dicts must have at least two keys")
        elif data and isinstance(data[0], (list, tuple)) and len(data[0]) == 2:
            x, y = zip(*data)
        else:
            raise ValueError("Unsupported chart data format")
    else:
        raise ValueError("Chart block missing x/y or data fields")
    colors = ['#4A5568', '#718096', '#A0AEC0', '#CBD5E0']
    if chart_type == 'bar':
        bars = plt.bar(x, y, color=colors[0])
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height,
                     f'{height:.2f}',
                     ha='center', va='bottom',
                     fontsize=10,
                     fontweight='bold')
    elif chart_type == 'line':
        plt.plot(x, y, color=colors[0], marker='o', linewidth=2, markersize=8,
                 markerfacecolor='white', markeredgewidth=2)
        for xi, yi in zip(x, y):
            plt.text(xi, yi, f'{yi:,.0f}', ha='center', va='bottom',
                     fontsize=10, fontweight='bold')
    else:
        plt.bar(x, y, color=colors[0])
    plt.title(block.get('title', ''), pad=20, fontsize=14, fontweight='bold', color='#1f2937')
    plt.xlabel(block.get('x_axis', block.get('xlabel', '')), labelpad=10, fontsize=12, color='#4b5563')
    plt.ylabel(block.get('y_axis', block.get('ylabel', '')), labelpad=10, fontsize=12, color='#4b5563')
    if max(len(str(xi)) for xi in x) > 10:
        plt.xticks(rotation=45, ha='right')
    plt.grid(True, linestyle='--', alpha=0.3)
    for spine in plt.gca().spines.values():
        spine.set_visible(False)
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=300, bbox_inches='tight', facecolor='#ffffff')
    plt.close()
    buf.seek(0)
    b64_string = base64.b64encode(buf.read()).decode()
    img_tag = f'<img id="{block_id}" src="data:image/png;base64,{b64_string}" alt="{block.get("title", "")}" style="width:100%; height:auto;">'
    return img_tag

def render_table_html(table_block, block_id):
    if 'headers' in table_block and 'rows' in table_block:
        columns = table_block['headers']
        rows = table_block['rows']
        title = table_block.get('title', '')
    elif 'columns' in table_block and 'data' in table_block:
        columns = table_block['columns']
        rows = table_block['data']
        title = table_block.get('title', '')
    elif 'content' in table_block:
        content = table_block['content']
        columns = content.get('headers') or content.get('columns')
        rows = content.get('rows') or content.get('data')
        title = content.get('title', '')
    else:
        raise ValueError("Table block missing required keys")
    df = pd.DataFrame(rows, columns=columns)
    table_html = df.to_html(index=False, classes='table')
    return f'<div id="{block_id}"><h2>{title}</h2>{table_html}</div>'

def render_text_html(text_block, block_id):
    return f'<div id="{block_id}">' + markdown.markdown(text_block['content'], extensions=['markdown.extensions.tables']) + '</div>'

def assemble_html_from_blocks(block_metadata, block_html_map):
    # Simple concatenation in block order
    html_blocks = [block_html_map[meta['block_id']] for meta in block_metadata]
    # Add a basic wrapper for PDF rendering
    html = """
    <html><head><meta charset='utf-8'><title>Campaign Performance Report</title></head>
    <body style='font-family:Inter,sans-serif;max-width:900px;margin:0 auto;'>
    """ + "\n".join(html_blocks) + "\n</body></html>"
    return html

def call_llm_to_generate_html(block_metadata_path, block_html_map_path, openai_api_key, model="gpt-4o"):
    with open(block_metadata_path, "r", encoding="utf-8") as f:
        block_metadata = json.load(f)
    with open(block_html_map_path, "r", encoding="utf-8") as f:
        block_html_map = json.load(f)
    prompt = (
        "You are an expert report designer. "
        "Given the following report blocks (with their types, titles, and HTML content), "
        "assemble a single, beautiful, professional HTML report suitable for PDF export. "
        "Use modern styling, clear sectioning, and ensure tables are visually appealing. "
        "Add a title and logical flow. Do not omit any content. "
        "You may add a <style> block for CSS. "
        "Here are the blocks (in order):\n\n"
    )
    for meta in block_metadata:
        block_id = meta["block_id"]
        block_type = meta["type"]
        title = meta.get("title", "")
        prompt += f"\n---\nBlock ID: {block_id}\nType: {block_type}\nTitle: {title}\nHTML:\n{block_html_map[block_id]}\n"
    prompt += (
        "\n---\n"
        "Assemble these into a single HTML document. "
        "Wrap the result in <html><head>...</head><body>...</body></html>. "
        "Include a <style> block in the <head> for beautiful, modern, readable tables and typography. "
        "Do not add any explanations or comments outside the HTML."
    )
    openai.api_key = openai_api_key
    response = openai.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a professional report designer and HTML expert."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
        max_tokens=16384,
    )
    html = response.choices[0].message.content.strip()
    return html

def main():
    try:
        with open('final_report_blocks.json', 'r', encoding='utf-8') as f:
            report_blocks = json.load(f)
        block_map = {}
        block_metadata = []
        for i, block in enumerate(report_blocks):
            block_id = f'block_{i}_{uuid.uuid4().hex[:8]}'
            meta = {k: v for k, v in block.items() if k != 'content' and k != 'rows' and k != 'data'}
            meta['block_id'] = block_id
            meta['type'] = block['type']
            block_metadata.append(meta)
            if block['type'] == 'text':
                block_map[block_id] = render_text_html(block, block_id)
            elif block['type'] == 'table':
                block_map[block_id] = render_table_html(block, block_id)
            elif block['type'] == 'chart':
                block_map[block_id] = render_chart_base64(block, block_id)
        with open('block_metadata.json', 'w', encoding='utf-8') as f:
            json.dump(block_metadata, f, ensure_ascii=False, indent=2)
        with open('block_html_map.json', 'w', encoding='utf-8') as f:
            json.dump(block_map, f, ensure_ascii=False, indent=2)
        print("Block metadata and HTML map saved. Ready for LLM HTML assembly.")
        # LLM HTML assembly step
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            try:
                openai_api_key = input("Enter your OpenAI API key: ")
            except EOFError:
                openai_api_key = None
        if isinstance(openai_api_key, str):
            openai_api_key = openai_api_key.strip()
        if not openai_api_key:
            print("No OpenAI API key provided. Exiting.")
            return
        try:
            final_html = call_llm_to_generate_html('block_metadata.json', 'block_html_map.json', openai_api_key)
            HTML(string=final_html).write_pdf('report.pdf')
            print("Final PDF report written to report.pdf")
        except Exception as llm_err:
            print(f"An error occurred during LLM HTML generation: {llm_err}")
    except FileNotFoundError:
        print("Error: final_report_blocks.json not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == '__main__':
    main() 