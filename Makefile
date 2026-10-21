UNITS := $(wildcard units/*)

.PHONY: skills check-skills test-scripts

skills:
	@if [ -n "$(UNITS)" ]; then python3 -m scripts.build_skill $(UNITS); else echo "no units"; fi

check-skills:
	@if [ -n "$(UNITS)" ]; then python3 -m scripts.build_skill --check $(UNITS); else echo "no units"; fi

test-scripts:
	.venv/bin/python -m pytest scripts/tests -q
