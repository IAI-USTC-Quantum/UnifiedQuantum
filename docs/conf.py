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

def generate_release_notes():
    """Generate git-backed release notes used by the docs site."""
    script_path = parent_path / "scripts" / "generate_release_notes.py"
    output_path = parent_path / "docs" / "source" / "7_releases" / "_generated" / "strict_history.md"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not script_path.exists():
        output_path.write_text(
            "## 详细变更记录（自动整理）\n\n自动整理脚本缺失，当前无法生成版本变化记录。\n",
            encoding="utf-8",
        )
        return

    try:
        subprocess.run(
            [sys.executable, str(script_path), "--output", str(output_path)],
            cwd=str(parent_path),
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception as exc:
        output_path.write_text(
            "## 详细变更记录（自动整理）\n\n"
            "版本变化记录整理失败，因此这里只显示占位说明。请检查 `scripts/generate_release_notes.py`。\n",
            encoding="utf-8",
        )
        print(f"[docs] failed to generate release notes: {exc}")

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

generate_release_notes()

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
    'myst_parser',
    'sphinx.ext.viewcode',
]

# -- sphinx-autoapi ---------------------------------------------------------
# We use ``sphinx-apidoc`` (driven from the Makefile) as the canonical source
# of API reference pages under ``source/6_api/uniqc*.rst``. ``sphinx-autoapi``
# is intentionally **not** enabled — having both extensions generate docs for
# the same modules causes "duplicate object description" warnings and a noisy
# build. If you want autoapi-style cross-reference resolution, re-enable it
# below and additionally disable apidoc's targets in the Makefile.
#
# try:
#     import autoapi  # noqa: F401
#     extensions.append('autoapi.extension')
#     autoapi_type = 'python'
#     autoapi_dirs = [str((parent_path / 'uniqc').resolve())]
#     autoapi_root = 'source/6_api/autoapi'
#     autoapi_keep_files = False
#     autoapi_add_toctree_entry = False
#     autoapi_options = [
#         'members', 'undoc-members', 'show-inheritance',
#         'show-module-summary', 'imported-members',
#     ]
#     autoapi_ignore = ['*/test/*', '*/_version.py', '*/uniqc_cpp*']
#     autoapi_python_class_content = 'both'
# except ImportError:
#     pass

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
exclude_patterns = [
    '_build',
    'Thumbs.db',
    '.DS_Store',
    'source/uniqc.test.rst',
    'source/7_releases/_generated/*',
    # Generated example pages live under source/_generated/examples/ and are
    # only reachable via {include} from the chapter index pages — never as
    # standalone documents. Sphinx-compiling them standalone breaks the
    # relative paths because literalinclude / image paths in included
    # content are resolved relative to the *including* file at include time,
    # not the included file.
    'source/_generated/examples/**/*.md',
]
autodoc_typehints = "description"
source_suffix = {'.rst': 'restructuredtext', '.md': 'markdown'}

# Use index.md as the master document.
master_doc = 'index'

# -- Options for HTML output -------------------------------------------------

html_theme = "furo"

html_baseurl = "https://iai-ustc-quantum.github.io/UnifiedQuantum/docs/"

html_title = f"UnifiedQuantum {release}"

html_theme_options = {
    # Furo-specific options. The version switcher / theme switcher used by
    # PyData are not available; Furo provides its own light/dark toggle in
    # the top-right corner.
    "navigation_with_keys": True,
    "sidebar_hide_name": False,
    "top_of_page_buttons": ["view", "edit"],
    "source_repository": "https://github.com/IAI-USTC-Quantum/UnifiedQuantum",
    "source_branch": "main",
    "source_directory": "docs/",
}

suppress_warnings = [
    "myst.xref_missing",
    "ref.python",
    "docutils",
    "autosectionlabel.*",
    "epub.duplicated_toc_entry",
]

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
    ("py:class", "uniqc.simulator.Simulator"),
    ("py:class", "uniqc.simulator.NoisySimulator"),
    ("py:class", "uniqc.simulator.OpcodeSimulator"),
    ("py:class", "uniqc.algorithms.core.measurement.classical_shadow.ShadowSnapshot"),
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
    ("py:mod", "uniqc.backend_adapter.task.adapters.dummy_adapter"),
    ("py:obj", "uniqc.backend_adapter.circuit_adapter.T"),
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

# -- Options for LaTeX/PDF output --------------------------------------------
latex_engine = 'xelatex'
latex_use_xindy = False
latex_elements = {
    "fontpkg": (
        r"\usepackage{fontspec}"
        r"\setmainfont{Noto Serif CJK SC}"
        r"\setsansfont{Noto Sans CJK SC}"
        r"\setmonofont{Noto Sans Mono CJK SC}"
    ),
}

latex_show_urls = "inline"
latex_show_pagerefs = True


def _skip_duplicate_module_aliases(app, what, name, obj, skip, options):
    """Skip top-level package members that shadow same-named submodules.

    Some packages expose a lazy delegate (e.g. ``uniqc.compile.draw`` the
    function in ``uniqc/compile/__init__.py`` vs. the ``uniqc.compile.draw``
    submodule). Documenting both makes Sphinx register two objects under the
    fully-qualified name ``uniqc.compile.draw``, which raises
    "duplicate object description". We keep the canonical submodule entry and
    drop the top-level alias.
    """
    duplicates = {
        ("uniqc.compile", "draw"),
    }
    module = getattr(obj, "__module__", None)
    if module is not None and (module, name) in duplicates:
        return True
    return skip


def setup(app):
    app.connect("autodoc-skip-member", _skip_duplicate_module_aliases)
