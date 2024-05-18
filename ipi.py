#!/usr/bin/env python3
import requests
import netifaces
import subprocess
import argparse
import socket
from rich.console import Console
from rich.table import Table

console = Console()

def get_local_ip():
    interfaces = netifaces.interfaces()
    for interface in interfaces:
        if interface != 'lo':  # Ignore loopback interface
            addrs = netifaces.ifaddresses(interface)
            if netifaces.AF_INET in addrs:
                local_ip = addrs[netifaces.AF_INET][0]['addr']
                return local_ip, interface
    return None, None

def get_external_ip():
    try:
        response = requests.get('https://api.ipify.org')
        external_ip = response.text
        return external_ip
    except requests.RequestException:
        return "Could not retrieve external IP"

def get_gateway_ip():
    gateways = netifaces.gateways()
    if netifaces.AF_INET in gateways['default']:
        return gateways['default'][netifaces.AF_INET][0]
    return None

def get_gateway_ipv6():
    gateways = netifaces.gateways()
    if netifaces.AF_INET6 in gateways.get('default', {}):
        return gateways['default'][netifaces.AF_INET6][0]
    return None

def get_dns_servers():
    dns_servers = []
    resolv_conf = '/etc/resolv.conf'
    try:
        with open(resolv_conf, 'r') as f:
            lines = f.readlines()
            for line in lines:
                if line.startswith('nameserver'):
                    dns_servers.append(line.split()[1])
    except FileNotFoundError:
        dns_servers = ["Could not read /etc/resolv.conf"]
    return dns_servers

def get_dns_servers_ipv6():
    dns_servers = []
    resolv_conf = '/etc/resolv.conf'
    try:
        with open(resolv_conf, 'r') as f:
            lines = f.readlines()
            for line in lines:
                if line.startswith('nameserver') and ":" in line.split()[1]:
                    dns_servers.append(line.split()[1])
    except FileNotFoundError:
        dns_servers = ["Could not read /etc/resolv.conf"]
    return dns_servers

def get_subnet_mask():
    interfaces = netifaces.interfaces()
    for interface in interfaces:
        if interface != 'lo':  # Ignore loopback interface
            addrs = netifaces.ifaddresses(interface)
            if netifaces.AF_INET in addrs:
                subnet_mask = addrs[netifaces.AF_INET][0]['netmask']
                return subnet_mask, interface
    return None, None

def get_ipv6_address():
    interfaces = netifaces.interfaces()
    for interface in interfaces:
        if interface != 'lo':  # Ignore loopback interface
            addrs = netifaces.ifaddresses(interface)
            if netifaces.AF_INET6 in addrs:
                ipv6_address = addrs[netifaces.AF_INET6][0]['addr']
                return ipv6_address.split('%')[0], interface
    return None, None

def get_broadcast_address():
    interfaces = netifaces.interfaces()
    for interface in interfaces:
        if interface != 'lo':  # Ignore loopback interface
            addrs = netifaces.ifaddresses(interface)
            if netifaces.AF_INET in addrs:
                broadcast = addrs[netifaces.AF_INET][0].get('broadcast')
                return broadcast, interface
    return None, None

def get_mac_address(interface):
    addrs = netifaces.ifaddresses(interface)
    if netifaces.AF_LINK in addrs:
        mac = addrs[netifaces.AF_LINK][0]['addr']
        return mac
    return None

def get_host_name(ip):
    try:
        return socket.gethostbyaddr(ip)[0]
    except socket.herror:
        return None

def ping_address(address, timeout):
    try:
        output = subprocess.run(["ping", "-c", "1", "-W", str(timeout), address], capture_output=True, text=True, check=True)
        response_time = output.stdout.split("time=")[-1].split(" ms")[0]
        return response_time + " ms"
    except subprocess.CalledProcessError:
        return "No response"

