from fastapi import FastAPI, HTTPException
import winreg
import subprocess
from typing import Optional
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="NSSM Service Manager API")

# 📌 Request Model for Installing a Service
class ServiceInstallRequest(BaseModel):
    service_name: str
    executable_path: str
    startup_directory: str
    arguments: Optional[str] = ""

# 📌 Helper Function: Remove Null Characters
def clean_unicode_string(value: str) -> str:
    """Removes null characters and trims whitespace."""
    return value.replace("\u0000", "").strip() if value else "N/A"

# 📌 Get Service Executable Path from Registry
def get_service_path(service_name: str) -> str:
    try:
        key_path = fr"SYSTEM\CurrentControlSet\Services\{service_name}"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            image_path, _ = winreg.QueryValueEx(key, "ImagePath")
            return clean_unicode_string(image_path)
    except:
        return "N/A"

# 📌 Get Service Status
def get_service_status(service_name: str) -> str:
    try:
        result = subprocess.run(
            ["nssm", "status", service_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return clean_unicode_string(result.stdout.strip()) if result.returncode == 0 else "Unknown"
    except Exception as e:
        return f"Error: {str(e)}"

# 📌 Get Service Details
def get_service_details(service_name: str) -> dict:
    """Retrieve detailed information about a service using NSSM."""
    details = {}
    try:
        details["Path"] = get_service_path(service_name)

        result_startup_dir = subprocess.run(
            ["nssm", "get", service_name, "AppDirectory"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        details["Startup Directory"] = clean_unicode_string(result_startup_dir.stdout.strip()) if result_startup_dir.returncode == 0 else "N/A"

        result_arguments = subprocess.run(
            ["nssm", "get", service_name, "AppParameters"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        details["Arguments"] = clean_unicode_string(result_arguments.stdout.strip()) if result_arguments.returncode == 0 else "N/A"

        details["Status"] = get_service_status(service_name)

    except Exception as e:
        print(f"Error retrieving details for service '{service_name}': {str(e)}")

    return details

# 📌 List All NSSM Services
def list_nssm_services():
    try:
        services_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services")
        nssm_services = []
        i = 0
        while True:
            try:
                service_name = winreg.EnumKey(services_key, i)
                service_path = get_service_path(service_name)
                if service_path and "nssm.exe" in service_path.lower():
                    nssm_services.append(service_name)
                i += 1
            except OSError:
                break  # No more services

        services_details = []
        for service_name in nssm_services:
            services_details.append({
                "service_name": service_name,
                **get_service_details(service_name)
            })

        return services_details

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing NSSM services: {str(e)}")

# 📌 API Route: List All Services
@app.get("/services", summary="List all NSSM services")
def get_services():
    services = list_nssm_services()
    if not services:
        raise HTTPException(status_code=404, detail="No NSSM services found")
    return {"services": services}

# 📌 API Route: Install a New Service
@app.post("/services", summary="Install a new NSSM service")
def install_service(request: ServiceInstallRequest):
    try:
        install_service_command = ["nssm", "install", request.service_name, request.executable_path]
        if request.arguments:
            install_service_command.append(request.arguments)

        subprocess.run(install_service_command)
        subprocess.run(["nssm", "set", request.service_name, "AppDirectory", request.startup_directory])
        return {"message": f"Service '{request.service_name}' installed successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error installing service: {str(e)}")

# 📌 API Route: Start a Service
@app.post("/services/{service_name}/start", summary="Start a service")
def start_service(service_name: str):
    try:
        result = subprocess.run(["nssm", "start", service_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            return {"message": f"Service '{service_name}' started successfully."}
        else:
            raise HTTPException(status_code=500, detail=result.stderr.strip())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting service: {str(e)}")

# 📌 API Route: Stop a Service
@app.post("/services/{service_name}/stop", summary="Stop a service")
def stop_service(service_name: str):
    try:
        result = subprocess.run(["nssm", "stop", service_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            return {"message": f"Service '{service_name}' stopped successfully."}
        else:
            raise HTTPException(status_code=500, detail=result.stderr.strip())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error stopping service: {str(e)}")

# 📌 API Route: Remove a Service
@app.delete("/services/{service_name}", summary="Remove a service")
def remove_service(service_name: str):
    try:
        result = subprocess.run(["nssm", "remove", service_name, "confirm"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            return {"message": f"Service '{service_name}' removed successfully."}
        else:
            raise HTTPException(status_code=500, detail=result.stderr.strip())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error removing service: {str(e)}")

# 📌 Integrated Uvicorn in __main__
if __name__ == "__main__":
    print("\n🚀 Starting NSSM Service Manager API on http://127.0.0.1:8000/")
    uvicorn.run(app, host="0.0.0.0", port=54321)
