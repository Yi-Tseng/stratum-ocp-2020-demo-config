onos_host := localhost
onos_url := http://${onos_host}:8181/onos
onos_curl := curl --fail -sSL --user onos:rocks --noproxy localhost

.PHONY: netcfg

default:
	$(error Please specify a make target (see README.md))

netcfg:
	$(info *** Pushing netcfg.json to ONOS...)
	${onos_curl} -X POST -H 'Content-Type:application/json' \
		${onos_url}/v1/network/configuration -d@./netcfg/ports.json
	${onos_curl} -X POST -H 'Content-Type:application/json' \
		${onos_url}/v1/network/configuration -d@./netcfg/hosts.json
	${onos_curl} -X POST -H 'Content-Type:application/json' \
		${onos_url}/v1/network/configuration -d@./netcfg/devices.json
	${onos_curl} -X POST -H 'Content-Type:application/json' \
		${onos_url}/v1/network/configuration -d@./netcfg/dhcp-relay.json
	@echo

fabric-tofino-pipeconf:
	$(MAKE) -C fabric-tofino pipeconf

fabric-tofino-pipeconf-install:
	$(MAKE) -C fabric-tofino pipeconf-install ONOS_HOST=${onos_host}
