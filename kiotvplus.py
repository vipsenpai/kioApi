import requests
import json
import re
import concurrent.futures
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Setup a global session with automatic retries for network drops
session = requests.Session()
retries = Retry(total=3, backoff_factor=1, status_forcelist=[ 429, 500, 502, 503, 504 ])
session.mount('https://', HTTPAdapter(max_retries=retries, pool_connections=20, pool_maxsize=20))

def fetch_channel_data(channel):
    """Fetches cookie data, cleans dirty JSON, and formats the output."""
    channel_id = channel.get("channel_id", "")
    if not channel_id:
        return None

    cookie_url = "https://eliteapiyash.streamxlive.workers.dev"
    params = {'id': channel_id}
    headers = {
        'User-Agent': "okhttp/4.12.0",
        'Accept-Encoding': "gzip"
    }
    
    cookie = ""
    expires_in = ""
    
    try:
        response = session.get(cookie_url, params=params, headers=headers, timeout=15)
        
        if response.status_code == 200:
            # The API returns dirty JSON (extra text at the bottom). 
            # We must slice out only the part between [ and ]
            raw_text = response.text
            start_idx = raw_text.find('[')
            end_idx = raw_text.rfind(']') + 1
            
            if start_idx != -1 and end_idx != 0:
                clean_json_str = raw_text[start_idx:end_idx]
                try:
                    data = json.loads(clean_json_str)
                    
                    if isinstance(data, list) and len(data) > 0 and "cookie" in data[0]:
                        cookie = data[0]["cookie"]
                        
                        # Extract expiration timestamp
                        match = re.search(r"exp=(\d+)", cookie)
                        if match:
                            expires_in = match.group(1)
                except json.JSONDecodeError:
                    print(f"[!] ID {channel_id}: Could not parse cleaned JSON.")
            else:
                print(f"[!] ID {channel_id}: No valid JSON array found in response.")
        else:
            print(f"[!] ID {channel_id}: Failed to fetch cookie. HTTP {response.status_code}")
    except Exception as e:
        print(f"[!] ID {channel_id}: Request error - {type(e).__name__}")

    # Build license URL
    key_id = channel.get("keyId", "")
    key = channel.get("key", "")
    license_url = f"{key_id}:{key}" if key_id and key else ""

    return {
        "type": "dash",
        "id": channel_id,
        "name": channel.get("channel_name", ""),
        "group": channel.get("channel_genre", ""),
        "language": channel.get("language", ""),
        "logo": channel.get("channel_logo", ""),
        "user_agent": "Mozilla/5.0 (Linux; Android 10; Redmi Note 8 Pro Build/QP1A.190711.020; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/150.0.7871.181 Mobile Safari/537.36",
        "mpd_url": channel.get("channel_url", ""),
        "license_url": license_url,
        "headers": {
            "cookie": cookie
        },
        "expires_in": expires_in
    }

def main():
    print("Fetching main channel list from npoint...")
    
    main_url = "https://api.npoint.io/9db02feba76eb297fc65"
    main_params = {'v': "1786517989352"}
    main_headers = {
        'User-Agent': "Mozilla/5.0 (Linux; Android 10; Redmi Note 8 Pro Build/QP1A.190711.020; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/150.0.7871.181 Mobile Safari/537.36",
        'Accept-Encoding': "gzip, deflate, br, zstd",
        'sec-ch-ua-platform': '"Android"',
        'sec-ch-ua': '"Not;A=Brand";v="8", "Chromium";v="150", "Android WebView";v="150"',
        'sec-ch-ua-mobile': "?1",
        'origin': "null",
        'x-requested-with': "com.inplayer.plustv",
        'sec-fetch-site': "cross-site",
        'sec-fetch-mode': "cors",
        'sec-fetch-dest': "empty",
        'accept-language': "en-IN,en-US;q=0.9,en;q=0.8",
        'priority': "u=1, i"
    }
    
    try:
        response = session.get(main_url, params=main_params, headers=main_headers)
        channels = response.json()
    except Exception as e:
        print(f"Error fetching main API: {e}")
        return
        
    formatted_data = []
    print(f"Found {len(channels)} channels. Fetching cookies concurrently...")
    
    # Reduced max_workers to 5 to prevent "Network Unreachable" / Cloudflare Blocks
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        results = executor.map(fetch_channel_data, channels)
        
        for result in results:
            if result:
                formatted_data.append(result)

    # Save output
    output_filename = "Kio.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(formatted_data, f, indent=2, ensure_ascii=False)
        
    print(f"\nSuccess! Data mapped and saved to {output_filename}")

if __name__ == "__main__":
    main()
