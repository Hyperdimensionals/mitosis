# Mitosis

Blender add-on for procedurally animating the replication of objects and 'flock behavior'.

## Features

* Animate objects spawning and dividing into neighboring spaces.
* Specify speed, distance, axis, and style of spawning behavior, as well as size of spawned objects
* Specify post spawn behavior of objects, including location, size, and rotation changes.

## Tutorial

### Quickstart

* Download files, and then install the add on from the Blender <b>Preferences -> Add-ons</b> menu.  

* Upon installation, a panel for this add-on will appear within any selected object's <i>Properties</i> Editor. You can also access a popup of the settings under the <i>Object</i> menu when in Object Mode.

* Within the panel are various basic parameters to adjust. Hover the mouse over each for a basic description of its function.

* Click <i>Execute</i> (or <i>OK</i> if Mitosis is accessed via the popup panel) to write the animation.

### Behavior Modifiers

Click on the <i>Behavior Modifiers</i> button to access the settings panel. 

Behavior Modifiers allow for more complex post-replication behavior of each spawned object. From this panel, you can add Behavior Mods, and specify their behavior type, direction, duration, and amount.

Note that the <i>delay</i> parameter is based on the frame when each generation of spawned objects begins. So assigning a delay of <i>0</i> is later for each subsequent generation and depends on your settings in the main Mitosis panel.

As an example, if you'd like each spawned object to move 100m in the X direction for 30 frames, then 25m in the -Y direction for 20 frames, you'd create two Behavior Modifiers with these settings:
* Behavior Modifier #1:
    * Behavior: <i>Move</i>, Direction: <i>X</i>, Delay: <i>0</i>, Duration: <i>30</i>, Value: <i>100</i>
* Behavior Modifier #2:
    * Behavior: <i>Move</i>, Direction: <i>Y</i>, Delay: <i>30</i>, Duration: <i>20</i>, Value: <i>-25</i>

The delay of <i>30</i> in Mod #2 means its animation will begin right as the animation for Mod #1 ends, since Mod #1's duration was 30 frames.

<b><i>Note: Currently, there are no checks implemented yet for if the animations of different behavior modifiers of the same type 'clash' timing wise and cause unpredictable results. </i></b>

## Credits

The author and maintainer of this module is Brendan Krueger