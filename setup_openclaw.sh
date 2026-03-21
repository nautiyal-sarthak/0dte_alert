#!/bin/bash
# Setup script for 0DTE Alert OpenClaw integration

echo "🚀 Setting up 0DTE Alert for OpenClaw..."

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo "❌ Error: Please run this script from the 0dte_alert directory"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment and install dependencies
echo "📥 Installing dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "⚙️ Creating .env file from template..."
    cp .env.template .env
    echo ""
    echo "📝 IMPORTANT: Edit the .env file and add your API keys!"
    echo "   Required: ANTHROPIC_API_KEY"
    echo "   Optional: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID"
    echo ""
fi

# Make runner executable
chmod +x openclaw_runner.py

echo ""
echo "✅ Setup complete!"
echo ""
echo "🔧 Next steps:"
echo "   1. Edit .env file with your API keys"
echo "   2. Test run: ./openclaw_runner.py"
echo "   3. Add to OpenClaw cron: openclaw cron add '0 9-16 * * 1-5' './openclaw_runner.py' --workdir $(pwd)"
echo ""