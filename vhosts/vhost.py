#!/usr/bin/env python3

import glob
import json
import logging
import os
import subprocess
import sys
import re

DHCLIENT_BIN = '/sbin/dhclient'
DHCLIENT_PID = '/var/lib/dhcp/dhclient-%s-%s.pid'
DHCLIENT_LEASE = '/var/lib/dhcp/dhclient-%s-%s.lease'
DHCPD_BIN = '/usr/sbin/dhcpd'
DHCPD_PID = '/var/lib/dhcp/dhcpd-%s-%s.pid'
DHCPD_LEASE = '/var/lib/dhcp/dhcpd-%s-%s.lease'

ZEBRA_BIN = '/usr/lib/quagga/zebra'
ZEBRA_PID = '/var/run/quagga/zebra-%s.pid'
ZEBRA_SOCK = '/var/run/quagga/zebra-%s.sock'
BGPD_BIN = '/usr/lib/quagga/bgpd'
BGPD_PID = '/var/run/quagga/bgpd-%s.pid'

COREDNS_BIN = '/usr/local/bin/coredns'
COREDNS_PID = '/var/run/coredns/coredns-%s.pid'

# run command in namespace
def ns_exec(host, command, background=False):
    cmd = ['ip', 'netns', 'exec', host] + command
    logger.debug(' '.join(cmd))
    if not background:
        stdout, stderr = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
        return stdout.decode('utf-8')
    else:
        subprocess.Popen(cmd)
        return ''


# create namespace for host
def add_host(host):
    cmd = ['ip', 'netns', 'add', host]
    logger.debug(' '.join(cmd))
    stdout, stderr = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()


def kill_host_pids(host):
    pids = list_host_pids(host)

    for pid in pids:
        cmd = ['kill', '-9', pid]
        logger.debug(' '.join(cmd))
        stdout, stderr = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()


# delete namespace for host
def delete_host(host):
    kill_host_pids(host)
    cmd = ['ip', 'netns', 'del', host]
    logger.debug(' '.join(cmd))
    stdout, stderr = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()


# bind physical interface to namespace
def add_port(host, iface):
    cmd = ['ip', 'link', 'set', iface, 'netns', host]
    logger.debug(' '.join(cmd))
    stdout, stderr = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()


# create linux bonding
def create_bond(host, name):
    ns_exec(host, ['ip', 'link', 'add', name, 'type', 'bond', 'miimon', '100', 'mode',
                   'balance-xor', 'xmit_hash_policy', 'layer2+3'])


# add slave interface to the bond
def add_slave(host, bond, iface):
    ns_exec(host, ['ip', 'link', 'set', iface, 'master', bond])


# create vlan interface
def create_vlan(host, name, parent, vlan, tpid):
    ns_exec(host, ['ip', 'link', 'add', 'link', parent, name, 'type', 'vlan', 'proto', tpid, 'id', vlan])

# enable physical interface in namespace
def enable_port(host, iface):
    ns_exec(host, ['ip', 'link', 'set', iface, 'up'])


# set ip address on given interface of given host
def set_address(host, iface, address):
    if address == 'dhcp':
        pid_file = DHCLIENT_PID % (host, iface)
        lease_file = DHCLIENT_LEASE % (host, iface)
        ns_exec(host, ['touch', pid_file])
        ns_exec(host, ['touch', lease_file])
        ns_exec(host, [DHCLIENT_BIN, '-q', '-4', '-nw', '-pf', pid_file, '-lf', lease_file, iface])
    else:
        ns_exec(host, ['ip', 'addr', 'add', address, 'dev', iface])


# set default gateway on given host
def set_gateway(host, gateway):
    ns_exec(host, ['ip', 'route', 'add', 'default', 'via', gateway])


# start dhcpd
def start_dhcpd(host, iface, config):
    pid_file = DHCPD_PID % (host, iface)
    lease_file = DHCPD_LEASE % (host, iface)
    ns_exec(host, ['mkdir', '-p', '/'.join(pid_file.split('/')[:-1])])
    ns_exec(host, ['touch', pid_file])
    ns_exec(host, ['mkdir', '-p', '/'.join(lease_file.split('/')[:-1])])
    ns_exec(host, ['touch', lease_file])
    ns_exec(host, [DHCPD_BIN, '-q', '-4', '-pf', pid_file, '-lf', lease_file, '-cf', config, iface])


# start zebra
def start_zebra(host, config):
    pid_file = ZEBRA_PID % host
    sock_file = ZEBRA_SOCK % host
    ns_exec(host, ['mkdir', '-p', '/'.join(pid_file.split('/')[:-1])])
    ns_exec(host, ['touch', pid_file])
    ns_exec(host, ['mkdir', '-p', '/'.join(sock_file.split('/')[:-1])])
    ns_exec(host, ['touch', sock_file])
    ns_exec(host, [ZEBRA_BIN, '-d', '-f', config, '-z', sock_file, '-i', pid_file])


# start bgpd
def start_bgpd(host, config):
    pid_file = BGPD_PID % host
    sock_file = ZEBRA_SOCK % host
    ns_exec(host, ['touch', pid_file])
    ns_exec(host, ['touch', sock_file])
    ns_exec(host, [BGPD_BIN, '-d', '-f', config, '-z', sock_file, '-i', pid_file])

