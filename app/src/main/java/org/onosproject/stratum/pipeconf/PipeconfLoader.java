/*
 * Copyright 2020-present Open Networking Foundation
 *
 * SPDX-License-Identifier: Apache-2.0
 */

package org.onosproject.stratum.pipeconf;

import com.google.common.collect.ImmutableSet;
import com.google.common.collect.Lists;
import org.onosproject.core.ApplicationId;
import org.onosproject.core.CoreService;
import org.onosproject.net.behaviour.Pipeliner;
import org.onosproject.net.pi.model.*;
import org.onosproject.net.pi.service.PiPipeconfService;
import org.onosproject.p4runtime.model.P4InfoParser;
import org.onosproject.p4runtime.model.P4InfoParserException;
import org.osgi.service.component.annotations.Activate;
import org.osgi.service.component.annotations.Component;
import org.osgi.service.component.annotations.Deactivate;
import org.osgi.service.component.annotations.Reference;
import org.osgi.service.component.annotations.ReferenceCardinality;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.FileNotFoundException;
import java.net.URL;
import java.util.Collection;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * A component which among other things registers the fabricDeviceConfig to the
 * netcfg subsystem.
 */
@Component(immediate = true, service = PipeconfLoader.class)
public class PipeconfLoader {

    public static final String PIPELINE_APP_NAME = "org.onosproject.stratum-pipeconf";
    private static final String SEP = File.separator;

    private static final Logger log =
            LoggerFactory.getLogger(PipeconfLoader.class.getName());

    @Reference(cardinality = ReferenceCardinality.MANDATORY)
    private CoreService coreService;

    @Reference(cardinality = ReferenceCardinality.MANDATORY)
    private PiPipeconfService piPipeconfService;



    private Collection<PiPipeconf> pipeconfs;
    private ApplicationId appId;

    // For the sake of simplicity and to facilitate reading logs, use a
    // single-thread executor to serialize all configuration tasks.
    private final ExecutorService executorService = Executors.newSingleThreadExecutor();

    @Activate
    protected void activate() {
        appId = coreService.registerApplication(PIPELINE_APP_NAME);
        // Registers all pipeconf at component activation.
        pipeconfs = buildAllPipeconfs();
        pipeconfs.forEach(piPipeconfService::register);
        log.info("Started");
    }

    @Deactivate
    protected void deactivate() {
        pipeconfs.stream()
            .map(PiPipeconf::id)
            .forEach(piPipeconfService::unregister);
        log.info("Stopped");
    }

    private Collection<PiPipeconf> buildAllPipeconfs() {
        try {
            return ImmutableSet.of(
                    bmv2Pipeconf(),
                    fpmPipeconf()
            );
        } catch (FileNotFoundException e) {
            log.warn(e.getMessage());
        }
        return Collections.emptySet();
    }

    private PiPipeconf bmv2Pipeconf() throws FileNotFoundException {
        final URL bmv2JsonUrl = this.getClass().getResource("/bmv2/bmv2.json");
        final URL p4InfoUrl = this.getClass().getResource("/bmv2/p4info.txt");
        final URL cpuPortUrl = this.getClass().getResource("/bmv2/cpu-port.txt");

        checkFileExists(bmv2JsonUrl, "/bmv2/bmv2.json");
        checkFileExists(p4InfoUrl, "/bmv2/p4info.txt");
        checkFileExists(cpuPortUrl, "/bmv2/cpu-port.txt");

        final DefaultPiPipeconf.Builder builder = DefaultPiPipeconf.builder();

        return builder.withId(new PiPipeconfId(PIPELINE_APP_NAME + ".bmv2"))
                .withPipelineModel(parseP4Info(p4InfoUrl))
                .addExtension(PiPipeconf.ExtensionType.BMV2_JSON, bmv2JsonUrl)
                .addExtension(PiPipeconf.ExtensionType.P4_INFO_TEXT, p4InfoUrl)
                .addExtension(PiPipeconf.ExtensionType.CPU_PORT_TXT, cpuPortUrl)
                .addBehaviour(PiPipelineInterpreter.class, BcmBmv2PipelineInterpreter.class)
                .addBehaviour(Pipeliner.class, BcmPipeliner.class)
                .build();
    }

    private PiPipeconf fpmPipeconf() throws FileNotFoundException {
        final URL p4InfoUrl = this.getClass().getResource("/fpm/p4info.txt");
        final URL cpuPortUrl = this.getClass().getResource("/fpm/cpu-port.txt");
        final URL fpmBinUrl = this.getClass().getResource("/fpm/main.pb.bin");

        checkFileExists(p4InfoUrl, "/fpm/p4info.txt");
        checkFileExists(cpuPortUrl, "/fpm/cpu-port.txt");
        checkFileExists(fpmBinUrl, "/fpm/pipeline_config.bin");

        return DefaultPiPipeconf.builder()
                .withId(new PiPipeconfId(PIPELINE_APP_NAME + ".fpm"))
                .withPipelineModel(parseP4Info(p4InfoUrl))
                .addBehaviour(PiPipelineInterpreter.class, BcmPipelineInterpreter.class)
                .addBehaviour(Pipeliner.class, BcmPipeliner.class)
                .addExtension(PiPipeconf.ExtensionType.P4_INFO_TEXT, p4InfoUrl)
                .addExtension(PiPipeconf.ExtensionType.CPU_PORT_TXT, cpuPortUrl)
                .addExtension(PiPipeconf.ExtensionType.STRATUM_FPM_BIN, fpmBinUrl)
                .build();
    }

    private static PiPipelineModel parseP4Info(URL p4InfoUrl) {
        try {
            return P4InfoParser.parse(p4InfoUrl);
        } catch (P4InfoParserException e) {
            // FIXME: propagate exception that can be handled by whoever is
            //  trying to build pipeconfs.
            throw new IllegalStateException(e);
        }
    }

    private void checkFileExists(URL url, String name)
            throws FileNotFoundException {
        if (url == null) {
            throw new FileNotFoundException(name);
        }
    }
}
