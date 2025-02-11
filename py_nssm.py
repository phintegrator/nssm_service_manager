import winreg
import subprocess
from datetime import datetime

def get_service_path(service_name):
    """Retrieve the service executable path from the registry."""
    try:
        key_path = fr"SYSTEM\CurrentControlSet\Services\{service_name}"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            image_path, _ = winreg.QueryValueEx(key, "ImagePath")
            return image_path.strip('"')  # Remove quotes from the path if present
    except:
        return None

def get_service_status(service_name):
    """Retrieve the status of a service using nssm.exe."""
    try:
        result = subprocess.run(
            ["nssm", "status", service_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return "Unknown"
    except Exception as e:
        return f"Error: {str(e)}"

def get_service_details(service_name):
    """Retrieve detailed information about a service using nssm.exe."""
    details = {}
    try:
        # Get the service executable path
        details["Path"] = get_service_path(service_name) or "N/A"

        # Get the startup directory
        result_startup_dir = subprocess.run(
            ["nssm", "get", service_name, "AppDirectory"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        details["Startup Directory"] = result_startup_dir.stdout.strip() if result_startup_dir.returncode == 0 else "N/A"

        # Get the service arguments
        result_arguments = subprocess.run(
            ["nssm", "get", service_name, "AppParameters"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        details["Arguments"] = result_arguments.stdout.strip() if result_arguments.returncode == 0 else "N/A"

        # Get the service status
        details["Status"] = get_service_status(service_name)

    except Exception as e:
        print(f"Error retrieving details for service '{service_name}': {str(e)}")

    return details

def list_nssm_services():
    """List all services installed using nssm.exe along with their details."""
    try:
        # Open the registry key for Windows services
        services_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services")
        nssm_services = []

        # Iterate over all services in the registry
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

        if not nssm_services:
            print("\nNo services installed with nssm.exe were found.")
            return

        # Print header
        print(f"\nServices Installed Using NSSM - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 200)
        print(f"{'Service Name':<30} {'Path':<50} {'Startup Directory':<40} {'Arguments':<30} {'Status':<15}")
        print("-" * 200)

        for service_name in nssm_services:
            # Get service details
            details = get_service_details(service_name)
            print(
                f"{service_name:<30} {details['Path']:<50} {details['Startup Directory']:<40} {details['Arguments']:<30} {details['Status']:<15}"
            )

        print("-" * 200)

    except Exception as e:
        print(f"Error listing NSSM services: {str(e)}")

def remove_service(service_name):
    """Remove a service using nssm.exe."""
    try:
        confirmation = input(f"Are you sure you want to remove the service '{service_name}'? (yes/no): ").strip().lower()
        if confirmation == "yes":
            result = subprocess.run(
                ["nssm", "remove", service_name, "confirm"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            if result.returncode == 0:
                print(f"Service '{service_name}' removed successfully.")
            else:
                print(f"Failed to remove service '{service_name}': {result.stderr.strip()}")
        else:
            print("Service removal cancelled.")
    except Exception as e:
        print(f"Error removing service '{service_name}': {str(e)}")

if __name__ == "__main__":
    print("1. List all services installed using nssm.exe")
    print("2. Install a new service using nssm.exe")
    print("3. Start a service")
    print("4. Stop a service")
    print("5. Remove a service")
    print("6. Exit")

    while True:
        try:
            choice = input("\nEnter your choice: ").strip()
            if choice == "1":
                list_nssm_services()
            elif choice == "2":
                service_name = input("Enter the service name: ").strip()
                executable_path = input("Enter the executable path: ").strip()
                startup_directory = input("Enter the startup directory: ").strip()
                arguments = input("Enter optional arguments (leave blank if none): ").strip()
                install_service_command = ["nssm", "install", service_name, executable_path]
                if arguments:
                    install_service_command.append(arguments)
                subprocess.run(install_service_command)
                subprocess.run(["nssm", "set", service_name, "AppDirectory", startup_directory])
                print(f"Service '{service_name}' installed successfully.")
            elif choice == "3":
                service_name = input("Enter the service name to start: ").strip()
                subprocess.run(["nssm", "start", service_name])
            elif choice == "4":
                service_name = input("Enter the service name to stop: ").strip()
                subprocess.run(["nssm", "stop", service_name])
            elif choice == "5":
                service_name = input("Enter the service name to remove: ").strip()
                remove_service(service_name)
            elif choice == "6":
                print("Exiting...")
                break
            else:
                print("Invalid choice. Please try again.")
        except KeyboardInterrupt:
            print("\nExiting...")
            break
