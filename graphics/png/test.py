from png import *
image = None
gamma = None
with open_png_file("png3.png", "rb") as file:
    image, gamma = read_png(file)
file = open("test.png", "wb")
write_png(image, file, gamma)
file.close()
