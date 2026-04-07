// Forest Road — Search puzzle. Rummage through the truck to find tools and a
// critical clue (the frequency note). The bolt cutters open the gate.
// The broken crowbar is a red herring.

# Forest Road
LOOK: Cracked tarmac, pine needles drifting across the surface. Tyre tracks in the mud — weeks old, heading away. A chain-link gate blocks a gravel compound to the north. Beyond it, two low buildings and the antenna you spotted from the road. A pickup truck sits nose-down in the ditch, driver's door hanging open.

PICKUP_TRUCK
+ LOOK: A white pickup, sun-bleached and listing into the ditch. The cab door hangs open. A metal toolbox sits on the passenger seat. The glove box is latched shut.
+ USE:
  You haul yourself into the cab. No keys. Fuel gauge flat on empty. You pop the glove box — a crumpled note spills out onto the floor mat. The toolbox yields a pair of bolt cutters and a crowbar snapped clean in two.
  - FREQUENCY_NOTE -> room
    + LOOK: Maintenance handwriting, ballpoint on lined paper: "Emergency freq 47.3 MHz. If generator is dead — check fuel, then prime before pulling starter. Primer is behind the service panel."
    + TAKE:
      You fold the note and tuck it into your pocket.
      - FREQUENCY_NOTE -> player
  - BOLT_CUTTERS -> room
    + LOOK: Heavy-duty bolt cutters. The jaws are nicked but the edges still bite.
    + TAKE:
      You pull them out of the toolbox.
      - BOLT_CUTTERS -> player
  - BROKEN_CROWBAR -> room
    + LOOK: Half a crowbar. The break is clean — metal fatigue. No use to anyone.

COMPANION
+ LOOK: One of the freed prisoners. Wiry, watchful, sticking close. They haven't said much since catching up with you on the road.

GATE
+ LOOK: Chain-link, six feet high. A padlock holds the gate shut, the chain brown with rust. Through the mesh you can make out two buildings: one with the antenna mast, one a squat concrete shed. Gravel between them.
+ USE: You rattle the chain. The padlock holds. You need to cut through it.
+ USE + BOLT_CUTTERS:
  You set the jaws around the thickest link and squeeze. The chain parts with a dull snap. You kick the gate open.
  - GATE -> trash
  - BOLT_CUTTERS -> trash
  - OUTPOST_COMPOUND -> room
    + LOOK: Two buildings face each other across a gravel clearing. The one on the left has the antenna mast — some kind of relay station. The one on the right is a concrete shed, open on one side. Cables run between them along the ground.
    + USE:
      You step through and cross the clearing toward the shed.
      - player -> "Generator Shed"
