from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import winreg
import subprocess
import os
from typing import Optional
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="NSSM Service Manager API", version="1.1.0")

BLOCK_STOP_DELETE_ACTIONS = (
    os.getenv("NSSM_BLOCK_STOP_DELETE_ACTIONS", "true").strip().lower()
    not in {"0", "false", "no"}
)

# ✅ Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this to a specific domain in production
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)


# 📌 Request Model for Installing a Service
class ServiceInstallRequest(BaseModel):
    service_name: str
    executable_path: str
    startup_directory: str
    arguments: Optional[str] = ""


class LogPathRequest(BaseModel):
    path: str


class LogRotationRequest(BaseModel):
    enabled: bool
    rotate_bytes: Optional[int] = None
    rotate_files: Optional[int] = None


# 📌 Helper Function: Remove Null Characters
def clean_unicode_string(value: str) -> str:
    """Removes null characters and trims whitespace."""
    return value.replace("\u0000", "").strip() if value else "N/A"


# 📌 Get Service Executable Path from Registry
def get_service_path(service_name: str) -> str:
    try:
        key_path = rf"SYSTEM\CurrentControlSet\Services\{service_name}"
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
            text=True,
        )
        return (
            clean_unicode_string(result.stdout.strip())
            if result.returncode == 0
            else "Unknown"
        )
    except Exception as e:
        return f"Error: {str(e)}"


