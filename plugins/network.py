import re
import subprocess

from plugins import Plugin


class ConnectedDevices(Plugin):
    name = 'connected_devices'
    description = 'List devices on the local network (IP and MAC address).'

    MAC = re.compile(r'^(?:[0-9a-f]{2}[-:]){5}[0-9a-f]{2}$', re.IGNORECASE)

    def run(self):
        output = subprocess.run(['arp', '-a'], capture_output=True, text=True, timeout=15).stdout
        devices = []
        for line in output.splitlines():
            words = line.split()
            mac = next((w for w in words if self.MAC.match(w)), None)
            ip = next((w for w in words if re.match(r'^\d+\.\d+\.\d+\.\d+$', w.strip('()'))), None)
            if mac and ip and not mac.lower().startswith('ff-ff') and not ip.startswith(('224.', '239.', '255.')):
                devices.append(f"{ip.strip('()')} ({mac})")
        if not devices:
            return 'no devices found'
        return f"{len(devices)} devices: " + ', '.join(devices)
