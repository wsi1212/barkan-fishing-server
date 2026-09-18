// ★JDK 25 툴체인 자동 조달 — 이 맥에는 25가 없다(21이 최신). foojay 리졸버가 없으면
//   build.sh 가 "Java 25 JDK가 필요합니다"로 멈춰서, 무중단 Geyser 리로드 경로가
//   구현돼 있는데도 «빌드를 못 해» 2일간 배포되지 못했다(2026-09-19).
plugins {
    id("org.gradle.toolchains.foojay-resolver-convention") version "1.0.0"
}

rootProject.name = "barkan-maintenance-network"

include("proxy-plugin", "waiting-plugin")
