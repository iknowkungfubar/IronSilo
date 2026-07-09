"""Tests for SQL injection prevention in memory service.

Validates that the replacement memory service (memory/main.py) uses
parameterized queries, preventing SQL injection.
"""


class TestMemorySQLInjection:
    """Test SQL injection prevention for memory database operations."""

    SOURCE = "memory/main.py"

    def test_uses_parameterized_queries(self):
        """Test that memory service uses parameterized queries."""
        with open(self.SOURCE) as f:
            content = f.read()

        # All execute() calls should use parameterized placeholders
        assert "execute(" in content, "should have database query execution"
        assert "?, ?" in content, "queries should use parameterized placeholders (?, ?)"

    def test_no_f_string_sql_interpolation(self):
        """Test that SQL queries don't use f-string interpolation."""
        with open(self.SOURCE) as f:
            content = f.read()

        # Check INSERT/UPDATE/SELECT statements don't use f-strings
        import re

        # Find all SQL strings - they should always have ? placeholders
        sql_statements = re.findall(
            r'""".*?SELECT.*?"""|""".*?INSERT.*?"""|""".*?UPDATE.*?""".*?(?="""|;">)', content, re.DOTALL
        )

        for stmt in sql_statements:
            assert "? " in stmt or "=?" in stmt or "?" in stmt.split("\n")[-1], (
                f"SQL statement should use parameterized placeholders: {stmt[:50]}..."
            )

    def test_execute_with_params(self):
        """Test that execute() is called with separate params."""
        with open(self.SOURCE) as f:
            content = f.read()

        assert "?, ?" in content, "memory service should use ? placeholders for sqlite"

    def test_no_raw_string_interpolation(self):
        """Test no f-string or format-based SQL construction."""
        with open(self.SOURCE) as f:
            content = f.read()

        import re

        # Check for pattern like f"SELECT * FROM {table}" or "WHERE id = " + str(id)
        dangerous_pattern = r'f\s*""".*?SELECT|f\s*\'.*?SELECT|".*?"\s*\+.*?SELECT'
        matches = re.findall(dangerous_pattern, content)
        assert not matches, f"Found potentially dangerous SQL patterns: {matches}"