# 📌 Get Service Details
def get_service_details(service_name: str) -> dict:
    """Retrieve detailed information about a service using NSSM."""
    details = {}
    try:
        # details["Path"] = get_service_path(service_name)

        result_app_path = subprocess.run(
            ["nssm", "get", service_name, "Application"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        details["Path"] = (
            clean_unicode_string(result_app_path.stdout.strip())
            if result_app_path.returncode == 0
            else "N/A"
        )

        result_startup_dir = subprocess.run(
            ["nssm", "get", service_name, "AppDirectory"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        details["Startup Directory"] = (
            clean_unicode_string(result_startup_dir.stdout.strip())
            if result_startup_dir.returncode == 0
            else "N/A"
        )

        result_arguments = subprocess.run(
            ["nssm", "get", service_name, "AppParameters"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        details["Arguments"] = (
            clean_unicode_string(result_arguments.stdout.strip())
            if result_arguments.returncode == 0
            else "N/A"
        )

        details["Status"] = get_service_status(service_name)

    except Exception as e:
        print(f"Error retrieving details for service '{service_name}': {str(e)}")

    return details


# 📌 List All NSSM Services
def list_nssm_services():
    try:
        nssm_services = []
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services"
        ) as services_key:
            i = 0
            while True:
                try:
                    service_name = winreg.EnumKey(services_key, i)
                    service_path = get_service_path(service_name)
                    if service_path and "nssm.exe" in service_path.lower():
                        nssm_services.append(service_name)
                    i += 1
                except OSError:
                    break

        services_details = []
        for service_name in nssm_services:
            services_details.append(
                {"service_name": service_name, **get_service_details(service_name)}
            )

        return services_details

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error listing NSSM services: {str(e)}"
        )


def is_nssm_service(service_name: str) -> bool:
    try:
        key_path = rf"SYSTEM\CurrentControlSet\Services\{service_name}"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            image_path, _ = winreg.QueryValueEx(key, "ImagePath")
            return "nssm.exe" in image_path.lower()
    except Exception:
        return False


def block_stop_delete_actions(action: str):
    if BLOCK_STOP_DELETE_ACTIONS:
        raise HTTPException(
            status_code=403,
            detail=(
                f"'{action}' action is disabled by policy "
                "(NSSM_BLOCK_STOP_DELETE_ACTIONS=true)."
            ),
        )


# 📌 API Route: Health Check
@app.get("/health", summary="Health check")
def health_check():
    return {"status": "healthy", "service": "NSSM Service Manager API"}


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
        install_service_command = [
            "nssm",
            "install",
            request.service_name,
            request.executable_path,
        ]
        if request.arguments:
            install_service_command.append(request.arguments)

        result_install = subprocess.run(
            install_service_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result_install.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to install service: {result_install.stderr.strip()}",
            )

        result_set_dir = subprocess.run(
            [
                "nssm",
                "set",
                request.service_name,
                "AppDirectory",
                request.startup_directory,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result_set_dir.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Service installed but failed to set AppDirectory: {result_set_dir.stderr.strip()}",
            )

        return {"message": f"Service '{request.service_name}' installed successfully."}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error installing service: {str(e)}"
        )


# 📌 API Route: Start a Service
@app.post("/services/{service_name}/start", summary="Start a service")
def start_service(service_name: str):
    result = subprocess.run(
        ["nssm", "start", service_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode == 0:
        return {"message": f"Service '{service_name}' started successfully."}
    else:
        raise HTTPException(status_code=500, detail=result.stderr.strip())


# 📌 API Route: Stop a Service
@app.post("/services/{service_name}/stop", summary="Stop a service")
def stop_service(service_name: str):
    block_stop_delete_actions("stop")
    result = subprocess.run(
        ["nssm", "stop", service_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode == 0:
        return {"message": f"Service '{service_name}' stopped successfully."}
    else:
        raise HTTPException(status_code=500, detail=result.stderr.strip())


# 📌 API Route: Remove a Service
@app.delete("/services/{service_name}", summary="Remove a service")
def remove_service(service_name: str):
    block_stop_delete_actions("remove")
    result = subprocess.run(
        ["nssm", "remove", service_name, "confirm"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode == 0:
        return {"message": f"Service '{service_name}' removed successfully."}
    else:
        raise HTTPException(status_code=500, detail=result.stderr.strip())


# 📌 API Route: Get a Single Service
@app.get("/services/{service_name}", summary="Get details of a specific service")
def get_service(service_name: str):
    if not is_nssm_service(service_name):
        raise HTTPException(
            status_code=404,
            detail=f"Service '{service_name}' not found or not managed by NSSM.",
        )
    details = get_service_details(service_name)
    return {"service_name": service_name, **details}


# 📌 API Route: Get Service Status
@app.get("/services/{service_name}/status", summary="Get status of a service")
def get_service_status_endpoint(service_name: str):
    if not is_nssm_service(service_name):
        raise HTTPException(
            status_code=404,
            detail=f"Service '{service_name}' not found or not managed by NSSM.",
        )
    status = get_service_status(service_name)
    return {"service_name": service_name, "status": status}


# 📌 API Route: Restart a Service
@app.post("/services/{service_name}/restart", summary="Restart a service")
def restart_service(service_name: str):
    block_stop_delete_actions("restart")
    if not is_nssm_service(service_name):
        raise HTTPException(
            status_code=404,
            detail=f"Service '{service_name}' not found or not managed by NSSM.",
        )

    stop_result = subprocess.run(
        ["nssm", "stop", service_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if stop_result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop service: {stop_result.stderr.strip()}",
        )

    start_result = subprocess.run(
        ["nssm", "start", service_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if start_result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=f"Service stopped but failed to start: {start_result.stderr.strip()}",
        )

    return {"message": f"Service '{service_name}' restarted successfully."}


# 📌 API Route: Check if Service Exists
@app.get("/services/{service_name}/exists", summary="Check if a service exists")
def service_exists(service_name: str):
    exists = is_nssm_service(service_name)
    return {"service_name": service_name, "exists": exists}


def nssm_get(service_name: str, parameter: str) -> str:
    result = subprocess.run(
        ["nssm", "get", service_name, parameter],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get {parameter}: {result.stderr.strip()}",
        )
    return clean_unicode_string(result.stdout.strip())


def nssm_set(service_name: str, parameter: str, value: str):
    result = subprocess.run(
        ["nssm", "set", service_name, parameter, value],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to set {parameter}: {result.stderr.strip()}",
        )


# 📌 API Route: Get Stdout Log Path
@app.get(
    "/services/{service_name}/logs/stdout",
    summary="Get stdout log path",
)
def get_stdout_log(service_name: str):
    if not is_nssm_service(service_name):
        raise HTTPException(
            status_code=404,
            detail=f"Service '{service_name}' not found or not managed by NSSM.",
        )
    path = nssm_get(service_name, "AppStdout")
    return {"service_name": service_name, "stdout_log": path}


# 📌 API Route: Set Stdout Log Path
@app.put(
    "/services/{service_name}/logs/stdout",
    summary="Set stdout log path",
)
def set_stdout_log(service_name: str, request: LogPathRequest):
    if not is_nssm_service(service_name):
        raise HTTPException(
            status_code=404,
            detail=f"Service '{service_name}' not found or not managed by NSSM.",
        )
    nssm_set(service_name, "AppStdout", request.path)
    return {
        "service_name": service_name,
        "message": f"Stdout log path set to '{request.path}'.",
    }


# 📌 API Route: Get Stderr Log Path
@app.get(
    "/services/{service_name}/logs/stderr",
    summary="Get stderr log path",
)
def get_stderr_log(service_name: str):
    if not is_nssm_service(service_name):
        raise HTTPException(
            status_code=404,
            detail=f"Service '{service_name}' not found or not managed by NSSM.",
        )
    path = nssm_get(service_name, "AppStderr")
    return {"service_name": service_name, "stderr_log": path}


# 📌 API Route: Set Stderr Log Path
@app.put(
    "/services/{service_name}/logs/stderr",
    summary="Set stderr log path",
)
def set_stderr_log(service_name: str, request: LogPathRequest):
    if not is_nssm_service(service_name):
        raise HTTPException(
            status_code=404,
            detail=f"Service '{service_name}' not found or not managed by NSSM.",
        )
    nssm_set(service_name, "AppStderr", request.path)
    return {
        "service_name": service_name,
        "message": f"Stderr log path set to '{request.path}'.",
    }


# 📌 API Route: Configure Log Rotation
@app.put(
    "/services/{service_name}/logs/rotation",
    summary="Configure log rotation",
)
def set_log_rotation(service_name: str, request: LogRotationRequest):
    if not is_nssm_service(service_name):
        raise HTTPException(
            status_code=404,
            detail=f"Service '{service_name}' not found or not managed by NSSM.",
        )

    nssm_set(service_name, "AppRotateFiles", "1" if request.enabled else "0")

    if request.enabled:
        if request.rotate_bytes is not None:
            nssm_set(service_name, "AppRotateBytes", str(request.rotate_bytes))
        if request.rotate_files is not None:
            nssm_set(service_name, "AppRotateFilesOnline", "1")

    return {
        "service_name": service_name,
        "message": "Log rotation configured successfully.",
        "rotation": {
            "enabled": request.enabled,
            "rotate_bytes": request.rotate_bytes,
            "rotate_files": request.rotate_files,
        },
    }


# 📌 Integrated Uvicorn in __main__
if __name__ == "__main__":
    print("\n🚀 Starting NSSM Service Manager API on http://127.0.0.1:54321/")
    uvicorn.run(app, host="0.0.0.0", port=54321)
