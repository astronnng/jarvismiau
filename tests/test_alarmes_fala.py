import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import acoes
import jarvis
from lembretes import Lembretes


class ProcessarAlarmeBase(unittest.TestCase):
    def rodar(self, frase, tocando):
        """Roda jarvis.processar com o banco falso. Devolve (continua, chamadas de acoes)."""
        chamadas = []
        with patch.object(jarvis, "falar"), \
                patch.object(jarvis.lembretes, "Lembretes") as store, \
                patch.object(jarvis, "processar_com_ia", return_value=True), \
                patch.object(jarvis, "executar_acao",
                             lambda nome, params=None: chamadas.append((nome, params))):
            store.return_value.tem_alarmas_tocando.return_value = tocando
            continua = jarvis.processar(frase)
        return continua, chamadas


class ConfirmarAlarmeTocandoTests(ProcessarAlarmeBase):
    def test_relatos_sem_assunto_dispensam_o_alarme_que_toca(self):
        # "ok, verificado" virava assunto "ok" e nao achava alarme nenhum
        for frase in ("ok, verificado", "ok verificado", "verificado", "feito", "pronto, feito",
                      "ok, verifiquei", "beleza, resolvido", "Ok, verificado!"):
            continua, chamadas = self.rodar(frase, tocando=True)
            self.assertTrue(continua, frase)
            self.assertEqual(chamadas, [("confirmar_lembrete", {"assunto": ""})], frase)

    def test_relato_com_assunto_continua_funcionando(self):
        for frase, assunto in (("ok, discord verificado", "discord"),
                               ("ok, discord  verificado", "discord"),
                               ("pok, arroz verificado", "arroz"),
                               ("verifiquei o arroz", "arroz")):
            self.assertEqual(self.rodar(frase, True)[1],
                             [("confirmar_lembrete", {"assunto": assunto})], frase)

    def test_verbos_soltos_encerram_o_alarme_que_toca(self):
        # "encerre" sozinho nao era entendido e ia parar na IA
        for frase in ("encerre", "encerra", "encerrar", "pare", "para", "parar", "chega", "cala", "ok",
                      "beleza", "entendido", "pode encerrar", "pode parar", "por favor, encerra",
                      "desativa", "cancele", "pode desligar"):
            continua, chamadas = self.rodar(frase, tocando=True)
            self.assertTrue(continua, f"{frase}: nao deve fechar o Jarvis")
            self.assertEqual(chamadas, [("confirmar_lembrete", {"assunto": ""})], frase)

    def test_com_assunto_e_alarme_tocando(self):
        self.assertEqual(self.rodar("encerra o do discord", True)[1],
                         [("confirmar_lembrete", {"assunto": "discord"})])


class EncerrarLembreteNaoFechaOJarvisTests(ProcessarAlarmeBase):
    def test_encerrar_o_lembrete_nao_e_sair(self):
        # O bug: "encerrar o lembrete" casava com a palavra "encerrar" da regra de sair
        for tocando in (True, False):
            for frase in ("encerrar o lembrete", "encerre o lembrete", "encerrar o alarme",
                          "cancela o lembrete", "encerrar esse lembrete"):
                continua, chamadas = self.rodar(frase, tocando)
                self.assertTrue(continua, f"{frase} (tocando={tocando}) fechou o Jarvis")
                self.assertEqual(chamadas, [("confirmar_lembrete", {"assunto": ""})], frase)

    def test_encerrar_o_lembrete_de_um_assunto(self):
        self.assertEqual(self.rodar("encerre o lembrete do discord", False)[1],
                         [("confirmar_lembrete", {"assunto": "discord"})])
        self.assertEqual(self.rodar("cancela o lembrete de verificar o forno", False)[1],
                         [("confirmar_lembrete", {"assunto": "verificar o forno"})])

    def test_citar_lembrete_impede_a_saida_mesmo_sem_regra_de_alarme(self):
        continua, _ = self.rodar("stop lembrete", False)
        self.assertTrue(continua)

    def test_sair_de_verdade_continua_saindo(self):
        for frase in ("sair", "tchau", "encerrar", "desligar o jarvis", "goodbye"):
            continua, chamadas = self.rodar(frase, tocando=False)
            self.assertFalse(continua, frase)
            self.assertEqual(chamadas, [], frase)

    def test_sair_com_alarme_tocando_ainda_sai_mas_encerrar_dispensa(self):
        self.assertFalse(self.rodar("tchau", True)[0])
        self.assertFalse(self.rodar("sair", True)[0])
        continua, chamadas = self.rodar("encerrar", True)      # com alarme: dispensa, nao sai
        self.assertTrue(continua)
        self.assertEqual(chamadas, [("confirmar_lembrete", {"assunto": ""})])


