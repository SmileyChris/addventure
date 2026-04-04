# Control Room
LOOK: Fluorescent lights buzz. Banks of dead equipment line the walls.
  A crate sits near your feet. Something glints underneath it. A metal hatch is set into the floor.

TERMINAL
+ LOOK: A dusty CRT. A keycard slot sits beside it.
+ USE: ACCESS DENIED flashes on the screen.
+ USE + KEYCARD:
  You slide the keycard. The screen floods with data — including an emergency override code. Deep below, something rumbles.
  - TERMINAL -> TERMINAL__UNLOCKED
    + LOOK: Scrolling text. A map shows the facility layout — Control Room, Basement, Hallway. An exit is marked at the far end of the hallway.
  - KEYCARD -> trash
  - -> OVERRIDE
  - ? -> "Basement"
    A power surge ripples through the basement. The fuse box shudders and a hidden compartment clicks open behind it.
    - COMPARTMENT -> room

HATCH
+ LOOK: A metal hatch set into the floor. A ladder descends into darkness.
+ USE:
  You lower yourself through the hatch and climb down the ladder.
  - player -> "Basement"

CRATE
+ LOOK: A heavy wooden crate, nailed shut. Something metallic catches the light underneath.
+ USE + CROWBAR:
  You pry the lid off. A keycard glints inside.
  - CRATE -> CRATE__OPEN
    + LOOK: A splintered crate, lid hanging off.
  - KEYCARD -> room
    + LOOK: A small keycard with a red stripe.
    + TAKE:
      You pocket the keycard.
      - KEYCARD -> player
  - CROWBAR -> trash

BINDINGS
+ LOOK: Thick rope bindings around your wrists.

# Interactions

USE__RESTRAINED + *:
  You strain against the bindings. No use.

USE__RESTRAINED + CRATE:
  You lash out with your foot and kick the crate. It scrapes across the floor, revealing a knife underneath.
  - KNIFE -> room

KNIFE
+ LOOK: A rusty utility knife. Still sharp enough.
+ TAKE:
  You stretch your bound hands down and just manage to close your fingers around the handle.
  - KNIFE -> player
+ USE__RESTRAINED:
  What do you want to use the knife with?

  *Hint: you can USE + KNIFE + (another thing)*

USE__RESTRAINED + KNIFE + BINDINGS:
  You saw through the rope. Your hands are free.
  - KNIFE -> player
  - BINDINGS -> trash
  - USE__RESTRAINED -> USE
