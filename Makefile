# RetroGames: run a target in every game. Each game lives in systems/<system>/<game>/
# and has its own Makefile with at least: all, test, clean.
#
#   make                 build every game
#   make test            build and test every game
#   make clean           remove all build output
#   make list            show the games found
#   make GAME=nes/tidebell [test|clean]    just one game

GAMES := $(patsubst systems/%/Makefile,%,$(wildcard systems/*/*/Makefile))
ifdef GAME
GAMES := $(GAME)
endif

all test clean:
	@set -e; for g in $(GAMES); do \
		echo "== $$g: $@"; \
		$(MAKE) --no-print-directory -C systems/$$g $@; \
	done

list:
	@for g in $(GAMES); do echo $$g; done

.PHONY: all test clean list
