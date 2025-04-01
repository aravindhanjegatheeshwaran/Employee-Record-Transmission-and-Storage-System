#!/usr/bin/env python
"""
WebSocket Connection Test Script for Employee Record System

This script tests the WebSocket connection to the server.
"""

import asyncio
import websockets
import json
import argparse
import sys

async def test_websocket(ws_url, token):
    """Test WebSocket connection and send a test message."""
    try:
        print(f"Connecting to WebSocket at {ws_url}")
        headers = {"Authorization": f"Bearer {token}"}
        
        async with websockets.connect(ws_url, extra_headers=headers) as websocket:
            print("WebSocket connected successfully!")
            
            # Send a test message
            test_data = {
                "employee_id": "TEST123",
                "first_name": "Test",
                "last_name": "User",
                "email": "test@example.com",
                "department": "IT",
                "salary": 75000
            }
            
            print(f"Sending test data: {test_data}")
            await websocket.send(json.dumps(test_data))
            
            # Wait for response
            print("Waiting for response...")
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            print(f"Received response: {response}")
            
            return True
    except Exception as e:
        print(f"WebSocket test failed: {str(e)}")
        return False

async def get_token(server_url, username, password):
    """Get authentication token from server."""
    import aiohttp
    
    try:
        print(f"Getting authentication token from {server_url}/token")
        async with aiohttp.ClientSession() as session:
            form_data = {
                "username": username,
                "password": password,
            }
            
            async with session.post(
                f"{server_url}/token", 
                data=form_data,
                timeout=10.0
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    print(f"Auth failed: {response.status} - {error_text}")
                    return None
                
                result = await response.json()
                token = result.get("access_token")
                
                if not token:
                    print("No token received")
                    return None
                
                print("Authentication successful")
                return token
    except Exception as e:
        print(f"Auth error: {str(e)}")
        return None

async def main():
    parser = argparse.ArgumentParser(description='Test WebSocket connection')
    parser.add_argument('--server', type=str, default="http://localhost:8000", 
                      help='Server URL (default: http://localhost:8000)')
    parser.add_argument('--ws', type=str, default=None,
                      help='WebSocket URL (default: derived from server URL)')
    parser.add_argument('--username', type=str, default="admin",
                      help='Auth username (default: admin)')
    parser.add_argument('--password', type=str, default="adminpassword",
                      help='Auth password (default: adminpassword)')
    
    args = parser.parse_args()
    
    # Derive WebSocket URL if not provided
    ws_url = args.ws
    if not ws_url:
        server_host = args.server.replace("http://", "").replace("https://", "").split("/")[0]
        ws_url = f"ws://{server_host}/ws"
    
    print(f"Server URL: {args.server}")
    print(f"WebSocket URL: {ws_url}")
    
    # Get authentication token
    token = await get_token(args.server, args.username, args.password)
    if not token:
        print("Failed to get authentication token")
        return 1
    
    # Test WebSocket connection
    success = await test_websocket(ws_url, token)
    
    return 0 if success else 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("Process interrupted by user")
        sys.exit(1)