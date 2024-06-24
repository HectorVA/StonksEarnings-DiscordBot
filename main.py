import discord
import requests
import csv
import logging
from datetime import datetime, timedelta

# Set up logging to console
logging.basicConfig(level=logging.DEBUG)

TOKEN = '<YOUR_TOKEN>' # This is the discord bot token acquired when setting up your discord bot app. Learn more at https://discord.com/developers/docs/topics/oauth2
API_KEY = '<YOUR_PUBLIC_KEY>' # You can get a public key by requesting one from https://www.alphavantage.co/support/#api-key
CSV_URL = f'https://www.alphavantage.co/query?function=EARNINGS_CALENDAR&horizon=3month&apikey={API_KEY}'

# List of predefined tickers. You can add or remove more tickers if you wish. 
predefined_tickers = [
    "AAPL", "ABBV", "ABNB", "ABT", "ADBE", "ADI", "ADP", "ADSK", "AEP", "AFL", "AIG", "AJG", "AMAT", "AMD", "AMGN", "AMT", "AMZN", "ANET", "APD", "APH", "APO", "AVGO", "AXP", "AZO",
    "BA", "BAC", "BDX", "BKNG", "BLK", "BMY", "BRK-B", "BSX", "BX", "C", "CARR", "CAT", "CDNS", "CEG", "CI", "CL", "CMCSA", "CME", "CMG", "COF", "COIN", "COP", "COR", "COST", "CPRT",
    "CRM", "CRWD", "CSCO", "CSX", "CTAS", "CVS", "CVX", "DE", "DELL", "DHI", "DHR", "DIS", "DLR", "DUK", "DXCM", "ECL", "ELV", "EMR", "EOG", "EPD", "EQIX", "ET", "EW", "F", "FCX", "FDX",
    "FI", "FTNT", "GD", "GE", "GILD", "GM", "GOOG", "GS", "HCA", "HD", "HLT", "HON", "IBKR", "IBM", "ICE", "INTC", "INTU", "ISRG", "ITW", "JNJ", "JPM", "KDP", "KKR", "KLAC", "KMB", "KO",
    "LLY", "LMT", "LOW", "LRCX", "MA", "MAR", "MCD", "MCHP", "MCK", "MCO", "MDLZ", "MET", "META", "MMC", "MMM", "MNST", "MO", "MPC", "MRK", "MRNA", "MRVL", "MS", "MSFT", "MSI", "MU", "NEE",
    "NEM", "NFLX", "NKE", "NOC", "NOW", "NSC", "NVDA", "ORCL", "ORLY", "OXY", "PANW", "PCAR", "PCG", "PEP", "PFE", "PG", "PGR", "PH", "PLD", "PLTR", "PM", "PNC", "PSA", "PSX", "PXD", "PYPL",
    "QCOM", "REGN", "ROP", "ROST", "RSG", "RTX", "SBUX", "SCCO", "SCHW", "SHW", "SLB", "SMCI", "SNPS", "SO", "SPG", "SPGI", "SRE", "STZ", "SYK", "T", "TDG", "TFC", "TGT", "TJX", "TMO", "TMUS",
    "TRV", "TSLA", "TTD", "TXN", "UBER", "UNH", "UNP", "UPS", "USB", "V", "VLO", "VRTX", "VZ", "WDAY", "WELL", "WFC", "WM", "WMB", "WMT", "XOM", "ZTS",
]

# Define the intents, including MESSAGE_CONTENT
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

client = discord.Client(intents=intents) # This allows the bot to read the messages from all discord channels but discord will only allow a response to be sent to the channels the bot has permission to reply to.

# Function to get company overview
def get_company_overview(symbol):
    url = f'https://www.alphavantage.co/query?function=OVERVIEW&symbol={symbol}&apikey={API_KEY}'
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        return None

# Function to get daily close price for a symbol
def get_daily_close_price(symbol):
    url = f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&apikey={API_KEY}'
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        today = datetime.now().strftime('%Y-%m-%d')
        time_series = data.get("Time Series (Daily)")
        if time_series and today in time_series:
            return time_series[today]["4. close"]
    return None

# Function to process each symbol
def process_symbol(symbol):
    overview = get_company_overview(symbol)
    close_price = get_daily_close_price(symbol)
    if overview:
        # Debugging: Print the retrieved overview data
        print(f"Retrieved data for {symbol}: {overview}")
        result = {
            "Symbol": overview.get("Symbol"),
            "Name": overview.get("Name"),
            "Description": overview.get("Description"),
            "Exchange": overview.get("Exchange"),
            "Country": overview.get("Country"),
            "Sector": overview.get("Sector"),
            "MarketCapitalization": format_market_cap(overview.get("MarketCapitalization")),
            "52WeekHigh": overview.get("52WeekHigh"),
            "52WeekLow": overview.get("52WeekLow")
        }
        if close_price:
            result["ClosePrice"] = close_price
        return result
    return None

# Function to format market capitalization
def format_market_cap(market_cap):
    market_cap = int(market_cap)
    if market_cap >= 1_000_000_000_000:
        return f'{market_cap / 1_000_000_000_000:.1f}T'
    elif market_cap >= 1_000_000_000:
        return f'{market_cap / 1_000_000_000:.1f}B'
    elif market_cap >= 1_000_000:
        return f'{market_cap / 1_000_000:.1f}M'
    else:
        return str(market_cap)

