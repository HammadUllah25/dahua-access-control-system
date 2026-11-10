
import ctypes
from NetSDK.NetSDK import NetClient
from NetSDK.SDK_Struct import (
    NET_IN_LOGIN_WITH_HIGHLEVEL_SECURITY,
    NET_OUT_LOGIN_WITH_HIGHLEVEL_SECURITY
)
from NetSDK.SDK_Enum import EM_LOGIN_SPAC_CAP_TYPE

DEVICE_IP = "192.168.0.2"
DEVICE_PORT = 37777
USERNAME = "admin"
PASSWORD = "YOUR_DEVICE_PASSWORD"

sdk = NetClient()

# Initialize SDK
if not sdk.InitEx(None):
    print("SDK initialization failed")
    raise SystemExit

print("SDK initialized successfully")

# Prepare login input
login_in = NET_IN_LOGIN_WITH_HIGHLEVEL_SECURITY()
login_in.dwSize = ctypes.sizeof(login_in)
login_in.szIP = DEVICE_IP.encode()
login_in.nPort = DEVICE_PORT
login_in.szUserName = USERNAME.encode()
login_in.szPassword = PASSWORD.encode()
login_in.emSpecCap = EM_LOGIN_SPAC_CAP_TYPE.TCP

# Prepare login output
login_out = NET_OUT_LOGIN_WITH_HIGHLEVEL_SECURITY()
login_out.dwSize = ctypes.sizeof(login_out)

# Login
login_id, device_info, error_message = (
    sdk.LoginWithHighLevelSecurity(login_in, login_out)
)

if login_id:
    print("LOGIN SUCCESSFUL!")
    print("Device IP:", DEVICE_IP)
    print("Login handle:", login_id)
    print("Device serial:", device_info.sSerialNumber)
    input("Press Enter to logout and exit...")
    sdk.Logout(login_id)
    print("Logged out successfully")
else:
    print("LOGIN FAILED:", error_message)

sdk.Cleanup()
