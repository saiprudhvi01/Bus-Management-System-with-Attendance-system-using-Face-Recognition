# Email Setup Guide for Smart Campus Transit System

## 📧 Current Issue
The email system is not working because it's using placeholder credentials:
- sender_email: 'yourmail@gmail.com' 
- sender_password: 'APP_PASSWORD'

## 🔧 How to Fix - Step by Step

### Option 1: Use Gmail (Recommended)

#### Step 1: Enable 2-Factor Authentication
1. Go to your Google Account: https://myaccount.google.com/
2. Go to Security → 2-Step Verification
3. Enable it if not already enabled

#### Step 2: Create App Password
1. Go to Google Account → Security → App Passwords
2. Select "Mail" for the app
3. Select "Other (Custom name)" and enter "Smart Campus Transit"
4. Click "Generate"
5. Copy the 16-character password (without spaces)

#### Step 3: Update Configuration
Edit `bus_pass_app.py` and replace:
```python
EMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'sender_email': 'yourmail@gmail.com',  # Replace with your actual Gmail
    'sender_password': 'APP_PASSWORD',      # Replace with your App Password
    'sender_name': 'Smart Campus Transit System'
}
```

### Option 2: Use a Test Email Service

For testing, you can use a temporary email service like:
- 10minutemail.com
- temp-mail.org

## 🧪 Quick Test

After configuring, try sending an email and check the server logs for debug messages.

## 🚨 Common Issues

1. **"Less secure app access"**: Use App Password instead
2. **Firewall blocking**: Check port 587 is open
3. **Wrong password**: Ensure you're using the App Password, not your regular password

## 📞 Troubleshooting

If emails still don't work, check the server console for debug messages that show the exact error.
