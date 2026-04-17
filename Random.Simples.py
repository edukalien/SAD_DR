import json
import tkinter as tk
from tkinter import filedialog, messagebox

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from sorteio_core import (
    autenticar_utilizador,
    avaliar_imparcialidade,
    criar_admin,
    criar_utilizador,
    guardar_sorteio,
    ligar_base_dados,
    limpar_lista_nomes,
    limpar_username,
    listar_eventos,
    listar_sorteios,
    preparar_base_dados,
    realizar_sorteio,
    registar_evento,
)


conn = ligar_base_dados("sistema.db")
preparar_base_dados(conn)
criar_admin(conn)

nomes = []
utilizador_atual = None
ultimo_resultado = []
ultima_auditoria = None


def criar_botao(parent, texto, comando, bg, fg="white", width=18):
    return tk.Button(
        parent,
        text=texto,
        command=comando,
        width=width,
        bg=bg,
        fg=fg,
        activebackground=bg,
        activeforeground=fg,
        relief="flat",
        cursor="hand2",
        pady=8,
    )


def atualizar_lista_participantes():
    lista.delete(0, tk.END)
    for indice, nome in enumerate(nomes, start=1):
        lista.insert(tk.END, f"{indice} - {nome}")

    texto_participantes.delete("1.0", tk.END)
    if nomes:
        texto_participantes.insert("1.0", "\n".join(nomes))
        entrada_total_var.set(str(len(nomes)))


def limpar_dados_entrada():
    global nomes

    bruto = texto_participantes.get("1.0", tk.END).splitlines()
    nomes = limpar_lista_nomes(bruto)
    atualizar_lista_participantes()
    registar_evento(conn, utilizador_atual, "LIMPEZA_DADOS", "Lista de participantes normalizada.")

    if nomes:
        messagebox.showinfo("Limpeza concluida", "Os participantes foram limpos e duplicados removidos.")
    else:
        messagebox.showwarning("Aviso", "Não existem participantes válidos para limpar.")


def adicionar_nome():
    global nomes

    nome = entrada_nome.get()
    novos = limpar_lista_nomes([nome])
    if not novos:
        messagebox.showwarning("Aviso", "Informe um nome valido.")
        return

    nome_limpo = novos[0]
    if nome_limpo.casefold() in {item.casefold() for item in nomes}:
        messagebox.showwarning("Aviso", "Este participante ja existe na lista.")
        return

    nomes.append(nome_limpo)
    entrada_nome.delete(0, tk.END)
    atualizar_lista_participantes()


def carregar_participantes_do_ficheiro():
    global nomes

    caminho = filedialog.askopenfilename(
        title="Selecionar ficheiro de participantes",
        filetypes=[("Ficheiros de texto", "*.txt"), ("Todos os ficheiros", "*.*")],
    )
    if not caminho:
        return

    with open(caminho, "r", encoding="utf-8") as ficheiro:
        linhas = ficheiro.read().splitlines()

    nomes = limpar_lista_nomes(linhas)
    atualizar_lista_participantes()
    registar_evento(conn, utilizador_atual, "IMPORTACÃO_PARTICIPANTES", f"Participantes importados de {caminho}.")
    messagebox.showinfo("Sucesso", f"Foram carregados {len(nomes)} participantes.")


def limpar_tudo():
    global nomes, ultimo_resultado, ultima_auditoria

    nomes = []
    ultimo_resultado = []
    ultima_auditoria = None

    entrada_nome.delete(0, tk.END)
    texto_participantes.delete("1.0", tk.END)
    entrada_total_var.set("")
    entrada_qtd.delete(0, tk.END)
    lista.delete(0, tk.END)
    resultado.delete(0, tk.END)
    resumo_auditoria_var.set("Nenhum sorteio executado nesta sessao.")
    registar_evento(conn, utilizador_atual, "LIMPEZA_SESSAO", "Campos da interface foram limpos.")


def obter_total_participantes():
    if nomes:
        entrada_total_var.set(str(len(nomes)))
        return len(nomes)

    total_texto = entrada_total_var.get().strip()
    if not total_texto:
        raise ValueError("Informe o total de participantes ou adicione nomes a lista.")

    return int(total_texto)


