Recovery Keys
=============

What is a "Recovery Key"?
-------------------------

A _Recovery Key_ is a small text file containing enough information (specifically, a grid's connection settings and a personal "rootcap") to a) re-establish a connection to a storage grid and b) restore access to any previously uploaded or joined folders. Gridsync uses Recovery Keys as primarily as backup mechanism; in the event that something goes wrong with your computer (e.g., hardware failure or accidental data-loss), you can import your Recovery Key into Gridsync in order to restore access to your folders.


How do I create a Recovery Key?
-------------------------------

Starting in Gridsync version 0.3, you can export a Recovery Key at any time either from the main window toolbar (next to the "Preferences" icon) or from the system tray menu. It is strongly recommended that you choose to _encrypt_ your Recovery Key with a strong password when prompted and store the resulting file in a safe and secure location (such as an encrypted USB drive), as any persons who can access your decrypted Recovery Key can also potentially access any of the folders you've uploaded or joined previously.


Do I need to export a new Recovery Key every time I add or join a new folder?
-----------------------------------------------------------------------------

No. Every time that you add or join a new folder, Gridsync will automatically "link" that folder into your personal "_rootcap_" -- the special top-level directory inside your grid that only you have access to. Because every exported Recovery Key contains a copy of this same rootcap -- and because the corresponding directory contains links to every folder you add or join -- you need only export it once (typically, shortly after joining a new storage grid).


My computer exploded and I need to restore my folders! How do I do it?
----------------------------------------------------------------------

From the initial Gridsync welcome screen, click on "I don't have an invite code" and then, under the "Import from Recovery Section" on the next screen, choose "Select file". If your Recovery Key was encrypted, you will be prompted for a passphrase and, assuming you enter it correctly, it your old settings will load after Gridsync finishes decrypting the file. Simply click "OK" after this to restore access to your previous connection and folders.

Note: when you first restore from a Recovery Key, your folders will appear in a "grayed out" state in main status window, indicating that they are only stored remotely, i.e., that they do not exist on your local computer). To re-download a folder, simply right- or double-click it from this list and select the desired download/sync location on your computer.


My Recovery Key is taking a long time to decrypt -- what gives?
---------------------------------------------------------------

Gridsync uses the [Argon2id](https://en.wikipedia.org/wiki/Argon2) key-derivation function when Recovery Keys, which adds additional time and memory constraints to the underlying encryption/decryption process. This is done intentionally in order to make brute-force attacks more difficult (i.e., to slow down attackers that might try to repeatedly guess your passphrase). On modern consumer hardware, a single decryption-attempt should only take approximately 5 seconds, however, if your computer is especially low on memory, this process could take considerably longer. If you find that the decryption process appears "stuck" (e.g., sitting at 99% on the progress indicator after some time has passed), try closing some applications and trying again.
