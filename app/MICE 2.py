import pygame

# Inicijalizacija pygame
pygame.init()

# Postavke ekrana
width, height = 800, 800
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("Mica Polje")

# Učitavanje pozadine
background = pygame.image.load(r"C:\Users\Korisnik\Desktop\BREAKOUT\MICA POLJE.png")

# Boje
plava = (0, 0, 255)
zelena = (0, 255, 0)

# Kreiranje zetona
zetoni_plavi = []
zetoni_zeleni = []
radius = 15

for i in range(8):
    zetoni_plavi.append(pygame.Rect(50 + i * 20, 700, radius * 2, radius * 2))
    zetoni_zeleni.append(pygame.Rect(50 + i * 20, 750, radius * 2, radius * 2))

# Glavna petlja
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Crtanje pozadine
    screen.blit(background, (0, 0))

    # Crtanje plavih zetona
    for zeton in zetoni_plavi:
        pygame.draw.circle(screen, plava, (zeton.x + radius, zeton.y + radius), radius)

    # Crtanje zelenih zetona
    for zeton in zetoni_zeleni:
        pygame.draw.circle(screen, zelena, (zeton.x + radius, zeton.y + radius), radius)

    pygame.display.flip()

pygame.quit()
