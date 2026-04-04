# Basement
LOOK: Damp concrete walls. Water drips from a cracked pipe overhead. Metal ducts run along the ceiling. A steel door is set into the far wall.

HATCH
+ LOOK: A metal hatch in the ceiling. The ladder leads back up to the control room.
+ USE:
  You climb the ladder back up.
  - player -> "Control Room"

WORKBENCH
+ LOOK: A rusted workbench. Tools are scattered across it, mostly broken. A crowbar lies among them.

CROWBAR
+ LOOK: A heavy iron crowbar. Could pry just about anything open.
+ TAKE:
  You grab the crowbar.
  - CROWBAR -> player

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
  You pry the compartment open. An old fuse tumbles out, hits the floor, and rolls under the workbench.
  - COMPARTMENT -> COMPARTMENT__EMPTY
    + LOOK: An empty compartment behind the fuse box.
  - FUSE__FLOOR -> room
    + LOOK: A glass fuse, just visible under the workbench.
    + TAKE:
      You get on your hands and knees and scramble under the bench. Your fingers close around the fuse — still intact.
      - FUSE__FLOOR -> player

AIR_DUCT
+ LOOK: A ventilation duct runs along the ceiling. One panel hangs open — big enough to crawl through. But it's too high to reach alone.
+ USE: You jump but your fingers barely graze the edge. You'd need someone to give you a boost.
+ USE + PRISONER:
  The prisoner cups their hands and you step up. You grab the edge of the open duct and haul yourself in. They climb up after you.

  Cool air rushes past. Then daylight. The duct opens onto the roof. Below, others are streaming out through every exit they can find.

  You made the right call.

PRISONER
+ LOOK: One of the freed prisoners. They followed you down here, eyes wide but determined.
