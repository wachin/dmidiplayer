from __future__ import annotations

from pathlib import Path

from PyQt6 import uic
from PyQt6.QtCore import QSignalBlocker
from PyQt6.QtWidgets import QDialog

from drumstick_py import BackendManager


class ConnectionsDialog(QDialog):
    def __init__(self, backend: BackendManager, parent: object | None = None) -> None:
        super().__init__(parent)
        ui_path = Path(__file__).resolve().parents[1] / "connections.ui"
        uic.loadUi(str(ui_path), self, package="dmidiplayer_py")

        self._backend = backend
        self.btnOutputDriverCfg.setEnabled(False)

        self.m_outputBackends.currentIndexChanged.connect(self._refresh_ports)
        self._populate_backends()
        self._refresh_ports()

    def _populate_backends(self) -> None:
        drivers = self._backend.output_drivers()
        with QSignalBlocker(self.m_outputBackends):
            self.m_outputBackends.clear()
            for driver in drivers:
                self.m_outputBackends.addItem(driver, driver)

    def _refresh_ports(self) -> None:
        driver = self.selected_driver()
        connections = self._backend.connections(driver)
        with QSignalBlocker(self.m_outputPorts):
            self.m_outputPorts.clear()
            for connection in connections:
                self.m_outputPorts.addItem(connection.name, connection)

    def selected_driver(self) -> str:
        data = self.m_outputBackends.currentData()
        return str(data) if data else "dummy"

    def set_selected_driver(self, driver: str) -> None:
        for index in range(self.m_outputBackends.count()):
            if self.m_outputBackends.itemData(index) == driver:
                self.m_outputBackends.setCurrentIndex(index)
                return

    def selected_connection(self) -> object | None:
        return self.m_outputPorts.currentData()

    def set_selected_connection_query(self, query: str) -> None:
        if not query:
            return
        for index in range(self.m_outputPorts.count()):
            connection = self.m_outputPorts.itemData(index)
            if getattr(connection, "matches", None) and connection.matches(query):
                self.m_outputPorts.setCurrentIndex(index)
                return

