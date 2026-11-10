from NetSDK.NetSDK import NetClient

def main():
    sdk = NetClient()

    print("Dahua SDK initialized successfully")

    sdk.InitEx(None)

    print("Dahua SDK initialization completed")

if __name__ == "__main__":
    main()