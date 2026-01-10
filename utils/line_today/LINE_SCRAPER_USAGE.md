# LINE TODAY API Scraper

A high-performance, resilient scraper for [LINE TODAY](https://today.line.me) that bypasses the DOM and fetches data directly from internal APIs.

## Features
- **Fast**: No browser overhead (Puppeteer/Selenium not required).
- **Resilient**: Bypasses all popups, ad-blocker modals, and cookie consents.
- **Comprehensive**: Automatically extracts listing IDs from the page and fetches 200+ unique articles per category.
- **Rich Metadata**: Includes Title, URL, Category, Publisher, and Publish Time.

## Prerequisites
- [Node.js](https://nodejs.org/) (v16+)
- `node-fetch@2`

```bash
npm install node-fetch@2
```

## Usage

### Command Line
Run the scraper by passing any LINE TODAY category URL:

```bash
# Scrape Sports
node line_scraper_api.js "https://today.line.me/tw/v3/tab/sports"

# Scrape Entertainment/Fun
node line_scraper_api.js "https://today.line.me/tw/v3/tab/fun"
```

### Advanced: Filtering with `jq`
You can pipe the JSON output to `jq` for powerful filtering, such as searching for specific keywords in titles:

```bash
# Find news about "林志玲" in the Entertainment tab
node line_scraper_api.js https://today.line.me/tw/v3/tab/entertainment | jq '.[] | select(.title | contains("林志玲"))'

# Find news about "大谷翔平" in Sports
node line_scraper_api.js https://today.line.me/tw/v3/tab/sports | jq '.[] | select(.title | contains("大谷翔平"))'
```

## Output Format
Returns a JSON array of objects:
```json
[
  {
    "title": "Article Title",
    "url": "https://today.line.me/tw/v3/article/...",
    "category": "NBA",
    "publisher": "麗台運動",
    "publishTime": "2025-12-29T06:30:00.000Z"
  }
]
```
