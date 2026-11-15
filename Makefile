SPECS := $(wildcard skills/*/skill.yaml)
# Use the project venv when present so pytest and pyyaml are available; otherwise system python3.
PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)

.PHONY: skills check-skills test-scripts install-skills progress-demo

skills:
	@if [ -n "$(SPECS)" ]; then $(PYTHON) -m scripts.build_skill $(SPECS); else echo "no skill specs"; fi

check-skills:
	@if [ -n "$(SPECS)" ]; then $(PYTHON) -m scripts.build_skill --check $(SPECS); else echo "no skill specs"; fi

test-scripts:
	$(PYTHON) -m pytest scripts/tests -q

# Install built skills into the user-level folder (run by hand).
# Depends on check-skills so a stale build is refused before anything is copied.
install-skills: check-skills
	$(PYTHON) -m scripts.install_skills

# Play a fake batch through the eval harness's progress bar. Pass DEMO_ARGS to change it, e.g. DEMO_ARGS="--runs 30".
progress-demo:
	$(PYTHON) -m test_harness progress-demo $(DEMO_ARGS)
