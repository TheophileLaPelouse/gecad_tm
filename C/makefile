# Avant on avait gcc -fPIC -shared -o libmodel.so meta.c
# Mais maintenant on a plein de fichier donc c'est plus pratique de faire un makefile
# Compiler
# CC = /opt/homebrew/Cellar/llvm/19.1.7/bin/clang
CC = gcc
# Compiler flags
# CFLAGS = -Wall -Wextra -O2 -fPIC -fopenmp -v --sysroot=$(shell xcrun --show-sdk-path) -I$(shell xcrun --show-sdk-path)/usr/include
CFLAGS = -Wall -Wextra -O2 -fPIC 
# Include directory
# SYSROOT = /Library/Developer/CommandLineTools/SDKs/MacOSX.sdk
# INCLUDES = "-I/Library/Developer/CommandLineTools/SDKs/MacOSX13.3.sdk/System/Library/Frameworks/Kernel.framework/Versions/A/Headers/sys"
# Linker flags
LDFLAGS = -shared -v
# Output library name
LIBRARY = libmodel.so

# Source files
SOURCES = $(wildcard *.c)

# Object files
OBJECTS = $(SOURCES:.c=.o)

# Default target
all: $(LIBRARY)

# Rule to create the shared library
$(LIBRARY): $(OBJECTS)
	$(CC) $(LDFLAGS) -o $@ $(OBJECTS)

# Rule to compile source files into object files
%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

# Clean target to remove generated files
clean:
	rm -f $(OBJECTS) $(LIBRARY)

.PHONY: all clean