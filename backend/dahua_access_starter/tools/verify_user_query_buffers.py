"""Verify the Dahua personnel GET output buffers without contacting a device.

Run with the same Python environment that has the NetSDK wheel installed.
This only allocates ctypes structures; it does not initialize the native SDK.
"""
from ctypes import sizeof, pointer

from NetSDK.SDK_Struct import (
    NET_ACCESS_USER_INFO,
    NET_ACCESS_USER_INFO_EX,
    NET_FLOORS_INFO,
    NET_IN_ACCESS_USER_SERVICE_GET,
    NET_OUT_ACCESS_USER_SERVICE_GET,
)


def main() -> None:
    batch_size = 1
    query = NET_IN_ACCESS_USER_SERVICE_GET()
    query.dwSize = sizeof(NET_IN_ACCESS_USER_SERVICE_GET)
    query.nUserNum = batch_size
    query.szUserID = b"TEST-001"

    users = (NET_ACCESS_USER_INFO * batch_size)()
    floors = [NET_FLOORS_INFO() for _ in range(batch_size)]
    user_ex = [NET_ACCESS_USER_INFO_EX() for _ in range(batch_size)]
    for index in range(batch_size):
        users[index].pstuFloorsEx2 = pointer(floors[index])
        users[index].pstuUserInfoEx = pointer(user_ex[index])

    out = NET_OUT_ACCESS_USER_SERVICE_GET()
    out.dwSize = sizeof(NET_OUT_ACCESS_USER_SERVICE_GET)
    out.nMaxRetNum = batch_size
    out.pUserInfo = pointer(users[0])

    assert sizeof(NET_IN_ACCESS_USER_SERVICE_GET) == 16012
    assert sizeof(NET_OUT_ACCESS_USER_SERVICE_GET) == 24
    assert sizeof(NET_ACCESS_USER_INFO) == 6840
    assert bool(users[0].pstuFloorsEx2)
    assert bool(users[0].pstuUserInfoEx)
    assert not bool(users[0].pstuUserInfoEx2)
    assert not bool(users[0].pstuUserInfoEx3)
    print("PASS: personnel GET query/output structures and required backing buffers are valid.")
    print("NOTE: this does not test communication with the physical controller.")


if __name__ == "__main__":
    main()
