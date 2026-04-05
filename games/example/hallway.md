# Cell Block
LOOK: A long corridor lined with steel doors. Small windows set into each one, faces pressed against the glass. Eyes follow you as you pass. Thin red laser beams crisscross the far end of the passage. Beyond them, a door marked EXIT.

PASSAGE
+ LOOK: The open doorway back to the basement.
+ USE:
  You head back through the passage.
  - player -> "Basement"

CELLS
+ LOOK: Dozens of holding cells, each sealed with an electronic lock. The people inside are gaunt but alive. One of them mouths something at you through the glass — *please*.
+ USE: The locks are electronic. You can't force them open by hand.

LASER_GRID
+ LOOK: A security grid. Thin red beams slice the corridor from floor to ceiling.
+ USE: You'd be cut to ribbons walking through that.
+ USE + KNIFE:
  You angle the blade into the nearest beam. It refracts, hitting a sensor on the far wall. The grid flickers and dies.
  - LASER_GRID -> trash
  - KNIFE -> trash

SECURITY_CONSOLE
+ LOOK: A console mounted on the wall. A row of cell lock indicators glow red. A keypad blinks beneath the screen.
+ USE: The console needs some kind of override code.
+ OVERRIDE:
  You punch the override code into the console. Every cell lock indicator flips to green. Bolts slam back in unison. Doors swing open down the length of the corridor. People stumble out, blinking, clutching each other.

  The code is spent — but these people are free.
  - OVERRIDE -> trash
  - ? -> "Basement"
    One of the freed prisoners catches up to you, breathless. "I know another way out — through the air ducts."
    - PRISONER -> room

EXIT_DOOR
+ LOOK: A heavy door with an electronic lock. Daylight leaks through the edges.
+ USE: The lock's keypad blinks red. You need some kind of override code.
+ OVERRIDE:
  You punch in the code. The lock clicks green. The door swings open. Cold air hits your face. You're out.

  You don't look back.

  ::: fragment
  The light is wrong — too bright, too open after all that concrete.

  You walk. Then run. Down a service road, through a gap in the perimeter fence, into a stand of pines. You don't stop until the facility is out of sight.

  Later, you find a payphone. You know a journalist. You know what you saw.

  You left them behind. You know that too. The faces at the windows. The one who mouthed *please.* You tell yourself you had no choice.

  Maybe, with what you know now, you can do more good out here than you could have done in there.

  You pick up the receiver. You dial.

  *Ending: The Witness*
  :::

