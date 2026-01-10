const puppeteer = require('puppeteer');

/**
 * Scrapes headlines, links, and metadata from a LINE TODAY page.
 * 
 * @param {string} url - The URL of the LINE TODAY page (e.g., "https://today.line.me/tw/v3/tab/sports")
 * @returns {Promise<Array<{title: string, url: string, category?: string, thumbnail?: string, publisher?: string}>>}
 */
async function scrapeLineToday(url) {
    if (!url || !url.startsWith('https://today.line.me')) {
        throw new Error('Please provide a valid URL starting with https://today.line.me');
    }

    const browser = await puppeteer.launch({
        headless: "new",
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    try {
        const page = await browser.newPage();
        await page.setUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');

        console.log(`Navigating to ${url}...`);
        await page.goto(url, { waitUntil: 'networkidle2', timeout: 60000 });

        try { await page.keyboard.press('Escape'); } catch (e) { }

        console.log('Scrolling to load content...');
        for (let i = 0; i < 5; i++) {
            await page.evaluate(() => window.scrollBy(0, window.innerHeight * 2));
            await new Promise(r => setTimeout(r, 1500));
        }

        console.log('Extracting articles...');
        const articles = await page.evaluate(() => {
            const results = [];
            const seenUrls = new Set();

            const linkElements = document.querySelectorAll('a.ltcp-link');

            linkElements.forEach(link => {
                // Main title element
                // We use a broader selection to catch different layout variations
                const h3 = link.querySelector('h3');

                if (h3) {
                    // Clone so we can manipulate (remove badge) without breaking ref
                    const titleNode = h3.cloneNode(true);

                    // 1. Extract and Remove Category Badge
                    // Badges often appear as spans inside the h3 or divs with specific background colors
                    let category = '';
                    // Common selector for the badge text container inside valid LINE content
                    // It usually is the first span that contains text.
                    // We'll look for the specific structure observed: div > span with text
                    const badgeCandidate = titleNode.querySelector('span div span, .badge, [class*="badge"]');
                    if (badgeCandidate) {
                        category = badgeCandidate.innerText.trim();
                        // Remove the entire badge container to clean up the title
                        // We need to find the root of the badge in the h3 to remove it cleanly
                        // Often it's a top-level span in the h3
                        const badgeRoot = titleNode.querySelector('span');
                        if (badgeRoot) badgeRoot.remove();
                    }

                    let title = titleNode.innerText.trim();
                    let articleUrl = link.getAttribute('href');

                    // 2. Extract Thumbnail
                    let thumbnail = '';
                    const img = link.querySelector('img');
                    if (img) {
                        thumbnail = img.getAttribute('src') || '';
                    }

                    // 3. Extract Publisher
                    // Publishers are usually in a separate div/span below the title
                    // We'll try to get text content of the link that is NOT the title.
                    // This is a heuristic.
                    let publisher = '';
                    const allText = link.innerText;
                    // If we remove the title text and category text from allText, what remains might be publisher/time
                    // A simpler way: look for the publisher class if known, or just the last element.
                    // Based on previous inspections, publisher is often not explicitly class-named clearly globally.
                    // We will report what we can find.

                    if (title && articleUrl) {
                        if (articleUrl.startsWith('/')) {
                            articleUrl = 'https://today.line.me' + articleUrl;
                        }

                        const isAd = title.includes('Sponsored') || title.includes('廣告');

                        if (!isAd && !seenUrls.has(articleUrl)) {
                            results.push({
                                title,
                                url: articleUrl,
                                category,
                                thumbnail
                            });
                            seenUrls.add(articleUrl);
                        }
                    }
                }
            });

            return results;
        });

        return articles;

    } finally {
        await browser.close();
    }
}

if (require.main === module) {
    const targetUrl = process.argv[2] || 'https://today.line.me/tw/v3/tab/sports';
    scrapeLineToday(targetUrl)
        .then(result => console.log(JSON.stringify(result, null, 2)))
        .catch(console.error);
}

module.exports = scrapeLineToday;
