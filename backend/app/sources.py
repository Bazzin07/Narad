"""
Narad — Comprehensive Indian & Global News Source Registry.

Every publicly available RSS feed, YouTube Atom feed, Reddit feed,
and API-compatible source relevant to Indian news coverage.

Sources are grouped by:
  1. Language
  2. Medium (news site, YouTube, Reddit, govt, agency)

Each source dict has:
  - name:               Display name
  - base_url:           RSS / Atom / API URL
  - source_type:        "news" | "social" | "govt" | "agency" | "wire"
  - language:           ISO 639-1 code
  - credibility_weight: 0.0–1.0
  - region:             "national" | "regional" | "international"
  - category:           Primary beat (general, politics, business, tech, sports, etc.)

To add a new source, just append to the appropriate section below.
The ingestion service imports ALL_SOURCES from this file.
"""

# ═══════════════════════════════════════════════════════════════════════════════
#  ENGLISH — National / International
# ═══════════════════════════════════════════════════════════════════════════════

ENGLISH_NEWS = [
    # ── Tier 1: Major Indian English Dailies ──────────────────────────────────
    {
        "name": "The Hindu",
        "base_url": "https://www.thehindu.com/news/national/feeder/default.rss",
        "source_type": "news",
        "language": "en",
        "credibility_weight": 1.0,
        "region": "national",
        "category": "general",
    },
    {
        "name": "The Hindu - International",
        "base_url": "https://www.thehindu.com/news/international/feeder/default.rss",
        "source_type": "news",
        "language": "en",
        "credibility_weight": 1.0,
        "region": "international",
        "category": "general",
    },
    {
        "name": "The Hindu - Business",
        "base_url": "https://www.thehindu.com/business/feeder/default.rss",
        "source_type": "news",
        "language": "en",
        "credibility_weight": 1.0,
        "region": "national",
        "category": "business",
    },
    {
        "name": "Times of India",
        "base_url": "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
        "source_type": "news",
        "language": "en",
        "credibility_weight": 0.85,
        "region": "national",
        "category": "general",
    },
    {
        "name": "TOI - World",
        "base_url": "https://timesofindia.indiatimes.com/rssfeeds/296589292.cms",
        "source_type": "news",
        "language": "en",
        "credibility_weight": 0.85,
        "region": "international",
        "category": "general",
    },
    {
        "name": "TOI - Business",
        "base_url": "https://timesofindia.indiatimes.com/rssfeeds/1898055.cms",
        "source_type": "news",
        "language": "en",
        "credibility_weight": 0.85,
        "region": "national",
        "category": "business",
    },
    {
        "name": "Hindustan Times",
        "base_url": "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml",
        "source_type": "news",
        "language": "en",
        "credibility_weight": 0.9,
        "region": "national",
        "category": "general",
    },
    {
        "name": "HT - World",
        "base_url": "https://www.hindustantimes.com/feeds/rss/world-news/rssfeed.xml",
        "source_type": "news",
        "language": "en",
        "credibility_weight": 0.9,
        "region": "international",
        "category": "general",
    },
    {
        "name": "HT - Business",
        "base_url": "https://www.hindustantimes.com/feeds/rss/business/rssfeed.xml",
        "source_type": "news",
        "language": "en",
        "credibility_weight": 0.9,
        "region": "national",
        "category": "business",
    },
    {
        "name": "Indian Express",
        "base_url": "https://indianexpress.com/section/india/feed/",
        "source_type": "news",
        "language": "en",
        "credibility_weight": 0.95,
        "region": "national",
        "category": "general",
    },
    {
        "name": "Indian Express - World",
        "base_url": "https://indianexpress.com/section/world/feed/",
        "source_type": "news",
        "language": "en",
        "credibility_weight": 0.95,
        "region": "international",
        "category": "general",
    },
    {
        "name": "Indian Express - Business",
        "base_url": "https://indianexpress.com/section/business/feed/",
        "source_type": "news",
        "language": "en",
        "credibility_weight": 0.95,
        "region": "national",
        "category": "business",
    },
    {
        "name": "NDTV",
        "base_url": "https://feeds.feedburner.com/ndtvnews-top-stories",
        "source_type": "news",
        "language": "en",
        "credibility_weight": 0.9,
        "region": "national",
        "category": "general",
    },
    {
        "name": "NDTV - World",
        "base_url": "https://feeds.feedburner.com/ndtvnews-world-news",
        "source_type": "news",
        "language": "en",
        "credibility_weight": 0.9,
        "region": "international",
        "category": "general",
    },
    {
        "name": "NDTV - Business",
        "base_url": "https://feeds.feedburner.com/ndtvprofit-latest",
        "source_type": "news",
        "language": "en",
        "credibility_weight": 0.9,
        "region": "national",
        "category": "business",
    },
    {
        "name": "Deccan Herald",
        "base_url": "https://www.deccanherald.com/rss/india.rss",
        "source_type": "news",
        "language": "en",
        "credibility_weight": 0.85,
        "region": "national",
        "category": "general",
    },
    {
        "name": "The Telegraph India",
        "base_url": "https://www.telegraphindia.com/rss/all.xml",
        "source_type": "news",
        "language": "en",
        "credibility_weight": 0.85,
        "region": "national",
        "category": "general",
    },
    {
        "name": "The Wire",
        "base_url": "https://thewire.in/feed",
        "source_type": "news",
        "language": "en",
        "credibility_weight": 0.8,
        "region": "national",
        "category": "general",
    },
    {
        "name": "Scroll.in",
        "base_url": "https://scroll.in/feed",
        "source_type": "news",
        "language": "en",
        "credibility_weight": 0.8,
        "region": "national",
        "category": "general",
    },
    {
        "name": "The Print",
        "base_url": "https://theprint.in/feed/",
        "source_type": "news",
        "language": "en",
        "credibility_weight": 0.8,
        "region": "national",
        "category": "general",
    },
    {
        "name": "Firstpost",
        "base_url": "https://www.firstpost.com/rss/india.xml",
        "source_type": "news",
        "language": "en",
        "credibility_weight": 0.8,
        "region": "national",
        "category": "general",
    },
    {
        "name": "Mint (Livemint)",
        "base_url": "https://www.livemint.com/rss/news",
        "source_type": "news",
        "language": "en",
        "credibility_weight": 0.9,
        "region": "national",
        "category": "business",
    },
    {
        "name": "Economic Times",
        "base_url": "https://economictimes.indiatimes.com/rssfeedstopstories.cms",
        "source_type": "news",
        "language": "en",
        "credibility_weight": 0.9,
        "region": "national",
        "category": "business",
    },
    {
        "name": "Business Standard",
        "base_url": "https://www.business-standard.com/rss/home_page_top_stories.rss",
        "source_type": "news",
        "language": "en",
        "credibility_weight": 0.9,
        "region": "national",
        "category": "business",
    },
    {
        "name": "MoneyControl",
        "base_url": "https://www.moneycontrol.com/rss/latestnews.xml",
        "source_type": "news",
        "language": "en",
        "credibility_weight": 0.85,
        "region": "national",
        "category": "business",
    },

    # ── Tier 2: English News Channels (TV) ────────────────────────────────────
    {
        "name": "Republic World",
        "base_url": "https://www.republicworld.com/rss/india-news.xml",
        "source_type": "news",
        "language": "en",
        "credibility_weight": 0.7,
        "region": "national",
        "category": "general",
    },
    {
        "name": "News18",
        "base_url": "https://www.news18.com/rss/india.xml",
        "source_type": "news",
        "language": "en",
        "credibility_weight": 0.8,
        "region": "national",
        "category": "general",
    },
    {
        "name": "Zee News English",
        "base_url": "https://zeenews.india.com/rss/india-national-news.xml",
        "source_type": "news",
        "language": "en",
        "credibility_weight": 0.75,
        "region": "national",
        "category": "general",
    },
    {
        "name": "India Today",
        "base_url": "https://www.indiatoday.in/rss/home",
        "source_type": "news",
        "language": "en",
        "credibility_weight": 0.85,
        "region": "national",
        "category": "general",
    },
    {
        "name": "Outlook India",
        "base_url": "https://www.outlookindia.com/rss",
        "source_type": "news",
        "language": "en",
        "credibility_weight": 0.8,
        "region": "national",
        "category": "general",
    },

    # ── Tech / Startup ────────────────────────────────────────────────────────
    {
        "name": "YourStory",
        "base_url": "https://yourstory.com/rss",
        "source_type": "news",
        "language": "en",
        "credibility_weight": 0.75,
        "region": "national",
        "category": "technology",
    },
    {
        "name": "Inc42",
        "base_url": "https://inc42.com/feed/",
        "source_type": "news",
        "language": "en",
        "credibility_weight": 0.75,
        "region": "national",
        "category": "technology",
    },
    {
        "name": "Entrackr",
        "base_url": "https://entrackr.com/feed/",
        "source_type": "news",
        "language": "en",
        "credibility_weight": 0.7,
        "region": "national",
        "category": "technology",
    },

    # ── Science / Defence ─────────────────────────────────────────────────────
    {
        "name": "The Quint",
        "base_url": "https://www.thequint.com/quintlab/rss-feeds/the-quint-rss.xml",
        "source_type": "news",
        "language": "en",
        "credibility_weight": 0.8,
        "region": "national",
        "category": "general",
    },
    {
        "name": "DNA India",
        "base_url": "https://www.dnaindia.com/feeds/india.xml",
        "source_type": "news",
        "language": "en",
        "credibility_weight": 0.75,
        "region": "national",
        "category": "general",
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
#  ENGLISH — International (for cross-referencing Indian stories globally)
# ═══════════════════════════════════════════════════════════════════════════════

ENGLISH_INTERNATIONAL = [
    {
        "name": "NYT World",
        "base_url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "source_type": "news",
        "language": "en",
        "credibility_weight": 1.0,
        "region": "international",
        "category": "general",
    },
    {
        "name": "BBC World",
        "base_url": "https://feeds.bbci.co.uk/news/world/rss.xml",
        "source_type": "news",
        "language": "en",
        "credibility_weight": 1.0,
        "region": "international",
        "category": "general",
    },
    {
        "name": "BBC South Asia",
        "base_url": "https://feeds.bbci.co.uk/news/world/south_asia/rss.xml",
        "source_type": "news",
        "language": "en",
        "credibility_weight": 1.0,
        "region": "international",
        "category": "general",
    },
    {
        "name": "CNN World",
        "base_url": "https://rss.cnn.com/rss/edition_world.rss",
        "source_type": "news",
        "language": "en",
        "credibility_weight": 0.9,
        "region": "international",
        "category": "general",
    },
    {
        "name": "Reuters World",
        "base_url": "https://www.reutersagency.com/feed/?taxonomy=best-sectors&post_type=best",
        "source_type": "wire",
        "language": "en",
        "credibility_weight": 1.0,
        "region": "international",
        "category": "general",
    },
    {
        "name": "Al Jazeera",
        "base_url": "https://www.aljazeera.com/xml/rss/all.xml",
        "source_type": "news",
        "language": "en",
        "credibility_weight": 0.85,
        "region": "international",
        "category": "general",
    },
    {
        "name": "The Guardian - World",
        "base_url": "https://www.theguardian.com/world/rss",
        "source_type": "news",
        "language": "en",
        "credibility_weight": 0.95,
        "region": "international",
        "category": "general",
    },
    {
        "name": "AP News",
        "base_url": "https://rsshub.app/apnews/topics/apf-topnews",
        "source_type": "wire",
        "language": "en",
        "credibility_weight": 1.0,
        "region": "international",
        "category": "general",
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
#  HINDI — हिन्दी
# ═══════════════════════════════════════════════════════════════════════════════

HINDI_NEWS = [
    {
        "name": "BBC Hindi",
        "base_url": "https://feeds.bbci.co.uk/hindi/rss.xml",
        "source_type": "news",
        "language": "hi",
        "credibility_weight": 1.0,
        "region": "national",
        "category": "general",
    },
    {
        "name": "NDTV Hindi",
        "base_url": "https://feeds.feedburner.com/ndtvkhabar",
        "source_type": "news",
        "language": "hi",
        "credibility_weight": 0.9,
        "region": "national",
        "category": "general",
    },
    {
        "name": "Dainik Jagran",
        "base_url": "https://www.jagran.com/rss/news-national.xml",
        "source_type": "news",
        "language": "hi",
        "credibility_weight": 0.85,
        "region": "national",
        "category": "general",
    },
    {
        "name": "Amar Ujala",
        "base_url": "https://www.amarujala.com/rss/breaking-news.xml",
        "source_type": "news",
        "language": "hi",
        "credibility_weight": 0.85,
        "region": "national",
        "category": "general",
    },
    {
        "name": "Dainik Bhaskar",
        "base_url": "https://www.bhaskar.com/rss-feed/1061",
        "source_type": "news",
        "language": "hi",
        "credibility_weight": 0.85,
        "region": "national",
        "category": "general",
    },
    {
        "name": "Navbharat Times",
        "base_url": "https://navbharattimes.indiatimes.com/rssfeedsdefault.cms",
        "source_type": "news",
        "language": "hi",
        "credibility_weight": 0.85,
        "region": "national",
        "category": "general",
    },
    {
        "name": "Zee News Hindi",
        "base_url": "https://zeenews.india.com/hindi/rss/india-news.xml",
        "source_type": "news",
        "language": "hi",
        "credibility_weight": 0.75,
        "region": "national",
        "category": "general",
    },
    {
        "name": "ABP News Hindi",
        "base_url": "https://www.abplive.com/rss",
        "source_type": "news",
        "language": "hi",
        "credibility_weight": 0.8,
        "region": "national",
        "category": "general",
    },
    {
        "name": "News18 Hindi",
        "base_url": "https://hindi.news18.com/rss/khabar/nation.xml",
        "source_type": "news",
        "language": "hi",
        "credibility_weight": 0.8,
        "region": "national",
        "category": "general",
    },
    {
        "name": "Jansatta",
        "base_url": "https://www.jansatta.com/feed/",
        "source_type": "news",
        "language": "hi",
        "credibility_weight": 0.85,
        "region": "national",
        "category": "general",
    },
    {
        "name": "Hindustan (Hindi Daily)",
        "base_url": "https://www.livehindustan.com/rss/india-news",
        "source_type": "news",
        "language": "hi",
        "credibility_weight": 0.85,
        "region": "national",
        "category": "general",
    },
    {
        "name": "Prabhat Khabar",
        "base_url": "https://www.prabhatkhabar.com/rss",
        "source_type": "news",
        "language": "hi",
        "credibility_weight": 0.8,
        "region": "national",
        "category": "general",
    },
    {
        "name": "Patrika",
        "base_url": "https://www.patrika.com/rss/national-news.xml",
        "source_type": "news",
        "language": "hi",
        "credibility_weight": 0.8,
        "region": "national",
        "category": "general",
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
#  TAMIL — தமிழ்
# ═══════════════════════════════════════════════════════════════════════════════

TAMIL_NEWS = [
    {
        "name": "The Hindu Tamil",
        "base_url": "https://www.thehindu.com/tamil/rss/tamilnadu-rss.xml",
        "source_type": "news",
        "language": "ta",
        "credibility_weight": 0.9,
        "region": "regional",
        "category": "general",
    },
    {
        "name": "Dinamani",
        "base_url": "https://www.dinamani.com/feeds/feed.xml",
        "source_type": "news",
        "language": "ta",
        "credibility_weight": 0.85,
        "region": "regional",
        "category": "general",
    },
    {
        "name": "Dinamalar",
        "base_url": "https://www.dinamalar.com/rss_feed.asp",
        "source_type": "news",
        "language": "ta",
        "credibility_weight": 0.85,
        "region": "regional",
        "category": "general",
    },
    {
        "name": "Tamil Murasu",
        "base_url": "https://www.tamilmurasu.com.sg/rss/breaking-news.xml",
        "source_type": "news",
        "language": "ta",
        "credibility_weight": 0.8,
        "region": "regional",
        "category": "general",
    },
    {
        "name": "Vikatan",
        "base_url": "https://www.vikatan.com/rss/news.xml",
        "source_type": "news",
        "language": "ta",
        "credibility_weight": 0.85,
        "region": "regional",
        "category": "general",
    },
    {
        "name": "BBC Tamil",
        "base_url": "https://feeds.bbci.co.uk/tamil/rss.xml",
        "source_type": "news",
        "language": "ta",
        "credibility_weight": 1.0,
        "region": "regional",
        "category": "general",
    },
    {
        "name": "Puthiya Thalaimurai",
        "base_url": "https://www.puthiyathalaimurai.com/rss/news.xml",
        "source_type": "news",
        "language": "ta",
        "credibility_weight": 0.8,
        "region": "regional",
        "category": "general",
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
#  TELUGU — తెలుగు
# ═══════════════════════════════════════════════════════════════════════════════

TELUGU_NEWS = [
    {
        "name": "Sakshi Telugu",
        "base_url": "https://www.sakshi.com/rss/telangana.xml",
        "source_type": "news",
        "language": "te",
        "credibility_weight": 0.85,
        "region": "regional",
        "category": "general",
    },
    {
        "name": "Eenadu",
        "base_url": "https://www.eenadu.net/rss/telangana-news-rss.xml",
        "source_type": "news",
        "language": "te",
        "credibility_weight": 0.85,
        "region": "regional",
        "category": "general",
    },
    {
        "name": "Andhra Jyothi",
        "base_url": "https://www.andhrajyothy.com/rss/telangana.xml",
        "source_type": "news",
        "language": "te",
        "credibility_weight": 0.8,
        "region": "regional",
        "category": "general",
    },
    {
        "name": "Namaste Telangana",
        "base_url": "https://ntnews.com/rss/telangana.xml",
        "source_type": "news",
        "language": "te",
        "credibility_weight": 0.75,
        "region": "regional",
        "category": "general",
    },
    {
        "name": "BBC Telugu",
        "base_url": "https://feeds.bbci.co.uk/telugu/rss.xml",
        "source_type": "news",
        "language": "te",
        "credibility_weight": 1.0,
        "region": "regional",
        "category": "general",
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
#  BENGALI — বাংলা
# ═══════════════════════════════════════════════════════════════════════════════

BENGALI_NEWS = [
    {
        "name": "ABP Ananda Bengali",
        "base_url": "https://bengali.abplive.com/rss/topnews.xml",
        "source_type": "news",
        "language": "bn",
        "credibility_weight": 0.85,
        "region": "regional",
        "category": "general",
    },
    {
        "name": "BBC Bengali",
        "base_url": "https://feeds.bbci.co.uk/bengali/rss.xml",
        "source_type": "news",
        "language": "bn",
        "credibility_weight": 1.0,
        "region": "regional",
        "category": "general",
    },
    {
        "name": "Anandabazar Patrika",
        "base_url": "https://www.anandabazar.com/rss/topnews.xml",
        "source_type": "news",
        "language": "bn",
        "credibility_weight": 0.9,
        "region": "regional",
        "category": "general",
    },
    {
        "name": "Ei Samay",
        "base_url": "https://eisamay.indiatimes.com/rssfeedsdefault.cms",
        "source_type": "news",
        "language": "bn",
        "credibility_weight": 0.85,
        "region": "regional",
        "category": "general",
    },
    {
        "name": "Sangbad Pratidin",
        "base_url": "https://www.sangbadpratidin.in/feed/",
        "source_type": "news",
        "language": "bn",
        "credibility_weight": 0.8,
        "region": "regional",
        "category": "general",
    },
    {
        "name": "Bartaman Patrika",
        "base_url": "https://bartamanpatrika.com/rss.php",
        "source_type": "news",
        "language": "bn",
        "credibility_weight": 0.8,
        "region": "regional",
        "category": "general",
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
#  MARATHI — मराठी
# ═══════════════════════════════════════════════════════════════════════════════

MARATHI_NEWS = [
    {
        "name": "Loksatta Marathi",
        "base_url": "https://www.loksatta.com/feed/",
        "source_type": "news",
        "language": "mr",
        "credibility_weight": 0.85,
        "region": "regional",
        "category": "general",
    },
    {
        "name": "ABP Majha Marathi",
        "base_url": "https://marathi.abplive.com/rss/topnews.xml",
        "source_type": "news",
        "language": "mr",
        "credibility_weight": 0.85,
        "region": "regional",
        "category": "general",
    },
    {
        "name": "Maharashtra Times",
        "base_url": "https://maharashtratimes.com/rssfeedsdefault.cms",
        "source_type": "news",
        "language": "mr",
        "credibility_weight": 0.85,
        "region": "regional",
        "category": "general",
    },
    {
        "name": "Sakal",
        "base_url": "https://www.esakal.com/rss.xml",
        "source_type": "news",
        "language": "mr",
        "credibility_weight": 0.85,
        "region": "regional",
        "category": "general",
    },
    {
        "name": "Pudhari",
        "base_url": "https://www.pudhari.news/rss/",
        "source_type": "news",
        "language": "mr",
        "credibility_weight": 0.8,
        "region": "regional",
        "category": "general",
    },
    {
        "name": "Saamana",
        "base_url": "https://www.saamana.com/feed/",
        "source_type": "news",
        "language": "mr",
        "credibility_weight": 0.7,
        "region": "regional",
        "category": "politics",
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
#  GUJARATI — ગુજરાતી
# ═══════════════════════════════════════════════════════════════════════════════

GUJARATI_NEWS = [
    {
        "name": "Divya Bhaskar Gujarati",
        "base_url": "https://www.divyabhaskar.co.in/rss/home.xml",
        "source_type": "news",
        "language": "gu",
        "credibility_weight": 0.85,
        "region": "regional",
        "category": "general",
    },
    {
        "name": "Gujarat Samachar",
        "base_url": "https://www.gujaratsamachar.com/rss/top-stories.xml",
        "source_type": "news",
        "language": "gu",
        "credibility_weight": 0.85,
        "region": "regional",
        "category": "general",
    },
    {
        "name": "Sandesh",
        "base_url": "https://www.sandesh.com/rss/top-stories.xml",
        "source_type": "news",
        "language": "gu",
        "credibility_weight": 0.85,
        "region": "regional",
        "category": "general",
    },
    {
        "name": "BBC Gujarati",
        "base_url": "https://feeds.bbci.co.uk/gujarati/rss.xml",
        "source_type": "news",
        "language": "gu",
        "credibility_weight": 1.0,
        "region": "regional",
        "category": "general",
    },
    {
        "name": "Akila News Gujarati",
        "base_url": "https://www.akilanews.com/feed",
        "source_type": "news",
        "language": "gu",
        "credibility_weight": 0.75,
        "region": "regional",
        "category": "general",
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
#  KANNADA — ಕನ್ನಡ
# ═══════════════════════════════════════════════════════════════════════════════

KANNADA_NEWS = [
    {
        "name": "Prajavani Kannada",
        "base_url": "https://www.prajavani.net/feeds/feed.xml",
        "source_type": "news",
        "language": "kn",
        "credibility_weight": 0.85,
        "region": "regional",
        "category": "general",
    },
    {
        "name": "Vijaya Karnataka",
        "base_url": "https://vijaykarnataka.com/rssfeedsdefault.cms",
        "source_type": "news",
        "language": "kn",
        "credibility_weight": 0.85,
        "region": "regional",
        "category": "general",
    },
    {
        "name": "Udayavani Kannada",
        "base_url": "https://www.udayavani.com/rss/top-stories",
        "source_type": "news",
        "language": "kn",
        "credibility_weight": 0.8,
        "region": "regional",
        "category": "general",
    },
    {
        "name": "Kannada Prabha",
        "base_url": "https://www.kannadaprabha.com/rss/top-stories.xml",
        "source_type": "news",
        "language": "kn",
        "credibility_weight": 0.8,
        "region": "regional",
        "category": "general",
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
#  MALAYALAM — മലയാളം
# ═══════════════════════════════════════════════════════════════════════════════

MALAYALAM_NEWS = [
    {
        "name": "Manorama Malayalam",
        "base_url": "https://www.manoramaonline.com/news.rss.xml",
        "source_type": "news",
        "language": "ml",
        "credibility_weight": 0.9,
        "region": "regional",
        "category": "general",
    },
    {
        "name": "Mathrubhumi",
        "base_url": "https://www.mathrubhumi.com/rss/news",
        "source_type": "news",
        "language": "ml",
        "credibility_weight": 0.9,
        "region": "regional",
        "category": "general",
    },
    {
        "name": "Asianet News Malayalam",
        "base_url": "https://www.asianetnews.com/rss/kerala-news",
        "source_type": "news",
        "language": "ml",
        "credibility_weight": 0.8,
        "region": "regional",
        "category": "general",
    },
    {
        "name": "Deshabhimani",
        "base_url": "https://www.deshabhimani.com/rss.xml",
        "source_type": "news",
        "language": "ml",
        "credibility_weight": 0.75,
        "region": "regional",
        "category": "general",
    },
    {
        "name": "Madhyamam Malayalam",
        "base_url": "https://www.madhyamam.com/rss/kerala",
        "source_type": "news",
        "language": "ml",
        "credibility_weight": 0.8,
        "region": "regional",
        "category": "general",
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
#  PUNJABI — ਪੰਜਾਬੀ
# ═══════════════════════════════════════════════════════════════════════════════

PUNJABI_NEWS = [
    {
        "name": "BBC Punjabi",
        "base_url": "https://feeds.bbci.co.uk/punjabi/rss.xml",
        "source_type": "news",
        "language": "pa",
        "credibility_weight": 1.0,
        "region": "regional",
        "category": "general",
    },
    {
        "name": "Ajit Punjabi Daily",
        "base_url": "https://www.ajitjalandhar.com/rss/top-stories.xml",
        "source_type": "news",
        "language": "pa",
        "credibility_weight": 0.8,
        "region": "regional",
        "category": "general",
    },
    {
        "name": "Jagbani Punjabi",
        "base_url": "https://www.jagbani.com/feed/",
        "source_type": "news",
        "language": "pa",
        "credibility_weight": 0.8,
        "region": "regional",
        "category": "general",
    },
    {
        "name": "Rozana Spokesman",
        "base_url": "https://www.rozanaspokesman.com/rss/top-stories.xml",
        "source_type": "news",
        "language": "pa",
        "credibility_weight": 0.75,
        "region": "regional",
        "category": "general",
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
#  URDU — اردو
# ═══════════════════════════════════════════════════════════════════════════════

URDU_NEWS = [
    {
        "name": "BBC Urdu",
        "base_url": "https://feeds.bbci.co.uk/urdu/rss.xml",
        "source_type": "news",
        "language": "ur",
        "credibility_weight": 1.0,
        "region": "national",
        "category": "general",
    },
    {
        "name": "Inquilab Urdu",
        "base_url": "https://www.inquilab.com/rss",
        "source_type": "news",
        "language": "ur",
        "credibility_weight": 0.8,
        "region": "national",
        "category": "general",
    },
    {
        "name": "Siasat Daily Urdu",
        "base_url": "https://www.siasat.com/feed/",
        "source_type": "news",
        "language": "ur",
        "credibility_weight": 0.75,
        "region": "regional",
        "category": "general",
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
#  ASSAMESE — অসমীয়া
# ═══════════════════════════════════════════════════════════════════════════════

ASSAMESE_NEWS = [
    {
        "name": "Pratidin Time Assamese",
        "base_url": "https://www.pratidintime.com/rss/top-stories.xml",
        "source_type": "news",
        "language": "as",
        "credibility_weight": 0.8,
        "region": "regional",
        "category": "general",
    },
    {
        "name": "News Live Assamese",
        "base_url": "https://www.newslivetv.com/feed/",
        "source_type": "news",
        "language": "as",
        "credibility_weight": 0.75,
        "region": "regional",
        "category": "general",
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
#  ODIA — ଓଡ଼ିଆ
# ═══════════════════════════════════════════════════════════════════════════════

ODIA_NEWS = [
    {
        "name": "Sambad Odia",
        "base_url": "https://www.sambad.in/feed/",
        "source_type": "news",
        "language": "or",
        "credibility_weight": 0.8,
        "region": "regional",
        "category": "general",
    },
    {
        "name": "Dharitri Odia",
        "base_url": "https://www.dharitri.com/rss/top-stories.xml",
        "source_type": "news",
        "language": "or",
        "credibility_weight": 0.8,
        "region": "regional",
        "category": "general",
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
#  YOUTUBE — Indian News Channels
# ═══════════════════════════════════════════════════════════════════════════════

YOUTUBE_SOURCES = [
    # English
    {
        "name": "NDTV (YouTube)",
        "base_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCHMm3_RMF4z03hQoMSQpPnQ",
        "source_type": "social",
        "language": "en",
        "credibility_weight": 0.7,
        "region": "national",
        "category": "general",
    },
    {
        "name": "WION (YouTube)",
        "base_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UC_gUM8rL-Lrg6O3adPW9K1g",
        "source_type": "social",
        "language": "en",
        "credibility_weight": 0.6,
        "region": "national",
        "category": "general",
    },
    {
        "name": "Republic World (YouTube)",
        "base_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCwqusr8YDwM-0gEU1aO_BvA",
        "source_type": "social",
        "language": "en",
        "credibility_weight": 0.55,
        "region": "national",
        "category": "general",
    },
    {
        "name": "India Today (YouTube)",
        "base_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCYPvAwZP8pZhSMW8qs7cVCw",
        "source_type": "social",
        "language": "en",
        "credibility_weight": 0.65,
        "region": "national",
        "category": "general",
    },
    {
        "name": "Times Now (YouTube)",
        "base_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCyojr4gWmlKq0TBdGMwaz0Q",
        "source_type": "social",
        "language": "en",
        "credibility_weight": 0.6,
        "region": "national",
        "category": "general",
    },
    {
        "name": "CNN-News18 (YouTube)",
        "base_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCef1-8eOpJgud7szVPlZQAQ",
        "source_type": "social",
        "language": "en",
        "credibility_weight": 0.6,
        "region": "national",
        "category": "general",
    },
    # Hindi YouTube
    {
        "name": "Aaj Tak (YouTube)",
        "base_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCt4t-jeY85JegMlZ-E5UXtA",
        "source_type": "social",
        "language": "hi",
        "credibility_weight": 0.6,
        "region": "national",
        "category": "general",
    },
    {
        "name": "ABP News (YouTube)",
        "base_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCRWFSbif-RFENbBrSiez1DA",
        "source_type": "social",
        "language": "hi",
        "credibility_weight": 0.6,
        "region": "national",
        "category": "general",
    },
    {
        "name": "Zee News (YouTube)",
        "base_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCIvaYmXn910QMdemBG3v1pQ",
        "source_type": "social",
        "language": "hi",
        "credibility_weight": 0.55,
        "region": "national",
        "category": "general",
    },
    {
        "name": "NDTV India Hindi (YouTube)",
        "base_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCBbpLKJLhIbDd_wX4ubU_Cw",
        "source_type": "social",
        "language": "hi",
        "credibility_weight": 0.65,
        "region": "national",
        "category": "general",
    },
    # Telugu YouTube
    {
        "name": "TV9 Telugu (YouTube)",
        "base_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UC-iMWM_mkSAnJYEXQ2mMHyQ",
        "source_type": "social",
        "language": "te",
        "credibility_weight": 0.65,
        "region": "regional",
        "category": "general",
    },
    {
        "name": "NTV Telugu (YouTube)",
        "base_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCumNjVOxPGawLFN7ZGPfrRg",
        "source_type": "social",
        "language": "te",
        "credibility_weight": 0.6,
        "region": "regional",
        "category": "general",
    },
    # Tamil YouTube
    {
        "name": "Sun News Tamil (YouTube)",
        "base_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCYlh4lH762HvHt6mmiecyWQ",
        "source_type": "social",
        "language": "ta",
        "credibility_weight": 0.6,
        "region": "regional",
        "category": "general",
    },
    {
        "name": "Thanthi TV Tamil (YouTube)",
        "base_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCqaTDaXSkMtwMA5DVuEraXw",
        "source_type": "social",
        "language": "ta",
        "credibility_weight": 0.6,
        "region": "regional",
        "category": "general",
    },
    # International (for cross-reference)
    {
        "name": "Al Jazeera (YouTube)",
        "base_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCNye-wNBqNL5ZzHSJj3l8Bg",
        "source_type": "social",
        "language": "en",
        "credibility_weight": 0.7,
        "region": "international",
        "category": "general",
    },
    {
        "name": "BBC News (YouTube)",
        "base_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UC16niRr50-MSBwiO3YDb3RA",
        "source_type": "social",
        "language": "en",
        "credibility_weight": 0.7,
        "region": "international",
        "category": "general",
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
#  REDDIT — Subreddits
# ═══════════════════════════════════════════════════════════════════════════════

REDDIT_SOURCES = [
    {
        "name": "Reddit r/india",
        "base_url": "https://www.reddit.com/r/india/.rss",
        "source_type": "social",
        "language": "en",
        "credibility_weight": 0.5,
        "region": "national",
        "category": "general",
    },
    {
        "name": "Reddit r/worldnews",
        "base_url": "https://www.reddit.com/r/worldnews/.rss",
        "source_type": "social",
        "language": "en",
        "credibility_weight": 0.5,
        "region": "international",
        "category": "general",
    },
    {
        "name": "Reddit r/IndianDefense",
        "base_url": "https://www.reddit.com/r/IndianDefense/.rss",
        "source_type": "social",
        "language": "en",
        "credibility_weight": 0.45,
        "region": "national",
        "category": "military",
    },
    {
        "name": "Reddit r/IndiaSpeaks",
        "base_url": "https://www.reddit.com/r/IndiaSpeaks/.rss",
        "source_type": "social",
        "language": "en",
        "credibility_weight": 0.45,
        "region": "national",
        "category": "general",
    },
    {
        "name": "Reddit r/IndianStockMarket",
        "base_url": "https://www.reddit.com/r/IndianStockMarket/.rss",
        "source_type": "social",
        "language": "en",
        "credibility_weight": 0.45,
        "region": "national",
        "category": "business",
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
#  GOVERNMENT & WIRE AGENCIES
# ═══════════════════════════════════════════════════════════════════════════════

GOVT_AND_AGENCIES = [
    {
        "name": "PIB (Press Information Bureau)",
        "base_url": "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3",
        "source_type": "govt",
        "language": "en",
        "credibility_weight": 1.0,
        "region": "national",
        "category": "politics",
    },
    {
        "name": "PIB Hindi",
        "base_url": "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=2&Regid=3",
        "source_type": "govt",
        "language": "hi",
        "credibility_weight": 1.0,
        "region": "national",
        "category": "politics",
    },
    {
        "name": "ANI News",
        "base_url": "https://www.aninews.in/rss/india.xml",
        "source_type": "wire",
        "language": "en",
        "credibility_weight": 0.9,
        "region": "national",
        "category": "general",
    },
    {
        "name": "PTI (via NDTV)",
        "base_url": "https://feeds.feedburner.com/ndtvnews-latest",
        "source_type": "wire",
        "language": "en",
        "credibility_weight": 0.95,
        "region": "national",
        "category": "general",
    },
    {
        "name": "IANS (via Outlook)",
        "base_url": "https://www.outlookindia.com/rss",
        "source_type": "wire",
        "language": "en",
        "credibility_weight": 0.85,
        "region": "national",
        "category": "general",
    },
    {
        "name": "RBI Press Releases",
        "base_url": "https://www.rbi.org.in/scripts/BS_PressReleaseDisplay.aspx?output=rss",
        "source_type": "govt",
        "language": "en",
        "credibility_weight": 1.0,
        "region": "national",
        "category": "economy",
    },
    {
        "name": "Ministry of External Affairs",
        "base_url": "https://www.mea.gov.in/rss/press-releases.xml",
        "source_type": "govt",
        "language": "en",
        "credibility_weight": 1.0,
        "region": "national",
        "category": "diplomacy",
    },
    {
        "name": "ISRO News",
        "base_url": "https://www.isro.gov.in/rss-feeds/updates.xml",
        "source_type": "govt",
        "language": "en",
        "credibility_weight": 1.0,
        "region": "national",
        "category": "technology",
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
#  MASTER LISTS
# ═══════════════════════════════════════════════════════════════════════════════

# Primary feed sources — RSS/news/govt/wire only (what users see in their feed)
FEED_SOURCES = (
    ENGLISH_NEWS
    + ENGLISH_INTERNATIONAL
    + HINDI_NEWS
    + TAMIL_NEWS
    + TELUGU_NEWS
    + BENGALI_NEWS
    + MARATHI_NEWS
    + GUJARATI_NEWS
    + KANNADA_NEWS
    + MALAYALAM_NEWS
    + PUNJABI_NEWS
    + URDU_NEWS
    + ASSAMESE_NEWS
    + ODIA_NEWS
    + GOVT_AND_AGENCIES
)

# Social/pattern sources — used only for cross-referencing and pattern detection
PATTERN_SOURCES = (
    YOUTUBE_SOURCES
    + REDDIT_SOURCES
)

# Backward-compat: ALL_SOURCES includes everything (used for pattern detection)
ALL_SOURCES = FEED_SOURCES + PATTERN_SOURCES


# ── Convenience accessors ────────────────────────────────────────────────────

def get_sources_by_language(lang: str):
    """Filter ALL_SOURCES by language code."""
    return [s for s in ALL_SOURCES if s["language"] == lang]

def get_sources_by_type(source_type: str):
    """Filter ALL_SOURCES by source_type (news, social, govt, wire)."""
    return [s for s in ALL_SOURCES if s["source_type"] == source_type]

def get_sources_by_region(region: str):
    """Filter ALL_SOURCES by region (national, regional, international)."""
    return [s for s in ALL_SOURCES if s["region"] == region]

def source_summary():
    """Print summary statistics of all registered sources."""
    from collections import Counter
    lang_c = Counter(s["language"] for s in ALL_SOURCES)
    type_c = Counter(s["source_type"] for s in ALL_SOURCES)
    region_c = Counter(s["region"] for s in ALL_SOURCES)

    return {
        "total_sources": len(ALL_SOURCES),
        "feed_sources": len(FEED_SOURCES),
        "pattern_sources": len(PATTERN_SOURCES),
        "by_language": dict(lang_c.most_common()),
        "by_type": dict(type_c.most_common()),
        "by_region": dict(region_c.most_common()),
    }
