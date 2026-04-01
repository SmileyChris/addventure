# Control Room
LOOK: Fluorescent lights buzz. Banks of dead equipment line the walls. Something glints under the crate near your feet.

TERMINAL
+ LOOK: A dusty CRT. A keycard slot sits beside it.
+ USE: ACCESS DENIED flashes on the screen.
+ USE + KEYCARD:
  You slide the keycard. The screen floods with data.
  - TERMINAL -> TERMINAL__UNLOCKED
    + LOOK: Scrolling text. A map shows the facility layout.
  - KEYCARD -> trash
  - ? -> "Basement"
    The power surge triggers the fuse box. A hidden compartment clicks open behind it.
    - COMPARTMENT -> room
  - room -> room__POWERED
    + LOOK: The room hums with energy. A hatch has opened in the floor.
    + HATCH -> room
      + LOOK: A dark opening, just wide enough to squeeze through.
      + USE:
        You lower yourself into the darkness.
        - player -> "Basement"

CRATE
+ LOOK: A heavy wooden crate, nailed shut. Something metallic catches the light underneath.
+ USE:
  You kick the crate hard. It scrapes across the floor, revealing a knife underneath.
  - KNIFE -> room
    + LOOK: A rusty utility knife. Still sharp enough.
    + TAKE:
      You grab the knife.
      - KNIFE -> player
+ USE + CROWBAR:
  You pry it open. A keycard glints inside. A knife clatters out from underneath.
  - CRATE -> CRATE__OPEN
    + LOOK: A splintered crate, lid hanging off.
  - KEYCARD -> room
    + LOOK: A small keycard among the splinters.
    + TAKE:
      You pocket the keycard.
      - KEYCARD -> player
  - KNIFE -> room
  - CROWBAR -> trash

WALL_PANEL
+ LOOK: Featureless steel bolted to the wall.

BINDINGS
+ LOOK: Thick rope bindings around your wrists.

# Interactions

USE + KNIFE + BINDINGS:
  You saw through the rope. Your hands are free.
  - BINDINGS -> trash
  - USE__RESTRAINED -> USE

USE__RESTRAINED + CRATE:
  You lash out with your foot and kick the crate. It scrapes across the floor, revealing a knife underneath.
  - KNIFE -> room

USE__RESTRAINED + *:
  You strain against the bindings. No use.
