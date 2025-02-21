
# LinkedIn Profile API Documentation

## Overview
This project is a FastAPI-based service that provides LinkedIn profile and company search capabilities through a RESTful API interface. It uses multiple search services to gather LinkedIn profile information and provides both synchronous and streaming responses.

## Requirements

### Hardware Requirements
- Minimum 2GB RAM
- 2 CPU cores
- 10GB storage space

### Software Requirements
- Python 3.9 or higher
- Docker (optional for containerized deployment)
- SQLite3
- Internet connection for API calls

### API Keys Required
- LinkedIn account credentials
- Serper.dev API key
- Google Custom Search API key (optional)

## Setup Instructions

### Local Development Setup

1. Clone the repository:
    ```bash
    git clone <repository-url>
    cd linkedin_profile_api
    ```

2. Create and activate virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # For Unix
    venv\Scripts\activate     # For Windows
    ```

3. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

4. Configure environment variables:
- Copy `.env.example` to `.env`
- Fill in the required credentials:

        LINKEDIN_EMAIL="Your_LinkedIn_Email"
        LINKEDIN_PASSWORD="Your_LinkedIn_Password"
        GOOGLE_SEARCH_ENGINE_APIKEY="Your_Google_API_Key"
        SERPER_API_KEY="Your_Serper_API_Key"


5. Run the application:
    ```bash
    python main.py
    ```

### Docker Deployment

1. Build the Docker image:
    ```bash
    docker build -t linkedin-profile-api .
    ```

2. Run the container:
    ```bash
    docker run -d -p 8000:8000 \
    -e LINKEDIN_EMAIL="Your_Email" \
    -e LINKEDIN_PASSWORD="Your_Password" \
    -e SERPER_API_KEY="Your_API_Key" \
    -e GOOGLE_SEARCH_ENGINE_APIKEY="Your_API_Key" \
    linkedin-profile-api
    ```

## Server Deployment

### Prerequisites
- Ubuntu 20.04 LTS or higher
- Python 3.9+
- Nginx (for production deployment)

### Production Deployment Steps

1. Set up the server:
    ```bash
    sudo apt update
    sudo apt install python3.9 python3.9-venv python3-pip nginx
    ```

2. Create application directory:
    ```bash
    sudo mkdir /opt/linkedin-profile-api
    sudo chown $USER:$USER /opt/linkedin-profile-api
    ```

3. Clone and setup the application:
    ```bash
    cd /opt/linkedin-profile-api
    git clone <repository-url> .
    python3.9 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

4. Create systemd service:
    ```bash
    sudo nano /etc/systemd/system/linkedin-api.service
    ```

    Add the following content:

    ```toml
    [Unit]
    Description=LinkedIn Profile API
    After=network.target

    [Service]
    User=<your-user>
    WorkingDirectory=/opt/linkedin-profile-api
    Environment="PATH=/opt/linkedin-profile-api/venv/bin"
    EnvironmentFile=/opt/linkedin-profile-api/.env
    ExecStart=/opt/linkedin-profile-api/venv/bin/python main.py

    [Install]
    WantedBy=multi-user.target
    ```

5. Configure Nginx:
    ```bash
    sudo nano /etc/nginx/sites-available/linkedin-api
    ```

Add the following configuration:


