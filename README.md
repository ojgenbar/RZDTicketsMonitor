# RZD Tickets Monitor

This is RZD Tickets monitor.

## Run as Telegram bot

1. Install `Python 3.7+` and `requirements.txt`: 

         python3.7 -m venv venv
         source venv/bin/activate
         pip install -r requirements.txt

1. Also you need to set env variables:
    *   `RZD_TICKETS_MONITOR_BOT_TOKEN`=*BOT_TOKEN*
    *   `RZD_TICKETS_MONITOR_BOT_PROXY`=*SOCKS5 or HTTP proxy*

1. Start bot (with env variables):

       RZD_TICKETS_MONITOR_BOT_TOKEN=... \
       RZD_TICKETS_MONITOR_BOT_PROXY=... \
       python  run_bot.py

## Run as terminal app
1. Show help:

        python run_terminal.py -h
         
1. Run: 

        python  run_terminal.py \
        --type Купе --count 2 \
        2004000 2000000 001А 31.01.2020
