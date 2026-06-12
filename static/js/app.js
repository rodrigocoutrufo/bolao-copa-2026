document.addEventListener('DOMContentLoaded', () => {
    
    // ==========================================================================
    // CONTROLO DE INSTÂNCIA E PERSISTÊNCIA DE TEMA (CLARO / ESCURO)
    // ==========================================================================
    const themeBtn = document.getElementById('toggle-theme-btn');
    
    function atualizarIconeTema(tema) {
        if (!themeBtn) return;
        const icone = themeBtn.querySelector('i');
        if (tema === 'light') {
            icone.className = 'fa-solid fa-moon'; // Se está claro, mostra a lua para escurecer
        } else {
            icone.className = 'fa-solid fa-sun';  // Se está escuro, mostra o sol para clarear
        }
    }

    // Inicializa o ícone com base no estado atual herdado do HTML
    const temaAtual = document.documentElement.getAttribute('data-theme') || 'dark';
    atualizarIconeTema(temaAtual);

    if (themeBtn) {
        themeBtn.addEventListener('click', () => {
            const tAcesso = document.documentElement.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
            
            // Aplica a mutação visual com efeito fade controlado pelo CSS
            document.documentElement.setAttribute('data-theme', tAcesso);
            localStorage.setItem('bolao-theme', tAcesso);
            atualizarIconeTema(tAcesso);
        });
    }

    // ==========================================================================
    // FILTRAGEM DE INTERFACE DIRETIVA
    // ==========================================================================
    const botoesFiltro = document.querySelectorAll('.filter-btn');
    const cardsJogos = document.querySelectorAll('.match-card');

    botoesFiltro.forEach(botao => {
        botao.addEventListener('click', () => {
            botoesFiltro.forEach(b => b.classList.remove('active'));
            botao.classList.add('active');

            const faseSelecionada = botao.getAttribute('data-stage');

            cardsJogos.forEach(card => {
                const faseCard = card.getAttribute('data-stage');
                let exibir = false;

                if (faseSelecionada === 'all') {
                    exibir = true;
                } else if (faseSelecionada === 'Semifinal') {
                    exibir = ['Semifinal', 'Terceiro Lugar', 'Grande Final'].includes(faseCard);
                } else {
                    exibir = (faseCard === faseSelecionada);
                }

                card.style.display = exibir ? 'flex' : 'none';
            });
        });
    });

    // ==========================================================================
    // DISPARAR AJAX INDIVÍDUOS
    // ==========================================================================
    const botoesSalvar = document.querySelectorAll('.btn-salvar');
    botoesSalvar.forEach(botao => {
        botao.addEventListener('click', async () => {
            const card = botao.closest('.match-card');
            const jogoId = card.getAttribute('data-id');
            const golsA = card.querySelector('.input-gols-a').value;
            const golsB = card.querySelector('.input-gols-b').value;

            if (golsA === '' || golsB === '') {
                alert('Preencha os dois campos de placar.');
                return;
            }

            if (!confirm("Confirmar envio do palpite? Ele será bloqueado para edição.")) return;

            botao.disabled = true;
            botao.innerText = "GRAVANDO...";

            try {
                const response = await fetch(`/salvar_palpite/${jogoId}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ gols_a: golsA, gols_b: golsB })
                });
                const data = await response.json();

                if (data.success) {
                    window.location.reload();
                } else {
                    alert(data.message);
                    botao.disabled = false;
                    botao.innerText = "SALVAR PALPITE";
                }
            } catch {
                alert('Inconsistência de rede.');
                botao.disabled = false;
                botao.innerText = "SALVAR PALPITE";
            }
        });
    });

    // ==========================================================================
    // CRAVAR CAMPEÃO DO MUNDO
    // ==========================================================================
    const btnCampeao = document.getElementById('btn-cravar-campeao');
    const selectCampeao = document.getElementById('select-campeao');

    if (btnCampeao && selectCampeao) {
        btnCampeao.addEventListener('click', async () => {
            const nomeSelecao = selectCampeao.value;
            const optionUrl = selectCampeao.options[selectCampeao.selectedIndex].getAttribute('data-codigo');

            if (!nomeSelecao) {
                alert("Selecione uma equipe nacional.");
                return;
            }

            if (!confirm(`Confirmar ${nomeSelecao} como campeão definitivo do torneio?`)) return;

            btnCampeao.disabled = true;
            btnCampeao.innerText = "GRAVANDO...";

            try {
                const response = await fetch('/salvar_campeao', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ campeao: nomeSelecao, codigo: optionUrl })
                });
                const data = await response.json();

                if (data.success) {
                    window.location.reload();
                } else {
                    alert(data.message);
                    btnCampeao.disabled = false;
                    btnCampeao.innerText = "CRAVAR";
                }
            } catch {
                alert("Erro ao enviar dados.");
                btnCampeao.disabled = false;
            }
        });
    }

    // AUTO-SELECT INPUT FOCUS
    document.querySelectorAll('.score-input:not(:disabled)').forEach(input => {
        input.addEventListener('focus', () => input.select());
    });
});