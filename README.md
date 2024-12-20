# LambdaStockAnalyzer

### Overview
This is an AWS Lambda project designed to analyze and monitor a user-defined portfolio of stocks. Each day, the Lambda function queries a DynamoDB table to retrieve and calculate key stock metrics, then emails the results to the user using SNS. This project provides insights into stock performance, including daily price changes, volume comparisons and all-time low prices. All tools used are encompassed in the AWS always free tier.

### Tech Stack
- AWS Lambda
- AWS DynamoDB
- AWS SNS
- Amazon EventBridge
- Python 3.13

### Files
- lambdaFunction.py: Main lambda function that runs on an EventBridge schedule every weekday at 8pm.
- ingestion.ipynb: Data ingestion for the initial set of stock data in the form of a JSON file (stock_prices_data.json).
- dailyIngestion.ipynb: Gets the current day's stock data in a JSON file (today_stock_prices_data.json).
- dynamodbImporter.ipynb: Imports data from JSON file to dynamoDB table.

### Database
- DynamoDB table with partition key: price_id and sort key: date.
- 2 secondary indexes: stock_id-low_price-index and stock_id-volume-index

