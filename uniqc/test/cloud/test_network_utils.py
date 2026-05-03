"""Tests for network_utils module.

This module tests the proxy detection and connectivity checking utilities.
"""

from __future__ import annotations

import os
import socket
import unittest
from unittest.mock import MagicMock, patch

import pytest

from uniqc.backend_adapter.network_utils import (
    check_proxy_connectivity,
    detect_system_proxy,
    get_ibm_proxy_from_config,
)
from uniqc.backend_adapter.network_utils import (
    test_ibm_connectivity as check_ibm_connectivity,
)
from uniqc.test.cloud._config_helpers import platform_has_token, write_uniqc_config


def ibm_config_has_proxy() -> bool:
    """Return True when the active IBM config has a non-empty proxy."""
    try:
        from uniqc.backend_adapter.config import get_ibm_config

        return bool(get_ibm_proxy_from_config(get_ibm_config()))
    except Exception:
        return False


def unused_local_port() -> int:
    """Return a currently unused localhost TCP port for unreachable-proxy checks."""
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


class TestDetectSystemProxy(unittest.TestCase):
    """Tests for detect_system_proxy function."""

    def test_detect_no_proxy(self):
        """Test detection when no proxy is set."""
        # Use clear=True to completely isolate the test environment
        with patch.dict(os.environ, {}, clear=True):
            result = detect_system_proxy()
            self.assertIsNone(result["http"])
            self.assertIsNone(result["https"])

    def test_detect_http_proxy(self):
        """Test detection of HTTP proxy."""
        with patch.dict(os.environ, {"HTTP_PROXY": "http://proxy.example.com:8080"}, clear=True):
            result = detect_system_proxy()
            self.assertEqual(result["http"], "http://proxy.example.com:8080")
            self.assertIsNone(result["https"])

    def test_detect_https_proxy(self):
        """Test detection of HTTPS_PROXY."""
        with patch.dict(os.environ, {"HTTPS_PROXY": "https://proxy.example.com:8080"}, clear=True):
            result = detect_system_proxy()
            self.assertEqual(result["https"], "https://proxy.example.com:8080")

    def test_detect_both_proxies(self):
        """Test detection of both HTTP and HTTPS proxies."""
        env_vars = {
            "HTTP_PROXY": "http://http-proxy.example.com:8080",
            "HTTPS_PROXY": "https://https-proxy.example.com:8443"
        }
        with patch.dict(os.environ, env_vars, clear=True):
            result = detect_system_proxy()
            self.assertEqual(result["http"], "http://http-proxy.example.com:8080")
            self.assertEqual(result["https"], "https://https-proxy.example.com:8443")

    def test_detect_http_proxy_lowercase(self):
        """Test detection of http_proxy (lowercase)."""
        with patch.dict(os.environ, {"http_proxy": "http://proxy.example.com:8080"}, clear=True):
            result = detect_system_proxy()
            self.assertEqual(result["http"], "http://proxy.example.com:8080")

    def test_uppercase_takes_precedence(self):
        """Test that uppercase env vars take precedence over lowercase when both exist."""
        env_vars = {
            "HTTP_PROXY": "http://uppercase.example.com:8080",
            "http_proxy": "http://lowercase.example.com:9090"
        }
        with patch.dict(os.environ, env_vars, clear=True):
            result = detect_system_proxy()
            self.assertEqual(result["http"], "http://uppercase.example.com:8080")


class TestCheckProxyConnectivity(unittest.TestCase):
    """Tests for check_proxy_connectivity function."""

    @patch("socket.create_connection")
    def test_proxy_connectivity_success(self, mock_create_connection):
        """Test successful proxy connectivity check."""
        mock_socket = MagicMock()
        mock_create_connection.return_value = mock_socket

        result = check_proxy_connectivity("http://proxy.example.com:8080")

        self.assertTrue(result)
        mock_create_connection.assert_called_once()
        mock_socket.close.assert_called_once()

    @patch("socket.create_connection")
    def test_proxy_connectivity_failure(self, mock_create_connection):
        """Test failed proxy connectivity check."""
        mock_create_connection.side_effect = OSError("Connection refused")

        result = check_proxy_connectivity("http://proxy.example.com:8080")

        self.assertFalse(result)

    def test_proxy_connectivity_invalid_url(self):
        """Test connectivity check with invalid URL."""
        result = check_proxy_connectivity("not-a-valid-url")
        self.assertFalse(result)

    def test_proxy_connectivity_default_port(self):
        """Test connectivity check with URL without port."""
        with patch("socket.create_connection") as mock_create_connection:
            mock_socket = MagicMock()
            mock_create_connection.return_value = mock_socket

            result = check_proxy_connectivity("http://proxy.example.com")

            self.assertTrue(result)
            # Should use default port 80 for http
            call_args = mock_create_connection.call_args
            self.assertEqual(call_args[0][0][1], 80)


