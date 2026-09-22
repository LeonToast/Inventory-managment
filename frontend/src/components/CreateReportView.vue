<script setup lang="ts">
defineEmits<{ back: [] }>()
</script>
<template>
    <section class="create-report"><button class="back" @click="$emit('back')">‹　Tillbaka till rapporter</button>
        <div class="form-heading">
            <div>
                <h1>Skapa rapport</h1>
                <p>Välj vilken sammanställning du vill skapa.</p>
            </div><button class="primary">Generera rapport</button>
        </div>
        <div class="form-card"><label>Rapporttyp<select>
                    <option>Månadsrapport</option>
                    <option>Lageröversikt</option>
                    <option>Leveransrapport</option>
                    <option>Avvikelserapport</option>
                </select></label><label>Period<select>
                    <option>Oktober 2024</option>
                    <option>September 2024</option>
                    <option>Senaste 30 dagarna</option>
                </select></label><label>Inkludera lager<div class="checks"><span>✓ Lager A</span><span>✓ Lager
                        B</span><span>✓ Lager C</span></div></label><label>Beskrivning<textarea
                    placeholder="Lägg till en kort beskrivning (valfritt)"></textarea></label></div>
    </section>
</template>
