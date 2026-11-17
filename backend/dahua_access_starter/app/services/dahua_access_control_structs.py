"""ctypes layouts for Dahua NetSDK configuration structures.

The definitions in this module mirror the AccessControl declarations in
Dahua's ``dhconfigsdk.h`` (General NetSDK V3.060, Win64).  They are needed
for CLIENT_ParseData / CLIENT_PacketData; the C/C++ import libraries are not
required when calling the runtime DLLs from Python ctypes.

Keep every field in CFG_ACCESS_EVENT_INFO, including reserved/extension
fields.  Omitting even an apparently unused field changes the structure size
and offsets and can cause CLIENT_ParseData to reject the structure or corrupt
subsequent field interpretation.
"""

from __future__ import annotations

from ctypes import (
    Structure,
    c_char,
    c_int,
    c_uint8,
    c_uint32,
)


# dhconfigsdk.h constants
MAX_NAME_LEN = 128
CFG_MAX_SN_LEN = 32
CFG_MAX_ACCESS_CONTROL_ADDRESS_LEN = 64
WEEK_DAY_NUM = 7
MAX_DOOR_TIME_SECTION = 4


class CFG_TIME(Structure):
    """CFG_TIME uses three DWORD values in dhconfigsdk.h."""

    _fields_ = [
        ("dwHour", c_uint32),
        ("dwMinute", c_uint32),
        ("dwSecond", c_uint32),
    ]


class CFG_TIME_PERIOD(Structure):
    _fields_ = [
        ("stuStartTime", CFG_TIME),
        ("stuEndTime", CFG_TIME),
    ]


class CFG_DOOROPEN_TIMESECTION_INFO(Structure):
    _fields_ = [
        ("stuTime", CFG_TIME_PERIOD),
        ("emDoorOpenMethod", c_int),
        ("abOutDoorMethodEnable", c_int),
        ("bOutDoorMethodEnable", c_int),
        ("nOutDoorMethod", c_uint32),
        ("szReserved", c_char * 36),
    ]


class CFG_ACCESS_FIRSTENTER_INFO(Structure):
    _fields_ = [
        ("bEnable", c_int),
        ("emStatus", c_int),
        ("nTimeIndex", c_int),
    ]


class CFG_ACCESS_FIRSTENTER_INFO_EX(Structure):
    _fields_ = [
        ("nHolidayScheduleID", c_uint32),
        ("szReserved", c_char * 124),
    ]


class CFG_REMOTE_DETAIL_INFO(Structure):
    _fields_ = [
        ("nTimeOut", c_int),
        ("bTimeOutDoorStatus", c_int),
    ]


class CFG_HANDICAP_TIMEOUT_INFO(Structure):
    _fields_ = [
        ("nUnlockHoldInterval", c_int),
        ("nCloseTimeout", c_int),
    ]


class CFG_AUTO_REMOTE_CHECK_INFO(Structure):
    _fields_ = [
        ("bEnable", c_int),
        ("nTimeSechdule", c_int),
    ]


class CFG_AUTO_REMOTE_CHECK_INFO_EX(Structure):
    _fields_ = [
        ("nHolidayScheduleID", c_uint32),
        ("szResvered", c_char * 60),
    ]


class CFG_ACCESS_CONTROL_UDP_INFO(Structure):
    _fields_ = [
        ("szAddress", c_char * CFG_MAX_ACCESS_CONTROL_ADDRESS_LEN),
        ("nPort", c_int),
    ]


class NET_AUTO_REMOTE_OUT_DOOR_CHECK(Structure):
    _fields_ = [
        ("bEnable", c_int),
        ("nTime", c_uint32),
        ("nHolidayScheduleID", c_uint32),
        ("szReserved", c_char * 60),
    ]


