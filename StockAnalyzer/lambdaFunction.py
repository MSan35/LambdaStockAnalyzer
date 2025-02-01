import json
import boto3
import os
from botocore.exceptions import ClientError
from datetime import datetime, timedelta
import pandas as pd

dynamodb = boto3.client("dynamodb", region_name=os.getenv('AWS_REGION', 'us-east-2'))
sns = boto3.client('sns', region_name=os.getenv('AWS_REGION', 'us-east-2'))

table_name = "stock_prices"
stock_symbols = [
    'NVDA',  # Nvidia
    'AAPL',  # Apple
    'AMZN',  # Amazon
    'GOOGL',  # Google
    'TSLA',  # Tesla
    'RY',  # Royal Bank of Canada
    'TD',  # Toronto-Dominion Bank
    'T.TO'  # Telus
]

# Get data for past 30 days
def fetch_stock_data(start_date, end_date):
    try:
        response = dynamodb.scan(
            TableName=table_name,
            FilterExpression="#date BETWEEN :start_date AND :end_date",
            ExpressionAttributeNames={"#date": "date"},
            ExpressionAttributeValues={
                ":start_date": {"S": start_date},
                ":end_date": {"S": end_date}
            }
        )

        items = response.get('Items', [])
        
        stock_data = [
            {
                "stock_id": item['stock_id']['S'],
                "date": item['date']['S'],
                "opening_price": float(item['opening_price']['N']),
                "closing_price": float(item['closing_price']['N']),
                "low_price": float(item['low_price']['N']),
                "high_price": float(item['high_price']['N']),
                "volume": int(item['volume']['N'])
            }
            for item in items
        ]

        return pd.DataFrame(stock_data)

    except ClientError as e:
        print(f"DynamoDB Query Error: {str(e)}")
        return pd.DataFrame()

# Compute stock metrics including trend analysis
def compute_stock_metrics(df, df_trend):
    if df.empty or df_trend.empty:
        return pd.DataFrame()

    # Compute daily price change
    df['price_change'] = df['closing_price'] - df['opening_price']

    # Monthly trends
    trend_analysis = df_trend.groupby('stock_id').agg(
        avg_price_change=("closing_price", lambda x: x.diff().mean()),  # Avg daily price change
        avg_volume=("volume", "mean"),  # Avg trading volume over 30 days
        high_30d=("high_price", "max"),  # Highest price in last 30 days
        low_30d=("low_price", "min")  # Lowest price in last 30 days
    ).reset_index()

    # Compute daily metrics
    daily_metrics = df[['stock_id', 'price_change', 'closing_price', 'volume']]

    # Merge daily and trend metrics
    result = daily_metrics.merge(trend_analysis, on='stock_id', how='left')

    return result.fillna(0)

# Create email template
def format_email_body(df, today):
    email_body = f"Daily Stock & 30-Day Trend Metrics for {today}\n\n"
    email_body += "--------------------------------------------\n"

    for _, row in df.iterrows():

        email_body += (
            f"Stock ID: {row['stock_id']}\n"
            f"Today's Price Change: {row['price_change']:.2f}\n"
            f"Today's Closing Price: {row['closing_price']:.2f}\n"
            f"Today's Volume: {int(row['volume']):,}\n"
            f"Avg Daily Price Change (30d): {row['avg_price_change']:.2f}\n"
            f"Avg Volume (30d): {int(row['avg_volume']):,}\n"
            f"30-Day High: {row['high_30d']:.2f}\n"
            f"30-Day Low: {row['low_30d']:.2f}\n"
            "--------------------------------------------\n"
        )
    
    return email_body

# Send email via SNS
def send_email(body):
    try:
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message=body,
            Subject="Daily & 30-Day Stock Metrics"
        )
        print("Email sent successfully!")
    except ClientError as e:
        print(f"SNS Error: {str(e)}")

def lambda_handler(event, context):
    today = datetime(2025, 1, 31)  # Change back to datetime.today() after demo
    start_date = today - timedelta(days=30)

    # Convert to string for DynamoDB queries
    today_str = today.strftime('%Y-%m-%d')
    start_date_str = start_date.strftime('%Y-%m-%d')

    # Fetch data
    df_today = fetch_stock_data(today_str, today_str)
    df_trend = fetch_stock_data(start_date_str, today_str)

    # Compute metrics
    df_metrics = compute_stock_metrics(df_today, df_trend)

    # Generate email and send report
    email_body = format_email_body(df_metrics, today_str)
    send_email(email_body)

    return {
        "date": today_str,
        "metrics": df_metrics.to_dict(orient="records")
    }
