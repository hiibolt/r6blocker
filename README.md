# R6 Blocked Player Monitor

This Discord bot monitors blocked players on Rainbow Six Siege (R6). Whenever a player is blocked, it prints their status including their rank, KD (Kill/Death ratio), WL (Win/Loss ratio), and provides a link to their R6 Tracker profile.

## Setup

1. Clone this repository.

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the root directory and add the following variables:
   ```plaintext
   AUTH_EMAIL=your_email
   AUTH_PW=your_password
   TOKEN=your_discord_bot_token
   CHANNEL_ID=your_discord_channel_id
   ```

4. Ensure you have Python 3.7 or later installed.

5. Run the bot:
   ```bash
   python main.py
   ```

## Bot Functionality

- The bot connects to Rainbow Six Siege services and listens for blocked player notifications.
- When a player is blocked, it retrieves their profile information including rank, KD, WL, etc.
- It sends an embedded message to the designated Discord channel with the player's information and a link to their R6 Tracker profile.

## Usage

Simply add the bot to your Discord server and ensure it has permissions to read messages in the designated channel. Once running, it will automatically monitor and notify about blocked players.

## Credits

This bot is created and maintained by [@hiibolt](https://github.com/hiibolt). Many thanks to @Ubi-frax on Twitter for their help!

## Disclaimer

This project is not affiliated with Rainbow Six Siege or Ubisoft. Use it responsibly and in accordance with Discord's terms of service.
