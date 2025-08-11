# 🔑 API Setup Guide for AI Email Manager

This guide will walk you through obtaining the necessary API keys and credentials to run the AI Email Manager application.

## ⚡ Quick Setup

**You only need two things:**
1. A **Gemini API Key** (for AI features)
2. **Google OAuth 2.0 Credentials** (for Gmail & Calendar access)

---

## 📱 Step 1: Get Your Gemini API Key

The Gemini API powers all the AI features in the application (email classification, summarization, etc.).

### Instructions:

1. **Visit Google AI Studio**
   - Go to: [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
   - Sign in with your Google account

2. **Create API Key**
   - Click the **"Create API key"** button
   - Choose to create it in a new project or use an existing Google Cloud project
   - The API key will be generated instantly

3. **Copy Your Key**
   - Click the copy icon next to your new API key
   - **Keep this secure!** Don't share it publicly

4. **Important Notes:**
   - The Gemini API has a generous free tier
   - You can monitor your usage in the AI Studio dashboard
   - API keys are tied to your Google account

---

## 🔐 Step 2: Get Google OAuth 2.0 Credentials

These credentials allow the app to securely access your Gmail and Calendar with your permission.

### Instructions:

#### **A. Create a Google Cloud Project**

1. **Go to Google Cloud Console**
   - Visit: [https://console.cloud.google.com/](https://console.cloud.google.com/)
   - Sign in with your Google account

2. **Create New Project**
   - Click the project dropdown at the top of the page
   - Select "**New Project**"
   - Name it something like "AI Email Manager"
   - Click "**Create**"

#### **B. Enable Required APIs**

1. **Enable Gmail API**
   - In the search bar, type "Gmail API"
   - Click on the Gmail API result
   - Click "**Enable**"

2. **Enable Google Calendar API**
   - Search for "Google Calendar API"
   - Click on the result and click "**Enable**"

#### **C. Configure OAuth Consent Screen**

1. **Navigate to OAuth Consent Screen**
   - From the navigation menu (☰), go to:
   - **APIs & Services → OAuth consent screen**

2. **Choose User Type**
   - Select "**External**" (unless you have a Google Workspace domain)
   - Click "**Create**"

3. **Fill Required Information**
   - **App name**: `AI Email Manager`
   - **User support email**: Select your email address
   - **Developer contact information**: Enter your email address
   - Leave other fields as default

4. **Save and Continue**
   - Click "**Save and Continue**" through each section
   - You don't need to add anything in "Scopes" or "Test users"
   - On the summary page, click "**Back to Dashboard**"

5. **Publish the App (Important!)**
   - Click "**Publish the App**" to avoid token expiration issues
   - This is safe for personal use

#### **D. Create OAuth 2.0 Credentials**

1. **Navigate to Credentials**
   - From the navigation menu, go to:
   - **APIs & Services → Credentials**

2. **Create Credentials**
   - Click "**+ Create Credentials**"
   - Select "**OAuth client ID**"

3. **Configure Application**
   - **Application type**: Choose "**Desktop app**"
   - **Name**: Enter "AI Email Manager Client"
   - Click "**Create**"

4. **Copy Your Credentials**
   - A popup will show your:
     - **Client ID** (long string starting with numbers)
     - **Client Secret** (shorter string)
   - **Copy both values** - you'll need them in the app

---

## 🎯 Step 3: Enter Credentials in the App

Once you have your API keys, you can enter them directly in the application:

### Method 1: Using the Settings Window (Recommended)

1. **Start the Application**
   ```bash
   python main.py
   ```

2. **Open Settings**
   - Click the "**Settings**" button in the top-right corner
   - The Settings window will open

3. **Enter Your Credentials**
   - **Gemini API Key**: Paste your Gemini API key
   - **Google Client ID**: Paste your OAuth Client ID
   - **Google Client Secret**: Paste your OAuth Client Secret

4. **Save and Restart**
   - Click "**Save and Close**"
   - Restart the application for changes to take effect

### Method 2: Manual .env File Configuration

1. **Copy the Template**
   ```bash
   copy .env.template .env
   ```

2. **Edit the .env File**
   Open `.env` in a text editor and replace the placeholder values:
   ```
   GEMINI_API_KEY=your_actual_gemini_api_key_here
   GOOGLE_CLIENT_ID=your_actual_google_client_id_here
   GOOGLE_CLIENT_SECRET=your_actual_google_client_secret_here
   ```

3. **Save and Restart**
   Save the file and restart the application

---

## ✅ Step 4: Test Your Setup

1. **Start the Application**
   ```bash
   python main.py
   ```

2. **Authenticate**
   - Click the "**Authenticate**" button
   - Your default browser will open with Google's OAuth consent screen
   - Sign in and grant permissions to the app
   - Copy the authorization code and paste it back in the application

3. **Load Emails**
   - Once authenticated, click "**Refresh Emails**"
   - The app will fetch your recent emails and analyze them with AI

---

## 🔧 Troubleshooting

### Common Issues and Solutions:

**❌ "Invalid API Key" Error**
- Double-check your Gemini API key is correct
- Make sure there are no extra spaces or characters
- Verify the key is active in Google AI Studio

**❌ "OAuth Error" or "Invalid Client"**
- Verify your Google Client ID and Secret are correct
- Make sure you published your OAuth consent screen
- Check that Gmail and Calendar APIs are enabled in your project

**❌ "Scope Error" or "Access Denied"**
- Make sure you granted all requested permissions during OAuth
- Try re-authenticating by clicking the "Authenticate" button again

**❌ "Application Blocked" Message**
- Make sure you published your OAuth consent screen to production
- If you see "This app isn't verified", click "Advanced" → "Go to AI Email Manager (unsafe)"
- This is normal for personal projects

### Need Help?

1. **Check the Logs**
   - Look at `data/app.log` for detailed error messages

2. **Verify API Status**
   - Gmail API: [https://console.cloud.google.com/apis/library/gmail.googleapis.com](https://console.cloud.google.com/apis/library/gmail.googleapis.com)
   - Calendar API: [https://console.cloud.google.com/apis/library/calendar-json.googleapis.com](https://console.cloud.google.com/apis/library/calendar-json.googleapis.com)
   - Gemini API: [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)

3. **Reset and Try Again**
   - Delete the `.env` file and `data/google_token.pickle`
   - Restart the application and re-enter your credentials

---

## 🔒 Security Notes

- **Never share your API keys publicly** (e.g., in GitHub repositories, forums)
- **Keep your `.env` file secure** - it's excluded from version control by default
- **Revoke access** in your Google Account settings if you no longer use the app
- **Monitor API usage** in Google AI Studio and Google Cloud Console

---

## 💰 Costs and Limits

### Gemini API (Free Tier):
- **15 requests per minute**
- **1,500 requests per day**
- **1 million tokens per month**
- More than enough for personal email management

### Google APIs (Free):
- **Gmail API**: 1 billion quota units per day (essentially unlimited for personal use)
- **Calendar API**: 1,000,000 requests per day
- No cost for personal use

---

**🎉 That's it! Your AI Email Manager is now ready to intelligently manage your inbox.**
