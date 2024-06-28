import requests
import base64

# Define variables
owner = 'repository-owner'
repo = 'repository-name'
file_path = 'path/to/file.txt'
branch = 'main'  # or any specific branch you want to target

# Construct the URL for the GitHub API
url = f'https://api.github.com/repos/{owner}/{repo}/contents/{file_path}?ref={branch}'

# Construct the URL for the GitHub API
url = f'https://api.github.com/repos/{owner}/{repo}/branches'

# Make the API request with authentication
response = requests.get(url, headers=headers)

# Check if the request was successful
if response.status_code == 200:
    branches = response.json()
    for branch in branches:
        print(branch['name'])
else:
    print(f"Error: {response.status_code}")
    print(response.json())

# Make the API request
# response = requests.get(url)
# Define your personal access token
access_token = 'your_personal_access_token'

# Include the token in the request headers
headers = {
    'Authorization': f'token {access_token}'
}

# Make the API request with authentication
response = requests.get(url, headers=headers)


# Check if the request was successful
if response.status_code == 200:
    file_info = response.json()
    file_content = base64.b64decode(file_info['content']).decode('utf-8')
    print(file_content)
else:
    print(f"Error: {response.status_code}")
    print(response.json())


import requests

# Define variables
owner = 'repository-owner'
repo = 'repository-name'
access_token = 'your_personal_access_token'  # optional if accessing private repos or to increase rate limits

# Construct the initial URL for the GitHub API
url = f'https://api.github.com/repos/{owner}/{repo}/branches'
headers = {
    'Authorization': f'token {access_token}'
} if access_token else {}

branches = []

while url:
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        branches.extend(response.json())
        # Check for pagination
        if 'next' in response.links:
            url = response.links['next']['url']
        else:
            url = None
    else:
        print(f"Error: {response.status_code}")
        print(response.json())
        break

# Print all branches
for branch in branches:
    print(branch['name'])
