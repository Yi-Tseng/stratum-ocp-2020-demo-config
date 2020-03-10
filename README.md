Stratum pipeline for Trellis (OCP demo)
====

Run `git submodule update --init` after clone to pull fabric-tofino repo.

## Repo structure

This repo is structured as follows:

 * `netcfg` Network configs for ONOS
 * `vhosts` vhost script and configurations for each device

## VHosts

vhosts directory includes following configs:

 * co-srv: hosts for central office, which simulate one dummy service and one NAT
 * fo-leaf1: we uses internal interface from BF2556X which attached to the ASIC to simulate two dummy hosts with DHCP client.
 * fo-leaf2: same as `fo-leaf1`, but we simulate a DHCP Server and a Simple DNS server
 * fo-srv: two dummy services.

 > Dummy service: empty network namespace

To run vhost script, simply sopy the vhost.py to the device and run `vhost.py prov [json file]`

Use `vhost.py --help` for more information (or ask Charles)

## Commands

| Make command         | Description                                            |
|----------------------|------------------------------------------------------- |
| `make fabric-tofino-pipeconf` | Builds Fabric pipeconf oar file for tofino    |
| `make fabric-tofino-pipeconf-install` | Installs fabric pipeconf to ONOS      |
| `make onos-cli`      | Access the ONOS CLI (password: `rocks`, Ctrl-D to exit)|
| `make onos-log`      | Show the ONOS log                                      |
| `make netcfg`        | Push netcfg.json file (network config) to ONOS         |
