Stratum pipeline for Trellis (OCP demo)
====

## Repo structure

This repo is structured as follows:

 * `p4src/` P4 implementation
 * `app/` ONOS pipeconf with pipeliner implementation
 * `mininet/` Mininet script to emulate a 2x2 leaf-spine fabric topology of
   `stratum_bmv2` devices and a netcfg file for this topology


## Commands

| Make command        | Description                                            |
|---------------------|------------------------------------------------------- |
| `make pull-deps`    | Pull all required dependencies                         |
| `make p4-build`     | Build P4 program                                       |
| `make start`        | Start Mininet and ONOS containers                      |
| `make stop`         | Stop all containers                                    |
| `make reset`        | Stop containers and remove any state associated        |
| `make onos-cli`     | Access the ONOS CLI (password: `rocks`, Ctrl-D to exit)|
| `make onos-log`     | Show the ONOS log                                      |
| `make mn-cli`       | Access the Mininet CLI (Ctrl-D to exit)                |
| `make mn-log`       | Show the Mininet log (i.e., the CLI output)            |
| `make app-build`    | Build custom ONOS app                                  |
| `make app-reload`   | Install and activate the ONOS app                      |
| `make netcfg`       | Push netcfg.json file (network config) to ONOS         |
| `make app-install`  | Install pipeconf to ONOS                               |

