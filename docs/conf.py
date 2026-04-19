# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
import pathlib
parent_path = pathlib.Path(__file__).resolve().parent.parent

# Only the project root is needed; uniqc/ lives directly under it.
sys.path.insert(0, os.path.abspath(parent_path))

# Read version from setuptools_scm or git tags
# For stable releases: set DOCS_STABLE_VERSION env var to force clean version

import subprocess
import os

def get_version_from_setuptools_scm(strip_dev=False):
    """Get version from setuptools_scm.

    Args:
        strip_dev: If True, strip .devN+g... suffix to get base version.
                   Used for stable/release builds.
    """
    try:
        from setuptools_scm import get_version
        version = get_version(root=str(parent_path), relative_to=__file__)
        if strip_dev:
            # Extract base version (strip .devN+g... suffix)
            import re
            match = re.match(r'^(\d+\.\d+\.\d+)', version)
            return match.group(1) if match else version
        return version
    except Exception:
        return None

def get_version_from_git_tag():
    """Get clean version from nearest git tag (e.g., v0.3.0 -> 0.3.0)."""
    try:
        result = subprocess.run(
            ['git', 'describe', '--tags', '--abbrev=0'],
            capture_output=True, text=True, check=True,
            cwd=str(parent_path)
        )
        tag = result.stdout.strip()
        return tag[1:] if tag.startswith('v') else tag
    except Exception:
        return None

def get_version_from_metadata():
    """Get version from installed package metadata."""
    try:
        from importlib.metadata import version as get_version, PackageNotFoundError
        return get_version('unified-quantum')
    except (PackageNotFoundError, Exception):
        return None

def get_version_from_file():
    """Get version from _version.py file."""
    try:
        _version_file = parent_path / 'uniqc' / '_version.py'
        if _version_file.exists():
            exec(_version_file.read_text())
            return __version__
    except Exception:
        pass
    return None

# If DOCS_STABLE_VERSION=1, use clean version from git tag (for releases)
# Otherwise, use setuptools_scm which shows dev versions for main branch

# Determine if this is a stable/release build
is_stable = os.environ.get('DOCS_STABLE_VERSION') == '1'

if is_stable:
    release = (
        get_version_from_git_tag() or
        get_version_from_setuptools_scm(strip_dev=True) or
        get_version_from_metadata() or
        get_version_from_file() or
        '0.0.0+unknown'
    )
else:
    # Default: show actual version (including dev versions for unreleased changes)
    release = (
        get_version_from_setuptools_scm(strip_dev=False) or
        get_version_from_git_tag() or
        get_version_from_metadata() or
        get_version_from_file() or
        '0.0.0+unknown'
    )

# Get version for version switcher
version_match = 'stable' if is_stable else 'latest'

copyright = '2025, IAI-USTC-Quantum'
author = ', '.join(['IAI-USTC-Quantum'])
project = 'UnifiedQuantum'

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.doctest',
    'sphinx.ext.intersphinx',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
    'sphinx.ext.mathjax',
    # 'recommonmark',
    'myst_parser',
    'sphinx.ext.viewcode'
]

# -- Options for myst_parser
# See https://myst-parser.readthedocs.io/en/latest/syntax/optional.html
myst_enable_extensions = [
    "amsmath",
    "attrs_inline",
    "attrs_block",
    "colon_fence",
    "deflist",
    "dollarmath",
    "fieldlist",
    "html_admonition",
    "html_image",
    "linkify",
    "replacements",
    "smartquotes",
    "strikethrough",
    "substitution",
    "tasklist",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# Sphinx's autodoc can be configured to mock certain imports so that they don't actually get executed. 
autodoc_mock_imports = ["qiskit", 
                        "qiskit_ibm_provider", 
                        "quafu", 
                        "pandas", 
                        "uniqc_cpp",
                        "qiskit-aer", 
                        "qutip",
                        "qutip_qip",
                        "matplotlib",
                        "matplotlib.pyplot",
                        "pyqpanda3"]

os.environ['SPHINX_DOC_GEN'] = '1'
# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#
# This is also used if you do content translation via gettext catalogs.
# Usually you set "language" from the command line for these cases.
language = 'zh-CN'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store', 'source/uniqc.test.rst']
autodoc_typehints = "description"
source_suffix = {'.rst': 'restructuredtext', '.md': 'markdown'}

# -- Options for HTML output -------------------------------------------------

html_theme = "pydata_sphinx_theme"

import pydata_sphinx_theme, os
_html_theme_path = os.path.dirname(pydata_sphinx_theme.__file__)
html_theme_path = [_html_theme_path]

html_theme_options = {
    "show_nav_level": 1,
    "navigation_with_keys": True,
    "show_toc_level": 2,
    "header_links_before_dropdown": 6,
    # Logo/title configuration - only show project name without version
    "logo": {
        "text": "UnifiedQuantum文档",
    },
    # Version switcher configuration for GitHub Pages
    "switcher": {
        "json_url": "https://iai-ustc-quantum.github.io/UnifiedQuantum/_static/switcher.json",
        "version_match": version_match,
    },
    # Add version switcher to navbar
    "navbar_end": ["theme-switcher", "version-switcher"],
}

suppress_warnings = ["myst.xref_missing"]

# Napoleon: render ``Attributes:`` sections as ``:ivar:`` roles inline instead
# of standalone ``.. attribute::`` directives. Otherwise autodoc also picks up
# the class-level ``name: type = ...`` annotations and registers the same
# attribute twice, producing "duplicate object description" warnings.
napoleon_use_ivar = True

# Autodoc: ignore ``__all__`` in package ``__init__.py`` files so re-exports are
# documented only at their canonical submodule location, not also at the
# package level (which would register each function twice).
autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
    "ignore-module-all": True,
}

