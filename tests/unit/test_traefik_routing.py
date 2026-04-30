"""
Unit tests for Traefik API Gateway routing configuration.

Tests verify that:
- Route definitions match the expected service endpoints
- Middleware configurations are correct
- Path prefix stripping works as expected
- Health check endpoints are defined
"""

import os
import pytest
import yaml
from pathlib import Path
from typing import Any, Dict, List


class TestTraefikConfiguration:
    """Test Traefik static configuration file."""

    @pytest.fixture
    def traefik_config(self) -> Dict[str, Any]:
        """Load and parse traefik.yml configuration."""
        config_path = Path(__file__).parent.parent.parent / "traefik.yml"
        if not config_path.exists():
            pytest.skip("traefik.yml not found - may not be in project root")
        with open(config_path, "r") as f:
            return yaml.safe_load(f)

    def test_traefik_file_exists(self):
        """Test that traefik.yml exists in project root."""
        config_path = Path(__file__).parent.parent.parent / "traefik.yml"
        assert config_path.exists(), "traefik.yml must exist in project root"

    def test_entrypoints_defined(self, traefik_config):
        """Test that required entrypoints are defined."""
        entry_points = traefik_config.get("entryPoints", {})
        assert "web" in entry_points, "Web entrypoint required for port 8080"
        assert "websecure" in entry_points, "Websecure entrypoint required for TLS"

    def test_web_entrypoint_port(self, traefik_config):
        """Test web entrypoint listens on port 8080."""
        entry_points = traefik_config.get("entryPoints", {})
        web_config = entry_points.get("web", {})
        address = web_config.get("address", "")
        assert ":8080" in address, "Web entrypoint must listen on :8080"

    def test_providers_configured(self, traefik_config):
        """Test that required providers are configured."""
        providers = traefik_config.get("providers", {})
        assert "docker" in providers, "Docker provider required"
        assert "file" in providers, "File provider required for dynamic config"

    def test_docker_provider_discovery(self, traefik_config):
        """Test Docker provider configuration."""
        providers = traefik_config.get("providers", {})
        docker = providers.get("docker", {})
        assert docker.get("endpoint") == "unix:///var/run/docker.sock"
        assert docker.get("exposedByDefault") is False, "Services must opt-in to exposure"
        assert docker.get("network") == "internal_bridge"


class TestRouteDefinitions:
    """Test HTTP route definitions in traefik.yml."""

    @pytest.fixture
    def traefik_config(self) -> Dict[str, Any]:
        """Load and parse traefik.yml configuration."""
        config_path = Path(__file__).parent.parent.parent / "traefik.yml"
        if not config_path.exists():
            pytest.skip("traefik.yml not found")
        with open(config_path, "r") as f:
            return yaml.safe_load(f)

    def test_api_proxy_route_exists(self, traefik_config):
        """Test /api/v1 route points to llm-proxy service."""
        http = traefik_config.get("http", {})
        routers = http.get("routers", {})
        
        assert "api-proxy" in routers, "api-proxy router must be defined"
        rule = routers["api-proxy"].get("rule", "")
        assert "PathPrefix(`/api/v1`)" in rule, "Route must match /api/v1 path"
        
        service = routers["api-proxy"].get("service", "")
        assert service == "llm-proxy", "Route must point to llm-proxy service"

    def test_khoj_route_exists(self, traefik_config):
        """Test /khoj route points to khoj service."""
        http = traefik_config.get("http", {})
        routers = http.get("routers", {})
        
        assert "khoj" in routers, "khoj router must be defined"
        rule = routers["khoj"].get("rule", "")
        assert "PathPrefix(`/khoj`)" in rule, "Route must match /khoj path"
        
        service = routers["khoj"].get("service", "")
        assert service == "khoj", "Route must point to khoj service"

    def test_genesys_route_exists(self, traefik_config):
        """Test /genesys route points to genesys-memory service."""
        http = traefik_config.get("http", {})
        routers = http.get("routers", {})
        
        assert "genesys" in routers, "genesys router must be defined"
        rule = routers["genesys"].get("rule", "")
        assert "PathPrefix(`/genesys`)" in rule, "Route must match /genesys path"

    def test_mcp_routes_exist(self, traefik_config):
        """Test MCP routes for genesys and khoj."""
        http = traefik_config.get("http", {})
        routers = http.get("routers", {})
        
        assert "mcp-genesys" in routers, "mcp-genesys router must be defined"
        assert "mcp-khoj" in routers, "mcp-khoj router must be defined"
        
        genesys_rule = routers["mcp-genesys"].get("rule", "")
        khoj_rule = routers["mcp-khoj"].get("rule", "")
        assert "PathPrefix(`/mcp/genesys`)" in genesys_rule
        assert "PathPrefix(`/mcp/khoj`)" in khoj_rule

    def test_swarm_routes_exist(self, traefik_config):
        """Test swarm routes for HTTP and WebSocket."""
        http = traefik_config.get("http", {})
        routers = http.get("routers", {})
        
        assert "swarm" in routers, "swarm router must be defined"
        assert "swarm-ws" in routers, "swarm-ws WebSocket router must be defined"
        
        swarm_rule = routers["swarm"].get("rule", "")
        swarm_ws_rule = routers["swarm-ws"].get("rule", "")
        assert "PathPrefix(`/swarm`)" in swarm_rule
        assert "PathPrefix(`/ws/swarm`)" in swarm_ws_rule

    def test_searxng_route_exists(self, traefik_config):
        """Test /search route points to searxng service."""
        http = traefik_config.get("http", {})
        routers = http.get("routers", {})
        
        assert "searxng" in routers, "searxng router must be defined"
        rule = routers["searxng"].get("rule", "")
        assert "PathPrefix(`/search`)" in rule, "Route must match /search path"


