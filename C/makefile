# Avant on avait gcc -fPIC -shared -o libmodel.so meta.c
# Mais maintenant on a plein de fichier donc c'est plus pratique de faire un makefile
# Compiler
CC = gcc

# Compiler flags
CFLAGS = -Wall -Wextra -O2 -fPIC

# Linker flags
LDFLAGS = -shared

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