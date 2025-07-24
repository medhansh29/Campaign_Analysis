import json
import os
from datetime import datetime
from weasyprint import HTML

def render_table_rows(rows):
    if not rows or not isinstance(rows, list) or not rows[0]:
        return ''
    rows_html = ''
    for row in rows[1:]:
        row_html = ''.join([f'<td>{cell}</td>' for cell in row])
        rows_html += f'<tr>{row_html}</tr>'
    return rows_html

def render_highlights(highlights):
    if not highlights or not isinstance(highlights, list):
        return ''
    return ''.join(f'<div class="bullet">{item}</div>' for item in highlights)

def render_list_section(value):
    if isinstance(value, list):
        return ''.join(f'<div class="bullet">{item}</div>' for item in value)
    elif isinstance(value, str):
        items = [line.strip('-• ').strip() for line in value.split('\n') if line.strip()]
        return ''.join(f'<div class="bullet">{item}</div>' for item in items if item)
    return ''

def main():
    with open('llm_output.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    with open('template.html', 'r', encoding='utf-8') as f:
        template = f.read()

    placeholders = [
        'report_date',
        'executive_summary',
        'time_frame',
        'key_highlights_boxes',
        'campaign_scorecard_quant_table',
        'campaign_scorecard_qual_table',
        'journey_scorecard_quant_table',
        'journey_scorecard_qual_table',
        'deep_dive_personalization',
        'deep_dive_segmentation_depth',
        'deep_dive_experimentation',
        'deep_dive_campaign_diversity',
        'deep_dive_audience_reach_rotation',
        'deep_dive_creative_variation',
        'deep_dive_performance_metrics',
        'missed_opportunities',
        'recommendations',
        'campaign_agent_access',
        'campaigns_grade_breakdown_table',
        'journeys_grade_breakdown_table',
        'grade_scale_table',
        'grade_weights_table',
        'campaign_table_rows',
        'journey_table_rows',
    ]

    # Deep dive keys for new structure
    deep_dive_keys = [
        'deep_dive_personalization',
        'deep_dive_segmentation_depth',
        'deep_dive_experimentation',
        'deep_dive_campaign_diversity',
        'deep_dive_audience_reach_rotation',
        'deep_dive_creative_variation',
        'deep_dive_performance_metrics',
    ]

    # Fill in report_date if not present
    report_date = data.get('report_date')
    if not report_date:
        report_date = datetime.now().strftime('%d %b %Y')
    template = template.replace('{{report_date}}', report_date)

    # Fill in each placeholder
    for key in placeholders:
        if key == 'report_date':
            continue  # already handled
        value = data.get(key, '')
        if key in deep_dive_keys:
            focus = value.get('focus', '') if isinstance(value, dict) else ''
            grade = value.get('grade', '') if isinstance(value, dict) else ''
            details = value.get('details', []) if isinstance(value, dict) else value
            # Compose details as bullet divs, including focus and grade
            details_html = ''.join([
                f'<div class="bullet"><strong>Focus:</strong> {focus}</div>' if focus else '',
                f'<div class="bullet"><strong>Grade:</strong> {grade}</div>' if grade else '',
                render_list_section(details)
            ])
            template = template.replace(f'{{{{{key}_details}}}}', details_html)
        elif key.endswith('_table') or key.endswith('_table_rows'):
            html = render_table_rows(value) if value else ''
            template = template.replace(f'{{{{{key}}}}}', html)
        elif key.endswith('_boxes'):
            html = render_highlights(value) if value else ''
            template = template.replace(f'{{{{{key}}}}}', html)
        elif key in ['missed_opportunities', 'recommendations']:
            html = render_list_section(value) if value else ''
            template = template.replace(f'{{{{{key}}}}}', html)
        else:
            template = template.replace(f'{{{{{key}}}}}', value if isinstance(value, str) else '')

    with open('report.html', 'w', encoding='utf-8') as f:
        f.write(template)
    print('HTML report written to report.html')

    HTML(string=template).write_pdf('report.pdf')
    print('PDF report written to report.pdf')

if __name__ == '__main__':
    main() 