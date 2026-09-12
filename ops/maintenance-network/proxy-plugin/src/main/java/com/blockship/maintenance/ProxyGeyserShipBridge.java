package com.blockship.maintenance;

import org.geysermc.geyser.api.GeyserApi;
import org.geysermc.geyser.api.entity.custom.CustomEntityDefinition;
import org.geysermc.geyser.api.event.EventRegistrar;
import org.geysermc.geyser.api.event.java.ServerSpawnEntityEvent;
import org.slf4j.Logger;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

/** Reads BlockShip's same-host entity markers before Geyser translates the spawn packet. */
final class ProxyGeyserShipBridge {

    private final Logger logger;
    private final Path markerDirectory;
    private final EventRegistrar registrar;

    private ProxyGeyserShipBridge(Object plugin, Logger logger, Path markerDirectory) {
        this.logger = logger;
        this.markerDirectory = markerDirectory;
        this.registrar = EventRegistrar.of(plugin);
    }

    static ProxyGeyserShipBridge install(Object plugin, Logger logger, Path markerDirectory)
            throws IOException {
        Files.createDirectories(markerDirectory);
        ProxyGeyserShipBridge bridge = new ProxyGeyserShipBridge(plugin, logger, markerDirectory);
        GeyserApi.api().eventBus().subscribe(
                bridge.registrar, ServerSpawnEntityEvent.class, bridge::onServerSpawn);
        logger.info("Proxy-side Bedrock ship bridge subscribed; markers={}", markerDirectory);
        return bridge;
    }

    private void onServerSpawn(ServerSpawnEntityEvent event) {
        Path marker = markerDirectory.resolve(event.uuid() + ".entity");
        final String identifier;
        try {
            if (Files.notExists(marker)) return;
            identifier = Files.readString(marker, StandardCharsets.UTF_8).trim();
        } catch (IOException failure) {
            logger.debug("Could not read ship marker {}: {}", marker, failure.toString());
            return;
        }
        if (identifier.isEmpty()) return;
        CustomEntityDefinition definition = CustomEntityDefinition.of(identifier);
        if (definition.registered()) event.definition(definition);
    }

    void close() {
        try {
            GeyserApi.api().eventBus().unregisterAll(registrar);
        } catch (Throwable failure) {
            logger.debug("Could not unregister the Bedrock ship bridge: {}", failure.toString());
        }
    }
}
