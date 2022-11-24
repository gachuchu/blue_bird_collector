@echo off
cd /d %~dp0

call venv\Scripts\activate.bat & py blue_bird_collector.py "twitter.csv" "twitter_result.csv"
