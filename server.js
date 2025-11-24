import express from "express";
import cors from "cors";
import puppeteer from "puppeteer-core";
import chrome from "chrome-aws-lambda";

const app = express();
app.use(cors());

app.get("/extract", async (req, res) => {
  const target = req.query.url;

  if (!target) 
    return res.json({ error: "Missing ?url=" });

  try {
    const executablePath = await chrome.executablePath;

    const browser = await puppeteer.launch({
      executablePath,
      headless: true,
      args: chrome.args
    });

    const page = await browser.newPage();

    let links = [];

    page.on("request", reqObj => {
      const url = reqObj.url();
      if (url.includes(".m3u8")) links.push(url);
    });

    await page.goto(target, { waitUntil: "networkidle2", timeout: 0 });
    await page.waitForTimeout(4000);

    await browser.close();

    res.json({ extracted: [...new Set(links)] });

  } catch (err) {
    res.json({ error: err.toString() });
  }
});

app.get("/", (req, res) => {
  res.send("M3U8 Extractor is running!");
});

app.listen(3000, () => console.log("Server started"));
