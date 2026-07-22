# Minimal makefile for Sphinx documentation
#
# This project ships a *two-step* docs build:
#
# 1. Pre-doc-execution: scripts/build_docs.py walks examples/<chapter>/*.py,
#    runs the runnable subset, captures stdout / stderr / matplotlib figures,
#    splices a Markdown page into source/_generated/examples/, and refreshes
#    example-exec-logs/ (which is committed). Fails the build on unfiltered
#    warnings / errors.
# 2. Sphinx HTML build: a normal `sphinx-build`, which `{include}`s the
#    generated example pages into the chapter prose.
#
# CI does not re-run examples; it just calls scripts/check_doc_logs.py and
# the html-fast target.
#

SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SPHINXAPIDOC  ?= sphinx-apidoc
SOURCEDIR     = .
BUILDDIR      = _build

# sphinx-apidoc still emits a per-module reference rst tree under source/
# from the live ../uniqc tree.  The output is not committed; running any
# doc target below refreshes it first.
APIDOC_OUT    = source/6_api
APIDOC_IN     = ../uniqc
APIDOC_EXCLUDE = $(APIDOC_IN)/test $(APIDOC_IN)/cli $(APIDOC_IN)/_version.py $(APIDOC_IN)/**/test_*.py $(APIDOC_IN)/algorithms/core/measurement/test_measurement.py
APIDOC_FLAGS  = -f -e -T
APIDOC_CLEAN  = $(APIDOC_OUT)/uniqc.rst $(APIDOC_OUT)/uniqc.*.rst

# Python for post-processing (replace Unicode math chars in generated tex)
PYTHON        ?= python3
TEXPATCHER    = $(SOURCEDIR)/_tex_patch.py

# Pre-doc-execution driver (paths are relative to PROJECT_ROOT after `cd ..`).
BUILD_DOCS_SCRIPT = scripts/build_docs.py
CHECK_LOGS_SCRIPT = scripts/check_doc_logs.py
CHECK_LINKS_SCRIPT = scripts/check_local_links.py

.PHONY: help apidoc examples examples-real-cloud check-links check-logs html html-fast latexpdf clean Makefile

help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

# Regenerate the per-module reference rst (uniqc*.rst) from the source tree.
apidoc:
	mkdir -p $(APIDOC_OUT)
	rm -f $(APIDOC_CLEAN)
	$(SPHINXAPIDOC) $(APIDOC_FLAGS) -o $(APIDOC_OUT) $(APIDOC_IN) $(APIDOC_EXCLUDE)

# Pre-doc-execution: re-run runnable examples and refresh example-exec-logs/
# plus source/_generated/examples/. Fails on unfiltered warnings/errors.
examples:
	cd .. && $(PYTHON) $(BUILD_DOCS_SCRIPT)

# Same as `examples`, but also runs examples gated on real-cloud submissions.
examples-real-cloud:
	cd .. && $(PYTHON) $(BUILD_DOCS_SCRIPT) --real-cloud

# CI-side: just verify the cached example-exec-logs/index.json verdict.
check-logs:
	cd .. && $(PYTHON) $(CHECK_LOGS_SCRIPT)

# CI-side: validate all active repository-local documentation links offline.
check-links:
	cd .. && $(PYTHON) $(CHECK_LINKS_SCRIPT)

# Default html target: full local pipeline (re-run examples, then sphinx).
html: examples apidoc
	@$(SPHINXBUILD) -M html "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

# CI / fast local rebuild: skip the pre-doc-execution step, trust the
# committed logs / generated pages.
html-fast: check-links apidoc
	@$(SPHINXBUILD) -M html "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

# Catch-all target for any other sphinx mode (man, dirhtml, ...).
%: apidoc Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

# Special target for PDF: patch the tex file before latexmk runs
latexpdf: examples apidoc
	@$(SPHINXBUILD) -b latex "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
	@if [ -f "$(TEXPATCHER)" ]; then \
		$(PYTHON) $(TEXPATCHER) "$(BUILDDIR)/unifiedquantum.tex"; \
		fi
	@$(MAKE) -C "$(BUILDDIR)" LATEXMKOPTS="$(LATEXMKOPTS)" all-pdf

clean:
	rm -rf $(BUILDDIR)
	rm -rf source/_generated
	rm -rf $(APIDOC_OUT)/uniqc.rst $(APIDOC_OUT)/uniqc.*.rst $(APIDOC_OUT)/autoapi
