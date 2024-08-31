import sys
from PyQt5.QtWidgets import QApplication
from ui import InvestmentToolApp

def main():
    app = QApplication(sys.argv)
    window = InvestmentToolApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
