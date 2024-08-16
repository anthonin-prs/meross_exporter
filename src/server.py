import os
import json
from prometheus_client import start_http_server, Gauge, Enum, Counter
import time
import asyncio, os

from meross_iot.http_api import MerossHttpClient
from meross_iot.manager import MerossManager

plugs_refs = ["mss310"]

class MerossMetrics:
    email = os.environ["EMAIL"]
    password = os.environ["PASSWORD"]
    metadata = {}

    """
    Representation of Prometheus metrics and loop to fetch and transform
    application metrics into Prometheus metrics.
    """

    def __init__(self, polling_interval_seconds=10):
        self.polling_interval_seconds = polling_interval_seconds
        with open('/app/src/metadata.json') as file:
            self.metadata = json.load(file)

        self.module_device_info = Gauge(
            "module_device_info", "Module informations status", ['device', 'name', 'tag', 'network_status', 'type', 'source'])
        self.module_power_status = Gauge(
            "module_power_status", "Module turned on or off", ['device', 'name', 'tag', 'type'])
        self.module_power_consumption = Gauge(
            "module_power_consumption", "Power consuption of module", ['device', 'name', 'tag', 'type'])

    def run_metrics_loop(self, loop):
        """Metrics fetching loop"""

        while True:
            final_data = loop.run_until_complete(self.fetch())
            # self.fetch()
            print(str(time.strftime("%Y-%m-%d %H:%M:%S")) +
                  " -- GATHERING DATA")
            time.sleep(self.polling_interval_seconds)

    async def fetch(self):
        """
        Get metrics from application and refresh Prometheus metrics with
        new values.
        """

        http_api_client = await MerossHttpClient.async_from_user_password(api_base_url='https://iotx-eu.meross.com', email=self.email, password=self.password)
        manager = MerossManager(http_client=http_api_client)
        await manager.async_init()
        await manager.async_device_discovery()
        meross_devices = manager.find_devices()
        for module in meross_devices:
            if(module.type in plugs_refs):
                instant_consumption = await module.async_get_instant_metrics()
                wattage = str(instant_consumption).split(" ")[2]
                power_on = True if float(wattage) > 0.0 else False
                network = str(module.online_status).split(".")[1]
                device_type = self.metadata[module.name]['type']
                if module.name in self.metadata:
                    tagline = self.metadata[module.name]['tag']
                else:
                    tagline = "none"
                
                self.module_device_info.labels(
                    device=module.uuid,
                    name=module.name,
                    tag=tagline,
                    network_status=str(network),
                    type=device_type,
                    source="Meross").set("1")
                if power_on :
                    self.module_power_status.labels(
                        device=module.uuid,
                        name=module.name,
                        tag=tagline,
                        type=device_type).set("1")

                    self.module_power_consumption.labels(
                        device=module.uuid,
                        name=module.name,
                        tag=tagline,
                        type=device_type).set(str(wattage))

                else:
                    self.module_power_status.labels(
                        device=module.uuid,
                        name=module.name,
                        tag=tagline,
                        type=device_type).set("0")
                    
                    self.module_power_consumption.labels(
                        device=module.uuid,
                        name=module.name,
                        tag=tagline,
                        type=device_type).set("0")

def main():
    """Main entry point"""

    polling_interval_seconds = int(
        os.getenv("POLLING_INTERVAL_SECONDS", "60"))
    exporter_port = int(os.getenv("EXPORTER_PORT", "8000"))

    app_metrics = MerossMetrics(
        polling_interval_seconds=polling_interval_seconds
    )
    start_http_server(exporter_port)
    loop = asyncio.get_event_loop()
    app_metrics.run_metrics_loop(loop)
    loop.close()



if __name__ == "__main__":
    main()
