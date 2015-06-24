import pyNotificationCenter

# tests

# show a message instantly
pyNotificationCenter.notify("Test message", "Subtitle", "This message should appear instantly, with a sound", sound=True)

# show a message after 20 seconds
pyNotificationCenter.notify("Another test", None, "This message appears after 20 seconds, without playing a sound", 20)
