#!/usr/bin/env bash
set -e
echo "Updating and installing system dependencies..."
sudo apt update
sudo apt install -y nmap python3-pip python3-venv libpcap-dev python3-tk
echo "Installing Npcap/WinPcap is required on Windows. Install Wireshark if needed."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo "Done. Fill config.json paths if any tools are installed in custom locations."
