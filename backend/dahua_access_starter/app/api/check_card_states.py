from NetSDK.SDK_Enum import EM_A_NET_ACCESSCTLCARD_STATE

print("Dahua card-state definitions:\n")

for name in dir(EM_A_NET_ACCESSCTLCARD_STATE):
    if "ACCESSCTLCARD_STATE" in name:
        value = getattr(EM_A_NET_ACCESSCTLCARD_STATE, name)
        print(f"{name} = {value!r}")