def fazer_sorteio():
    global ultimo_resultado, ultima_auditoria

    try:
        total = obter_total_participantes()
        quantidade_texto = entrada_qtd.get().strip()
        if not quantidade_texto:
            messagebox.showwarning("Aviso", "Precisa primeiro de indicar o numero de sorteados.")
            return

        quantidade = int(quantidade_texto)

        # Executa o sorteio real e, em paralelo, calcula o relatorio estatistico
        # usado para auditar a imparcialidade do algoritmo.
        sorteio = realizar_sorteio(total, quantidade, nomes)
        auditoria = avaliar_imparcialidade(total, quantidade)

        resultado.delete(0, tk.END)
        for item in sorteio["selecionados"]:
            resultado.insert(tk.END, f'{item["numero"]} - {item["nome"]}')

        # Cada sorteio fica persistido com o operador, configuracao e resultado.
        guardar_sorteio(
            conn,
            utilizador_atual,
            total,
            quantidade,
            sorteio["participantes"],
            sorteio["selecionados"],
            auditoria,
        )

        ultimo_resultado = sorteio["selecionados"]
        ultima_auditoria = auditoria
        resumo_auditoria_var.set(
            "Teste de Qui-quadrado: "
            f"X2={auditoria['chi_square']:.4f} | p={auditoria['p_value']:.4f} | "
            f"{auditoria['mensagem']}"
        )
        messagebox.showinfo("Sucesso", "Sorteio concluído e registado no historico.")

    except ValueError as erro:
        messagebox.showerror("Erro", str(erro))


def abrir_historico():
    janela_historico = tk.Toplevel(janela)
    janela_historico.title("Historico e Auditoria")
    janela_historico.geometry("900x620")
    janela_historico.resizable(False, False)
    janela_historico.configure(bg="#eef3f8")

    frame = tk.Frame(janela_historico, bg="white", padx=20, pady=20, highlightbackground="#d5dde6", highlightthickness=1)
    frame.pack(fill="both", expand=True, padx=20, pady=20)

    tk.Label(frame, text="Historico de Sorteios", font=("Arial", 14, "bold"), bg="white", fg="#14324a").pack(anchor="w")
    tk.Label(frame, text="Consulta dos ultimos sorteios registados no sistema.", bg="white", fg="#667684").pack(anchor="w", pady=(4, 0))
    bloco_sorteios = tk.Frame(frame, bg="white")
    bloco_sorteios.pack(fill="x", pady=(8, 16))
    texto_sorteios = tk.Text(bloco_sorteios, height=12, wrap="word", bg="#f8fbfe", relief="solid", bd=1)
    scroll_sorteios = tk.Scrollbar(bloco_sorteios, orient="vertical", command=texto_sorteios.yview)
    texto_sorteios.configure(yscrollcommand=scroll_sorteios.set)
    texto_sorteios.pack(side="left", fill="both", expand=True)
    scroll_sorteios.pack(side="right", fill="y")

    # Mostra os sorteios mais recentes para consulta e rastreabilidade.
    for sorteio in listar_sorteios(conn, limite=15):
        sorteio_id, username, total, quantidade, resultado_json, created_at, chi_square, p_value = sorteio
        resultado_lista = json.loads(resultado_json)
        nomes_texto = ", ".join(f'{item["numero"]}-{item["nome"]}' for item in resultado_lista)
        texto_sorteios.insert(
            tk.END,
            f"[{created_at}] Sorteio #{sorteio_id} por {username} | total={total} | quantidade={quantidade}\n"
            f"Resultado: {nomes_texto}\n"
            f"Auditoria: X2={chi_square:.4f} | p={p_value:.4f}\n\n",
        )

    texto_sorteios.configure(state="disabled")

    tk.Label(frame, text="Log de Eventos", font=("Arial", 14, "bold"), bg="white", fg="#14324a").pack(anchor="w")
    tk.Label(frame, text="Registo de acções executadas pelos utilizadores.", bg="white", fg="#667684").pack(anchor="w", pady=(4, 0))
    bloco_eventos = tk.Frame(frame, bg="white")
    bloco_eventos.pack(fill="both", expand=True, pady=(8, 0))
    texto_eventos = tk.Text(bloco_eventos, height=12, wrap="word", bg="#f8fbfe", relief="solid", bd=1)
    scroll_eventos = tk.Scrollbar(bloco_eventos, orient="vertical", command=texto_eventos.yview)
    texto_eventos.configure(yscrollcommand=scroll_eventos.set)
    texto_eventos.pack(side="left", fill="both", expand=True)
    scroll_eventos.pack(side="right", fill="y")

    # O log de eventos ajuda a identificar quem fez cada acao no sistema.
    for username, event_type, details, created_at in listar_eventos(conn, limite=25):
        texto_eventos.insert(
            tk.END,
            f"[{created_at}] {username} | {event_type}\n{details}\n\n",
        )

    texto_eventos.configure(state="disabled")


