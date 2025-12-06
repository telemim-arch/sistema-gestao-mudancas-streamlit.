# 🔍 DIAGNÓSTICO: Funcionários não aparecem na lista

## ❓ Possíveis Causas

### 1. **Problema de Escopo (Filter)**
- A função `filter_by_scope()` pode estar filtrando demais
- Você está logado como Secretária mas os funcionários estão vinculados a outra

### 2. **Problema no Banco de Dados**
- As colunas podem estar com nomes diferentes
- Dados podem não estar sendo salvos corretamente

### 3. **Problema de Sessão**
- O `st.session_state.data` pode não estar atualizado
- Cache pode estar impedindo a atualização

---

## 🔧 VERSÃO COM DEBUG ATIVADO

Acabei de criar uma versão do app.py que mostra informações de debug:

### O que a versão de debug mostra:

1. **Total de funcionários no sistema** - Quantos funcionários existem no total
2. **Funcionários no seu escopo** - Quantos você deveria ver
3. **Colunas disponíveis** - Quais campos o banco de dados tem
4. **Mensagens de erro detalhadas** - Se algo der errado, mostra o erro completo
5. **Debug para Admin** - Se você for admin, pode ver todos os funcionários em JSON

---

## 📋 COMO DIAGNOSTICAR

### PASSO 1: Substitua o arquivo
Baixe e use o app.py atualizado (link abaixo)

### PASSO 2: Acesse a tela de Funcionários
Faça login e vá para a aba "Funcionários"

### PASSO 3: Veja as mensagens de debug
A tela vai mostrar:

```
Funcionários Cadastrados
Total de funcionários no sistema: 4
Funcionários no seu escopo: 0
Colunas disponíveis: id, name, email, role, jobTitle, secretaryId
```

### PASSO 4: Me diga os números
Me informe:
- Quantos funcionários aparecem no "sistema"?
- Quantos aparecem no "seu escopo"?
- Quais colunas aparecem?

---

## 🎯 SOLUÇÕES POSSÍVEIS

### Se "Funcionários no seu escopo" = 0:

**PROBLEMA:** Filtro de escopo está bloqueando

**SOLUÇÃO 1 - Para ADMIN:**
Faça login como admin@telemim.com / 123

**SOLUÇÃO 2 - Para Secretária:**
Os funcionários precisam estar vinculados à sua secretaria

**SOLUÇÃO 3 - Desabilitar filtro temporariamente:**
Modifique a linha no código:
```python
# ANTES:
scoped_staff = filter_by_scope(st.session_state.data['staff'], key='id')

# DEPOIS (TEMPORÁRIO PARA TESTE):
scoped_staff = st.session_state.data['staff']  # Mostra TODOS
```

### Se as colunas estão faltando:

**PROBLEMA:** Banco de dados não tem as colunas

**SOLUÇÃO:** Verificar o schema do banco de dados

### Se aparecem mas não exibem:

**PROBLEMA:** Erro no mapeamento de ROLES

**SOLUÇÃO:** A versão de debug já corrige isso

---

## 📥 ARQUIVOS ATUALIZADOS

1. **app.py com debug ativado** - Mostra informações de diagnóstico
2. **Guia de diagnóstico** - Este arquivo

---

## 🚨 AÇÃO IMEDIATA

1. Baixe o app.py atualizado
2. Substitua no GitHub
3. Aguarde deploy (2-3 minutos)
4. Acesse a tela de Funcionários
5. **Me envie as 3 informações que aparecem:**
   - Total de funcionários no sistema: ?
   - Funcionários no seu escopo: ?
   - Colunas disponíveis: ?

Com essas informações, vou saber exatamente qual é o problema! 🎯
