import sqlite3
import tempfile
import unittest

from sorteio_core import (
    autenticar_utilizador,
    avaliar_imparcialidade,
    criar_admin,
    criar_utilizador,
    guardar_sorteio,
    limpar_lista_nomes,
    preparar_base_dados,
    realizar_sorteio,
)


class SorteioCoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_file.close()
        self.conn = sqlite3.connect(self.temp_file.name)
        preparar_base_dados(self.conn)
        criar_admin(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_limpeza_remove_duplicados_e_espacos(self):
        nomes = ["  Ana  ", "", "Bruno", "ana", " Carla   Silva "]
        self.assertEqual(limpar_lista_nomes(nomes), ["Ana", "Bruno", "Carla Silva"])

    def test_autenticacao_admin_funciona(self):
        sucesso, _, username = autenticar_utilizador(self.conn, "admin", "1234")
        self.assertTrue(sucesso)
        self.assertEqual(username, "admin")

    def test_criacao_de_utilizador_persiste(self):
        criar_utilizador(self.conn, "utilizador.novo", "senha123")
        cursor = self.conn.cursor()
        cursor.execute("SELECT username FROM users WHERE username = ?", ("utilizador.novo",))
        self.assertEqual(cursor.fetchone()[0], "utilizador.novo")

    def test_sorteio_devolve_numeros_unicos(self):
        sorteio = realizar_sorteio(10, 3, ["Ana", "Bruno", "Carla"], rng=__import__("random").Random(10))
        numeros = [item["numero"] for item in sorteio["selecionados"]]
        self.assertEqual(len(numeros), len(set(numeros)))
        self.assertEqual(len(numeros), 3)

    def test_quiquadrado_equilibrado(self):
        auditoria = avaliar_imparcialidade(4, 1, repeticoes=4000, seed=123)
        self.assertGreaterEqual(auditoria["p_value"], 0.01)

    def test_guardar_sorteio_regista_historico(self):
        auditoria = avaliar_imparcialidade(5, 2, repeticoes=100, seed=99)
        sorteio = realizar_sorteio(5, 2, ["Ana", "Bruno", "Carla", "Dino", "Eva"])
        guardar_sorteio(
            self.conn,
            "admin",
            5,
            2,
            sorteio["participantes"],
            sorteio["selecionados"],
            auditoria,
        )

        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sorteios")
        self.assertEqual(cursor.fetchone()[0], 1)

        cursor.execute("SELECT COUNT(*) FROM event_logs WHERE event_type = 'SORTEIO_EXECUTADO'")
        self.assertEqual(cursor.fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
