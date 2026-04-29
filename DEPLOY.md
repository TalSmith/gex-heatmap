# GEX Heatmap — Deploy Guide
## Get it live on your phone in ~10 minutes (no coding required)

---

## What you'll end up with
A URL like `https://your-name-gex-heatmap.streamlit.app` that works on
any phone, tablet, or computer. Bookmarkable like any website.

---

## Step 1 — Create a free GitHub account (2 min)

1. Go to **github.com**
2. Click **Sign up** → follow the steps (it's free)
3. Verify your email

---

## Step 2 — Create a new repository (2 min)

A "repository" is just a folder in the cloud that holds your app files.

1. Once logged in to GitHub, click the **+** icon (top right) → **New repository**
2. Name it: `gex-heatmap`
3. Set it to **Public**
4. Click **Create repository**

---

## Step 3 — Upload your files (2 min)

You need to upload TWO files: `gex_app.py` and `requirements.txt`

1. On the repository page, click **uploading an existing file** (or drag and drop)
2. Drag both files onto the page
3. Scroll down → click **Commit changes**

---

## Step 4 — Deploy on Streamlit Cloud (3 min)

1. Go to **share.streamlit.io**
2. Click **Sign in with GitHub** → authorize it
3. Click **New app**
4. Fill in:
   - Repository: `your-github-username/gex-heatmap`
   - Branch: `main`
   - Main file path: `gex_app.py`
5. Click **Deploy!**

Wait about 60–90 seconds while it installs everything. You'll see a spinning
screen — that's normal.

---

## Step 5 — Add your Anthropic API key (for AI summaries)

This keeps your key safe and out of the code.

1. In Streamlit Cloud, click your app → **Settings** → **Secrets**
2. Add this (replace with your actual key):

```
ANTHROPIC_API_KEY = "sk-ant-your-key-here"
```

3. Click **Save** → the app restarts automatically

Get a free Anthropic key at: **console.anthropic.com**
(Free tier is plenty — AI summaries use very few tokens)

---

## Step 6 — Open on your phone

1. Copy your app URL (looks like `https://xxx.streamlit.app`)
2. Open it in Chrome or Safari on your Android/iPhone
3. Optional: tap **Share → Add to Home Screen** for an app-like shortcut

---

## Updating the app later

If you want to change anything (e.g. add a ticker, adjust the strike range):

1. Open the file on GitHub (click it → click the pencil ✏️ icon)
2. Make your change
3. Click **Commit changes**

Streamlit Cloud auto-deploys the update in about 30 seconds.

---

## Changing settings without editing code

Once the app is open, use the **sidebar** (tap the ≡ icon on mobile):
- Switch tickers (SPY, QQQ, AAPL, etc.)
- Change auto-refresh interval
- Enter your API key (if you haven't added it to Secrets yet)

---

## Troubleshooting

**"Module not found" error on deploy:**
Make sure `requirements.txt` is in the repository alongside `gex_app.py`.

**App shows "No options data found":**
Markets may be closed or Yahoo Finance is temporarily rate-limiting.
Wait 30 seconds and refresh the page.

**AI summary says "check your API key":**
Double-check that your key in Streamlit Secrets starts with `sk-ant-`
and has no extra spaces.

**Page loads but heatmap is empty / all zeros:**
Yahoo Finance sometimes returns missing gamma data for thinly-traded options.
Try SPY or QQQ first — they always have complete data.
