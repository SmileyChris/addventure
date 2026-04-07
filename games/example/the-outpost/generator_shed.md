// Generator Shed — Multi-step mechanical puzzle. The wrench is a reusable tool
// (not trashed) needed for two tasks: loosening the fuel drum tap, then
// unbolting the service panel to access the primer.
//
// Enforced sequence: fuel drum (wrench) → generator fueled →
//   service panel (wrench) → primer exposed → use primer → start → cue
//
// The service panel interaction is nested under GENERATOR__FUELED to prevent
// the player from priming an empty fuel line (which would soft-lock the game).

# Generator Shed
LOOK: Three concrete walls and a corrugated roof. The fourth side is open to the compound. An industrial generator squats in the centre, thick cables snaking from its housing through the wall toward the relay station. A steel fuel drum stands in the far corner. The air is sharp with old diesel.

GENERATOR
+ LOOK: An industrial diesel generator, cold and silent. A pull-start cord hangs from the right side. The fuel gauge needle rests on the pin — bone dry. A metal service panel is bolted to the front with hex-head bolts.
+ USE: You wrap the cord around your fist and pull. The engine doesn't even turn over. Nothing in the tank.

FUEL_DRUM
+ LOOK: A red steel drum, dented and streaked with grime. A hand-crank pump is mounted on the lid. Down at the base, a brass tap — rusted shut. Something metallic catches the light on the concrete behind it.
+ USE: You try the pump handle. Seized solid, won't budge a millimetre. The tap is just as bad — frozen with corrosion.
+ USE + WRENCH:
  You fit the wrench over the tap and put your weight into it. It gives with a shriek that echoes off the walls. Dark diesel streams into the generator's tank. The fuel gauge needle climbs, trembles, settles on full.
  - FUEL_DRUM -> FUEL_DRUM__EMPTY
    + LOOK: An empty drum. Diesel has pooled beneath the tap and is creeping across the concrete.
  - GENERATOR -> GENERATOR__FUELED
    + LOOK: The fuel gauge reads full. The pull cord hangs ready. A service panel on the front is still bolted shut — the note mentioned priming the fuel line before starting.
    + USE: You pull the cord. The engine turns over once, coughs, dies. Air in the fuel line. You need to prime it — the service panel on the front should have what you need.
    + USE + WRENCH:
      You crack the hex bolts one by one and swing the panel open on its hinge. Inside, plumbed into the fuel line: a rubber primer bulb. A faded sticker reads PRIME BEFORE STARTING.
      - GENERATOR__FUELED -> GENERATOR__OPEN
        + LOOK: The panel hangs open. A rubber primer bulb sits in the housing, connected inline to the fuel feed. Squeeze it to bleed the air.
        + USE:
          You squeeze the bulb — once, twice, three times. Diesel fills the clear section of the line. No bubbles. You slam the panel shut, set your feet, and yank the pull cord hard.

          The engine catches. Turns over. Roars. The shed fills with noise and fumes. Across the compound, lights stutter on in the relay station windows.
          - GENERATOR__OPEN -> GENERATOR__RUNNING
            + LOOK: The generator shakes on its mounts, exhaust rattling through a pipe in the wall. A green indicator light glows steady on the housing.
          - ? -> "Relay Station"
            Something hums to life. The strip light overhead flickers twice and holds. The console screen blooms pale green — power is flowing.
            - CONSOLE -> CONSOLE__POWERED

SERVICE_PANEL
+ LOOK: A metal access panel bolted to the front of the generator. Six hex-head bolts, tight.
+ USE: You try the bolts by hand. They don't move. You need a wrench or a socket.
+ USE + WRENCH: The tank is empty — nothing to prime. Fuel it first.

WRENCH
+ LOOK: An adjustable wrench, heavy, half-hidden behind the fuel drum. Someone kicked it there and forgot about it.
+ TAKE:
  You pick it up. Solid. Good weight.
  - WRENCH -> player

DOORWAY
+ LOOK: Open air. Gravel. The relay station across the clearing, its door ajar.
+ USE:
  You cross the compound to the relay station.
  - player -> "Relay Station"