def gerar_pdf():
    if not ultimo_resultado:
        messagebox.showwarning("Aviso", "Faça um sorteio antes de gerar o PDF.")
        return

    caminho = filedialog.asksaveasfilename(defaultextension=".pdf")
    if not caminho:
        return

    pdf = canvas.Canvas(caminho, pagesize=A4)
    pdf.drawImage("logo.png", 250, 740, width=100, height=100)

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawCentredString(300, 710, "República de Angola")
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawCentredString(300, 690, "Concurso público")
    pdf.setFont("Helvetica", 12)
    pdf.drawCentredString(300, 670, "Relatório oficial do sorteio")

    pdf.line(50, 650, 550, 650)
    pdf.setFont("Helvetica", 11)
    pdf.drawString(60, 630, f"Operador responsável: {utilizador_atual}")

    y = 600
    for item in ultimo_resultado:
        pdf.drawString(80, y, f'{item["numero"]} - {item["nome"]}')
        y -= 18

    if ultima_auditoria:
        y -= 12
        pdf.drawString(60, y, f"Qui-quadrado: {ultima_auditoria['chi_square']:.4f}")
        y -= 18
        pdf.drawString(60, y, f"p-value: {ultima_auditoria['p_value']:.4f}")
        y -= 18
        pdf.drawString(60, y, f"Simulacoes: {ultima_auditoria['repeticoes']}")
        y -= 18
        pdf.drawString(60, y, ultima_auditoria["mensagem"][:85])

    pdf.line(50, 100, 550, 100)
    pdf.drawCentredString(300, 80, "Documento gerado automaticamente pelo sistema auditável")
    pdf.save()

    registar_evento(conn, utilizador_atual, "PDF_GERADO", f"Relatório PDF guardado em {caminho}.")
    messagebox.showinfo("Sucesso", "PDF criado com sucesso.")


def terminar_sessao():
    registar_evento(conn, utilizador_atual, "LOGOUT", "Sessao terminada pelo utilizador.")
    janela.destroy()
    abrir_login()


