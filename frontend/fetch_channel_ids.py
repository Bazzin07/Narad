import urllib.request
import re

video_ids = {
    "NDTV": "CkgJ_PWLcPM",
    "TIMES_NOW": "-uLJfqSsX6M",
    "INDIA_TODAY": "kZLaSDu4_Og",
    "REPUBLIC": "8ZVRCUccRLw",
    "ABP": "uu1hjwO1D7A",
    "NEWS18": "TvAV58jMUHo",
    "WION": "hOO35m5eGeg",
    "DD_NEWS": "Et1rjUJFqrs"
}

for name, vid in video_ids.items():
    try:
        url = f"https://www.youtube.com/watch?v={vid}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        html = urllib.request.urlopen(req).read().decode('utf-8')
        match = re.search(r'"channelId":"(UC[^"]+)"', html)
        if match:
            print(f"{name}: {match.group(1)}")
        else:
            print(f"{name}: Channel ID not found")
    except Exception as e:
        print(f"{name}: Error - {e}")
