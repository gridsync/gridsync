Tor integration
===============

**WARNING: Tor integration in Gridsync is currently _experimental_ and is being made available for preliminary user-testing purposes only. As such -- and so long as this notice remains -- it should be considered both unsafe and/or subject to change; do not rely upon this (yet)!**


Overview
--------

Beginning in version 0.4 (to be released), Gridsync provides built-in support for tunneling outgoing connections over the [Tor](https://www.torproject.org/) anonymity network. This allows users to connect to storage grids and share folders without revealing their geographical location to any of the parties typically involved in such activities, including:

* The operator of the storage grid and any/all introducer/storage nodes
* The magic-wormhole server used to negotiate grid and folder [invites](https://github.com/gridsync/gridsync/blob/master/docs/invite-codes.md)
* Any servers specified in the `icon_url` field of incoming invite messages 


Prerequisites
-------------

In order to route the above-mentioned connections over Tor, Gridsync requires that a Tor daemon be installed and running and configured to expose an available control port at one the following locations:

* `/var/run/tor/control` (UNIX socket): The default on Debian-based GNU/Linux systems
* `localhost:9051` (TCP): The standard control port for standalone `tor` daemons
* `localhost:9151` (TCP): The standard control port for TorBrowser's embedded `tor` daemon

If Gridsync _cannot_ find a running Tor daemon at any one of the above locations, any grid connections configured to use Tor will fail (with an error-message) until a new/working `tor` daemon is launched with a control port exposed. Gridsync will not attempt to connect without Tor for any connection that has Tor enabled.

(Note: In the future, Gridsync may offer the option to launch/configure a Tor daemon automatically on startup or when needed; see [Issue #??](https://github.com/gridsync/gridsync/issues))


Usage
-----

To enabled Tor for a given connection, users can simply check/enable the "Connect over the Tor network" checkbox (found on either the initial/first-run "welcome" screen or the "add new folder from invite code" window) while entering an invite code. Switching this checkbox "on" before proceeding with an invite will force any subsequent connections associated with that invitation/connection to be tunneled through the Tor network, in particular: 1) connecting to the `magic-wormhole` server, 2) fetching any service icons, and 3) the resulting Tahoe-LAFS connection(s) to the storage grid.

Alternatively, users may choose to enable Tor for a given connection from the manual configuration dialog (i.e., by selecting "Tor" from the "Connections" combobox/dropdown menu).

(Note: Currently, Gridsync does not provide the option to disable Tor connections once enabled; users wishing to connect to an existing Tor-enabled grid _without_ Tor should create a new connection to that grid with Tor disabled; see [Issue #100](https://github.com/gridsync/gridsync/issues/100))


Other notes
-----------

Gridsync's Tor integration relies largely upon -- and makes use of -- the existing implementations for Tor support already present in the Magic-Wormhole and Tahoe-LAFS applications. See the relevant documentation for each implementation ([here](https://magic-wormhole.readthedocs.io/en/latest/tor.html) and [here](https://tahoe-lafs.readthedocs.io/en/latest/anonymity-configuration.html), respectively) for further details.
