# NSSM Service Manager API 🚀  

![GitHub Repo](https://img.shields.io/badge/GitHub-Repository-blue)  

A FastAPI-based RESTful API to manage Windows services installed via **NSSM (Non-Sucking Service Manager)**. This API allows listing, installing, starting, stopping, restarting, and removing NSSM-managed services.  

## ⚠️ WARNING: USE AT YOUR OWN RISK ⚠️  
This API **exposes service installation, modification, and execution via a web interface**. **DO NOT USE** this if you **do not fully understand the security risks** involved.  
- Running this API on a publicly accessible server **can allow unauthorized users to install or control services**.  
- It is **strongly recommended** to restrict access using a firewall, authentication, or a private network.  
- Use only in **controlled environments** where security measures are in place.  

## 📌 Features  

- List all NSSM-installed services.  
- Retrieve service details (executable path, startup directory, arguments, and status).  
- Get status of a single service.  
- Check if a service exists.  
- Install a new Windows service using NSSM.  
- Start, stop, and restart NSSM services.  
- Remove services.  
- Health check endpoint.

## 🛠 Requirements  

- **Python 3.8+**  
- **Windows OS** (NSSM is Windows-only)  
- **NSSM (Non-Sucking Service Manager)**  
- **Administrator privileges** (to modify Windows services)  

## 📦 Installation  

1. **Clone the repository**  
   ```sh
   git clone https://github.com/phintegrator/nssm_service_manager.git
   cd nssm_service_manager
   ```  

2. **Install dependencies**  
   ```sh
   pip install -r requirements.txt
   ```  

3. **Ensure NSSM is installed and accessible in your system `PATH`**  
   - Download NSSM from [https://nssm.cc/download](https://nssm.cc/download)  
   - Extract and move `nssm.exe` to a directory in your system's `PATH`  
   - Test installation:  
     ```sh
     nssm --version
     ```  

## 🚀 Usage  

### Start the API Server  
Run the following command to start the API:  
```sh
python fastapi_nssm.py
```  
By default, the server runs on `http://127.0.0.1:54321/`.  

### API Endpoints  

| Method   | Endpoint                            | Description                      |
|----------|-------------------------------------|----------------------------------|
| `GET`    | `/health`                           | Health check                     |
| `GET`    | `/services`                         | List all NSSM-managed services   |
| `GET`    | `/services/{service_name}`          | Get details of a specific service|
| `GET`    | `/services/{service_name}/status`   | Get status of a service          |
| `GET`    | `/services/{service_name}/exists`   | Check if a service exists        |
| `POST`   | `/services`                         | Install a new service            |
| `POST`   | `/services/{service_name}/start`    | Start a service                  |
| `POST`   | `/services/{service_name}/stop`     | Stop a service                   |
| `POST`   | `/services/{service_name}/restart`  | Restart a service                |
| `DELETE` | `/services/{service_name}`          | Remove a service                 |

### Example API Calls  

#### ✅ Health check  
```sh
curl -X GET "http://127.0.0.1:54321/health"
```  

#### ✅ List all NSSM services  
```sh
curl -X GET "http://127.0.0.1:54321/services" -H "accept: application/json"
```  

#### ✅ Get details of a specific service  
```sh
curl -X GET "http://127.0.0.1:54321/services/MyService"
```  

#### ✅ Get status of a service  
```sh
curl -X GET "http://127.0.0.1:54321/services/MyService/status"
```  

#### ✅ Check if a service exists  
```sh
curl -X GET "http://127.0.0.1:54321/services/MyService/exists"
```  

#### ✅ Install a new NSSM service  
```sh
curl -X POST "http://127.0.0.1:54321/services" \
-H "Content-Type: application/json" \
-d '{
  "service_name": "MyService",
  "executable_path": "C:\\path\\to\\app.exe",
  "startup_directory": "C:\\path\\to",
  "arguments": "--arg1 value1 --arg2 value2"
}'
```  

#### ✅ Start a service  
```sh
curl -X POST "http://127.0.0.1:54321/services/MyService/start"
```  

#### ✅ Stop a service  
```sh
curl -X POST "http://127.0.0.1:54321/services/MyService/stop"
```  

#### ✅ Restart a service  
```sh
curl -X POST "http://127.0.0.1:54321/services/MyService/restart"
```  

#### ✅ Remove a service  
```sh
curl -X DELETE "http://127.0.0.1:54321/services/MyService"
```  

## ⚠️ Notes  
- This API **requires administrator privileges** to modify services.  
- Ensure **NSSM is installed and in your system PATH** before running the API.  
- NSSM is used for managing long-running services, such as background tasks, web servers, and monitoring tools.  

## 📄 License  
This project is licensed under the MIT License.  

## 🏆 Credits  
Developed by **[Phintegrator](https://github.com/phintegrator)**.  
Inspired by the need for a simple, scriptable service manager using NSSM.  

---
💡 **Pull requests are welcome!** If you find a bug or have a feature request, feel free to contribute. 🎯