def abrir_sistema():
    global janela, entrada_nome, texto_participantes, lista, entrada_qtd, resultado, resumo_auditoria_var, entrada_total_var

    janela = tk.Tk()
    janela.title("Sistema de Sorteio Auditavel")
    janela.geometry("980x700")
    janela.resizable(False, False)
    janela.configure(bg="#eef3f8")

    cabecalho = tk.Frame(janela, bg="#14324a", padx=18, pady=12)
    cabecalho.pack(fill="x")
    tk.Label(
        cabecalho,
        text=f"Sistema de Sorteio Auditável | Utilizador: {utilizador_atual}",
        font=("Arial", 14, "bold"),
        bg="#14324a",
        fg="white",
    ).pack(side="left")
    criar_botao(cabecalho, "Logout", terminar_sessao, "#0f2436", width=12).pack(side="right")

    area_conteudo = tk.Frame(janela, bg="#eef3f8")
    area_conteudo.pack(fill="both", expand=True)

    # O canvas permite manter a tela principal navegavel quando o conteudo
    # ultrapassa a area visivel da janela.
    canvas_principal = tk.Canvas(area_conteudo, bg="#eef3f8", highlightthickness=0)
    scrollbar_vertical = tk.Scrollbar(area_conteudo, orient="vertical", command=canvas_principal.yview)
    canvas_principal.configure(yscrollcommand=scrollbar_vertical.set)

    scrollbar_vertical.pack(side="right", fill="y")
    canvas_principal.pack(side="left", fill="both", expand=True)

    conteudo_scroll = tk.Frame(canvas_principal, bg="#eef3f8", width=960, height=900)
    janela_scroll = canvas_principal.create_window((0, 0), window=conteudo_scroll, anchor="nw")

    def ajustar_scroll(_event=None):
        canvas_principal.configure(scrollregion=canvas_principal.bbox("all"))

    def ajustar_largura(event):
        canvas_principal.itemconfigure(janela_scroll, width=event.width)

    conteudo_scroll.bind("<Configure>", ajustar_scroll)
    canvas_principal.bind("<Configure>", ajustar_largura)

    # Ativa scroll com a roda do rato sem depender apenas da barra lateral.
    def scroll_mouse(event):
        delta = event.delta
        if delta == 0:
            return
        canvas_principal.yview_scroll(int(-delta / 120), "units")

    def ativar_scroll(_event):
        canvas_principal.bind_all("<MouseWheel>", scroll_mouse)

    def desativar_scroll(_event):
        canvas_principal.unbind_all("<MouseWheel>")

    canvas_principal.bind("<Enter>", ativar_scroll)
    canvas_principal.bind("<Leave>", desativar_scroll)

    coluna_esquerda = tk.Frame(
        conteudo_scroll,
        bg="#f8fbfe",
        padx=18,
        pady=18,
        highlightbackground="#d5dde6",
        highlightthickness=1,
    )
    coluna_esquerda.place(x=18, y=18, width=450, height=680)

    coluna_direita = tk.Frame(
        conteudo_scroll,
        bg="#f8fbfe",
        padx=18,
        pady=18,
        highlightbackground="#d5dde6",
        highlightthickness=1,
    )
    coluna_direita.place(x=490, y=18, width=470, height=680)

    tk.Label(coluna_esquerda, text="Participantes", font=("Arial", 16, "bold"), bg="white", fg="#14324a").pack(anchor="w")
    tk.Label(coluna_esquerda, text="Adicione manualmente, cole uma lista ou importe de um ficheiro.", bg="white", fg="#667684").pack(anchor="w", pady=(4, 12))

    tk.Label(coluna_esquerda, text="Novo participante", bg="white").pack(anchor="w")
    entrada_nome = tk.Entry(coluna_esquerda, width=42, relief="solid", bd=1)
    entrada_nome.pack(anchor="w", pady=(0, 8), ipady=4)

    botoes_participantes = tk.Frame(coluna_esquerda, bg="white")
    botoes_participantes.pack(anchor="w", pady=(0, 10))
    criar_botao(botoes_participantes, "Adicionar", adicionar_nome, "#1f6aa5", width=14).grid(row=0, column=0, padx=(0, 6))
    criar_botao(botoes_participantes, "Importar", carregar_participantes_do_ficheiro, "#2e8b57", width=14).grid(row=0, column=1, padx=6)
    criar_botao(botoes_participantes, "Limpar dados", limpar_dados_entrada, "#946c00", width=14).grid(row=0, column=2, padx=(6, 0))

    tk.Label(coluna_esquerda, text="Lista em texto", bg="white").pack(anchor="w")
    texto_participantes = tk.Text(coluna_esquerda, height=10, width=48, relief="solid", bd=1)
    texto_participantes.pack(pady=(0, 10))

    tk.Label(coluna_esquerda, text="Participantes limpos", bg="white").pack(anchor="w")
    lista = tk.Listbox(coluna_esquerda, width=48, height=12, relief="solid", bd=1)
    lista.pack()

    tk.Label(coluna_direita, text="Execução do Sorteio", font=("Arial", 16, "bold"), bg="white", fg="#14324a").pack(anchor="w")
    tk.Label(coluna_direita, text="Cada sorteio fica guardado no historico com auditoria estatistica.", bg="white", fg="#667684").pack(anchor="w", pady=(4, 16))

    # A area administrativa so aparece para o utilizador com privilegios de admin.
    if utilizador_atual == "admin":
        bloco_admin = tk.LabelFrame(
            coluna_direita,
            text="Administracao",
            bg="white",
            fg="#14324a",
            padx=12,
            pady=10,
        )
        bloco_admin.pack(fill="x", pady=(0, 14))
        tk.Label(
            bloco_admin,
            text="Apenas o administrador pode adicionar novos utilizadores.",
            bg="white",
            fg="#667684",
            wraplength=380,
            justify="left",
        ).pack(anchor="w", pady=(0, 8))
        criar_botao(bloco_admin, "Novo utilizador", abrir_registo, "#2e8b57", width=16).pack(anchor="w")

    entrada_total_var = tk.StringVar()
    resumo_auditoria_var = tk.StringVar(value="Nenhum sorteio executado nesta sessão.")

    linha_campos = tk.Frame(coluna_direita, bg="white")
    linha_campos.pack(anchor="w", fill="x", pady=(0, 14))

    bloco_total = tk.Frame(linha_campos, bg="white")
    bloco_total.grid(row=0, column=0, padx=(0, 18), sticky="w")
    tk.Label(bloco_total, text="Total de participantes", bg="white").pack(anchor="w")
    entrada_total = tk.Entry(bloco_total, textvariable=entrada_total_var, width=18, relief="solid", bd=1)
    entrada_total.pack(anchor="w", pady=(0, 0), ipady=4)

    bloco_qtd = tk.Frame(linha_campos, bg="white")
    bloco_qtd.grid(row=0, column=1, padx=(0, 12), sticky="w")
    tk.Label(bloco_qtd, text="Quantidade sorteada", bg="white").pack(anchor="w")
    entrada_qtd = tk.Entry(bloco_qtd, width=18, relief="solid", bd=1)
    entrada_qtd.pack(anchor="w", pady=(0, 0), ipady=4)

    bloco_sortear = tk.Frame(linha_campos, bg="white")
    bloco_sortear.grid(row=0, column=2, sticky="sw")
    tk.Label(bloco_sortear, text="", bg="white").pack(anchor="w")
    criar_botao(bloco_sortear, "Sortear", fazer_sorteio, "#8a1c2a", width=12).pack(anchor="w")

    botoes_sorteio = tk.Frame(coluna_direita, bg="white")
    botoes_sorteio.pack(anchor="w", pady=(0, 14))
    criar_botao(botoes_sorteio, "Historico", abrir_historico, "#4c6a85", width=13).grid(row=0, column=0, padx=(0, 6))
    criar_botao(botoes_sorteio, "PDF", gerar_pdf, "#5a3d8c", width=13).grid(row=0, column=1, padx=6)
    criar_botao(botoes_sorteio, "Limpar tudo", limpar_tudo, "#6f7b86", width=13).grid(row=0, column=2, padx=6)

    tk.Label(coluna_direita, text="Resultado", bg="white").pack(anchor="w")
    bloco_resultado = tk.Frame(coluna_direita, bg="white")
    bloco_resultado.pack(fill="x", pady=(0, 14))
    resultado = tk.Listbox(bloco_resultado, width=50, height=12, relief="solid", bd=1)
    scroll_resultado = tk.Scrollbar(bloco_resultado, orient="vertical", command=resultado.yview)
    resultado.configure(yscrollcommand=scroll_resultado.set)
    resultado.pack(side="left", fill="both", expand=True)
    scroll_resultado.pack(side="right", fill="y")

    bloco_auditoria = tk.LabelFrame(
        coluna_direita,
        text="Auditoria de Imparcialidade",
        bg="white",
        fg="#14324a",
        padx=12,
        pady=12,
    )
    bloco_auditoria.pack(fill="x")

    tk.Label(
        bloco_auditoria,
        textvariable=resumo_auditoria_var,
        bg="white",
        justify="left",
        wraplength=390,
        fg="#263747",
    ).pack(anchor="w")

    tk.Frame(coluna_direita, bg="white", height=12).pack(fill="x")

    janela.mainloop()


