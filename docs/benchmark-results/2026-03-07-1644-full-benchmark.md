# Full Benchmark Report

**Date:** 2026-03-07-1644
**Ollama:** http://192.168.2.69:11434
**Phase 1 model:** mistral-small3.1:24b
**Phase 2 models:** mistral-small3.1:24b, type32/eva-qwen-2.5-14b:latest, muse-12b:latest, LESSTHANSUPER/MAGNUM_V4-Mistral_Small:12b_Q5_K_M
**Judge model:** dolphin3:latest
**Characters:** Beavis
**Films:** 1

## Phase 1 — Prompt Battle

| Variant | Description | Avg Voice | Calibration% | Format% |
|---------|-------------|-----------|--------------|---------|
| V0 | Baseline — prompt actual de producción sin cambios | 2.00 | 100% | 100% |
| V1 | Instrucción de voz explícita — pide muletillas y anécdotas | n/a | n/a | n/a |
| V2 | Anécdotas en el soul — referencias concretas del personaje | n/a | n/a | n/a |
| V3 | Combinado — instrucción de voz + anécdotas (full enrichment) | 3.00 | 100% | 100% |

**Winner: V3** — Combinado — instrucción de voz + anécdotas (full enrichment)

## Per-Character Best Combo

| Character | Best Variant | Best Model | Voice Score |
|-----------|-------------|------------|-------------|
| Beavis | V3 | mistral-small3.1:24b | 3 |

## Top Critic Samples

### Beavis x Barbie (V3 | mistral-small3.1:24b)
Voice score: 3/3 | Rating: 9/10 | Words: 155

9/10
Butt-Head, ¿has visto todas esas Barbies? ¡Es como si hubieran hecho una película solo para mí! Chicas rubias, guapas, en bikini y con tacones, ¡esto es el paraíso! Y lo mejor es que todo es brillante y rosa, como si estuviera en un mundo de helados de fresa. ¡Es como cuando prendí fuego a la papelera del cole y todo se volvió rojo y naranja! Pero esto es mejor, porque no me van a castigar por esto.

Y lo más alucinante, ¡hay una Barbie que piensa! ¡Qué pasada! Es como si Cornholio hubiera salido del videoclub y se hubiera encontrado con todas sus Barbies favoritas en la pantalla. ¡Es la mejor película de chicas que he visto en mi vida!

Y otra cosa, Butt-Head, ¿has visto cómo bailan? ¡Es como si estuviera en un concierto de Metallica! ¡Es genial! No hay nada de diálogos aburridos, solo acción y chicas guapas. ¡Esta película mola mucho!

### Beavis x Barbie (V0 | mistral-small3.1:24b)
Voice score: 2/3 | Rating: 7/10 | Words: 126

7/10. Esta peli es un rollo, no va a tener explosiones ni nada, pero, ¿has visto las Barbies? ¡Están buenísimas! Y son todas rubias, ¡es como un sueño hecho realidad! Barbieland parece un lugar genial, lleno de chicas en bikini y con tacones. Y Barbie viaja al mundo real, ¡qué pasada! Aunque no va a haber peleas ni cosas así, al menos hay muchas Barbies y Ken. ¡Y seguro que hay música chula! Pero, Beavis, ¿qué es ese rollo de los pensamientos existenciales? ¿Qué es eso? ¿Qué pasa si Barbie se pone a hablar de sus sentimientos y todo eso? ¡Ese rollo me aburre! Pero, bueno, al menos hay muchas Barbies y cosas brillantes. ¡Y seguro que hay chicas guapas en bikini! Butt-Head, ¡me la pido!
