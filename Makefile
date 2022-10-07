CC = "g++"
PROJECT = test3 # Cambia a nombre del ejecutable deseado.
SRC = test3.cpp # Cambia a nombre del código fuente

LIBS = `pkg-config opencv4 --cflags --libs`

$(PROJECT) : $(SRC)
	$(CC) $(SRC) -o $(PROJECT) $(LIBS)

# NOTA: Ejecutar con './$(PROJECT)' -> './test1Opencv' en mi caso; después de haber ejecutado el comando 'make'.