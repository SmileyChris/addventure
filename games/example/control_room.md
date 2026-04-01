# Control Room
LOOK: Fluorescent lights buzz. Banks of dead equipment line the walls.

TERMINAL
+ LOOK: A dusty CRT. A keycard slot sits beside it.
+ USE: ACCESS DENIED flashes on the screen.
+ USE + KEYCARD:
  You slide the keycard. The screen floods with data.
  - TERMINAL -> TERMINAL__UNLOCKED
    + LOOK: Scrolling text. A map shows the facility layout.
  - KEYCARD -> trash
  - room -> room__POWERED
    + LOOK: The room hums with energy. A hatch has opened in the floor.
    + HATCH -> room
      + LOOK: A dark opening, just wide enough to squeeze through.
      + USE:
        You lower yourself into the darkness.
        - player -> "Basement"

CRATE
+ LOOK: A heavy wooden crate, nailed shut.
+ USE + CROWBAR:
  You pry it open. A keycard glints inside.
  - CRATE -> CRATE__OPEN
    + LOOK: A splintered crate, lid hanging off.
  - KEYCARD -> room
    + LOOK: A small keycard among the splinters.
    + TAKE:
      You pocket the keycard.
      - KEYCARD -> player
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

USE__RESTRAINED + *:
  You strain against the bindings. No use.
