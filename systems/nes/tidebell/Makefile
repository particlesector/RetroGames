# TIDEBELL build. Needs cc65 (ca65/ld65) and Python 3; tests also need Pillow, numpy and a libretro NES core.
B := build
ROM := $(B)/tidebell.nes

all: $(ROM)

$(B)/gfx.inc: tools/build_chr.py
	@mkdir -p $(B)
	python3 tools/build_chr.py $(B)

$(B)/levels.inc: assets/levels.txt tools/build_levels.py $(B)/gfx.inc
	python3 tools/build_levels.py assets/levels.txt $(B)

$(B)/music.inc: assets/music.txt tools/build_music.py
	@mkdir -p $(B)
	python3 tools/build_music.py assets/music.txt $@

$(B)/main.o: src/main.s src/sound.s $(B)/gfx.inc $(B)/levels.inc $(B)/music.inc
	ca65 -g -I $(B) -I src --bin-include-dir $(B) src/main.s -o $@

$(ROM): $(B)/main.o src/tidebell.cfg
	ld65 -C src/tidebell.cfg -o $@ -Ln $(B)/labels.txt -m $(B)/map.txt $(B)/main.o

test: $(ROM)
	python3 tests/run_tests.py
	python3 tests/test_flows.py

clean:
	rm -rf $(B)

.PHONY: all test clean
