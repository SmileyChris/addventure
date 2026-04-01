# Basement
LOOK: Damp concrete walls. Water drips from a cracked pipe overhead. A steel door is set into the far wall.

WORKBENCH
+ LOOK: A rusted workbench. Tools are scattered across it, mostly broken.

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
      You step through the doorway.
      - player -> "Hallway"

STEEL_DOOR
+ LOOK: A heavy steel door. There's no handle — it must be powered.
+ USE: The door won't budge. It needs power.

COMPARTMENT
+ LOOK: A small compartment behind the fuse box. A fuse sits inside, still intact.
+ TAKE:
  You pull the fuse free.
  - COMPARTMENT -> COMPARTMENT__EMPTY
    + LOOK: An empty compartment behind the fuse box.
  - FUSE -> player
