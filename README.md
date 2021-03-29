# raspi-gardener
In which my Raspberry Pis and Beaglebones alert me on IRC when my plants need water.

Starting with a RasPi 3 B+, and probably next an original Model B, and then I have three Beaglebone Blacks and umpteen STM32 Black Pills that I'm sure could use some exercise.

## Installation

I hate systemd like anyone else rational but until something better comes along, copy the included systemd unit file to /etc/systemd/system/ and point it at your script file.