#Function to fetch earnings data
def fetch_earnings_data():
    url = CSV_URL
    
    with requests.Session() as s:
        download = s.get(url)
        decoded_content = download.content.decode('utf-8')
        logging.debug(f"API response content: {decoded_content}")
        cr = csv.reader(decoded_content.splitlines(), delimiter=',')
        my_list = list(cr)
        logging.debug(f"Parsed CSV data: {my_list}")
        return my_list

# Function to filter earnings data.
def filter_earnings_data(data, tickers, start_date=None, end_date=None):
    filtered_data = []
    for row in data[1:]:  # Skip the header row
        if len(row) < 6:  # Ensure the row has enough columns
            continue
        try:
            # Try different date formats
            try:
                report_date = datetime.strptime(row[2], '%Y-%m-%d').date()
            except ValueError:
                report_date = datetime.strptime(row[2], '%m-%d-%Y').date()
                
            if row[0].upper() in tickers:
                if start_date and end_date:
                    if start_date <= report_date <= end_date:
                        filtered_data.append(row)
                else:
                    filtered_data.append(row)
        except Exception as e:
            logging.error(f"Error processing row: {row} - {e}")
    return filtered_data

def format_earnings_data(data):
    formatted_data = []
    for row in data:
        symbol = row[0]
        company_name = row[1]
        report_date = row[2]
        estimate = row[4]
        formatted_data.append(f"{symbol}, {company_name}, Earnings Call: {report_date}, Estimate: {estimate}")
    return formatted_data

@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')

@client.event
async def on_message(message): 
    if message.author == client.user:
        return

    print(f"Received message: {message.content}")

    content = message.content.lower().strip()

    if content == '!earnings help':
        response = (
            "Hello! Welcome to Stonks Bot, your friendly guide to earnings and stock info. Let's make some stonks! 🚀\n\n"
            "Earnings Bot Commands:\n\n"
            "1. `!earnings today` - Get earnings reports for today.\n"
            "2. `!earnings tomorrow` - Get earnings reports for the next business day.\n"
            "3. `!earnings next week` - Get earnings reports for the next 7 business days.\n"
            "4. `!earnings next month` - Get earnings reports for the next 30 business days.\n"
            "5. `!earnings year` - Get all remaining earnings reports for the current year.\n"
            "6. `!earnings [ticker]` - Get all earnings report dates for a specific ticker (case insensitive).\n"
            "7. `!earnings help` - Show this help message.\n"
            "8. `!overview [ticker]` - Get company overview for a specific ticker (case insensitive).\n"
            "Remember, buy high and sell low... or was it the other way around? 🤔"
        )
        await message.channel.send(response)  # 'await' within async function
        return

    today = datetime.now().date()
    start_date = None
    end_date = None
    specific_ticker = None

    if content.startswith('!earnings today'):
        start_date = today
        end_date = today

    elif content.startswith('!earnings tomorrow'):
        start_date = today
        end_date = today + timedelta(days=1)

    elif content.startswith('!earnings next week'):
        start_date = today
        end_date = today + timedelta(days=7)

    elif content.startswith('!earnings next month'):
        start_date = today
        end_date = today + timedelta(days=30)

    elif content.startswith('!earnings year'):
        start_date = today
        end_date = datetime(today.year, 12, 31).date()

    elif content.startswith('!earnings '):
        command, *ticker = content.split()
        specific_ticker = ticker[0].upper()

    elif content.startswith('!overview '):
        command, *ticker = content.split()
        specific_ticker = ticker[0].upper()
        overview_data = process_symbol(specific_ticker)
        if overview_data:
            response = (
                f"Symbol: {overview_data['Symbol']}\n"
                f"Name: {overview_data['Name']}\n"
                f"Description: {overview_data['Description']}\n"
                f"Exchange: {overview_data['Exchange']}\n"
                f"Country: {overview_data['Country']}\n"
                f"Sector: {overview_data['Sector']}\n"
                f"Market Capitalization: {overview_data['MarketCapitalization']}\n"
                f"52 Week High: {overview_data['52WeekHigh']}\n"
                f"52 Week Low: {overview_data['52WeekLow']}\n"
                f"Close Price: {overview_data.get('ClosePrice', 'N/A')}"
            )
        else:
            response = f"No overview data found for {specific_ticker}."
        await message.channel.send(response)  # 'await' within async function
        return

    else:
        return

    # Fetch, filter, and format the earnings data
    earnings_data = fetch_earnings_data()
    if specific_ticker:
        filtered_earnings_data = filter_earnings_data(earnings_data, [specific_ticker])
    else:
        filtered_earnings_data = filter_earnings_data(earnings_data, predefined_tickers, start_date, end_date)

    formatted_earnings_data = format_earnings_data(filtered_earnings_data)

    # Split the response if it exceeds 2000 characters
    response = "\n".join(formatted_earnings_data)
    if not response:
        response = "No earnings found for the specified period."

    print(f"Sending response: {response}")

    try:
        if len(response) > 2000:
            response_parts = [response[i:i+2000] for i in range(0, len(response), 2000)]
            for part in response_parts:
               await message.channel.send(part)  # 'await' within async function
        else:
            await message.channel.send(response)  # 'await' within async function

        print("Response sent successfully")
    except Exception as e:
        print(f"Failed to send message: {e}")
client.run(TOKEN)
