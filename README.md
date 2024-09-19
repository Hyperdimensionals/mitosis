# Mitosis

Blender add-on for procedurally animating the replication of objects and 'flock behavior'.

## Features

* Animate objects spawning and dividing into neighboring spaces.
* Specify speed, distance, axis, and style of spawning behavior, as well as size of spawned objects
* Specify post spawn behavior of objects, including location, size, and rotation changes.

## Tutorial

### Quickstart

* Download files, and then install the add on from the Blender <b>Preferences -> Add-ons</b> menu. (Click the `install...` button and navigate to `mitosis.py`.)

* Upon installation, a panel for this add-on will appear within any selected object's <i>Properties</i> Editor. You can also access a popup of the add-on under the <i>Object</i> menu when in Object Mode.

* Within the panel are various basic parameters to adjust. Hover the mouse over each for a basic description of its function.

* Click <i>Execute</i> (or <i>OK</i> if Mitosis is accessed via the popup panel) to write the animation.

### Behavior Modifiers

Behavior Modifiers allow for more complex post-replication behavior of each spawned object.

Click on the <i>Behavior Modifiers</i> button to access the settings panel. From this panel, you can add Behavior Mods, and specify their behavior type, direction, duration, and amount.

Note that the <i>delay</i> parameter is based on the frame when each generation of spawned objects begins. So assigning a delay of <i>0</i> is later for each subsequent generation and depends on your settings in the main Mitosis panel.

As an example, if you'd like each spawned object to move 100m in the X direction for 30 frames, then 25m in the -Y direction for 20 frames, you'd create two Behavior Modifiers with these settings:
* Behavior Modifier #1:
    * Behavior: <i><b>Move</b></i>, Direction: <i><b>X</b></i>, Delay: <i><b>0</b></i>, Duration: <i><b>30</b></i>, Value: <i><b>100</b></i>
* Behavior Modifier #2:
    * Behavior: <i><b>Move</b></i>, Direction: <i><b>Y</b></i>, Delay: <i><b>30</b></i>, Duration: <i><b>20</b></i>, Value: <i><b>-25</b></i>

The delay of <i>30</i> in Mod #2 means its animation will begin right as the animation for Mod #1 ends, since Mod #1's duration was 30 frames.

<b><i>Note: There are no checks implemented yet for if the timing of different behavior modifiers of the same type overlap and cause unpredictable results. </i></b>

## Compatability

Tested with:

<b>Blender - 4.1.1</b>

## Credits

The author and maintainer of this module is Brendan Krueger