from typing import List, Dict

from .aws_signer import AWSSigner
from .station import Station
from .mqtt_helper import MQTTHelper


class House:
    rooms: Dict[str, Dict[str, str]] = None
    room_order: List[str] = None

    stations: Dict[str, Station] = None
    station_order: List[str] = None

    def __init__(
        self,
        signer: AWSSigner,
        house_id: str,
        name: str,
        region: str,
        mqtt_region: str,
        mqtt_server: str,
    ):
        self.house_id = house_id
        self.name = name
        self.region = region
        self.mqtt_region = mqtt_region
        self.mqtt_server = mqtt_server

        self.mqtt = MQTTHelper(signer, self)

    def set_rooms(self, data):
        self.rooms = data.get("houseRooms")
        self.room_order = data.get("roomSort")

    def set_stations(self, data):
        self.station_order = data.get("stationSort")

        stations = {}
        for i in data.get("stations", []):
            s = Station(self, **i)
            s.set_devices(i)

            stations[i["stationId"]] = s

        self.stations = stations

    def get_station_by_sn(self, sn: str):
        return next((i for _, i in self.stations.items() if i.sn == sn), None)