class VerbosAmbiguosFicamComSeusComandosTests(ProcessarAlarmeBase):
    def test_sem_alarme_tocando_estas_frases_nao_sao_de_alarme(self):
        for frase in ("ok", "ok, verificado", "encerre", "para", "chega", "verificado", "confirmar",
                      "pare a musica", "cancelar a musica", "parar o video", "cancela isso"):
            chamadas = self.rodar(frase, tocando=False)[1]
            self.assertNotIn("confirmar_lembrete", [c[0] for c in chamadas], frase)

    def test_cancelar_desligamento_chega_ao_comando_certo(self):
        # antes era "confirmar o alarme do desligamento"
        continua, chamadas = self.rodar("cancelar desligamento", tocando=False)
        self.assertTrue(continua)
        self.assertEqual(chamadas, [("cancelar_desligamento", None)])

    def test_confirmar_com_assunto_continua_valendo_sem_alarme_tocando(self):
        self.assertEqual(self.rodar("confirmar arroz no fogo", False)[1],
                         [("confirmar_lembrete", {"assunto": "arroz no fogo"})])


class LembretesEncerrarTests(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.addCleanup(self.pasta.cleanup)
        self.store = Lembretes(Path(self.pasta.name) / "l.sqlite3")

    def test_cena_da_conversa_dois_lembretes_do_discord(self):
        """Um alarme tocando (13:33) e outro marcado para 13:39, ambos 'verificar o discord'."""
        self.store.criar("verificar o discord", 0.0167, agora=1000)     # vence em ~1s
        self.store.criar("verificar o discord", 3, agora=1000)          # vence em 3 min
        self.store.marcar_alarmas(agora=1002)                           # o primeiro passa a tocar
        # "ok, discord verificado": encerra so o que toca
        self.assertIn("confirmado", self.store.encerrar("discord", agora=1003))
        self.assertEqual([r["estado"] for r in self.store.listar()], ["pendente"])
        # "encerrar o lembrete": nada toca, o futuro e cancelado
        self.assertIn("cancelado", self.store.encerrar("", agora=1004))
        self.assertEqual(self.store.listar(), [])

    def test_o_cancelado_nao_toca_depois(self):
        self.store.criar("ver o forno", 1, agora=1000)
        self.store.encerrar("", agora=1001)
        self.assertEqual(self.store.marcar_alarmas(agora=2000), [])

    def test_alarme_tocando_tem_prioridade_sobre_cancelar_futuro(self):
        self.store.criar("arroz", 0.01, agora=1000)
        self.store.criar("forno", 60, agora=1000)
        self.store.marcar_alarmas(agora=1001)
        self.assertIn("Alarme de arroz confirmado", self.store.encerrar("", agora=1001))
        self.assertEqual([r["motivo"] for r in self.store.listar()], ["forno"])

    def test_varios_futuros_sem_assunto_pergunta_qual(self):
        self.store.criar("arroz", 10, agora=1000)
        self.store.criar("forno", 20, agora=1000)
        resposta = self.store.encerrar("", agora=1001)
        self.assertIn("2 lembretes pendentes", resposta)
        self.assertEqual(len(self.store.listar()), 2)          # nada foi cancelado

    def test_cancela_pelo_assunto_so_o_certo(self):
        self.store.criar("arroz", 10, agora=1000)
        self.store.criar("forno", 20, agora=1000)
        self.assertIn("Lembrete de forno cancelado", self.store.encerrar("forno", agora=1001))
        self.assertEqual([r["motivo"] for r in self.store.listar()], ["arroz"])

    def test_assunto_ambiguo_entre_futuros_pede_o_completo(self):
        self.store.criar("ver o arroz", 10, agora=1000)
        self.store.criar("ver o forno", 20, agora=1000)
        self.assertIn("mais de um lembrete", self.store.encerrar("ver", agora=1001))
        self.assertEqual(len(self.store.listar()), 2)

    def test_assunto_inexistente_e_sem_lembretes(self):
        self.assertIn("Nao ha alarme tocando nem lembrete pendente", self.store.encerrar("", agora=1))
        self.store.criar("arroz", 10, agora=1000)
        self.assertIn("Nao encontrei alarme ativo", self.store.encerrar("banana", agora=1001))
        self.assertEqual(len(self.store.listar()), 1)

    def test_confirmar_antigo_nao_cancela_futuros(self):
        self.store.criar("arroz", 10, agora=1000)
        self.assertIn("Nao encontrei", self.store.confirmar("arroz", agora=1001))
        self.assertEqual(len(self.store.listar()), 1)


class AcaoUsaEncerrarTests(unittest.TestCase):
    def test_confirmar_lembrete_passa_pelo_encerrar(self):
        with patch.object(acoes.armazenamento_lembretes, "Lembretes") as store:
            store.return_value.encerrar.return_value = "ok"
            self.assertEqual(acoes.confirmar_lembrete(None, assunto="arroz"), "ok")
        store.return_value.encerrar.assert_called_once_with("arroz")


if __name__ == "__main__":
    unittest.main()
