plugins {
    java
}

dependencies {
    compileOnly("com.velocitypowered:velocity-api:4.1.1")
    annotationProcessor("com.velocitypowered:velocity-api:4.1.1")
    compileOnly("org.geysermc.geyser:api:2.11.2-SNAPSHOT")
}

java {
    toolchain.languageVersion.set(JavaLanguageVersion.of(25))
}

tasks.jar {
    archiveFileName.set("BarkanMaintenanceProxy.jar")
}

tasks.withType<JavaCompile>().configureEach {
    options.compilerArgs.add("-Xlint:deprecation")
}
