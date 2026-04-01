# Control Room
LOOK: Fluorescent lights buzz. Banks of dead equipment line the walls. Something glints under the crate near your feet.

TERMINAL
+ LOOK: A dusty CRT. A keycard slot sits beside it.
+ USE: ACCESS DENIED flashes on the screen.
+ USE + KEYCARD:
  You slide the keycard. The screen floods with data. The room shudders as something powers up.
  - TERMINAL -> TERMINAL__UNLOCKED
    + LOOK: Scrolling text. A map shows the facility layout — Control Room, Basement, Hallway. An exit is marked at the far end of the hallway.
  - KEYCARD -> trash
  - ? -> "Basement"
    The power surge triggers the fuse box. A hidden compartment clicks open behind it.
    - COMPARTMENT -> room
  - room -> room__POWERED
    + LOOK: The room hums with energy. A hatch has opened in the floor.
    - HATCH -> room
      + LOOK: A dark opening leading down. You can hear water dripping below.
      + USE:
        You lower yourself into the darkness.
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

WALL_PANEL
+ LOOK: A steel panel bolted to the wall. One corner is bent outward slightly.
+ USE:
  You work the bent corner back and forth until it snaps free, revealing a crawlspace behind it.
  - WALL_PANEL -> WALL_PANEL__OPEN
    + LOOK: A gap in the wall. A crowbar lies wedged behind the panel.
  - CROWBAR -> room
    + LOOK: A heavy iron crowbar. Could pry just about anything open.
    + TAKE:
      You grab the crowbar.
      - CROWBAR -> player

BINDINGS
+ LOOK: Thick rope bindings around your wrists.

# Interactions

USE__RESTRAINED + KNIFE + BINDINGS:
  You saw through the rope. Your hands are free.
  - BINDINGS -> trash
  - USE__RESTRAINED -> USE

USE__RESTRAINED + CRATE:
  You lash out with your foot and kick the crate. It scrapes across the floor, revealing a knife underneath.
  - KNIFE -> room
    + LOOK: A rusty utility knife. Still sharp enough.
    + TAKE:
      You grab the knife.
      - KNIFE -> player

USE__RESTRAINED + *:
  You strain against the bindings. No use.
