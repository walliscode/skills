SPECS := $(wildcard skills/*/skill.yaml)
PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)

.PHONY: skills check-skills test-scripts

skills:
	@if [ -n "$(SPECS)" ]; then $(PYTHON) -m scripts.build_skill $(SPECS); else echo "no skill specs"; fi

check-skills:
	@if [ -n "$(SPECS)" ]; then $(PYTHON) -m scripts.build_skill --check $(SPECS); else echo "no skill specs"; fi

test-scripts:
	$(PYTHON) -m pytest scripts/tests -q
