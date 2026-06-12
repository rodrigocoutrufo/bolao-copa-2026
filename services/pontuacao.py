def calcular_pontos(palpite_a, palpite_b, resultado_a, resultado_b):
    """
    Calcula a pontuação de um palpite baseado no resultado real do jogo.
    - Acertou o placar exato: 3 pontos
    - Acertou vitória/empate com placar diferente: 1 ponto
    - Errou tudo: 0 pontos
    """
    # 1. Acerto Exato do Placar (3 Pontos)
    if palpite_a == resultado_a and palpite_b == resultado_b:
        return 3

    # Determina a tendência do palpite e do resultado real
    tendencia_palpite = 1 if palpite_a > palpite_b else (-1 if palpite_b > palpite_a else 0)
    tendencia_real = 1 if resultado_a > resultado_b else (-1 if resultado_b > resultado_a else 0)

    # 2. Acertou a tendência (Vitória de A, Vitória de B ou Empate diferente) (1 Ponto)
    if tendencia_palpite == tendencia_real:
        return 1

    # 3. Errou o resultado (0 Pontos)
    return 0