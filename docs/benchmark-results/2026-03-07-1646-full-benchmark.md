# Full Benchmark Report

**Date:** 2026-03-07-1646
**Ollama:** http://192.168.2.69:11434
**Phase 1 model:** mistral-small3.1:24b
**Phase 2 models:** mistral-small3.1:24b, type32/eva-qwen-2.5-14b:latest, muse-12b:latest, LESSTHANSUPER/MAGNUM_V4-Mistral_Small:12b_Q5_K_M
**Judge model:** dolphin3:latest
**Characters:** Beavis
**Films:** 1

## Phase 1 — Prompt Battle

| Variant | Description | Avg Voice | Calibration% | Format% |
|---------|-------------|-----------|--------------|---------|
| V0 | Baseline — prompt actual de producción sin cambios | 3.00 | 100% | 100% |
| V1 | Instrucción de voz explícita — pide muletillas y anécdotas | n/a | n/a | n/a |
| V2 | Anécdotas en el soul — referencias concretas del personaje | n/a | n/a | n/a |
| V3 | Combinado — instrucción de voz + anécdotas (full enrichment) | 2.00 | 100% | 100% |

**Winner: V0** — Baseline — prompt actual de producción sin cambios

## Per-Character Best Combo

| Character | Best Variant | Best Model | Voice Score |
|-----------|-------------|------------|-------------|
| Beavis | V0 | mistral-small3.1:24b | 3 |

## Top Critic Samples

### Beavis x Barbie (V0 | mistral-small3.1:24b)
Voice score: 3/3 | Rating: 9/10 | Words: 177

9/10, ¡espera un momento!  La peli es super genial, man. Chicas rubias, ¿qué más se puede pedir? Y van todas en bikini y con tacones, ¡guau! Y el mundo ese de Barbieland es como un sueño hecho realidad, todo brillante y rosa. ¡Me encanta! Y no hay nada de esos diálogos aburridos que duran horas, solo acción y chicas. Además, las Barbies están siempre bailando y posando, ¡es como un festival de chicas! Y hasta hay crítica a no sé qué, pero no me importa, solo me fijo en las Barbies. Y, ¡oh, mira!, hasta hay una Barbie rubia que se llama Barbie, ¡qué original! Pero, Butt-Head, ¿por qué siempre tienes esa cara de idiota? ¡Espera! ¿Por qué no hay explosiones ni peleas? ¡Ah, bueno!, eso no importa, ¡hay muchas chicas! ¡Esta peli es la mejor!

Butt-Head: "¿Y el heavy metal, Beavis?"

Beavis: "¡Oh, sí! ¡Heavy metal! ¡Chicas y heavy metal! ¡Es como si Metallica tocara mientras las Barbies bailan!"

Butt-Head: "¡Ja, ja! ¡Eres un idiota, Beavis!"

Beavis: "¡Cornholio, ven aquí! ¡Vamos a ver Barbie otra vez!"

### Beavis x Barbie (V3 | mistral-small3.1:24b)
Voice score: 2/3 | Rating: 8/10 | Words: 137

8/10

¿Pero tú has visto cuántas Barbies rubias hay? Es como si todo el mundo fuera Cornholio y viniera al videoclub. Esto mola. Yo quiero vivir en Barbieland. Allí todo es de colores, todas son guapas y llevan bikini. Pero, ¿tú has visto lo que pasa en el mundo real? Aquí no hay nada de eso. Aquí, lo mejor que he hecho es prender fuego a la papelera del cole. Pero eso no es nada comparado con lo que se ve en esta peli. ¡Explosiones! ¡Chicas guapas! ¡Y todo brillando! Esto es lo mejor. Pero, ¿tú has visto a Butt-Head? Dice que El Padrino es una obra maestra. ¡Ja! Pero qué va a saber él. Esto es lo que mola. Y las Barbies bailando, ¡eso es heavy metal en movimiento! ¡Esto sí que es una buena peli!
