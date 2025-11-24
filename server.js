import express from "express";
import cors from "cors";
import puppeteer from "puppeteer";

const app = express();
app.use(cors());

app.get("/extract", async (req, res) => {
  const target = req.query.url;

  if (!target) {
    return res.json({ error: "Missing ?url=https://..." });
  }

  try {
    const browser = await puppeteer.launch({
      executablePath: process.env.PUPPETEER_EXECUTABLE_PATH, 
      headless: "new",
      args: [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--no-zygote",
        "--single-process",
      ],
    });

    const page = await browser.newPage();

    let links = [];

    page.on("request", (reqObj) => {
      const url = reqObj.url();
      if (url.includes(".m3u8")) {
        links.push(url);
      }
    });

    await page.goto(target, {
      waitUntil: "networkidle2",
      timeout: 0,
    });

    await page.waitForTimeout(5000);

    await browser.close();

    res.json({ extracted: [...new Set(links)] });

  } catch (err) {
    res.json({ error: err.toString() });
  }
});

app.get("/", (req, res) => {
  res.send("M3U8 Extractor is running!");
});

app.listen(3000, () => console.log("Server running on port 3000"));
