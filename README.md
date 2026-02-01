Collecting workspace information

# SPX 0-DTE Options Trading Bot

This project is a Python-based SPX 0-DTE options trading bot that fetches market data, calculates technical indicators, evaluates trading conditions using an AI agent, and sends alerts for potential trades.

---

## Features

- Fetches SPX market data from an external API.
- Calculates technical indicators like RSI, MACD, and Bollinger Bands.
- Uses Anthropic's Claude AI to evaluate trading conditions.
- Sends alerts for potential trades based on clean setups.
- Logs decisions and maintains state for cooldowns.

---

## Prerequisites

- Python 3.9 or higher
- An Anthropic API key for using Claude AI
- Access to the required market data API

---

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd <repository-folder>
```

---

### 2. Create a Virtual Environment

To isolate dependencies, create a virtual environment:

```bash
python3 -m venv venv
```

Activate the virtual environment:

- **Linux/MacOS**:
  ```bash
  source venv/bin/activate
  ```
- **Windows**:
  ```powershell
  .\venv\Scripts\Activate.ps1
  ```

---

### 3. Install Required Libraries

Install the dependencies listed in 

requirements.txt

:

```bash
pip install -r requirements.txt
```

---

### 4. Create the 

.env

 File

The 

.env

 file is used to store sensitive information like the Anthropic API key. Create a 

.env

 file in the root directory and add the following:

```properties
ANTHROPIC_API_KEY=your-anthropic-api-key
```

---

### 5. Obtain the Anthropic API Key

1. Sign up for an Anthropic account at [Anthropic](https://www.anthropic.com/).
2. Navigate to the API section in your account dashboard.
3. Generate an API key and copy it.
4. Replace `your-anthropic-api-key` in the 

.env

 file with the generated key.

---

## Running the Bot

To start the bot, run the following command:

```bash
python main.py
```

---

## Notes

- The bot fetches market data and evaluates trading conditions in real-time.
- Alerts are logged in 

alert_log.csv

.
- The bot uses a cooldown mechanism to avoid frequent alerts.

---

## Disclaimer

This project is for educational purposes only. Use it at your own risk. Always perform due diligence before making trading decisions.
