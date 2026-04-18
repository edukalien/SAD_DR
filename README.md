# SAD_DR
# Decisões Randomizadas
Existem diversos processos que conduzem à tomada de decisões. Segundo Puterman (1994), nos Markov Decision Processes, uma política de decisão pode ser determinística — escolhendo sempre a mesma ação em determinado estado — ou randomizada, atribuindo probabilidades diferentes às possíveis ações. Neste trabalho, propomos abordar as decisões randomizadas, cujo objectivo é basear-se em sorteios ou aleatoriedade.
A relevância deste tema se evidencia na sua capacidade de promover imparcialidade e eficiência em diferentes contextos de decisão. Em particular, processos de seleção de candidatos frequentemente enfrentam problemas de nepotismo e favorecimento indevido, comprometendo a equidade e a confiança nas instituições. Essa lacuna evidencia a necessidade de soluções que minimizem a influência humana direta e aumentem a transparência do processo.
# Métodos de randomização
# Randomização Simples:
Funciona como um sorteio (ex: cara ou coroa), onde cada participante tem a mesma chance de ir para qualquer grupo. É ideal para amostras grandes, mas pode gerar desequilíbrio em amostras pequenas.
	Sua fórmula: P(E_i)=1/N
P(E_i)= probabilidade de selecionar o elemento i
N= número total de elementos na população
# Randomização em Blocos (Block Randomization): 
Garante que o número de participantes seja equilibrado entre os grupos ao longo do estudo, dividindo a amostra em "blocos" com tamanhos definidos.
	Sua fórmula: N = b!/(n1!n2!…nk!)
b - Tamanho do bloco
k - Número de grupos;
n1, n2 . . . nk – Número de participantes de cada grupo dentro do bolco
# Randomização Estratificada: 
Utilizada para garantir que características importantes (ex: idade, sexo, gravidade da doença) sejam distribuídas uniformemente entre os grupos.
	Sua fórmula: nhk=Nh/K; onde,
 nhk – número de indivíduos do estrato h no grupo k.
Nh – tamanho do estrato
K – número de grupos do estudo
# Áreas de Aplicação
As decisões randomizadas começaram a ser usadas de forma sistemática no início do século XX, especialmente em estatística e pesquisa científica, com destaque para os ensaios clínicos randomizados na década de 1920–30. No campo da computação, algoritmos randomizados ganharam força a partir dos anos 1970–80, com aplicações em otimização, criptografia e inteligência artificial.
# Randomização algoritímica vs Pseudo-aleatoriedade
A randomização algorítmica e a pseudo-aleatoriedade são conceitos distintos, mas interdependentes dentro da computação.
A randomização algorítmica refere-se ao uso de decisões baseadas em probabilidade dentro de algoritmos, permitindo múltiplas saídas possíveis para a mesma entrada. O seu principal objectivo é garantir imparcialidade, eficiência e robustez, sendo amplamente aplicada em sistemas de selecção, simulações e optimização.
Por outro lado, a pseudo-aleatoriedade diz respeito ao mecanismo que gera os valores “aleatórios” utilizados nesses algoritmos. Trata-se de um processo determinístico, baseado em fórmulas matemáticas, como:
X_(n+1)=(aX_n+c)" " mod" " m
Embora os números produzidos aparentem ser aleatórios, eles dependem de uma semente inicial e podem ser reproduzidos.
A randomização algorítmica é o uso estratégico do acaso. A pseudo-aleatoriedade é a fonte técnica desse acaso.
Em síntese, a randomização define como a aleatoriedade é aplicada, enquanto a pseudo-aleatoriedade define de onde ela vem.
# Conclusão
Os resultados obtidos demonstram que os objectivos propostos foram alcançados com sucesso. No que se refere aos objectivos específicos, foi possível implementar a técnica de randomização simples por meio de algoritmos computacionais, assegurando que todos os candidatos possuam igual probabilidade de selecção. Adicionalmente, foi desenvolvida uma interface gráfica funcional que permite a inserção de dados de forma intuitiva, bem como a visualização dos resultados do sorteio.
# Referências
Ferreira, A. B. H. (1975). Novo dicionário da língua portuguesa. Rio de Janeiro: Nova Fronteira.
Russell, S., & Norvig, P. (2013). Inteligência artificial: Uma abordagem moderna. Rio de Janeiro: Elsevier.
Puterman, M. L. (1994). Markov decision processes: Discrete stochastic dynamic programming. New York: Wiley.
Gil, A. C. (2008). Métodos e técnicas de pesquisa social (6ª ed.). São Paulo: Atlas.
Von Neumann, J., & Morgenstern, O. (1944). Theory of games and economic behavior. Princeton: Princeton University Press.
Fisher, R. A. (1935). The design of experiments. Edinburgh: Oliver & Boyd.
Menezes, A. J., van Oorschot, P. C., & Vanstone, S. A. (1996). Handbook of Applied Cryptography. CRC Press.
Papoulis, A., & Pillai, S. U. (2002). Probability, Random Variables and Stochastic Processes (4th ed.). McGraw-Hill.
Montgomery, D. C., & Runger, G. C. (2014). Applied Statistics and Probability for Engineers (6th ed.). Wiley.
Ross, S. M. (2014). Introduction to Probability Models (11th ed.). Academic Press.
# Para executar o código
Para executar e analisar o projecto, basta ter o Python instalado e abrir a pasta do projecto no terminal.
O ficheiro principal da aplicação é:
Random.Simples.py
Credenciais iniciais
Ao iniciar, o sistema cria um utilizador padrão:

utilizador: edukalien
senha: qwer
Ficheiros importantes para análise
  *Random.Simples.py
Interface gráfica e fluxo principal da aplicação.
  *sorteio_core.py
Lógica do sistema, SQLite, auditoria, randomização e teste de Qui-quadrado.
  *test_sorteio_core.py
Testes automatizados.
  *sistema.db
Base de dados SQLite usada pela aplicação.
