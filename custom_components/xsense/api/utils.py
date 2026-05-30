import argparse
import contextlib

from .base import XSenseBase


def get_credentials():
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", help="Username")
    parser.add_argument("--password", help="Password")
    args = parser.parse_args()

    if args.username and args.password:
        return args.username, args.password

    with contextlib.suppress(FileNotFoundError):
        with open(".env", "r") as file:
            for line in file:
                with contextlib.suppress(ValueError):
                    key, value = line.strip().split("=")
                    if key.lower() == "username":
                        username = value
                    elif key.lower() == "password":
                        password = value

    if username and password:
        return username, password

    raise ValueError("Username and password not provided")


def dump_environment(env: XSenseBase):
    for h_id, h in env.houses.items():
        print(f"----[ {h.name} ({h_id}) ]-----------------")
        for s_id, s in h.stations.items():
            dump_device(s)
            print(f"# {s.name} ({s_id})")
            for d_id, d in s.devices.items():
                dump_device(d)


def dump_device(d):
    print(f"{d.name} ({d.type}):")
    print(f"  serial  : {d.sn}")
    print(f"  online  : {'yes' if d.online else 'no'}")
    print(f"  values  : {d.data}")

    if hasattr(d, "has_alarm") and d.has_alarm:
        print(" - Alarm -")
        # print(f'  mode    : {d.alarm_data["safeMode"]}')
        print(f"  values  : {d.alarm_data}")
