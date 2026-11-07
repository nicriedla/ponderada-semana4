# Ponderada CC08

Nicole Riedla Paiva Neves — análise de arquitetura, pipeline, concorrência e deadlock aplicada à pulseira Tato.

As três versões da questão A4 usam N=5 e produzem 20.000 amostras por execução. Execute cada comando três vezes, a partir da raiz do repositório:

```powershell
python3 .\ponderada\codigo\versao1.py
python3 .\ponderada\codigo\versao2.py
python3 .\ponderada\codigo\versao3.py
```

Python 3 é necessário. A versão 1 demonstra a condição de corrida; a versão 2 usa os três semáforos na ordem segura; a versão 3 troca a ordem no produtor para reproduzir o deadlock.
