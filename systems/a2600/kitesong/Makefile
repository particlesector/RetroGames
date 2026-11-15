# KITESONG build. Needs cc65 (ca65/ld65) and Python 3; tests need Pillow and a libretro Stella core.
B := build
ROM := $(B)/kitesong.F8

all: $(ROM)

$(B)/songs.inc $(B)/tables.inc: assets/songs.txt tools/build_data.py
	@mkdir -p $(B)
	python3 tools/build_data.py assets/songs.txt $(B)

$(B)/kitesong.o: src/kitesong.s src/vcs.inc $(B)/songs.inc $(B)/tables.inc
	ca65 -g -I $(B) -I src src/kitesong.s -o $@

$(ROM): $(B)/kitesong.o src/kitesong.cfg
	ld65 -C src/kitesong.cfg -o $@ -Ln $(B)/labels.txt -m $(B)/map.txt $(B)/kitesong.o

test: $(ROM)
	python3 tests/run_tests.py

clean:
	rm -rf $(B)
