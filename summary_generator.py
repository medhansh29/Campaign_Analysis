import pandas as pd
import numpy as np
from campaign_pipeline import load_and_normalize_campaigns
import datetime

def safe_get(d, keys, default=None):
    for k in keys:
        if isinstance(d, dict) and k in d:
            d = d[k]
        else:
            return default
    return d

def epoch_to_iso(epoch):
    try:
        return datetime.datetime.fromtimestamp(int(epoch)).strftime('%Y-%m-%d')
    except Exception:
        return None

def extract_region_from_target(target):
    def find_region_in_query(query):
        arrs = safe_get(query, ['wc', 'arr'], [])
        if arrs and isinstance(arrs, list):
            for arr_item in arrs:
                subarrs = arr_item.get('arr', [])
                for subarr in subarrs:
                    e_list = subarr.get('e', [])
                    for e in e_list:
                        if e.get('k') == 7:
                            v = e.get('v', [])
                            if v:
                                # Return all regions as comma-separated string
                                return ', '.join(str(region) for region in v if region)
        return None

    # Try 'q', then 'qm', then any other likely query fields
    for key in ['q', 'qm']:
        query = target.get(key, {})
        region = find_region_in_query(query)
        if region:
            return region
    return 'N/A'

def prepare_summary_data(df):
    # Add computed columns
    df['CTR'] = np.where(df['impressions'] > 0, df['clicked'] / df['impressions'] * 100, 0)
    df['Error Rate'] = np.where(df['sent'] > 0, df['errors'].apply(lambda e: sum(e.values()) if isinstance(e, dict) else 0) / df['sent'] * 100, 0)

    # Aggregate metrics
    overall = {
        'total_campaigns': int(df['campaign_id'].nunique()),
        'total_sent': int(df['sent'].sum()),
        'total_impressions': int(df['impressions'].sum()),
        'total_clicked': int(df['clicked'].sum()),
        'time_frame': {
            'start': df['start_time'].min().strftime('%d %b %Y'),
            'end': df['start_time'].max().strftime('%d %b %Y')
        }
    }

    # Channel mapping
    channel_map = {1: 'Android', 2: 'iPhone'}

    # Load the original JSON to get all metadata fields
    import json
    with open('campaign_details.json', 'r', encoding='utf-8') as f:
        raw_campaigns = json.load(f)
    campaign_meta = {}
    for c in raw_campaigns:
        target = safe_get(c, ['data', 'response', 'target'], {})
        campaign_id = target.get('_id') or c.get('campaign_id')
        # Metadata fields
        region = extract_region_from_target(target)
        campaign_meta[campaign_id] = {
            'campaign_id': campaign_id,
            'campaign_name': target.get('name'),
            'date_sent': epoch_to_iso(target.get('startEpoch')),
            'region': region,
            'segment_id': safe_get(target, ['qm', 'segmentId']),
            'segment_name': safe_get(target, ['qm', 'segmentName']),
            'language': None,  # Not present
            'audience_size': safe_get(target, ['q_user_device_counts', 'users']),
            'delivery_channel': target.get('type'),
            'delivery_time': target.get('startTime'),
            'control_group_used': None,
            'ab_test_variants': None,
            'campaign_theme': None,
            'product_skus_included': None,
            'time_to_configure': None,
            'targeting_strategy': None,
            'personalization_type': None,
        }
        # Message attributes (per channel)
        content = target.get('content', {})
        for ch in ['1', '2']:
            ch_content = content.get(ch, {})
            msg = safe_get(ch_content, ['msg', 'wzrk_default'], {})
            kv = ch_content.get('kv', {})
            campaign_meta[campaign_id][f'headline_{ch}'] = msg.get('title')
            campaign_meta[campaign_id][f'body_text_{ch}'] = msg.get('text')
            campaign_meta[campaign_id][f'creative_type_{ch}'] = 'image' if kv.get('wzrk_bp') else 'text-only'
            campaign_meta[campaign_id][f'thumbnail_url_{ch}'] = kv.get('wzrk_bp')
            campaign_meta[campaign_id][f'cta_text_{ch}'] = kv.get('wzrk_dl')

    # Group by campaign_id and campaign_name, then collect channel metrics
    campaigns = []
    for (cid, cname), group in df.groupby(['campaign_id', 'campaign_name']):
        meta = campaign_meta.get(int(cid), {})
        channels = []
        for _, row in group.iterrows():
            channel_num = int(row['channel']) if 'channel' in row and not pd.isna(row['channel']) else None
            platform = channel_map.get(channel_num, f"Channel {channel_num}") if channel_num is not None else None
            errors_dict = row['errors'] if isinstance(row['errors'], dict) else {}
            errors_serializable = {str(k): int(v) for k, v in errors_dict.items()}
            ch_str = str(channel_num) if channel_num is not None else None
            channels.append({
                'channel': channel_num,
                'platform': platform,
                'sent': int(row['sent']) if not pd.isna(row['sent']) else 0,
                'impressions': int(row['impressions']) if not pd.isna(row['impressions']) else 0,
                'clicked': int(row['clicked']) if not pd.isna(row['clicked']) else 0,
                'CTR': float(row['CTR']) if not pd.isna(row['CTR']) else 0.0,
                'Error Rate': float(row['Error Rate']) if not pd.isna(row['Error Rate']) else 0.0,
                'errors': errors_serializable,
                'headline': meta.get(f'headline_{ch_str}'),
                'body_text': meta.get(f'body_text_{ch_str}'),
                'creative_type': meta.get(f'creative_type_{ch_str}'),
                'thumbnail_url': meta.get(f'thumbnail_url_{ch_str}'),
                'cta_text': meta.get(f'cta_text_{ch_str}')
            })
        # Merge meta and channel metrics
        campaign_entry = {**meta, 'channels': channels}
        campaigns.append(campaign_entry)

    # CTR trend (by campaign)
    ctr_by_campaign = [
        {'campaign_name': row['campaign_name'], 'CTR': float(row['CTR'])}
        for _, row in df[['campaign_name', 'CTR']].iterrows()
    ]

    # Error breakdown (aggregate)
    error_types = {}
    for e in df['errors']:
        if isinstance(e, dict):
            for k, v in e.items():
                error_types[str(k)] = error_types.get(str(k), 0) + int(v)
    error_breakdown = [{'error_type': k, 'count': v} for k, v in error_types.items()]

    summary_data = {
        'overall': overall,
        'campaigns': campaigns,
        'ctr_by_campaign': ctr_by_campaign,
        'error_breakdown': error_breakdown
    }

    # --- Journey summary logic ---
    import os
    journey_file = 'journey_details.json'
    journeys = []
    total_journeys = 0
    if os.path.exists(journey_file):
        with open(journey_file, 'r', encoding='utf-8') as jf:
            journey_data = json.load(jf)
        # Handle both dict and list top-level structures
        if isinstance(journey_data, dict):
            roots = journey_data.get('root', [])
        elif isinstance(journey_data, list):
            roots = journey_data
        else:
            roots = []
        journeys = []
        for journey in roots:
            # Handle both dict and list journey structures
            journey_data_dict = journey.get('data', journey) if isinstance(journey, dict) else journey
            root_list = journey_data_dict.get('root', []) if isinstance(journey_data_dict, dict) else []
            cg_stats = journey_data_dict.get('cg_stats', {}) if isinstance(journey_data_dict, dict) else {}
            exit_stats = journey_data_dict.get('exit_stats', {}) if isinstance(journey_data_dict, dict) else {}
            if root_list:
                path = root_list[0].get('path', {})
            else:
                path = {}
            journey_summary = {
                "journey_name": cg_stats.get("name"),
                "status": cg_stats.get("status"),
                "start_time": cg_stats.get("startTime"),
                "qualified_users": path.get("segment_action", {}).get("stats", {}).get("qualified", 0),
                "not_qualified": path.get("segment_action", {}).get("stats", {}).get("not_qualified", 0),
                "message_channel": "WhatsApp" if "message_whatsapp" in path else None,
                "message_sent": path.get("message_whatsapp", {}).get("stats", {}).get("sent", 0),
                "message_delivered": path.get("message_whatsapp", {}).get("stats", {}).get("delivered", 0),
                "message_viewed": path.get("message_whatsapp", {}).get("stats", {}).get("viewed", 0),
                "message_clicked": path.get("message_whatsapp", {}).get("stats", {}).get("clicked", 0),
                "goal_completions": 0,
                "control_group_size": path.get("segment_action", {}).get("stats", {}).get("control_group", 0),
                "conversion_count": cg_stats.get("conversionCount", 0),
                "conversion_rate": f"{cg_stats.get('conversion', '0')}%"
            }
            # Goal completions: try to extract from exit_stats
            try:
                goal_cnt = 0
                if "goal" in exit_stats:
                    for g in exit_stats["goal"].values():
                        for step in g.values():
                            goal_cnt += step.get("cnt", 0)
                journey_summary["goal_completions"] = goal_cnt
            except Exception:
                pass
            journeys.append(journey_summary)
        total_journeys = len(journeys)
    summary_data['journeys'] = journeys
    summary_data['overall']['total_journeys'] = total_journeys
    # --- End journey summary logic ---
    return summary_data

if __name__ == '__main__':
    df = load_and_normalize_campaigns('campaign_details.json')
    summary_data = prepare_summary_data(df)
    import json
    with open('summary_data.json', 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, ensure_ascii=False, indent=2)
    print("Summary data prepared and saved to summary_data.json") 