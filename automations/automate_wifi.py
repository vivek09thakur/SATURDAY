import subprocess

def check_connected_device():
    # Run the arp command and get the output
    output = subprocess.run(
        ['arp', '-a'], stdout=subprocess.PIPE).stdout.decode()
    lines = output.split('\n')
    devices = []
    for line in lines:
        words = line.split()
        if len(words) == 3:
            ip_address = words[0]
            mac_address = words[1]
            devices.append((ip_address, mac_address))
    return devices
    
def hack_wifi(user_input):
    print('not done yet')
