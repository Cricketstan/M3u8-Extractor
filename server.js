const express = require("express");
const puppeteer = require("puppeteer");

const app = express();
app.use(express.json());

app.post("/extract", async (req, res) => {
  const { url } = req.body;
  if (!url) return res.json({ error: "URL required" });

  let browser;

  try {
    browser = await puppeteer.launch({
      headless: "new",
      args: [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu"
      ]
    });

    const page = await browser.newPage();
    const found = new Set();

    page.on("request", r => {
      const u = r.url();
      if (u.includes(".m3u8")) found.add(u);
    });

    page.on("response", r => {
      const u = r.url();
      if (u.includes(".m3u8")) found.add(u);
    });

    await page.setUserAgent(
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
    );

    await page.goto(url, {
      waitUntil: "domcontentloaded",
      timeout: 60000
    });

    // Try autoplay
    await page.evaluate(() => {
      const v = document.querySelector("video");
      if (v) v.play().catch(()=>{});
    });

    await new Promise(r => setTimeout(r, 8000));

    await browser.close();

    if (found.size === 0) {
      return res.json({
        success: false,
        message: "No m3u8 found (DRM or protected)"
      });
    }

    res.json({
      success: true,
      count: found.size,
      streams: [...found]
    });

  } catch (e) {
    if (browser) await browser.close();
    res.status(500).json({ error: e.message });
  }
});

app.listen(process.env.PORT || 3000, () => {
  console.log("🚀 M3U8 extractor running");
});
