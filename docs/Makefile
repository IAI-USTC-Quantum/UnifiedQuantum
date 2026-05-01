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
APIDOC_EXCLUDE = $(APIDOC_IN)/test $(APIDOC_IN)/cli $(APIDOC_IN)/_version.py $(APIDOC_IN)/**/test_*.py
APIDOC_FLAGS  = -f -e -T

# Python for post-processing (replace Unicode math chars in generated tex)
PYTHON        ?= python3
TEXPATCHER    = $(SOURCEDIR)/_tex_patch.py

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help apidoc Makefile

# Regenerate the per-module reference rst (uniqc*.rst) from the source tree.
apidoc:
	$(SPHINXAPIDOC) $(APIDOC_FLAGS) -o $(APIDOC_OUT) $(APIDOC_IN) $(APIDOC_EXCLUDE)

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
