const fetch = require('node-fetch');

/**
 * Scrapes LINE TODAY articles by finding the internal Listing IDs
 * and calling the API directly. This is the fastest and most comprehensive method.
 */
async function scrapeLineTodayFullApi(url) {
    if (!url || !url.startsWith('https://today.line.me')) {
        throw new Error('Please provide a valid URL starting with https://today.line.me');
    }

    const headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Referer': 'https://today.line.me/'
    };

    console.error(`Step 1: Fetching initial page to extract listing IDs...`);
    const pageResp = await fetch(url, { headers });
    const html = await pageResp.text();

    const nextDataMatch = html.match(/<script id="__NEXT_DATA__" type="application\/json">([\s\S]*?)<\/script>/);
    if (!nextDataMatch) throw new Error('Could not find __NEXT_DATA__');

    const nextData = JSON.parse(nextDataMatch[1]);
    const fallback = nextData.props.pageProps.fallback || {};

    // Find the primary page data which contains the module layout
    // The key is usually "getPageData,{slug}"
    const pageDataKey = Object.keys(fallback).find(k => k.startsWith('getPageData'));
    const pageData = fallback[pageDataKey];

    if (!pageData || !pageData.modules) {
        throw new Error('Could not find page module definitions.');
    }

    // Collect all unique listing IDs from the modules
    const listingIds = new Set();
    pageData.modules.forEach(mod => {
        if (mod.listings) {
            mod.listings.forEach(l => listingIds.add(l.id));
        }
    });

    console.error(`Step 2: Identified ${listingIds.size} listing IDs. Fetching content from API...`);

    const allArticles = [];
    const seenUrls = new Set();

    // Fetch data for each listing ID
    for (const id of listingIds) {
        try {
            // We can control 'length' to get more items per ID
            const apiUrl = `https://today.line.me/api/v6/listings/${id}?country=tw&offset=0&length=50`;
            const apiResp = await fetch(apiUrl, { headers });
            const data = await apiResp.json();

            if (data.items && Array.isArray(data.items)) {
                data.items.forEach(item => {
                    if (item.title && item.url && item.type !== 'AD') {
                        let articleUrl = item.url.hash
                            ? `https://today.line.me/tw/v3/article/${item.url.hash}`
                            : item.url.url;

                        if (!seenUrls.has(articleUrl)) {
                            allArticles.push({
                                title: item.title.trim(),
                                url: articleUrl,
                                category: item.badgeText || item.categoryName || '',
                                publisher: item.publisher || '',
                                publishTime: item.publishTimeUnix ? new Date(item.publishTimeUnix).toISOString() : ''
                            });
                            seenUrls.add(articleUrl);
                        }
                    }
                });
            }
        } catch (err) {
            console.error(`Failed to fetch listing ${id}:`, err.message);
        }
    }

    return allArticles;
}

if (require.main === module) {
    const targetUrl = process.argv[2] || 'https://today.line.me/tw/v3/tab/sports';
    scrapeLineTodayFullApi(targetUrl)
        .then(result => {
            console.log(JSON.stringify(result, null, 2));
            console.error(`\nSuccess! Extracted ${result.length} unique articles directly from API.`);
        })
        .catch(console.error);
}

module.exports = scrapeLineTodayFullApi;