# start coredns
def start_coredns(host, config):
    pid_file = COREDNS_PID % host
    ns_exec(host, ['mkdir', '-p', '/'.join(pid_file.split('/')[:-1])])
    ns_exec(host, ['touch', pid_file])
    ns_exec(host, [COREDNS_BIN, '-conf', config, '-pidfile', pid_file, '-quiet'], background=True)

# list all namespaces
def list_hosts():
    cmd = ['ip', 'netns', 'show']
    logger.debug(' '.join(cmd))
    stdout, stderr = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
    lines = stdout.decode('utf-8').split('\n')
    hosts = []
    # Format may be:
    # [name]
    # [name] (id: [nsid])
    for line in lines:
        hostname = line
        if line and re.findall("\(id: \d+\)", hostname):
            hostname = line.split(' ')[0]
        hosts.append(hostname)

    return filter(None, hosts)


# list all pids inside a namespace
def list_host_pids(host):
    cmd = ['ip', 'netns', 'pids', host]
    logger.debug(' '.join(cmd))
    stdout, stderr = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
    return filter(None, stdout.decode('utf-8').split('\n'))


# clean up all namespaces and processes
def clear_hosts():
    cmd = ['killall', '-9', 'dhclient', 'dhcpd', 'zebra', 'bgpd']
    logger.debug(' '.join(cmd))
    stdout, stderr = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()

    for host in list_hosts():
        delete_host(host)

    # TODO make these paths constants
    for f in glob.glob("/var/lib/dhcp/*.lease"):
        logger.debug("Removing %s" % f)
        os.remove(f)
    for f in glob.glob("/var/lib/dhcp/*.pid"):
        logger.debug("Removing %s" % f)
        os.remove(f)
    for f in glob.glob("/var/run/quagga/*.pid"):
        logger.debug("Removing %s" % f)
        os.remove(f)
    for f in glob.glob("/var/run/quagga/*.sock"):
        logger.debug("Removing %s" % f)
        os.remove(f)


def discover_hosts():
    for host in list_hosts():
        result = ns_exec(host, ['ip', 'route', 'get', '8.8.8.8']).split()
        if len(result) >= 3:
            gateway = result[2]
            ns_exec(host, ['arping', '-c', '1', gateway])
        else:
            logger.info("Cannot find default gateway of %s" % host)


def usage():
    print("Usage:")
    print("    ./vhost.py prov <config> # provision namespaces")
    print("    ./vhost.py clear         # clean up namespaces and processes")
    print("    ./vhost.py list          # list provisioned namespaces")
    print("    ./vhost.py discover      # discover hosts by sending arping")


def main(config):
    # load configuration from JSON file
    with open(config) as file:
        config = json.load(file)

    # create namespace and attach interfaces
    for host in config['hosts']:
        add_host(host['name'])
        enable_port(host['name'], 'lo')
        if 'interfaces' in host:
            for iface in host['interfaces']:
                add_port(host['name'], iface['name'])
                enable_port(host['name'], iface['name'])
                if 'address' in iface:
                    set_address(host['name'], iface['name'], iface['address'])
                if 'gateway' in iface:
                    set_gateway(host['name'], iface['gateway'])
        if 'bonds' in host:
            for bond in host['bonds']:
                create_bond(host['name'], bond['name'])
                if 'slaves' in bond:
                    for slave in bond['slaves']:
                        add_port(host['name'], slave)
                        add_slave(host['name'], bond['name'], slave)
                enable_port(host['name'], bond['name'])
                if 'address' in bond:
                    set_address(host['name'], bond['name'], bond['address'])
                if 'gateway' in bond:
                    set_gateway(host['name'], bond['gateway'])
        if 'vlans' in host:
            for vlan in host['vlans']:
                create_vlan(host['name'], vlan['name'], vlan['parent'], vlan['vlan'], vlan['tpid'])
                enable_port(host['name'], vlan['name'])
                if 'address' in vlan:
                    set_address(host['name'], vlan['name'], vlan['address'])
                if 'gateway' in vlan:
                    set_gateway(host['name'], vlan['gateway'])
        if 'services' in host:
            if 'dhcpd' in host['services']:
                start_dhcpd(host['name'], host['services']['dhcpd']['iface'], host['services']['dhcpd']['config'])
            if 'zebra' in host['services']:
                start_zebra(host['name'], host['services']['zebra']['config'])
            if 'bgpd' in host['services']:
                start_bgpd(host['name'], host['services']['bgpd']['config'])
            if 'coredns' in host['services']:
                start_coredns(host['name'], host['services']['coredns']['config'])
        if 'cmd' in host:
            for cmd in host['cmd']:
                ns_exec(host['name'], cmd)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)-8s - %(message)s')
    logger = logging.getLogger(__name__)

    if os.getuid() != 0:
        print("Please run this script as root")
        exit(-1)
    if len(sys.argv) < 2 or sys.argv[1] == '--help' or sys.argv[1] == 'help' or sys.argv[1] == '-h':
        usage()
        exit(-1)
    if sys.argv[1] == 'prov' and len(sys.argv) == 3:
        clear_hosts()
        main(sys.argv[2])
        exit(0)
    if sys.argv[1] == 'clear' and len(sys.argv) == 2:
        clear_hosts()
        exit(0)
    if sys.argv[1] == 'list' and len(sys.argv) == 2:
        logger.info(' '.join(list_hosts()))
        exit(0)
    if sys.argv[1] == 'discover' and len(sys.argv) == 2:
        discover_hosts()
        exit(0)
    usage()
    exit(-1)