# External references (numpy / scipy / torch / python stdlib) are resolved via
# intersphinx. We source the registry from ``intersphinx-registry`` so URLs
# stay in sync with the upstream community table rather than hard-coded here.
from intersphinx_registry import get_intersphinx_mapping

intersphinx_mapping = get_intersphinx_mapping(
    packages={"python", "numpy", "scipy", "torch"},
)
intersphinx_timeout = 5

# Ignore cross-references that autodoc can't resolve but aren't actionable:
# short names in docstrings, re-exports (registered at canonical location),
# external types without an intersphinx inventory, and local type vars.
nitpick_ignore = [
    ("py:class", "QubitInput"),
    ("py:class", "Circuit"),
    ("py:class", "'Circuit'"),
    ("py:class", "QuantumCircuit"),
    ("py:class", "'QuantumCircuit'"),
    ("py:class", "'qiskit.QuantumCircuit'"),
    ("py:class", "qiskit.QuantumCircuit"),
    ("py:class", "'QuantumBackend'"),
    ("py:class", "Path"),
    ("py:class", "QReg"),
    ("py:class", "'QReg'"),
    ("py:class", "ShadowSnapshot"),
    ("py:class", "TaskStore"),
    ("py:class", "CircuitControlContext"),
    ("py:class", "CircuitDagContext"),
    ("py:class", "OpCode"),
    ("py:class", "CbitSpec"),
    ("py:class", "AnalysisResult"),
    ("py:class", "operation"),
    ("py:class", "optional"),
    ("py:class", "T"),
    ("py:class", "np.ndarray"),
    ("py:class", "pd.DataFrame"),
    ("py:class", "qprog"),
    ("py:class", "QProg"),
    ("py:class", "Qobj"),
    ("py:class", "sympy.core.symbol.Symbol"),
    # Classes re-exported from sub-package __init__; canonical location is the
    # sub-module, so the short re-export path won't resolve.
    ("py:class", "uniqc.circuit_builder.Circuit"),
    ("py:class", "uniqc.simulator.OriginIR_Simulator"),
    ("py:class", "uniqc.simulator.OriginIR_NoisySimulator"),
    ("py:class", "uniqc.simulator.QASM_Simulator"),
    ("py:class", "uniqc.simulator.OpcodeSimulator"),
    ("py:class", "uniqc.algorithmics.measurement.classical_shadow.ShadowSnapshot"),
    ("py:class", "uniqc.circuit_builder.qcircuit.CircuitDagContext"),
    ("py:exc", "MissingDependencyError"),
    ("py:exc", "NetworkError"),
    ("py:exc", "ConfigError"),
    ("py:exc", "BackendNotFoundError"),
    ("py:exc", "BackendNotAvailableError"),
    ("py:exc", "AuthenticationError"),
    ("py:exc", "InsufficientCreditsError"),
    ("py:exc", "QuotaExceededError"),
    ("py:exc", "TaskTimeoutError"),
    ("py:exc", "TaskFailedError"),
    ("py:exc", "TaskNotFoundError"),
    ("py:func", "rotation_prepare"),
    ("py:func", "dicke_state_circuit"),
    ("py:mod", "uniqc.task.adapters.dummy_adapter"),
    ("py:obj", "uniqc.circuit_adapter.T"),
    ("py:data", "MIGRATIONS"),
    ("py:data", "CURRENT_SCHEMA_VERSION"),
    ("py:data", "APPLICATION_ID"),
]

# Ignore :returns: prose like "dict with keys ...", "Dict with keys ..." that
# autodoc tries to resolve as a class because of autodoc_typehints="description".
nitpick_ignore_regex = [
    (r"py:class", r"^[Dd]ict with.*"),
]

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']
html_js_files = ['hide_myst_anchors.js']

# pydata-sphinx-theme uses breadcrumbs by default; keep it enabled
breadcrumbs = True
