UNITS := $(wildcard units/*)
PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)

.PHONY: skills check-skills test-scripts

skills:
	@if [ -n "$(UNITS)" ]; then $(PYTHON) -m scripts.build_skill $(UNITS); else echo "no units"; fi

check-skills:
	@if [ -n "$(UNITS)" ]; then $(PYTHON) -m scripts.build_skill --check $(UNITS); else echo "no units"; fi

test-scripts:
	$(PYTHON) -m pytest scripts/tests -q
