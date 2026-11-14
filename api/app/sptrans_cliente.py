"""CORREÇÃO DA SABOTAGEM (DevOps): o token sai do código e passa a vir de variável de ambiente
(GitHub Secrets / App Settings). O commit com o valor foi reescrito, então ele não fica no histórico."""
import os

SPTRANS_TOKEN = os.getenv("SPTRANS_TOKEN", "")
