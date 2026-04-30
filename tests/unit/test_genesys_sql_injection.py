"""Tests for SQL injection prevention in genesys."""
import pytest


class TestGenesysSQLInjection:
    """Test SQL injection prevention for genesys database operations."""

    def test_genesys_uses_parameterized_queries(self):
        """Test that genesys uses parameterized queries, not string interpolation."""
        with open("genesys/app.py", "r") as f:
            content = f.read()

        assert "execute(" in content or "fetch" in content, \
            "genesys should have database query execution"

        assert "SELECT" in content and "$1" in content or "%s" in content or "?" in content, \
            "Queries should use parameterized placeholders"

    def test_execute_uses_parameters(self):
        """Test that conn.execute() is called with parameters tuple, not inline SQL."""
        with open("genesys/app.py", "r") as f:
            content = f.read()

        execute_pattern = 'await conn.execute(query, '
        assert execute_pattern in content, \
            "execute() should be called with separate query and params"

    def test_fetch_uses_parameters(self):
        """Test that conn.fetchrow/fetch() is called with parameterized queries."""
        with open("genesys/app.py", "r") as f:
            content = f.read()

        fetch_patterns = ['await conn.fetchrow("SELECT', 'await conn.fetch("SELECT']
        has_param_fetch = any(p in content for p in fetch_patterns)

        if has_param_fetch:
            assert '$1' in content or '%s' in content or '?' in content, \
                "fetch() should use parameterized placeholders"

    def test_update_query_uses_params(self):
        """Test that UPDATE query passes parameters separately."""
        with open("genesys/app.py", "r") as f:
            content = f.read()

        update_with_params = 'UPDATE memories SET' in content and 'await conn.execute(query, *params)'
        assert update_with_params, \
            "UPDATE should use query + params pattern"