def autenticar():
    global utilizador_atual

    username = entry_user.get()
    password = entry_pass.get()

    username_limpo = limpar_username(username)
    if not username_limpo or not password:
        messagebox.showerror("Erro", "Preencha o utilizador e a senha.")
        return

    # A autenticacao valida as credenciais e devolve o utilizador final usado na sessao.
    sucesso, mensagem, username_final = autenticar_utilizador(conn, username_limpo, password)
    if not sucesso:
        messagebox.showerror("Erro", mensagem)
        return

    utilizador_atual = username_final
    messagebox.showinfo("Sucesso", mensagem)
    root.destroy()
    abrir_sistema()


def registrar_utilizador():
    if utilizador_atual != "admin":
        messagebox.showerror("Erro", "Apenas o administrador pode criar novos utilizadores.", parent=janela_registo)
        return

    username = entry_new_user.get()
    password = entry_new_pass.get()
    confirmar = entry_confirm_pass.get()

    if password != confirmar:
        messagebox.showerror("Erro", "As senhas não coincidem.", parent=janela_registo)
        return

    # O registo de contas novas fica restrito ao admin para centralizar o controlo de acesso.
    try:
        username_final = criar_utilizador(conn, username, password)
    except ValueError as erro:
        messagebox.showerror("Erro", str(erro), parent=janela_registo)
        return

    messagebox.showinfo("Sucesso", "Conta criada com sucesso.", parent=janela_registo)
    janela_registo.destroy()


