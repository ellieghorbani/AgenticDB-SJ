"""AgenticDB copilot components.

Modules are intentionally imported explicitly by callers. Keeping the package
initializer lightweight avoids loading database and model dependencies when a
single planning or embedding component is imported for tests or scripts.
"""

__all__: list[str] = []
