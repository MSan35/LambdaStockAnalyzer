import json
import boto3
import os
from botocore.exceptions import ClientError
from datetime import datetime

dynamodb = boto3.client("dynamodb", region_name=os.getenv('AWS_REGION', 'us-east-2'))
sns = boto3.client('sns', region_name=os.getenv('AWS_REGION', 'us-east-2'))
# SNS_TOPIC_ARN = 

def lambda_handler(event, context):
        
    table_name = "stock_prices"
    stock_symbols = [
        'NVDA',  # Nvidia
        'AAPL',  # Apple
        'MSFT',  # Microsoft
        'AMZN',  # Amazon
        'META',  # Meta
        'GOOGL',  # Google
        'TSLA',  # Tesla
        'AVGO',  # Broadcom
        'V',  # Visa
        'MA',  # Mastercard
        'RY',  # Royal Bank of Canada
        'TD',  # Toronto-Dominion Bank
        'BMO',  # Bank of Montreal
        'BCE',  # Bell
        'T.TO'  # Telus
    ]

    metrics = []
    today = datetime.today().strftime('%Y-%m-%d')

    price_change_query = f"""SELECT stock_id, closing_price, opening_price, volume FROM stock_prices WHERE "date" = ?"""

    # price change for each stock
    try:
        response = dynamodb.execute_statement(
            Statement=price_change_query,
            Parameters=[{'S': today}]
        )
        
        items = response.get('Items', [])
        
        for item in items:
            stock_id = item['stock_id']['S']
            opening_price = float(item['opening_price']['N'])
            closing_price = float(item['closing_price']['N'])
            daily_volume = float(item['volume']['N'])
            
            price_change = closing_price - opening_price
            
            metrics.append({
                "stock_id": stock_id,
                "price_change": price_change,
                "volume": daily_volume
            })
    
    except ClientError as e:
        print(f"ClientError in price change query: {str(e)}")
    except Exception as e:
        print(f"Error in price change query: {str(e)}")

    # minimum price for each stock
    try:
        for symbol in stock_symbols:
            minimum_price_query = f"""SELECT low_price FROM stock_prices."stock_id-low_price-index" WHERE stock_id = ? ORDER BY low_price"""

            response = dynamodb.execute_statement(
                Statement=minimum_price_query,
                Parameters=[{'S': symbol}]
            )

            low_price_items = response.get('Items', [])
            all_time_low_price = float(low_price_items[0]['low_price']['N']) if low_price_items else None
            
            metrics.append({
                "stock_id": symbol,
                "all_time_low_price": all_time_low_price
            })
        
    except ClientError as e:
        print(f"ClientError: {str(e)}")
    except Exception as e:
        print(f"Error: {str(e)}")

    # average volume for each stock
    try:
        for symbol in stock_symbols:
            avg_volume_query = f"""SELECT volume FROM stock_prices."stock_id-volume-index" WHERE stock_id = ?"""
            
            response = dynamodb.execute_statement(
                Statement=avg_volume_query,
                Parameters=[{'S': symbol}]
            )
            
            volume_items = response.get('Items', [])
            if volume_items:
                total_volume = sum(float(item['volume']['N']) for item in volume_items)
                average_volume = total_volume / len(volume_items)
            else:
                average_volume = None
            
            metrics.append({
                "stock_id": symbol,
                "average_volume": average_volume
            })
        
    except ClientError as e:
        print(f"ClientError in average volume query: {str(e)}")
    except Exception as e:
        print(f"Error in average volume query: {str(e)}")

    # publish results to SNS
    try:

        email_body = f"Daily Stock Metrics for {today}\n\n"
        email_body += "--------------------------------------------\n"
        
        stock_data = {}

        for metric in metrics:
            stock_id = metric.get('stock_id', 'N/A')

            if stock_id not in stock_data:
                stock_data[stock_id] = {
                    'price_change': 0,
                    'volume': 0,
                    'average_volume': 0,
                    'all_time_low_price': 0
                }
        
            if 'price_change' in metric:
                stock_data[stock_id]['price_change'] = metric['price_change']
            if 'volume' in metric:
                stock_data[stock_id]['volume'] = metric['volume']
            if 'average_volume' in metric:
                stock_data[stock_id]['average_volume'] = metric['average_volume']
            if 'all_time_low_price' in metric:
                stock_data[stock_id]['all_time_low_price'] = metric['all_time_low_price']
        
        for stock_id, data in stock_data.items():
            price_change = f"{data.get('price_change', 0):.2f}"
            volume = int(data.get('volume', 0))
            avg_volume = int(data.get('average_volume', 0))
            all_time_low_price = f"{data.get('all_time_low_price', 0):.2f}"

            email_body += f"Stock ID: {stock_id}\n"
            email_body += f"Price Change: {price_change}\n"
            email_body += f"Volume: {volume}\n"
            email_body += f"Average Volume: {avg_volume}\n"
            email_body += f"All-Time Low Price: {all_time_low_price}\n"
            email_body += "--------------------------------------------\n"
        
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message=email_body,
            Subject="Daily Stock Metrics"
        )
        print("Email sent successfully!")

    except ClientError as e:
        print(f"Error in sending SNS message: {str(e)}")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")

    return {
        "date": today,
        "metrics": metrics
    }
