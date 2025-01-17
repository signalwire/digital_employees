# Makefile for installing swaig_cli and its dependencies

# Variables
INSTALL_DIR = /usr/bin
MAN_DIR = /usr/share/man/man1
PACKAGE_NAME = swaig_cli
MAN_PAGE = swaig_cli.1

# Default target
all: install

# Install target
install: install_deps install_swaig_cli install_man

# Install dependencies
install_deps:
	pip install -r requirements.txt

# Install swaig_cli
install_swaig_cli:
	cp bin/$(PACKAGE_NAME) $(INSTALL_DIR)

# Install man page
install_man:
	cp man/man1/$(MAN_PAGE) $(MAN_DIR)

# Clean target
clean:
	rm -f $(INSTALL_DIR)/$(PACKAGE_NAME)
	rm -f $(MAN_DIR)/$(MAN_PAGE)

.PHONY: all install install_deps install_swaig_cli install_man clean

