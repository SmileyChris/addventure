// Relay Station — Combination puzzle + payoff. The console is dead until the
// generator cue fires (on room entry). Then the player must tune the frequency
// using the note found in the truck, then transmit.

# Relay Station
LOOK: Banks of radio equipment line the walls, toggle switches and patch cables and frequency readouts. Dust on everything. The overhead light is dead. The only illumination comes through a narrow window facing the compound. The air smells like warm plastic and old solder.

CONSOLE
+ LOOK: The main console. A microphone on a coiled cord, a large frequency dial, rows of switches. The screen is dark. No power.
+ USE: You try every switch on the panel. Nothing. The screen stays black. There's no power — the cables run to the generator shed across the compound.

CONSOLE__POWERED
+ LOOK: The screen glows pale green, scrolling static. The frequency dial reads 00.0. A microphone sits in its cradle. The speaker hisses white noise — alive, but tuned to nothing.
+ USE: You press transmit. Static answers. Every frequency is empty noise. You need to know which channel to use.

FREQUENCY_DIAL
+ LOOK: A heavy dial set into the console face, calibrated in megahertz. The needle sits on zero.
+ USE: You turn the dial. It clicks through empty positions. Without power to the console, nothing happens.

CABINET
+ LOOK: A wall-mounted cabinet, door rusted open on its hinge. Mouldy logbooks stacked inside, and a flashlight with corroded batteries. Nothing worth salvaging.

LOGBOOK
+ LOOK: A logbook on the desk, spiral-bound, open to the last page. The handwriting slopes downward like the writer was in a hurry.
+ USE:
  The final entry: "Signal lost from main site 0340 hrs. No response any channel. Generator fuel low — spare drum in the shed. Locking up, heading south on foot. If anyone reads this: 47.3 MHz. Someone might still be listening."

DOORWAY
+ LOOK: The door. Daylight. The generator shed is visible across the gravel.
+ USE:
  You step out and cross the compound.
  - player -> "Generator Shed"

## Interactions

// Once the generator cue transforms CONSOLE to CONSOLE__POWERED, these become available.

USE + FREQUENCY_DIAL + FREQUENCY_NOTE:
  You smooth the crumpled note flat on the desk. 47.3. You grip the frequency dial and turn it slowly — past bursts of static, dead air, the ghost of a signal — until the display reads 47.3 MHz. The static sharpens into a carrier tone. Clean. Steady. Someone is transmitting on this frequency.
  - FREQUENCY_DIAL -> trash
  - FREQUENCY_NOTE -> trash
  - CONSOLE__POWERED -> CONSOLE__TUNED
    + LOOK: The display reads 47.3 MHz. A steady carrier tone hums from the speaker. The microphone waits in its cradle.
    + USE:
      You lift the microphone. Your thumb finds the transmit button.
      EVERYONE_OUT_ESCAPE?
        Your companion leans close. "Tell them how many. Tell them everything."

        You press transmit. "This is someone who just escaped a detention facility north of here. We freed dozens of people — they're still coming out. There are more inside. Send everyone you have."

        Static. Five seconds. Ten. Then a voice, distant but clear: "Copy that. Multiple units en route. Stay on this frequency."

        Your companion exhales. You set the microphone down. Through the window the pines are swaying. Somewhere far off, the thud of rotor blades.

        You sit on the floor. Your companion sits beside you. Neither of you speaks.

        For the first time in hours, you breathe.
      WITNESS_ESCAPE?
        You press transmit. "This is — " Your voice cracks. You start again. "I escaped a facility north of here. There are people still inside. A lot of people. I couldn't get them out. Send help. Please."

        Static. Five seconds. Ten. You're about to try again when a voice cuts through, distant but clear: "Copy that. Search and rescue en route. Stay on this frequency. Do not move."

        You set the microphone down carefully, as if it might break. Through the window the pines are swaying. The sky is the colour of tin.

        You sit on the floor with your back against the console. You close your eyes. You think about the faces at the windows. You'll call the journalist next. You'll tell them everything.

        For the first time in hours, you breathe.
      otherwise?
        You press transmit. "This is someone requesting emergency assistance. There is a facility north of this location. People are being held inside. Send help."

        Static. Five seconds. Ten. Then a voice, distant but clear: "Copy that. Search and rescue en route to your position. Stay on this frequency. Help is coming."

        You set the microphone down. Through the window the pines are swaying. The sky is the colour of tin. Somewhere far off — or maybe you're imagining it — the thud of rotor blades.

        You sit on the floor with your back against the console. You close your eyes.

        For the first time in hours, you breathe.