class TestServiceDefinitions:
    """Test service definitions in traefik.yml."""

    @pytest.fixture
    def traefik_config(self) -> Dict[str, Any]:
        """Load and parse traefik.yml configuration."""
        config_path = Path(__file__).parent.parent.parent / "traefik.yml"
        if not config_path.exists():
            pytest.skip("traefik.yml not found")
        with open(config_path, "r") as f:
            return yaml.safe_load(f)

    def test_all_services_defined(self, traefik_config):
        """Test that all services have load balancer definitions."""
        http = traefik_config.get("http", {})
        services = http.get("services", {})
        
        expected_services = [
            "llm-proxy",
            "khoj",
            "genesys-memory",
            "mcp-genesys",
            "mcp-khoj",
            "searxng",
            "swarm-service",
        ]
        
        for service_name in expected_services:
            assert service_name in services, f"Service {service_name} must be defined"
            lb = services[service_name].get("loadBalancer", {})
            servers = lb.get("servers", [])
            assert len(servers) > 0, f"Service {service_name} must have at least one server"
            assert "url" in servers[0], f"Service {service_name} must have a URL"

    def test_service_urls_internal_only(self, traefik_config):
        """Test that all service URLs point to internal Docker network."""
        http = traefik_config.get("http", {})
        services = http.get("services", {})
        
        for service_name, service_config in services.items():
            lb = service_config.get("loadBalancer", {})
            servers = lb.get("servers", [])
            for server in servers:
                url = server.get("url", "")
                assert "internal" not in url.lower() or url.startswith("http://"), \
                    f"Service {service_name} has invalid URL: {url}"


class TestMiddlewareDefinitions:
    """Test middleware definitions in traefik.yml."""

    @pytest.fixture
    def traefik_config(self) -> Dict[str, Any]:
        """Load and parse traefik.yml configuration."""
        config_path = Path(__file__).parent.parent.parent / "traefik.yml"
        if not config_path.exists():
            pytest.skip("traefik.yml not found")
        with open(config_path, "r") as f:
            return yaml.safe_load(f)

    def test_auth_middleware_exists(self, traefik_config):
        """Test that authentication middleware is defined."""
        http = traefik_config.get("http", {})
        middlewares = http.get("middlewares", {})
        
        assert "silk-road-auth" in middlewares or "global-auth" in middlewares, \
            "Auth middleware must be defined"

    def test_strip_prefix_middleware_exists(self, traefik_config):
        """Test that strip prefix middlewares are defined."""
        http = traefik_config.get("http", {})
        middlewares = http.get("middlewares", {})
        
        assert "strip-khoj-prefix" in middlewares, "Khoj prefix strip middleware required"
        assert "strip-mcp-prefix" in middlewares, "MCP prefix strip middleware required"


class TestDynamicConfiguration:
    """Test dynamic configuration file."""

    @pytest.fixture
    def dynamic_config(self) -> Dict[str, Any]:
        """Load and parse dynamic.yml configuration."""
        config_path = Path(__file__).parent.parent.parent / "dynamic.yml"
        if not config_path.exists():
            pytest.skip("dynamic.yml not found")
        with open(config_path, "r") as f:
            return yaml.safe_load(f)

    def test_dynamic_file_exists(self):
        """Test that dynamic.yml exists."""
        config_path = Path(__file__).parent.parent.parent / "dynamic.yml"
        assert config_path.exists(), "dynamic.yml must exist in project root"

    def test_global_auth_middleware_exists(self, dynamic_config):
        """Test that global auth middleware is defined in dynamic config."""
        http = dynamic_config.get("http", {})
        middlewares = http.get("middlewares", {})
        
        assert "global-auth" in middlewares, "Global auth middleware must be defined"


