# Hallway
LOOK: A long corridor. Pipes run along the ceiling. Emergency lighting casts a dim red glow. Thin red laser beams crisscross the passage. At the far end, a door marked EXIT.

PASSAGE
+ LOOK: The open doorway back to the basement.
+ USE:
  You head back through the passage.
  - player -> "Basement"

LASER_GRID
+ LOOK: A security grid. Thin red beams slice the corridor from floor to ceiling.
+ USE: You'd be cut to ribbons walking through that.
+ USE + KNIFE:
  You angle the blade into the nearest beam. It refracts, hitting a sensor on the far wall. The grid flickers and dies.
  - LASER_GRID -> trash
  - KNIFE -> trash

SECURITY_CONSOLE
+ LOOK: A monitor showing camera feeds — holding cells, rows of them. People are alive in there.
+ USE: The console needs some kind of override code.
+ OVERRIDE:
  You punch the override code into the console. Every cell door in the facility clicks open at once. Alarms blare. On the monitors, figures stumble into corridors, blinking in the light.

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