class TestGetIbmProxyFromConfig(unittest.TestCase):
    """Tests for get_ibm_proxy_from_config function."""

    def test_no_proxy_config(self):
        """Test with no proxy configuration."""
        config = {"token": "test_token"}
        result = get_ibm_proxy_from_config(config)
        self.assertIsNone(result)

    def test_empty_proxy_config(self):
        """Test with empty proxy configuration."""
        config = {"token": "test_token", "proxy": {}}
        result = get_ibm_proxy_from_config(config)
        self.assertIsNone(result)

    def test_http_proxy_only(self):
        """Test with only HTTP proxy configured."""
        config = {
            "token": "test_token",
            "proxy": {"http": "http://proxy.example.com:8080"}
        }
        result = get_ibm_proxy_from_config(config)
        self.assertEqual(result, {"http": "http://proxy.example.com:8080"})

    def test_https_proxy_only(self):
        """Test with only HTTPS proxy configured."""
        config = {
            "token": "test_token",
            "proxy": {"https": "https://proxy.example.com:8443"}
        }
        result = get_ibm_proxy_from_config(config)
        self.assertEqual(result, {"https": "https://proxy.example.com:8443"})

    def test_both_proxies(self):
        """Test with both HTTP and HTTPS proxies configured."""
        config = {
            "token": "test_token",
            "proxy": {
                "http": "http://http-proxy.example.com:8080",
                "https": "https://https-proxy.example.com:8443"
            }
        }
        result = get_ibm_proxy_from_config(config)
        self.assertEqual(result, {
            "http": "http://http-proxy.example.com:8080",
            "https": "https://https-proxy.example.com:8443"
        })

    def test_empty_proxy_values(self):
        """Test with empty proxy values."""
        config = {
            "token": "test_token",
            "proxy": {
                "http": "",
                "https": ""
            }
        }
        result = get_ibm_proxy_from_config(config)
        self.assertIsNone(result)


class TestTestIbmConnectivity:
    """Unit tests for check_ibm_connectivity behavior."""

    def test_no_token_provided_and_no_yaml_token(self, monkeypatch, tmp_path):
        """Test when no token is provided and the YAML config has no IBM token."""
        write_uniqc_config(tmp_path, {"ibm": {"token": ""}})
        monkeypatch.setattr("uniqc.backend_adapter.config.CONFIG_FILE", tmp_path / ".uniqc" / "config.yaml")

        result = check_ibm_connectivity()

        assert result["success"] is False
        assert "token not provided" in result["message"]
        assert result["response_time_ms"] is None

    def test_uses_yaml_token(self, monkeypatch, tmp_path):
        """Test that the active YAML IBM token is used when token is not provided."""
        write_uniqc_config(tmp_path, {"ibm": {"token": "yaml_token_123"}})
        monkeypatch.setattr("uniqc.backend_adapter.config.CONFIG_FILE", tmp_path / ".uniqc" / "config.yaml")

        # Mock the actual HTTP request to avoid network calls
        with patch("urllib.request.OpenerDirector.open") as mock_open:
            mock_response = MagicMock()
            mock_response.getcode.return_value = 200
            mock_open.return_value.__enter__ = MagicMock(return_value=mock_response)
            mock_open.return_value.__exit__ = MagicMock(return_value=False)

            result = check_ibm_connectivity()

            # Should attempt to connect (actual result depends on mock)
            assert result is not None

    def test_with_explicit_proxy(self):
        """Test with explicit proxy configuration."""
        proxy = {"https": "http://proxy.example.com:8080"}
        with patch("urllib.request.OpenerDirector.open") as mock_open:
            mock_response = MagicMock()
            mock_response.getcode.return_value = 200
            mock_open.return_value.__enter__ = MagicMock(return_value=mock_response)
            mock_open.return_value.__exit__ = MagicMock(return_value=False)

            result = check_ibm_connectivity(
                token="test_token",
                proxy=proxy
            )

        # Verify proxy is recorded in result
        assert result["proxy_used"] == proxy

    def test_with_string_proxy(self):
        """Test with string proxy configuration."""
        with patch("urllib.request.OpenerDirector.open") as mock_open:
            mock_response = MagicMock()
            mock_response.getcode.return_value = 200
            mock_open.return_value.__enter__ = MagicMock(return_value=mock_response)
            mock_open.return_value.__exit__ = MagicMock(return_value=False)

            result = check_ibm_connectivity(
                token="test_token",
                proxy="http://proxy.example.com:8080"
            )

            # String proxy should be converted to dict
            assert result["proxy_used"] is not None

    def test_connectivity_failure(self):
        """Test handling of connection failure."""
        with patch("urllib.request.OpenerDirector.open") as mock_open:
            mock_open.side_effect = Exception("Connection refused")

            result = check_ibm_connectivity(token="test_token")

            assert result["success"] is False
            assert "Connection failed" in result["message"]
            assert result["response_time_ms"] is not None


