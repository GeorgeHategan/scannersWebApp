# Render Deployment Setup

## Environment Variables

After deploying to Render, you **MUST** manually set these environment variables in the Render Dashboard:

1. Go to https://dashboard.render.com
2. Select your service: `market-analysis-platform`
3. Click on the **Environment** tab
4. Add these variables:

### Required Variables:

| Key | Value | Description |
|-----|-------|-------------|
| `USE_MOTHERDUCK` | `true` | Enable MotherDuck cloud database |
| `DATABASE_NAME` | `marketflow` | Name of your MotherDuck database |
| `MOTHERDUCK_TOKEN` | `[your token]` | Your MotherDuck authentication token |

### Getting Your MotherDuck Token:

1. Visit https://motherduck.com
2. Log in to your account
3. Go to Settings → Access Tokens
4. Copy your token
5. Paste it in Render as the `MOTHERDUCK_TOKEN` value

## After Setting Variables:

1. Click **Save Changes** in Render
2. The service will automatically redeploy
3. Check the logs to verify:
   - `USE_MOTHERDUCK: true` ✅
   - `DATABASE_NAME: marketflow` ✅
   - Successful connection to MotherDuck ✅

## Troubleshooting:

If you see `USE_MOTHERDUCK: false` in logs after setting the variable:
- Verify you clicked "Save Changes" in Render
- Try manually triggering a redeploy
- Check the Environment tab to confirm the variable exists