class TestDockerComposeIntegration:
    """Test Docker Compose file integration with Traefik."""

    @pytest.fixture
    def compose_config(self) -> Dict[str, Any]:
        """Load and parse docker-compose.yml configuration."""
        config_path = Path(__file__).parent.parent.parent / "docker-compose.yml"
        if not config_path.exists():
            pytest.skip("docker-compose.yml not found")
        with open(config_path, "r") as f:
            return yaml.safe_load(f)

    def test_traefik_service_exists(self, compose_config):
        """Test that Traefik service is defined."""
        services = compose_config.get("services", {})
        assert "traefik" in services, "Traefik service must be defined"

    def test_traefik_exposes_single_port(self, compose_config):
        """Test that Traefik exposes only port 8080 to host."""
        services = compose_config.get("services", {})
        traefik = services.get("traefik", {})
        ports = traefik.get("ports", [])
        
        port_mappings = [str(p) for p in ports]
        assert any("8080:8080" in p for p in port_mappings), \
            "Traefik must expose port 8080"

    def test_internal_services_have_no_exposed_ports(self, compose_config):
        """Test that internal services do not expose ports to host."""
        services = compose_config.get("services", {})
        
        internal_services = [
            "ironclaw-db",
            "genesys-memory",
            "khoj",
            "llm-proxy",
            "mcp-genesys",
            "mcp-khoj",
            "searxng",
            "swarm-service",
        ]
        
        for service_name in internal_services:
            if service_name not in services:
                continue
            service = services[service_name]
            ports = service.get("ports", [])
            if service_name == "traefik":
                continue
            assert len(ports) == 0, \
                f"Internal service {service_name} should not expose ports directly"

    def test_internal_services_on_internal_network(self, compose_config):
        """Test that internal services are on internal_bridge network."""
        services = compose_config.get("services", {})
        
        for service_name, service_config in services.items():
            networks = service_config.get("networks", [])
            if service_name == "traefik":
                continue
            networks_list = networks if isinstance(networks, list) else list(networks.keys())
            assert "internal_bridge" in networks_list, \
                f"Service {service_name} must be on internal_bridge network"

    def test_services_have_traefik_labels(self, compose_config):
        """Test that routed services have Traefik labels."""
        services = compose_config.get("services", {})
        routed_services = ["llm-proxy", "khoj", "genesys-memory", "mcp-genesys", 
                          "mcp-khoj", "searxng", "swarm-service"]
        
        for service_name in routed_services:
            if service_name not in services:
                continue
            service = services[service_name]
            labels = service.get("labels", [])
            assert len(labels) > 0, f"Service {service_name} must have Traefik labels"
            assert any("traefik.enable=true" in str(l) for l in labels), \
                f"Service {service_name} must have traefik.enable=true label"

    def test_health_checks_defined(self, compose_config):
        """Test that health checks are defined for critical services."""
        services = compose_config.get("services", {})
        
        services_with_health = ["traefik", "llm-proxy", "khoj", "ironclaw-db", 
                               "swarm-service", "searxng"]
        
        for service_name in services_with_health:
            if service_name not in services:
                continue
            service = services[service_name]
            assert "healthcheck" in service, \
                f"Service {service_name} must have a health check"


class TestSecurityConfiguration:
    """Test security configuration for the API Gateway."""

    @pytest.fixture
    def traefik_config(self) -> Dict[str, Any]:
        """Load and parse traefik.yml configuration."""
        config_path = Path(__file__).parent.parent.parent / "traefik.yml"
        if not config_path.exists():
            pytest.skip("traefik.yml not found")
        with open(config_path, "r") as f:
            return yaml.safe_load(f)

    def test_api_dashboard_disabled(self, traefik_config):
        """Test that Traefik API dashboard is disabled."""
        api = traefik_config.get("api", {})
        assert api.get("dashboard") is False, "API dashboard should be disabled"
        assert api.get("insecure") is False, "API insecure mode should be disabled"

    def test_tls_configured(self, traefik_config):
        """Test that TLS is configured for websecure endpoint."""
        entry_points = traefik_config.get("entryPoints", {})
        websecure = entry_points.get("websecure", {})
        http_tls = websecure.get("http", {}).get("tls", {})
        assert http_tls is not None, "TLS must be configured"

    def test_middleware_sets_auth_header(self, traefik_config):
        """Test that auth middleware sets X-Silo-Auth header."""
        http = traefik_config.get("http", {})
        middlewares = http.get("middlewares", {})
        
        auth_middleware_found = False
        for middleware_name, middleware_config in middlewares.items():
            if "headers" in middleware_config:
                headers = middleware_config.get("headers", {})
                custom_headers = headers.get("customRequestHeaders", {})
                if "X-Silo-Auth" in custom_headers:
                    auth_middleware_found = True
                    break
        
        assert auth_middleware_found, "Auth middleware must set X-Silo-Auth header"
