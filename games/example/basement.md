# Basement
LOOK: Damp concrete walls. Water drips from a cracked pipe overhead. Metal ducts run along the ceiling. A steel door is set into the far wall.

HATCH
+ LOOK: A metal hatch in the ceiling. The ladder leads back up to the control room.
+ USE:
  You climb the ladder back up.
  - player -> "Control Room"

WORKBENCH
+ LOOK: A rusted workbench. A keycard with a red stripe lies among the scattered tools.

KEYCARD
+ LOOK: A small keycard with a red stripe.
+ TAKE:
  You pocket the keycard.
  - KEYCARD -> player

STEEL_DOOR
+ LOOK: A heavy steel door. There's no handle — it must be powered.
+ USE: The door won't budge. It needs power.

FUSE_BOX
+ LOOK: A fuse box mounted on the wall, door hanging open. The slots are empty.
+ USE + FUSE:
  You slot the fuse into place. Sparks fly. The overhead lights flicker on and the steel door groans, then slides open.
  - FUSE -> trash
  - FUSE_BOX -> FUSE_BOX__POWERED
    + LOOK: The fuse box hums quietly. A single fuse sits in the top slot.
  - STEEL_DOOR -> STEEL_DOOR__OPEN
    + LOOK: The door stands open. A long hallway stretches beyond it.
    + USE:
      You step through the doorway into the hallway.
      - player -> "Hallway"

COMPARTMENT
+ LOOK: A small compartment behind the fuse box. Something is wedged inside.
+ USE:
  You reach in and pull out an old fuse, still intact.
  - COMPARTMENT -> COMPARTMENT__EMPTY
    + LOOK: An empty compartment behind the fuse box.
  - FUSE -> room
    + LOOK: A glass fuse. It looks like it might still work.
    + TAKE:
      You pocket the fuse.
      - FUSE -> player

AIR_DUCT
+ LOOK: A ventilation duct runs along the ceiling. One panel hangs open — big enough to crawl through. But it's too high to reach alone.
+ USE: You jump but your fingers barely graze the edge. You'd need someone to give you a boost.
+ USE + PRISONER:
  The prisoner cups their hands and you step up. You grab the edge of the open duct and haul yourself in. They climb up after you.

  Cool air rushes past. Then daylight. The duct opens onto the roof. Below, others are streaming out through every exit they can find.

  You made the right call.

PRISONER
+ LOOK: One of the freed prisoners. They followed you down here, eyes wide but determined.
