# DRYLINE Grand Prix build. Needs cc65 (ca65/ld65) and Python 3 with numpy and Pillow.
B := build
ROM := $(B)/dryline.nes
SRC := $(wildcard src/*.s)

all: $(ROM)

$(B)/tracks.inc: $(wildcard assets/tracks/*.toml) tools/build_tracks.py tools/nespal.py
	@mkdir -p $(B)
	python3 tools/build_tracks.py assets/tracks $(B)

$(B)/sprites.chr: tools/build_sprites.py tools/nespal.py
	@mkdir -p $(B)
	python3 tools/build_sprites.py $(B)

$(B)/dryline.chr: $(B)/tracks.inc $(B)/sprites.chr tools/pack_chr.py
	python3 tools/pack_chr.py $(B)

$(B)/main.o: $(SRC) $(B)/tracks.inc $(B)/sprites.chr $(B)/dryline.chr
	ca65 -g -I $(B) -I src --bin-include-dir $(B) src/main.s -o $@

$(ROM): $(B)/main.o src/dryline.cfg
	ld65 -C src/dryline.cfg -o $@ -Ln $(B)/labels.txt -m $(B)/map.txt $(B)/main.o

test: $(ROM)
	python3 tests/run_tests.py

clean:
	rm -rf $(B)

.PHONY: all test clean