def abrir_registo():
    global janela_registo, entry_new_user, entry_new_pass, entry_confirm_pass

    if utilizador_atual != "admin":
        messagebox.showerror("Erro", "Apenas o administrador pode adicionar novos utilizadores.")
        return

    janela_registo = tk.Toplevel(janela)
    janela_registo.title("Criar conta")
    janela_registo.geometry("380x320")
    janela_registo.resizable(False, False)
    janela_registo.configure(bg="#eef3f8")
    janela_registo.transient(janela)
    janela_registo.grab_set()

    frame = tk.Frame(janela_registo, bg="white", padx=24, pady=22)
    frame.place(relx=0.5, rely=0.5, anchor="center")

    tk.Label(frame, text="Nova Conta", font=("Arial", 16, "bold"), bg="white", fg="#14324a").pack(pady=(0, 14))

    tk.Label(frame, text="Utilizador", bg="white").pack(anchor="w")
    entry_new_user = tk.Entry(frame, width=30, relief="solid", bd=1)
    entry_new_user.pack(pady=(0, 10), ipady=4)

    tk.Label(frame, text="Senha", bg="white").pack(anchor="w")
    entry_new_pass = tk.Entry(frame, width=30, show="*", relief="solid", bd=1)
    entry_new_pass.pack(pady=(0, 10), ipady=4)

    tk.Label(frame, text="Confirmar senha", bg="white").pack(anchor="w")
    entry_confirm_pass = tk.Entry(frame, width=30, show="*", relief="solid", bd=1)
    entry_confirm_pass.pack(pady=(0, 16), ipady=4)
    entry_confirm_pass.bind("<Return>", lambda event: registrar_utilizador())

    criar_botao(frame, "Criar conta", registrar_utilizador, "#2e8b57").pack()


def abrir_login():
    global root, entry_user, entry_pass

    root = tk.Tk()
    root.title("Login")
    root.geometry("430x360")
    root.resizable(False, False)
    root.configure(bg="#dbe7f3")

    frame = tk.Frame(root, bg="white", padx=28, pady=26, highlightbackground="#cfd9e3", highlightthickness=1)
    frame.place(relx=0.5, rely=0.5, anchor="center")

    tk.Label(frame, text="Entrar no Sistema", font=("Arial", 18, "bold"), bg="white", fg="#14324a").pack(pady=(0, 6))
    tk.Label(frame, text="Sorteios com histórico, auditoria e teste estatístico.", bg="white", fg="#5b6b79").pack(pady=(0, 18))

    tk.Label(frame, text="Utilizador", bg="white").pack(anchor="w")
    entry_user = tk.Entry(frame, width=30, relief="solid", bd=1)
    entry_user.pack(pady=(0, 10), ipady=4)

    tk.Label(frame, text="Senha", bg="white").pack(anchor="w")
    entry_pass = tk.Entry(frame, width=30, show="*", relief="solid", bd=1)
    entry_pass.pack(pady=(0, 16), ipady=4)
    entry_pass.bind("<Return>", lambda event: autenticar())

    botoes = tk.Frame(frame, bg="white")
    botoes.pack(pady=(0, 12))

    criar_botao(botoes, "Login", autenticar, "#1f6aa5").grid(row=0, column=0, padx=4)

    tk.Label(
        frame,
        text="Conta inicial: edukalien | Senha: qwer",
        bg="white",
        fg="#555555",
    ).pack(pady=(4, 4))

    tk.Label(
        frame,
        text="Cada início de sessão e cada sorteio ficam guardados em SQLite.",
        bg="white",
        fg="#7a8793",
        wraplength=300,
        justify="center",
    ).pack()

    root.mainloop()


if __name__ == "__main__":
    abrir_login()
