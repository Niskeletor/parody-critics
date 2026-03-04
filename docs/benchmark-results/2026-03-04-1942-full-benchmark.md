# Full Benchmark Report

**Date:** 2026-03-04-1942
**Ollama:** http://192.168.2.69:11434
**Phase 1 model:** mistral-small3.1:24b
**Phase 2 models:** mistral-small3.1:24b, type32/eva-qwen-2.5-14b:latest, muse-12b:latest, LESSTHANSUPER/MAGNUM_V4-Mistral_Small:12b_Q5_K_M
**Judge model:** dolphin3:latest
**Characters:** Beavis
**Films:** 1

## Phase 1 — Prompt Battle

| Variant | Description | Avg Voice | Calibration% | Format% |
|---------|-------------|-----------|--------------|---------|
| V0 | Baseline — prompt actual de producción sin cambios | 2.00 | 0% | 100% |
| V1 | Instrucción de voz explícita — pide muletillas y anécdotas | n/a | n/a | n/a |
| V2 | Anécdotas en el soul — referencias concretas del personaje | n/a | n/a | n/a |
| V3 | Combinado — instrucción de voz + anécdotas (full enrichment) | 3.00 | 0% | 100% |

**Winner: V3** — Combinado — instrucción de voz + anécdotas (full enrichment)

## Per-Character Best Combo

| Character | Best Variant | Best Model | Voice Score |
|-----------|-------------|------------|-------------|
| Beavis | V3 | mistral-small3.1:24b | 3 |

## Top Critic Samples

### Beavis x Barbie (V3 | mistral-small3.1:24b)
Voice score: 3/3 | Rating: 2/10 | Words: 127

2/10
¡Esta película es una mierda! ¡Barbie y Ken en un mundo perfecto sin fuego? ¡Qué aburrido! Yo soy más de explosiones y fuego, como cuando prendí fuego a la papelera del cole. ¡Ese sí que fue un día épico! Esta película solo habla y habla, y encima es un mensaje educativo. ¡Qué asco! ¡Y nada de heavy metal! Solo chicas hablando de sus sentimientos. ¡Puaj! Lo único que me gusta es cuando Barbie y Ken van al mundo real, pero incluso eso es una mierda porque no hay explosiones ni fuego. ¡Esta película es para niñas! ¡Yo soy Cornholio! ¡Necesito TP para mi bungholio! ¡Esta película es un 2/10! ¡Es una mierda! ¡Butt-Head dice que esto apesta, pero Butt-Head es idiota! ¡Aunque tiene razón! ¡FIRE! ¡FIRE!

### Beavis x Barbie (V0 | mistral-small3.1:24b)
Voice score: 2/3 | Rating: 2/10 | Words: 129

2/10

No way, man, esta película es una mierda. Barbie en un mundo matriarcal sin fuego. ¿Qué es eso? ¿Qué pasa con las explosiones? ¿Dónde están las guitarras heavy metal? Es como si alguien dijera: "¡Hey, hagamos una película sin nada que mola!" Y encima, ¿hablar de la muerte y el patriarcado? ¡Qué aburrimiento! Mucho diálogo y nada de acción. Solo una tía que piensa en cosas raras y un tipo que la sigue. No hay nada que quemar, nada que explote. Es como si hubieran hecho la película solo para molestar. ¿Y por qué Barbie tiene que pensar en la muerte? ¡Es una muñeca! ¡Debería estar en la playa o algo así, no pensando en cosas serias! Esta película es un fracaso total. ¡Ni siquiera hay fuego! ¡Asqueroso!
