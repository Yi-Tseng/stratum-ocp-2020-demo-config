ONOS_IMG := onosproject/onos:2.2.0
P4RT_SH_IMG := p4lang/p4runtime-sh:latest
P4C_IMG := opennetworking/p4c:stable
MN_STRATUM_IMG := opennetworking/mn-stratum:latest
MAVEN_IMG := maven:3.6.1-jdk-11-slim

ONOS_SHA := sha256:c1d18e6957a785d0234855eb8c70909bfc68849338f0567e12a6ae7ce6f4ba91
P4RT_SH_SHA := sha256:6ae50afb5bde620acb9473ce6cd7b990ff6cc63fe4113cf5584c8e38fe42176c
P4C_SHA := sha256:8f9d27a6edf446c3801db621359fec5de993ebdebc6844d8b1292e369be5dfea
MN_STRATUM_SHA := sha256:ae7c59885509ece8062e196e6a8fb6aa06386ba25df646ed27c765d92d131692
MAVEN_SHA := sha256:ca67b12d638fe1b8492fa4633200b83b118f2db915c1f75baf3b0d2ef32d7263

mkfile_path := $(abspath $(lastword $(MAKEFILE_LIST)))
curr_dir := $(patsubst %/,%,$(dir $(mkfile_path)))
curr_dir_sha := $(shell echo -n "$(curr_dir)" | shasum | cut -c1-7)

app_build_container_name := app-build-${curr_dir_sha}
onos_url := http://localhost:8181/onos
onos_curl := curl --fail -sSL --user onos:rocks --noproxy localhost
app_name := org.onosproject.stratum-pipeconf

default:
	$(error Please specify a make target (see README.md))

_docker_pull_all:
	docker pull ${ONOS_IMG}@${ONOS_SHA}
	docker tag ${ONOS_IMG}@${ONOS_SHA} ${ONOS_IMG}
	docker pull ${P4RT_SH_IMG}@${P4RT_SH_SHA}
	docker tag ${P4RT_SH_IMG}@${P4RT_SH_SHA} ${P4RT_SH_IMG}
	docker pull ${P4C_IMG}@${P4C_SHA}
	docker tag ${P4C_IMG}@${P4C_SHA} ${P4C_IMG}
	docker pull ${MN_STRATUM_IMG}@${MN_STRATUM_SHA}
	docker tag ${MN_STRATUM_IMG}@${MN_STRATUM_SHA} ${MN_STRATUM_IMG}
	docker pull ${MAVEN_IMG}@${MAVEN_SHA}
	docker tag ${MAVEN_IMG}@${MAVEN_SHA} ${MAVEN_IMG}

# Pull all Docker images and build app to seed mvn repo inside container, i.e.
# download deps
pull-deps: _docker_pull_all _create_mvn_container _mvn_package

start:
	@mkdir -p tmp/onos
	docker-compose up -d

stop:
	docker-compose down -t0

restart: reset start

onos-cli:
	$(info *** Connecting to the ONOS CLI... password: rocks)
	$(info *** Top exit press Ctrl-D)
	@ssh -o "UserKnownHostsFile=/dev/null" -o "StrictHostKeyChecking=no" -o LogLevel=ERROR -p 8101 onos@localhost

onos-log:
	docker-compose logs -f onos

onos-ui:
	open ${onos_url}/ui

mn-cli:
	$(info *** Attaching to Mininet CLI...)
	$(info *** To detach press Ctrl-D (Mininet will keep running))
	-@docker attach --detach-keys "ctrl-d" $(shell docker-compose ps -q mininet) || echo "*** Detached from Mininet CLI"

mn-log:
	docker logs -f mininet

netcfg:
	$(info *** Pushing netcfg.json to ONOS...)
	${onos_curl} -X POST -H 'Content-Type:application/json' \
		${onos_url}/v1/network/configuration -d@./mininet/netcfg.json
	@echo

reset: stop
	-rm -rf ./tmp

clean:
	-rm -rf p4src/build
	-rm -rf app/target
	-rm -rf app/src/main/resources/bmv2

deep-clean: clean
	-docker container rm ${app_build_container_name}

p4-build-bmv2: p4src/main.p4
	$(info *** Building P4 program...)
	@mkdir -p p4src/build/bmv2
	docker run --rm -v ${curr_dir}:/workdir -w /workdir ${P4C_IMG} \
		p4c-bm2-ss --arch v1model -o p4src/build/bmv2/bmv2.json \
		-D CPU_PORT=255 \
		--p4runtime-files p4src/build/bmv2/p4info.txt --Wdisable=unsupported \
		p4src/main.p4
	echo "255" > p4src/build/bmv2/cpu-port.txt
	@echo "*** P4 program compiled successfully! Output files are in p4src/build"

# Create container once, use it many times to preserve mvn repo cache.
_create_mvn_container:
	@if ! docker container ls -a --format '{{.Names}}' | grep -q ${app_build_container_name} ; then \
		docker create -v ${curr_dir}/app:/mvn-src -w /mvn-src --name ${app_build_container_name} ${MAVEN_IMG} mvn clean package; \
	fi

_copy_p4c_out:
	$(info *** Copying p4c outputs to app resources...)
	@mkdir -p app/src/main/resources/bmv2
	cp -f p4src/build/bmv2/p4info.txt app/src/main/resources/bmv2/
	cp -f p4src/build/bmv2/bmv2.json app/src/main/resources/bmv2/
	cp -f p4src/build/bmv2/cpu-port.txt app/src/main/resources/bmv2/

_mvn_package:
	$(info *** Building ONOS app...)
	@mkdir -p app/target
	@docker start -a -i ${app_build_container_name}

app-build: p4-build-bmv2 _copy_p4c_out _create_mvn_container _mvn_package
	$(info *** ONOS app .oar package created succesfully)
	@ls -1 app/target/*.oar

app-install:
	$(info *** Installing and activating app in ONOS...)
	${onos_curl} -X POST -HContent-Type:application/octet-stream \
		'${onos_url}/v1/applications?activate=true' \
		--data-binary @app/target/stratum-pipeconf-1.0-SNAPSHOT.oar
	@echo

app-uninstall:
	$(info *** Uninstalling app from ONOS (if present)...)
	-${onos_curl} -X DELETE ${onos_url}/v1/applications/${app_name}
	@echo

app-reload: app-uninstall app-install

mn-single:
	docker run --privileged --rm -it -v /tmp/mn-stratum:/tmp -p 50001:50001 ${MN_STRATUM_IMG}
