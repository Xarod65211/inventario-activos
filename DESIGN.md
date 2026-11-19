# Dirección de diseño

Sistemas de gestión para uso diario en oficina y almacén. Lo importante de cada pantalla son los datos y la acción siguiente.

Origen de la identidad: el CV del autor (azul marino con acento turquesa, Poppins para títulos e Inter para el texto). Así los sistemas, el portafolio y el CV se leen como trabajo de la misma persona.

Dial: ENERGY 2 / RHYTHM 1 / MOTION 1

- ENERGY 2: superficie clara y tranquila; la barra lateral azul marino y el acento turquesa dan carácter sin competir con las tablas.
- RHYTHM 1: todas las pantallas repiten título, acciones y tabla o formulario. El usuario aprende un patrón.
- MOTION 1: solo transiciones de color de 150 ms en botones y enlaces. Se apagan con `prefers-reduced-motion`.

## Color
| Token | Hex | Uso |
|---|---|---|
| `marino` | `#172a46` | Barra lateral, títulos |
| `marino-700` | `#22395c` | Elemento activo de la barra |
| `turquesa` | `#0f766e` | Botón principal, enlaces, foco (blanco encima: 5.4:1) |
| `turquesa-claro` | `#5eead4` | Marca del elemento activo sobre la barra marino |
| fondo | `#f4f6f9` | Fondo de página |
| superficie | `#ffffff` | Tarjetas y tablas, borde `#e2e8f0`, sin sombra |

Estados (siempre con texto, nunca solo color): ok `#15803d`, alerta `#b45309`, error `#b91c1c`, neutro `#475569`.

## Tipografía
Poppins 600 para títulos y Inter para todo lo demás, empaquetadas con `@fontsource` (sin CDN). Cifras de tablas con números tabulares.

## Forma
Radio de 8 px en controles y 12 px en tarjetas. Sin sombras salvo menús y diálogos. Sin franjas laterales de color ni íconos decorativos. Controles de 40 px de alto como mínimo y foco visible turquesa.
