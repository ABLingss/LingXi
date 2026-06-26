"""
core.registry — Module registration system for Stock JSON Clipper V2.1.

Provides:
  - BaseModule: Abstract base for all pluggable feature modules
  - ModuleRegistry: Central registry that manages module lifecycle

New features implement BaseModule and register with ModuleRegistry.
The panel UI auto-collects API methods and tab content from all modules.
"""

from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.clipper import StockClipper


class BaseModule:
    """Pluggable feature module base class.

    To add a new feature:
      1. Subclass BaseModule
      2. Override get_api_methods() to expose JS-callable methods
      3. Optionally override get_panel_tab() to add UI tabs
      4. Register via clipper.registry.register(YourModule())

    Lifecycle:
      on_register(clipper) → on_start() → [...running...] → on_stop()
    """

    # Metadata — override in subclasses
    name: str = ""
    description: str = ""
    version: str = "1.0"

    # ---- Lifecycle hooks (override as needed) ----

    def on_register(self, clipper: "StockClipper") -> None:
        """Called when the module is registered with StockClipper.

        Use this to store a reference to the clipper for later use.
        Default: store clipper as self._clipper.
        """
        self._clipper = clipper

    def on_start(self) -> None:
        """Called when the clipper starts (background threads begin)."""

    def on_stop(self) -> None:
        """Called when the clipper stops (graceful shutdown)."""

    # ---- API exposure ----

    def get_api_methods(self) -> Dict[str, Callable]:
        """Return methods exposed to JS via pywebview.api.<name>.

        Keys become `pywebview.api.<key>()` in JavaScript.
        Values are bound methods or plain functions (must accept JSON-serializable args).

        Example:
            return {
                "generate_prompt": self._generate_prompt,
                "quick_analyze": self._quick_analyze,
            }
        """
        return {}

    # ---- Panel UI contributions (optional) ----

    def get_panel_tab(self) -> Optional[Dict[str, str]]:
        """Return a tab definition for the info panel.

        Returns:
            Dict with keys:
              - id: Tab DOM id (e.g. 'tab-formula')
              - title: Tab button text (e.g. '🤖 AI分析')
              - html: Tab body HTML string (optional, can be empty)
            Or None if this module doesn't add a panel tab.
        """
        return None

    def get_panel_css(self) -> Optional[str]:
        """Return additional CSS to inject into the panel <style> block."""
        return None

    def get_panel_js(self) -> Optional[str]:
        """Return additional JavaScript to inject before </script>."""
        return None


class ModuleRegistry:
    """Central registry for all feature modules.

    Usage:
        registry = ModuleRegistry()
        registry.register(PromptModule(), clipper)
        registry.start_all()
    """

    def __init__(self) -> None:
        self._modules: List[BaseModule] = []

    def register(self, module: BaseModule, clipper: "StockClipper") -> None:
        """Register a module and call its on_register hook.

        Args:
            module: A BaseModule instance.
            clipper: The StockClipper instance.
        """
        module.on_register(clipper)
        self._modules.append(module)

    def start_all(self) -> None:
        """Call on_start() on all registered modules."""
        for mod in self._modules:
            try:
                mod.on_start()
            except Exception:
                pass  # Module start failure should not crash the app

    def stop_all(self) -> None:
        """Call on_stop() on all registered modules."""
        for mod in self._modules:
            try:
                mod.on_stop()
            except Exception:
                pass

    def get_all_api_methods(self) -> Dict[str, Callable]:
        """Collect API methods from ALL registered modules.

        Returns:
            Merged dict of all module API methods. Later modules override
            earlier ones on key conflict.

        Returns:
            Flat dict of method_name → callable.
        """
        methods: Dict[str, Callable] = {}
        for mod in self._modules:
            methods.update(mod.get_api_methods())
        return methods

    def get_all_panel_tabs(self) -> List[Dict[str, str]]:
        """Collect panel tab definitions from all modules.

        Returns:
            List of tab dicts from modules that provide them.
        """
        tabs: List[Dict[str, str]] = []
        for mod in self._modules:
            tab = mod.get_panel_tab()
            if tab:
                tabs.append(tab)
        return tabs

    def get_all_panel_css(self) -> str:
        """Collect additional CSS from all modules."""
        parts = []
        for mod in self._modules:
            css = mod.get_panel_css()
            if css:
                parts.append(css)
        return "\n".join(parts)

    def get_all_panel_js(self) -> str:
        """Collect additional JS from all modules."""
        parts = []
        for mod in self._modules:
            js = mod.get_panel_js()
            if js:
                parts.append(js)
        return "\n".join(parts)

    @property
    def modules(self) -> List[BaseModule]:
        """Return the list of registered modules (read-only)."""
        return list(self._modules)