@pytest.mark.cloud
class TestRealIbmConnectivity:
    """Real IBM connectivity and proxy behavior tests."""

    @pytest.mark.skipif(
        not platform_has_token("ibm"),
        reason="ibm.token not set in ~/.uniqc/config.yaml",
    )
    def test_real_ibm_connectivity_without_proxy(self):
        """Test real IBM endpoint connectivity without an explicit proxy."""
        result = check_ibm_connectivity(proxy={})

        assert result["success"] is True
        assert result["response_time_ms"] is not None

    @pytest.mark.skipif(
        not platform_has_token("ibm") or not ibm_config_has_proxy(),
        reason="ibm.token and ibm.proxy not set in ~/.uniqc/config.yaml",
    )
    def test_real_ibm_connectivity_with_config_proxy(self):
        """Test real IBM endpoint connectivity through configured proxy."""
        from uniqc.backend_adapter.config import get_ibm_config

        proxy = get_ibm_proxy_from_config(get_ibm_config())
        assert proxy

        result = check_ibm_connectivity(proxy=proxy)

        assert result["success"] is True
        assert result["proxy_used"] == proxy
        assert result["response_time_ms"] is not None

    def test_unreachable_proxy_fails(self):
        """Test that an unreachable proxy produces a connectivity failure."""
        port = unused_local_port()
        proxy = {"https": f"http://127.0.0.1:{port}"}

        result = check_ibm_connectivity(
            token="test_token",
            proxy=proxy,
            timeout=0.2,
        )

        assert result["success"] is False
        assert "Connection failed" in result["message"]
        assert result["proxy_used"] == proxy
        assert result["response_time_ms"] is not None


class TestIntegration:
    """Unit tests combining multiple network utility functions."""

    def test_system_proxy_to_ibm_connectivity(self, monkeypatch, tmp_path):
        """Test full flow from system proxy detection to IBM connectivity."""
        write_uniqc_config(tmp_path, {"ibm": {"token": "test_token"}})
        monkeypatch.setattr("uniqc.backend_adapter.config.CONFIG_FILE", tmp_path / ".uniqc" / "config.yaml")
        with patch.dict(os.environ, {
            "HTTPS_PROXY": "http://proxy.example.com:8080",
        }):
            # Detect system proxy
            proxies = detect_system_proxy()
            assert proxies["https"] == "http://proxy.example.com:8080"

            # Test IBM connectivity with detected proxy
            with patch("urllib.request.OpenerDirector.open") as mock_open:
                mock_response = MagicMock()
                mock_response.getcode.return_value = 200
                mock_open.return_value.__enter__ = MagicMock(return_value=mock_response)
                mock_open.return_value.__exit__ = MagicMock(return_value=False)

                result = check_ibm_connectivity(proxy=proxies)
                assert result["success"] is True


if __name__ == "__main__":
    unittest.main()
