REQUIREMENTS
============
on the host system the follwoins must be installed before running the code.

- BCC_tools
- lxc (currently this only works with lxc)

Running
======

usage: container_monitor.py [-h] [-i I] [-o O] container_name

positional arguments:
  container_name  Name of the container to monitor.

optional arguments:<br />
-h, --help      show this help message and exit<br />
-i I            interval between each poll (default 30 seconds).<br />
-o O            output file to store logs(default is <container_name>.log.<br />
  

