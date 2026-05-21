# 🚀 Deployment Guide: Render

Complete step-by-step guide to deploy the Student Face Recognition Attendance System to Render.

---

## 📋 Prerequisites

- GitHub account with your repository pushed
- Render account (free tier available at https://render.com)
- Your Flask application code ready

---

## ✅ Step 1: Prepare Your Project for Deployment

### 1.1 Create `render.yaml` Configuration File

Create a new file named `render.yaml` in the root of your project:

```yaml
services:
  - type: web
    name: student-face-system
    env: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: cd backend && gunicorn -w 4 -b 0.0.0.0:$PORT app:app
    envVars:
      - key: PYTHON_VERSION
        value: 3.9
```

### 1.2 Update `requirements.txt`

Make sure your `requirements.txt` includes Gunicorn (WSGI server for production):

```bash
pip install gunicorn
pip freeze > requirements.txt
```

Or manually add `gunicorn` to `requirements.txt`:

```
Flask==2.3.0
opencv-python==4.7.0
sqlite3
gunicorn==21.0.0
# ... other dependencies
```

### 1.3 Modify `backend/app.py` for Production

Update your Flask app to handle the PORT environment variable:

```python
import os
from flask import Flask

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FRAS_SECRET_KEY', 'dev-key-change-in-production')

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
```

### 1.4 Create `.gitignore` (if not already created)

Ensure your `.gitignore` file excludes unnecessary files:

```
.venv/
.env
__pycache__/
*.pyc
*.pyo
*.pyd
.DS_Store
.vscode/
.idea/
instance/
.pytest_cache/
*.db
```

---

## 🔐 Step 2: Set Up Environment Variables

### 2.1 Create `.env` File (Local Development Only)

Create a `.env` file in your project root (DO NOT push to GitHub):

```
FRAS_SECRET_KEY=your-super-secret-key-here
DATABASE_URL=sqlite:///attendance.db
FLASK_ENV=production
```

### 2.2 Add `.env` to `.gitignore`

```bash
echo ".env" >> .gitignore
```

**Important**: Never commit `.env` file to GitHub!

---

## 📤 Step 3: Push Updates to GitHub

Before deploying, commit and push all changes:

```powershell
# Stage all changes
git add .

# Commit changes
git commit -m "Add Render deployment configuration and production settings"

# Push to GitHub
git push origin main
```

---

## 🌐 Step 4: Create Render Account & Connect GitHub

### 4.1 Sign Up on Render

1. Visit https://render.com
2. Click **Sign Up**
3. Choose **Sign up with GitHub** (recommended)
4. Authorize Render to access your GitHub repositories
5. Complete the registration

### 4.2 Connect Your Repository

1. Go to https://dashboard.render.com
2. Click **New +** → **Web Service**
3. Select **Build and deploy from a Git repository**
4. Click **Connect** next to your `student-face-system` repository
5. If not visible, click **Connect your GitHub account** and grant permissions

---

## 🚀 Step 5: Configure Your Web Service on Render

### 5.1 Web Service Settings

Fill in the following details:

| Field | Value |
|-------|-------|
| **Name** | `student-face-system` |
| **Environment** | `Python 3` |
| **Region** | Choose closest to you |
| **Branch** | `main` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `cd backend && gunicorn -w 4 -b 0.0.0.0:$PORT app:app` |
| **Plan** | `Free` (or `Paid` for better performance) |

### 5.2 Add Environment Variables

1. Scroll down to **Environment**
2. Click **Add Environment Variable**
3. Add the following variables:

```
FRAS_SECRET_KEY = your-very-secret-key-change-this
PYTHON_VERSION = 3.9
FLASK_ENV = production
```

**⚠️ Important**: Use a strong, random secret key for `FRAS_SECRET_KEY`

### 5.3 Review and Create

1. Review all settings
2. Click **Create Web Service**
3. Render will start building and deploying your app

---

## ⏳ Step 6: Monitor Deployment

### 6.1 Watch the Build Logs

1. Your service will show build progress in real-time
2. Watch for any errors in the logs
3. Once complete, you'll see: **"Your service is live at: https://your-service-name.onrender.com"**

### 6.2 Access Your Application

Once deployment is successful:

```
https://student-face-system.onrender.com
```

Or use your custom domain if configured.

---

## 🔧 Step 7: Configure Application Settings

### 7.1 Update Firebase Configuration (if applicable)

1. Update `frontend/js/firebase-init.js` with your production Firebase project
2. Commit and push changes
3. Render will auto-redeploy

### 7.2 Database Configuration

For production SQLite:
- Database file: `/tmp/attendance.db` (Render's ephemeral storage)
- For persistent storage, upgrade to **Render Postgres** (paid feature)

**⚠️ Note**: Free tier Render services lose data when restarted. Consider upgrading for production use.

---

## ✅ Step 8: Test Your Deployment

### 8.1 Test Login Page

```
https://student-face-system.onrender.com/
```

### 8.2 Verify Demo Accounts

1. Teacher Login: `teacher` / `teacher123`
2. Dean Login: `dean` / `dean123`

### 8.3 Check Console Logs

- Go to **Logs** in your Render dashboard
- Check for any errors or warnings

---

## 🔄 Step 9: Auto-Deploy from GitHub

Render automatically deploys when you push to GitHub:

```powershell
# Make changes
git add .
git commit -m "Your commit message"
git push origin main
```

Render detects the push and automatically redeploys your app within a few minutes.

---

## 🐛 Troubleshooting

### Problem: Build Failed

**Solution**:
1. Check **Logs** tab in Render dashboard
2. Ensure `requirements.txt` includes all dependencies
3. Verify Python version in `render.yaml`

### Problem: Application Won't Start

**Solution**:
1. Check start command syntax
2. Ensure `app:app` matches your Flask app variable name
3. Verify environment variables are set

### Problem: 404 Not Found

**Solution**:
1. Check if service is running (green status in dashboard)
2. Verify URL is correct
3. Clear browser cache and try again

### Problem: Port Already in Use

**Solution**:
- Render automatically assigns PORT environment variable
- Ensure you're using `os.getenv('PORT', 5000)` in your app

### Problem: OpenCV Not Working

**Solution**:
1. Add system dependencies in `render.yaml`:

```yaml
services:
  - type: web
    name: student-face-system
    buildCommand: |
      apt-get update && apt-get install -y libsm6 libxext6 libxrender-dev
      pip install -r requirements.txt
```

---

## 📊 Monitor Your Application

### View Metrics

- Go to **Metrics** tab to see:
  - CPU usage
  - Memory consumption
  - Network traffic
  - Response time

### View Logs

- Go to **Logs** tab to see:
  - Deployment logs
  - Runtime errors
  - Access logs

### Enable Advanced Monitoring

- Upgrade to paid plan for:
  - Better resource allocation
  - Persistent storage
  - Better uptime guarantee

---

## 💰 Cost Considerations

| Feature | Free Tier | Paid Tier |
|---------|-----------|-----------|
| **Web Service** | 0.5 GB RAM, Shared CPU | 1+ GB RAM, Dedicated CPU |
| **Uptime** | ~99% | 99.99% |
| **Auto-Sleep** | Yes (after 15 min inactivity) | No |
| **Database** | SQLite (ephemeral) | Postgres (persistent) |
| **Cost** | Free | From $7/month |

---

## 🎓 Next Steps

1. **Add Custom Domain**: Go to **Settings** → **Custom Domain**
2. **Enable HTTPS**: Automatically enabled on Render
3. **Upgrade Database**: Switch to Postgres for production
4. **Set Up Monitoring**: Configure alerts for failures
5. **Optimize Performance**: Use Redis for caching (paid feature)

---

## 📚 Helpful Resources

- [Render Documentation](https://render.com/docs)
- [Flask Deployment Guide](https://flask.palletsprojects.com/en/2.3.x/deploying/)
- [Gunicorn Documentation](https://gunicorn.org/)
- [GitHub & Render Integration](https://render.com/docs/github)

---

**Need help?** Check Render's support documentation or contact their team at https://render.com/support

**Last Updated**: May 21, 2026
