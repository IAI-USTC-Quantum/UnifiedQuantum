# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SPHINXAPIDOC  ?= sphinx-apidoc
SOURCEDIR     = .
BUILDDIR      = _build
# Apidoc regenerates the per-module reference rst files under source/ from
# the live ../uniqc tree.  The output is not committed; running any doc
# target below will refresh it first.
APIDOC_OUT    = source
APIDOC_IN     = ../uniqc
APIDOC_EXCLUDE = $(APIDOC_IN)/test $(APIDOC_IN)/cli $(APIDOC_IN)/_version.py $(APIDOC_IN)/**/test_*.py $(APIDOC_IN)/algorithms/core/measurement/test_measurement.py
APIDOC_FLAGS  = -f -e -T
APIDOC_CLEAN  = $(APIDOC_OUT)/uniqc.rst $(APIDOC_OUT)/uniqc.*.rst

# Python for post-processing (replace Unicode math chars in generated tex)
PYTHON        ?= python3
TEXPATCHER    = $(SOURCEDIR)/_tex_patch.py

# Best-practice notebooks generator. Each notebook executes user-API
# paths against either local simulators or real provider chips. The
# generator skips notebooks whose required SDKs / credentials are
# absent (no silent fallbacks). Set UNIQC_DOCS_BUILD_ALL=1 to make
# missing prerequisites a hard error instead.
BEST_PRACTICES_SCRIPT = ../scripts/generate_best_practice_notebooks.py
BEST_PRACTICES_DIR    = source/best_practices

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help apidoc best-practices best-practices-strict Makefile

# Regenerate the per-module reference rst (uniqc*.rst) from the source tree.
apidoc:
	rm -f $(APIDOC_CLEAN)
	$(SPHINXAPIDOC) $(APIDOC_FLAGS) -o $(APIDOC_OUT) $(APIDOC_IN) $(APIDOC_EXCLUDE)

# Run the best-practice notebook generator. Skips notebooks with
# missing prereqs (writes a clear SKIP line per notebook).
best-practices:
	$(PYTHON) $(BEST_PRACTICES_SCRIPT)

# Strict variant: every notebook MUST be built. Aborts if any required
# SDK / API token is missing. Use this in release CI on a host with
# all extras + provider tokens configured.
best-practices-strict:
	UNIQC_DOCS_BUILD_ALL=1 $(PYTHON) $(BEST_PRACTICES_SCRIPT)

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
# Runs apidoc first so every build starts from a fresh module index.
%: apidoc Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

# Special target for PDF: patch the tex file before latexmk runs
latexpdf: apidoc
	@$(SPHINXBUILD) -b latex "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
	@if [ -f "$(TEXPATCHER)" ]; then \
		$(PYTHON) $(TEXPATCHER) "$(BUILDDIR)/unifiedquantum.tex"; \
		fi
	@$(MAKE) -C "$(BUILDDIR)" LATEXMKOPTS="$(LATEXMKOPTS)" all-pdf
