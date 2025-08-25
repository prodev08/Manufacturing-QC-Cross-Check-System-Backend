#!/usr/bin/env python3
"""
Simple test script to verify API endpoints are working.
Run this after starting the FastAPI server.
"""

import requests
import json
from pathlib import Path


def test_api_endpoints():
    """Test basic API endpoints"""
    base_url = 'http://localhost:8000'
    api_url = f'{base_url}/api/v1'
    
    print('Testing QC System API...\n')
    
    # Test health check
    print('1. Testing health check...')
    try:
        response = requests.get(f'{base_url}/')
        if response.status_code == 200:
            print('   ✅ Health check passed')
            print(f'   Response: {response.json()}')
        else:
            print(f'   ❌ Health check failed: {response.status_code}')
    except Exception as e:
        print(f'   ❌ Health check error: {e}')
    
    print()
    
    # Test create session
    print('2. Testing session creation...')
    try:
        response = requests.post(f'{api_url}/sessions/', json={})
        if response.status_code == 201:
            session_data = response.json()
            session_id = session_data['id']
            print('   ✅ Session created successfully')
            print(f'   Session ID: {session_id}')
            
            # Test get session
            print('3. Testing session retrieval...')
            response = requests.get(f'{api_url}/sessions/{session_id}')
            if response.status_code == 200:
                print('   ✅ Session retrieved successfully')
                print(f'   Session: {json.dumps(response.json(), indent=2, default=str)}')
            else:
                print(f'   ❌ Session retrieval failed: {response.status_code}')
                
        else:
            print(f'   ❌ Session creation failed: {response.status_code}')
            print(f'   Error: {response.text}')
            
    except Exception as e:
        print(f'   ❌ Session test error: {e}')
    
    print()
    
    # Test list sessions
    print('4. Testing session list...')
    try:
        response = requests.get(f'{api_url}/sessions/')
        if response.status_code == 200:
            sessions_data = response.json()
            print('   ✅ Session list retrieved successfully')
            print(f'   Total sessions: {sessions_data["total"]}')
        else:
            print(f'   ❌ Session list failed: {response.status_code}')
    except Exception as e:
        print(f'   ❌ Session list error: {e}')
    
    print('\nAPI test completed!')


if __name__ == '__main__':
    test_api_endpoints()
