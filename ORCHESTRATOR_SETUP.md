# Daily Orchestrator GitHub Actions Setup

This document explains how to set up the GitHub Actions workflow that runs the daily watchlist orchestrator every night at 9:30 PM CDT.

## 🚀 What the Workflow Does

The workflow runs every night at 9:30 PM CDT (2:30 AM UTC) and:

1. **Loads watchlist** from your Supabase database
2. **Fetches tech universe** from Financial Modeling Prep API  
3. **Builds priority queue** with watchlist symbols getting priority
4. **Rescores all symbols** using your swing_score algorithm
5. **Applies hysteresis logic** (ADD_THRESHOLD=0.67, DROP_THRESHOLD=0.60)
6. **Updates database** with new scores and watchlist changes
7. **Posts to Slack** with top 3 tickers and promotions/demotions

## 📋 Required GitHub Secrets

You need to add these secrets in your GitHub repository settings:

### Go to: Repository → Settings → Secrets and variables → Actions → New repository secret

**Core API Keys:**
- `TWELVE_DATA_API_KEY` - Your Twelve Data API key for market data
- `FMP_API_KEY` - Your Financial Modeling Prep API key for tech universe
- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_KEY` - Your Supabase anon/public API key

**Slack Integration:**
- `SLACK_WEBHOOK_URL` - Slack webhook URL for posting messages
- `SLACK_BOT_TOKEN` - Your Slack bot token (optional, for advanced features)
- `SLACK_SIGNING_SECRET` - Your Slack signing secret (optional)

**Trading (Optional):**
- `APCA_API_KEY_ID` - Alpaca API key ID
- `APCA_API_SECRET_KEY` - Alpaca secret key  
- `APCA_API_BASE_URL` - Alpaca base URL (paper trading)
- `APCA_API_DATA_URL` - Alpaca data URL

## 🔧 How to Set Up

### 1. Create Slack Webhook (Required for notifications)

1. Go to your Slack workspace
2. Navigate to Apps → Incoming Webhooks
3. Create a new webhook for the channel where you want notifications
4. Copy the webhook URL and add it as `SLACK_WEBHOOK_URL` secret

### 2. Get API Keys

- **Twelve Data**: Sign up at twelvedata.com and get your API key
- **FMP**: Sign up at financialmodelingprep.com and get your API key  
- **Supabase**: Get your project URL and anon key from your Supabase dashboard

### 3. Add GitHub Secrets

For each secret above:
1. Go to your repo → Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Enter the name exactly as shown above
4. Paste the secret value
5. Click "Add secret"

### 4. Verify Workflow

The workflow file is at `.github/workflows/daily-orchestrator.yml`. It will:
- Run automatically every night at 9:30 PM CDT
- Can be triggered manually from GitHub Actions tab
- Will send status updates to your Slack channel

## 📊 Expected Slack Output

When it runs successfully, you'll see messages like:

```
🚀 Starting Daily Watchlist Orchestrator
Date: 2025-08-20 02:30:15

✅ Daily Orchestrator Complete
🔝 Top 3: AAPL 0.742 | NVDA 0.721 | MSFT 0.693
> 📊 Rescored: 47 symbols
> 🔼 Promotions: 2
> 🔽 Demotions: 1  
> 📈 Watchlist size: 15

✅ GitHub Actions: Daily orchestrator completed successfully at 2025-08-20 02:35 UTC
```

## 🛠️ Manual Testing

You can test the workflow manually:

```bash
# Test locally (requires .env file with secrets)
python run_tasks.py daily_orchestrator

# Test just the orchestrator logic
python test_orchestrator.py

# Trigger workflow manually in GitHub Actions tab
```

## 🔍 Troubleshooting

**Common Issues:**

1. **Missing secrets**: Check all required secrets are added with exact names
2. **Database tables don't exist**: The workflow handles this gracefully, but you'll see warnings
3. **API rate limits**: The workflow includes 120ms delays between API calls
4. **Slack webhook fails**: Verify your webhook URL is correct and channel exists

**Checking Logs:**
- Go to GitHub Actions tab in your repository
- Click on the latest "Daily Watchlist Orchestrator" run  
- Check step logs for any error messages

## 📅 Schedule

- **Runtime**: 9:30 PM CDT (2:30 AM UTC) daily
- **Timezone**: The workflow runs on UTC, so times adjust for daylight saving automatically
- **Duration**: Typically 2-5 minutes depending on number of symbols

## 🎛️ Configuration

You can modify the orchestrator behavior by editing constants in `ticker_engine/orchestrator.py`:

```python
ADD_THRESHOLD = 0.67      # Score needed to add to watchlist
DROP_THRESHOLD = 0.60     # Score below which to start countdown to removal  
QUEUE_MAX = 50           # Maximum symbols to process per day
TOP_N = 12               # Number of top performers to track
SLEEP_MS = 120           # Milliseconds between API calls
```

The workflow will automatically use these updated values on the next run.