```
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

6. Enable and start services:
    ```bash
    sudo ln -s /etc/nginx/sites-available/linkedin-api /etc/nginx/sites-enabled/
    sudo systemctl start linkedin-api
    sudo systemctl enable linkedin-api
    sudo systemctl restart nginx
    ```

## API Endpoints

### 1. Search Profiles/Companies
- **Endpoint**: `/search`
- **Method**: GET
- **Parameters**: 
  - query (string): Search query
  - type (string): "profile" or "company"

### 2. Streaming Search
- **Endpoint**: `/stream`
- **Method**: GET
- **Parameters**: 
  - query (string): Search query
  - type (string): "profile" or "company"

### 3. Queue Search Task
- **Endpoint**: `/queue`
- **Method**: GET
- **Parameters**: 
  - query (string): Search query
  - type (string): "profile" or "company"

### 4. Get Tasks Status
- **Endpoint**: `/tasks`
- **Method**: GET

## Data Storage
The application uses SQLite for storing:
- Search history
- Task status and results
- Database location: `data/tasks.db`

## Monitoring and Maintenance

### Logs
- Application logs: Standard output (captured by systemd)
- Nginx logs: 
  - `/var/log/nginx/access.log`
  - `/var/log/nginx/error.log`

### Backup
Regular backup of the SQLite database is recommended:

```bash
cp /opt/linkedin-profile-api/data/tasks.db /backup/tasks_$(date +%Y%m%d).db
```

### Security Considerations
- Keep API keys secure
- Use HTTPS in production
- Implement rate limiting
- Regular security updates
- Monitor API usage and costs

## Troubleshooting

Common issues and solutions:
1. API Connection Issues:
   - Check API credentials
   - Verify network connectivity
   - Check API service status

2. Database Issues:
   - Verify write permissions
   - Check disk space
   - Backup and restore if corrupted

3. Performance Issues:
   - Monitor memory usage
   - Check CPU utilization
   - Review concurrent connections


## PHP Integration Examples

### Basic Search Request
```php
<?php
$query = urlencode("John Doe");
$type = "profile";
$url = "http://your-api-domain.com/search?query={$query}&type={$type}";

$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $url);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

$response = curl_exec($ch);
$data = json_decode($response, true);

if ($data['success']) {
    foreach ($data['data']['items'] as $profile) {
        echo "Name: " . $profile['name'] . "\n";
        echo "Title: " . $profile['title'] . "\n";
    }
}

curl_close($ch);
```

### Streaming Response Handler
```php
<?php
$query = urlencode("Directors Davienda");
$type = "profile";
$url = "http://your-api-domain.com/stream?query={$query}&type={$type}";

$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $url);
curl_setopt($ch, CURLOPT_WRITEFUNCTION, function($ch, $data) {
    $result = json_decode($data, true);
    if ($result && $result['success']) {
        foreach ($result['data'] as $item) {
            echo "Name: " . $item['name'] . "\n";
            echo "Title: " . $item['title'] . "\n";
            echo "Company: " . $item['company'] . "\n";
            echo "Location: " . $item['location'] . "\n";
            echo "Profile URL: " . $item['profile_url'] ."\n";
            echo "-------------------\n";
        }
    }
    return strlen($data);
});
curl_exec($ch);
curl_close($ch);
```

### Queue Task and Check Status
```php
<?php
// Queue a task
$query = urlencode("Albin Aimleap");
$type = "profile";
$url = "http://your-api-domain.com/queue?query={$query}&type={$type}";

$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $url);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

$response = curl_exec($ch);
$data = json_decode($response, true);
curl_close($ch);

if ($data['success']) {
    $taskId = $data['data']['task_id'];
    
    // Check task status
    $statusUrl = "http://your-api-domain.com/tasks";
    
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $statusUrl);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    
    $response = curl_exec($ch);
    $tasks = json_decode($response, true);
    
    foreach ($tasks['data']['tasks'] as $task) {
        if ($task['task_id'] === $taskId) {
            echo "Task Status: " . $task['status'] . "\n";
            if ($task['status'] === 'completed') {
                print_r($task['output']);
            }
        }
    }
    
    curl_close($ch);
}
```

### Error Handling Example
```php
<?php
function makeApiRequest($url) {
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 10);
    curl_setopt($ch, CURLOPT_TIMEOUT, 30);
    
    $response = curl_exec($ch);
    $error = curl_error($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    
    curl_close($ch);
    
    if ($error) {
        throw new Exception("API Request failed: " . $error);
    }
    
    if ($httpCode !== 200) {
        throw new Exception("API returned error code: " . $httpCode);
    }
    
    $data = json_decode($response, true);
    if (!$data['success']) {
        throw new Exception("API returned error: " . $data['message']);
    }
    
    return $data;
}

try {
    $query = urlencode("Developer");
    $url = "http://your-api-domain.com/search?query={$query}&type=profile";
    $result = makeApiRequest($url);
    print_r($result['data']);
} catch (Exception $e) {
    echo "Error: " . $e->getMessage() . "\n";
}
```