def check_connection():
    try:
        subprocess.run(["ping", "-c", "1", "8.8.8.8"], capture_output=True, text=True, check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def get_signal_strength(interface):
    try:
        output = subprocess.run(["iwconfig", interface], capture_output=True, text=True, check=True)
        for line in output.stdout.split('\n'):
            if 'Signal level' in line:
                signal_strength_dbm = int(line.split('Signal level=')[-1].split(' dBm')[0].strip())
                signal_strength_percent = max(0, min(100, 2 * (signal_strength_dbm + 100)))
                return f"{signal_strength_dbm} dBm ({signal_strength_percent}%)"
        return "Signal strength not found"
    except subprocess.CalledProcessError:
        return "Interface not wireless or not found"

def measure_latency(timeout):
    try:
        output = subprocess.run(["ping", "-c", "4", "-W", str(timeout), "google.com"], capture_output=True, text=True, check=True)
        for line in output.stdout.split('\n'):
            if "rtt min/avg/max/mdev" in line:
                return line.split("=")[-1].strip()
    except subprocess.CalledProcessError:
        return "Latency measurement failed"
    return "Latency measurement not available"

def log_results(filename, content):
    with open(filename, 'a') as f:
        f.write(content + "\n")

def display_network_info(args):
    console = Console()
    table = Table(title="Network Information", style="bold blue")

    table.add_column("Description", style="bold green")
    table.add_column("Details", style="bold yellow")

    local_ip, local_interface = None, None
    if args.all or args.local_ip or args.test:
        with console.status("[bold green]Getting local IP..."):
            local_ip, local_interface = get_local_ip()
            table.add_row("Local IP", f"{local_ip} (Interface: {local_interface}) - Ping: {ping_address(local_ip, args.timeout)}")

    external_ip = None
    if args.all or args.external_ip or args.test:
        with console.status("[bold green]Getting external IP..."):
            external_ip = get_external_ip()
            table.add_row("External IP", f"{external_ip} - Ping: {ping_address(external_ip, args.timeout)}")

    gateway_ip = None
    if args.all or args.gateway_ip or args.test:
        with console.status("[bold green]Getting gateway IP..."):
            gateway_ip = get_gateway_ip()
            table.add_row("Router IP", f"{gateway_ip} - Ping: {ping_address(gateway_ip, args.timeout)}")

    if args.all or args.dns or args.test:
        with console.status("[bold green]Getting DNS servers..."):
            table.add_row("DNS Servers", ', '.join(get_dns_servers()))
            table.add_row("IPv6 DNS Servers", ', '.join(get_dns_servers_ipv6()))

    if args.all or args.subnet_mask or args.test:
        with console.status("[bold green]Getting subnet mask..."):
            subnet_mask, subnet_interface = get_subnet_mask()
            table.add_row("Subnet Mask", f"{subnet_mask} (Interface: {subnet_interface})")

    if args.all or args.ipv6 or args.test:
        with console.status("[bold green]Getting IPv6 address..."):
            ipv6_address, ipv6_interface = get_ipv6_address()
            table.add_row("IPv6 Address", f"{ipv6_address} (Interface: {ipv6_interface}) - Ping: {ping_address(ipv6_address, args.timeout)}")

    if args.all or args.broadcast or args.test:
        with console.status("[bold green]Getting broadcast address..."):
            broadcast_address, broadcast_interface = get_broadcast_address()
            table.add_row("Broadcast Address", f"{broadcast_address} (Interface: {broadcast_interface})")

    if args.all or args.mac or args.test:
        with console.status("[bold green]Getting MAC address..."):
            mac_address = get_mac_address(local_interface)
            table.add_row("MAC Address", f"{mac_address} (Interface: {local_interface})")

    if args.all or args.gateway_ipv6 or args.test:
        with console.status("[bold green]Getting IPv6 gateway..."):
            table.add_row("Default Gateway IPv6", f"{get_gateway_ipv6()}")

    if args.all or args.signal or args.test:
        with console.status("[bold green]Getting signal strength..."):
            signal_strength = get_signal_strength(local_interface)
            table.add_row("Signal Strength", signal_strength)

    if args.test:
        with console.status("[bold green]Measuring latency..."):
            table.add_row("Latency", measure_latency(args.timeout))

    console.print(table)

    if args.logfile:
        log_content = table.__str__()
        log_results(args.logfile, log_content)

def main():
    parser = argparse.ArgumentParser(description="Display network information")
    parser.add_argument('--all', action='store_true', help="Display all information")
    parser.add_argument('--local-ip', action='store_true', help="Display local IP information")
    parser.add_argument('--external-ip', action='store_true', help="Display external IP information")
    parser.add_argument('--gateway-ip', action='store_true', help="Display gateway IP information")
    parser.add_argument('--dns', action='store_true', help="Display DNS information")
    parser.add_argument('--subnet-mask', action='store_true', help="Display subnet mask information")
    parser.add_argument('--ipv6', action='store_true', help="Display IPv6 information")
    parser.add_argument('--broadcast', action='store_true', help="Display broadcast address information")
    parser.add_argument('--mac', action='store_true', help="Display MAC address information")
    parser.add_argument('--gateway-ipv6', action='store_true', help="Display gateway IPv6 information")
    parser.add_argument('--signal', action='store_true', help="Display signal strength")
    parser.add_argument('--test', action='store_true', help="Measure network latency")
    parser.add_argument('--timeout', type=int, default=1, help="Ping timeout in seconds")
    parser.add_argument('-l', '--logfile', type=str, help="Log output to a file")
    args = parser.parse_args()

    # Sätt args.all till True om inga specifika flaggor är True
    if not (args.local_ip or args.external_ip or args.gateway_ip or args.dns or args.subnet_mask or args.ipv6 or args.broadcast or args.mac or args.gateway_ipv6 or args.signal or args.test):
        args.all = True

    host_name = socket.gethostname()
    console.print(f"Host Name: {host_name}", style="bold blue")

    display_network_info(args)

if __name__ == "__main__":
    main()
