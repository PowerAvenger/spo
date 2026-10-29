import unittest

import pandas as pd

from apuestas import (
    entrega_mensual_a_fecha,
    normalizar_entrega_mensual_meff,
    normalizar_precio_meff,
)


class MeffSpoTest(unittest.TestCase):
    def test_normaliza_nuevas_entregas_inglesas(self):
        self.assertEqual(normalizar_entrega_mensual_meff('Apr-27'), 'abr-27')
        self.assertEqual(normalizar_entrega_mensual_meff('Dec-26'), 'dic-26')

    def test_mantiene_entregas_historicas(self):
        self.assertEqual(normalizar_entrega_mensual_meff('ene-24'), 'ene-24')

    def test_recupera_entrega_desde_codigo(self):
        self.assertEqual(
            normalizar_entrega_mensual_meff('', 'FTBCMAPR27'), 'abr-27'
        )

    def test_orden_cronologico_supera_cambio_de_año(self):
        entregas = ['ene-27', 'dic-26', 'nov-26']
        self.assertEqual(
            sorted(entregas, key=entrega_mensual_a_fecha),
            ['nov-26', 'dic-26', 'ene-27'],
        )
        self.assertEqual(entrega_mensual_a_fecha('Apr-27'), pd.Timestamp(2027, 4, 1))

    def test_reconstruye_decimales_perdidos_en_sheet(self):
        self.assertEqual(normalizar_precio_meff(2005), 200.5)
        self.assertEqual(normalizar_precio_meff(19265), 192.65)
        self.assertEqual(normalizar_precio_meff(197), 197)
        self.assertEqual(normalizar_precio_meff(130.92), 130.92)


if __name__ == '__main__':
    unittest.main()
