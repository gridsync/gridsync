if __name__ == "__main__":
    import sys
    from qtpy.QtWidgets import QApplication
    from gridsync.gui.phrase import RecoveryPhraseImporter, generate_entropy

    app = QApplication(sys.argv)
    widget = RecoveryPhraseImporter()
    entropy_bytes = generate_entropy()
    widget.load(entropy_bytes)
    widget.completed.connect(lambda entropy: print("Success:", entropy))
    widget.show()
    sys.exit(app.exec_())
