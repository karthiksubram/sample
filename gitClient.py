import requests
import base64

# Define variables
owner = 'repository-owner'
repo = 'repository-name'
file_path = 'path/to/file.txt'
branch = 'main'  # or any specific branch you want to target

# Construct the URL for the GitHub API
url = f'https://api.github.com/repos/{owner}/{repo}/contents/{file_path}?ref={branch}'

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

