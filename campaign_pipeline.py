import json
import pandas as pd
from datetime import datetime

# Helper to parse date from epoch or string

def parse_epoch(epoch):
    try:
        # If epoch is in seconds
        return datetime.fromtimestamp(int(epoch))
    except Exception:
        return None

def extract_campaign_metrics(campaign, debug=False):
    """Extracts key metrics from a single campaign dict."""
    try:
        if debug:
            print(f"Top-level keys: {list(campaign.keys())}")
            print(f"data keys: {list(campaign.get('data', {}).keys())}")
            print(f"response keys: {list(campaign.get('data', {}).get('response', {}).keys())}")
            print(f"target keys: {list(campaign.get('data', {}).get('response', {}).get('target', {}).keys())}")
            stats = campaign.get('data', {}).get('response', {}).get('target', {}).get('stats', None)
            print(f"stats type: {type(stats)}, stats value: {repr(stats)[:500]}")
        target = campaign['data']['response']['target']
        stats = target.get('stats', {})
        name = target.get('name', '')
        campaign_id = target.get('_id', '')
        if debug:
            print(f"Extracting: {campaign_id} | {name} | stats present: {bool(stats)}")
            print(f"Stats content: {json.dumps(stats, indent=2)[:500]}\n---")
        start_epoch = target.get('startEpoch')
        start_time = parse_epoch(start_epoch) if start_epoch else None
        region = None
        # Try to extract region if present
        try:
            region = target['q']['wc']['arr'][0]['arr'][0]['e'][0]['v'][0]
        except Exception:
            region = None
        device_count = target.get('q_user_device_counts', {}).get('devices')
        user_count = target.get('q_user_device_counts', {}).get('users')
        # For each channel in stats, extract metrics
        metrics = []
        for date_key, channel_stats in stats.items():
            for channel, stat in channel_stats.items():
                s = stat.get('wzrk_default', {})
                sent = s.get('sent', 0)
                impressions = s.get('impressions', 0)
                clicked = s.get('clicked', 0)
                errors = s.get('errors', {})
                amplified = s.get('amplifiedByPush', 0)
                # Only append if there is real data
                if sent or impressions or clicked:
                    metrics.append({
                        'campaign_id': campaign_id,
                        'campaign_name': name,
                        'start_time': start_time,
                        'region': region,
                        'device_count': device_count,
                        'user_count': user_count,
                        'date': date_key,
                        'channel': channel,
                        'sent': sent,
                        'impressions': impressions,
                        'clicked': clicked,
                        'amplified': amplified,
                        'errors': errors
                    })
        # If no stats, still return a row for diagnostics
        if not metrics:
            metrics.append({
                'campaign_id': campaign_id,
                'campaign_name': name,
                'start_time': start_time,
                'region': region,
                'device_count': device_count,
                'user_count': user_count,
                'date': None,
                'channel': None,
                'sent': None,
                'impressions': None,
                'clicked': None,
                'amplified': None,
                'errors': None
            })
        return metrics
    except Exception as e:
        print(f"Error extracting campaign: {e}")
        return []

def load_and_normalize_campaigns(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    all_metrics = []
    campaigns_with_stats = 0
    campaigns_without_stats = 0
    for i, campaign in enumerate(data):
        stats = campaign['data']['response']['target'].get('stats', {})
        if stats:
            campaigns_with_stats += 1
            debug = campaigns_with_stats <= 3  # Only print debug for first 3 with stats
            all_metrics.extend(extract_campaign_metrics(campaign, debug=debug))
        else:
            campaigns_without_stats += 1
    print(f"Campaigns with stats: {campaigns_with_stats}")
    print(f"Campaigns without stats: {campaigns_without_stats}")
    df = pd.DataFrame(all_metrics)
    print(f"Extracted {len(df)} rows with metrics.")
    return df

if __name__ == '__main__':
    df = load_and_normalize_campaigns('campaign_details.json')
    print(df.head()) 