class CFG_ACCESS_EVENT_INFO(Structure):
    """Complete CFG_ACCESS_EVENT_INFO definition from dhconfigsdk.h.

    C/C++ ``bool`` fields use one byte; Windows ``BOOL``, ``int`` and enums
    use four bytes.  The 7 x 4 schedule matrix is retained in full.
    """

    _fields_ = [
        ("szChannelName", c_char * MAX_NAME_LEN),
        ("emState", c_int),
        ("emMode", c_int),
        ("nEnableMode", c_int),
        ("bSnapshotEnable", c_int),

        # Ability flags: native C++ bool (one byte each).
        ("abDoorOpenMethod", c_uint8),
        ("abUnlockHoldInterval", c_uint8),
        ("abCloseTimeout", c_uint8),
        ("abOpenAlwaysTimeIndex", c_uint8),
        ("abCloseAlwaysTimeIndex", c_uint8),
        ("abHolidayTimeIndex", c_uint8),
        ("abBreakInAlarmEnable", c_uint8),
        ("abRepeatEnterAlarmEnable", c_uint8),
        ("abDoorNotClosedAlarmEnable", c_uint8),
        ("abDuressAlarmEnable", c_uint8),
        ("abDoorTimeSection", c_uint8),
        ("abSensorEnable", c_uint8),
        ("abFirstEnterEnable", c_uint8),
        ("abRemoteCheck", c_uint8),
        ("abRemoteDetail", c_uint8),
        ("abHandicapTimeOut", c_uint8),
        ("abCheckCloseSensor", c_uint8),
        ("abAutoRemoteCheck", c_uint8),
        ("abSpecialDaysOpenAlwaysTime", c_uint8),
        ("abSpecialDaysCloseAlwaysTime", c_uint8),

        ("emDoorOpenMethod", c_int),
        ("nUnlockHoldInterval", c_int),
        ("nCloseTimeout", c_int),
        ("nOpenAlwaysTimeIndex", c_int),
        ("nCloseAlwaysTimeIndex", c_int),
        ("nHolidayTimeRecoNo", c_int),
        ("bBreakInAlarmEnable", c_int),
        ("bRepeatEnterAlarm", c_int),
        ("bDoorNotClosedAlarmEnable", c_int),
        ("bDuressAlarmEnable", c_int),

        # CFG_DOOROPEN_TIMESECTION_INFO stuDoorTimeSection[7][4].
        ("stuDoorTimeSection", (CFG_DOOROPEN_TIMESECTION_INFO * MAX_DOOR_TIME_SECTION) * WEEK_DAY_NUM),

        ("bSensorEnable", c_int),
        ("stuFirstEnterInfo", CFG_ACCESS_FIRSTENTER_INFO),
        ("bRemoteCheck", c_int),
        ("stuRemoteDetail", CFG_REMOTE_DETAIL_INFO),
        ("stuHandicapTimeOut", CFG_HANDICAP_TIMEOUT_INFO),
        ("bCloseCheckSensor", c_int),
        ("stuAutoRemoteCheck", CFG_AUTO_REMOTE_CHECK_INFO),
        ("bLocalControlEnable", c_int),
        ("bRemoteControlEnable", c_int),
        ("nSensorDelay", c_int),
        ("nHumanStatusSensitivity", c_int),
        ("nDetectSensitivity", c_int),
        ("bLockTongueEnable", c_int),
        ("nABLockRoute", c_int),
        ("nDoorNotClosedReaderAlarmTime", c_int),
        ("bEnable", c_int),
        ("szSN", c_char * CFG_MAX_SN_LEN),
        ("nCloseDuration", c_int),
        ("nUnlockReloadInterval", c_int),
        ("emAccessProtocol", c_int),
        ("emProtocolType", c_int),
        ("stuAccessControlUdpInfo", CFG_ACCESS_CONTROL_UDP_INFO),
        ("nEntranceLockChannel", c_uint32),
        ("bSnapshotUpload", c_int),
        ("nSnapUploadPos", c_uint32),
        ("bCustomPasswordEnable", c_int),
        ("nRepeatEnterTime", c_int),
        ("nCardNoConvert", c_int),
        ("bUnAuthorizedMaliciousSwipEnable", c_int),
        ("bFakeLockedAlarmEnable", c_int),
        ("emReadCardState", c_int),
        ("bHelmetEnable", c_int),
        ("nSpecialDaysOpenAlwaysTime", c_uint32),
        ("nSpecialDaysCloseAlwaysTime", c_uint32),
        ("nSensorType", c_uint32),
        ("stuAutoRemoteCheckEx", CFG_AUTO_REMOTE_CHECK_INFO_EX),
        ("bIsSpecialDaysAuthenticationTimeValid", c_int),
        ("nSpecialDaysAuthenticationTime", c_uint32),
        ("bIsOpenDoorGroupTimeOutValid", c_int),
        ("nOpenDoorGroupTimeOut", c_uint32),
        ("stuFirstEnterInfoEx", CFG_ACCESS_FIRSTENTER_INFO_EX),
        ("bIsDoorNotClosedReaderAlarmTypeValid", c_int),
        ("nDoorNotClosedReaderAlarmType", c_uint32),
        ("bAutoRemoteHolidayScheduleIDUnenable", c_int),
        ("bFirstEnterHolidayScheduleIDUnenable", c_int),
        ("abOutDoorMethodEnable", c_int),
        ("bOutDoorMethodEnable", c_int),
        ("nOutDoorMethod", c_uint32),
        ("nCardStoreFormat", c_uint32),
        ("nRepeatCardEnterTime", c_uint32),
        ("bAutoRemoteOutDoorCheck", c_int),
        ("stuAutoRemoteOutDoorCheck", NET_AUTO_REMOTE_OUT_DOOR_CHECK),
        ("szResvered", c_char * 768),
    ]


# Layout values calculated from the complete V3.060 header definition.
# They are intentionally checked at import/use time to prevent unsafe writes.
CFG_ACCESS_EVENT_INFO_EXPECTED_SIZE = 3672
CFG_ACCESS_EVENT_INFO_SENSOR_CAPABILITY_OFFSET = 155
CFG_ACCESS_EVENT_INFO_SENSOR_VALUE_OFFSET = 2332
