# attack_crawler.py
import os
import asyncio
import websockets
import requests
# Import your custom modular parser
from parser import parse_attack_payload

WEBSOCKET_URI = os.getenv("WEBSOCKET_URI", "ws://localhost:5002/stream")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
TEAM_IDENTIFIER = os.getenv("TEAM_IDENTIFIER", "OurTeam")

async def watch_attacks():
    if not DISCORD_WEBHOOK_URL:
        print("CRITICAL: DISCORD_WEBHOOK_URL environment variable is missing!")
        return

    print(f"Connecting to Attack Map stream at {WEBSOCKET_URI}...")
    
    async for websocket in websockets.connect(WEBSOCKET_URI):
        try:
            print("Connected to stream successfully.")
            async for message in websocket:
                
                # Hand over processing completely to your parser module
                alert_data = parse_attack_payload(message, TEAM_IDENTIFIER)
                
                # If the parser flags a match, fire the webhook
                if alert_data:
                    send_to_discord(alert_data)
                    
        except websockets.ConnectionClosed:
            print("Connection lost. Reconnecting in 5 seconds...")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"Error in engine loop: {e}")
            await asyncio.sleep(5)

def send_to_discord(alert_data):
    payload = {
        "embeds": [{
            "title": "DEFENSE LOG",
            "color": 15158332,
            "description": f"Our team (**{TEAM_IDENTIFIER}**) is taking hits!",
            "fields": [
                {"name": "Attacker", "value": f"`{alert_data['attacker']}`", "inline": True},
                {"name": "Vulnerable Service", "value": f"`{alert_data['service']}`", "inline": True},
            ],
            "footer": {"text": "Attack Map Monitor"}
        }]
    }
    
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        if response.status_code != 204:
            print(f"Discord error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Failed sending alert to Discord: {e}")

if __name__ == "__main__":
    asyncio.run(watch_attacks())