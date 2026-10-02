class InventoryError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status, self.code, self.message = status, code, message
        super().__init__(code)


def unavailable():
    return InventoryError(503, 'inventory_unavailable', 'Inventario no disponible. Inténtalo de nuevo.')
