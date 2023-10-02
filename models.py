import string
import graphviz

from dd.autoref import BDD
from typing import Dict

letters = set(string.ascii_lowercase)


class Formula:
    def __init__(self, text: str = ''):
        text = text.replace(' ', '')
        if '(' not in text:
            self.order = 0
            self.op = text
            self.left = None
            self.right = None
        else:
            if text[0] == '(':
                # binary operator of the form -- (operand) operator (operand)
                self.order = 2
                c = 0
                close_pos = -1
                for pos in range(len(text)):
                    if text[pos] == '(':
                        c += 1
                    elif text[pos] == ')':
                        c -= 1
                    if c == 0:
                        close_pos = pos
                        break
                self.left = Formula(text[1:close_pos])
                text = text[close_pos+1:]
                start_pos = text.find('(')
                self.op = text[:start_pos]
                self.right = Formula(text[start_pos+1:-1])
            else:
                # unary operator of the form -- operator (operand)
                self.order = 1
                start_pos = text.find('(')
                self.op = text[:start_pos]
                self.right = Formula(text[start_pos + 1:-1])
                self.left = None

    def __str__(self):
        if self.order == 0:
            return f'{self.op}'
        elif self.order == 1:
            return f'{self.op}({str(self.right)})'
        else:
            return f'({str(self.left)}){self.op}({self.right})'


class Model:
    def __init__(self, model_yml: Dict = None):
        self.logic = model_yml['logic']
        if model_yml['logic'].lower() == 'modal':
            self.model = Modal(model_yml)
        elif model_yml['logic'].lower() == 'lhs' or model_yml['logic'].lower() == 'travel':
            self.model = LHS(model_yml)
        elif model_yml['logic'].lower() == 'sabotage':
            self.model = Sabotage(model_yml)

    def check(self, formula, w, draw=False):
        form = Formula(formula)
        if isinstance(w, str):
            w = [w]

        if self.logic == 'modal':
            if draw:
                return self.model.draw_formula(w[0], formula=form)
            else:
                return self.model.check_formula(w[0], formula=form)
        elif self.logic == 'sabotage':
            if draw:
                return self.model.draw_formula(w[0], formula=form)
            else:
                return self.model.check_formula(w[0], formula=form)
        elif self.logic == 'lhs' or self.logic == 'modal':
            if draw:
                return self.model.draw_formula(w[0], w[1:], formula=form)
            else:
                return self.model.check_formula(w[0], w[1:], formula=form)

    def draw(self):
        dot = graphviz.Digraph(comment=f'{self.logic} Logic Model', engine='neato', format='png')
        for world in self.model.V:
            dot.node(world, world)

        for w in self.model.V:
            neighbors = self.model.get_neighbours(w)
            for w2 in neighbors:
                dot.edge(w, w2)

        dot.view()


class Modal:
    def __init__(self, model_yml: Dict = None):
        self.P = None
        self.V = None
        self.bdd = None
        self.world_formula = None
        self.relation_formula = None

        if model_yml is not None:
            self.create_model_from_file(model_yml)

    def create_model_from_file(self, model_yml: Dict):

        # Prop symbols
        self.P = set(model_yml['P'])
        self.V = model_yml['V']

        for w in self.V.keys():
            for w2 in self.V.keys():
                if w != w2:
                    if sorted(self.V[w]) == sorted(self.V[w2]):
                        new_letter = list(letters - self.P)[0]
                        self.V[w].append(new_letter)
                        self.P.add(new_letter)

        # Valuations
        self.bdd = BDD()
        for p in self.P:
            self.bdd.add_var(p)
            self.bdd.add_var(f"{p}'")

        formulas = []
        for w in self.V.keys():
            var_list = self.V[w] + [f'~{i}' for i in self.P if i not in self.V[w]]
            formulas.append('/\\'.join(var_list))
        formula = '\\/'.join([f'({i})' for i in formulas])
        self.world_formula = self.bdd.add_expr(formula)

        # Relations
        formulas = []
        for w in model_yml['R'].keys():
            source = '/\\'.join([i if i in self.V[w] else f'~{i}' for i in self.P])
            for w2 in model_yml['R'][w]:
                dest = '/\\'.join([i+"'" if i in self.V[w2] else f"~{i}'" for i in self.P])
                formulas.append(source + '/\\' + dest)
        formula = '\\/'.join([f'({i})' for i in formulas])
        self.relation_formula = self.bdd.add_expr(formula)

    def draw_formula(self, w, formula):
        flag = self.check_formula(w, formula)

        dot = graphviz.Digraph(comment=f'Modal Logic Model', engine='neato', format='png')
        for world in self.V:
            if w == world:
                dot.node(world, world, shape='square')
            else:
                dot.node(world, world)

        for world in self.V:
            neighbors = self.get_neighbours(world)
            for w2 in neighbors:
                dot.edge(world, w2)
        if flag:
            dot.attr(label=f'\nM, {w} \u22A8 {formula}', fontname="Sans Not-Rotated 14")
        else:
            dot.attr(label=f'\nM, {w} \u22AD {formula}', fontname="Sans Not-Rotated 14")
        dot.view()

    def check_formula(self, w, formula):
        # prop
        if formula.order == 0:
            if formula.op in self.V[w]:
                return True
            else:
                return False

        if formula.op == '/\\':
            return self.check_formula(w, formula.left) and self.check_formula(w, formula.right)

        elif formula.op == '\\/':
            return self.check_formula(w, formula.left) or self.check_formula(w, formula.right)

        elif formula.op == '~':
            return not self.check_formula(w, formula.right)

        elif formula.op == '<>':
            sol = False
            neighbors = self.get_neighbours(w)
            for w2 in neighbors:
                if w2 is not None:
                    if self.check_formula(w2, formula.right):
                        sol = True
                        break
            return sol
        elif formula.op == '[]':
            sol = True
            neighbors = self.get_neighbours(w)
            for w2 in neighbors:
                if w2 is not None:
                    if not self.check_formula(w2, formula.right):
                        sol = False
                        break
            return sol
        else:
            print(f'Invalid Operator {formula.op}')

    def get_neighbours(self, w):
        w_dict = {i: True if i in self.V[w] else False for i in self.P}
        neighbor_formula = self.bdd.let(w_dict, self.relation_formula)
        neighbors = []
        for iteration in self.bdd.pick_iter(neighbor_formula):
            vw = [i[:-1] for i in iteration.keys() if iteration[i]]
            for world in self.V.keys():
                if sorted(vw) == sorted(self.V[world]):
                    neighbors.append(world)
        return neighbors

    def __str__(self):
        return self.bdd.to_expr(self.world_formula) + '\n' + self.bdd.to_expr(self.relation_formula)


class LHS:

    def __init__(self, model_yml: Dict = None):
        self.PA = None
        self.PE = None
        self.P = None
        self.V = None
        self.bdd = None
        self.world_formula = None
        self.relation_formula = None
        self.agents = None

        if model_yml is not None:
            self.create_model_from_file(model_yml)

    def create_model_from_file(self, model_yml: Dict):

        # Prop symbols
        self.PA = set(model_yml['P_A'])
        self.PE = set(model_yml['P_E'])
        self.P = self.PA.union(self.PE)
        self.V = model_yml['V']
        self.agents = 1 if 'agents' not in model_yml.keys() else model_yml['agents'] - 1

        for w in self.V.keys():
            for w2 in self.V.keys():
                if w != w2:
                    if sorted(self.V[w]) == sorted(self.V[w2]):
                        new_letter = list(letters - self.P)[0]
                        self.V[w].append(new_letter)
                        self.P.add(new_letter)

        # Valuations
        self.bdd = BDD()
        for p in self.P:
            self.bdd.add_var(p)
            self.bdd.add_var(f"{p}'")

        formulas = []
        for w in self.V.keys():
            var_list = self.V[w] + [f'~{i}' for i in self.P if i not in self.V[w]]
            formulas.append('/\\'.join(var_list))
        formula = '\\/'.join([f'({i})' for i in formulas])
        self.world_formula = self.bdd.add_expr(formula)

        # Relations
        formulas = []
        for w in model_yml['R'].keys():
            source = '/\\'.join([i if i in self.V[w] else f'~{i}' for i in self.P])
            for w2 in model_yml['R'][w]:
                dest = '/\\'.join([i + "'" if i in self.V[w2] else f"~{i}'" for i in self.P])
                formulas.append(source + '/\\' + dest)
        formula = '\\/'.join([f'({i})' for i in formulas])
        self.relation_formula = self.bdd.add_expr(formula)

    def check_formula(self, s, t_list, formula):

        if not isinstance(t_list, list):
            t_list = [t_list]
        # prop
        if formula.order == 0:
            if formula.op == 'I':
                return s in t_list

            if formula.op in self.PA:
                if formula.op in self.V[s]:
                    return True
                else:
                    return False
            else:
                for t in t_list:
                    if formula.op in self.V[t]:
                        return True
                return False

        if formula.op == '/\\':
            return self.check_formula(s, t_list, formula.left) and self.check_formula(s, t_list, formula.right)

        elif formula.op == '\\/':
            return self.check_formula(s, t_list, formula.left) or self.check_formula(s, t_list, formula.right)

        elif formula.op == '~':
            return not self.check_formula(s, t_list, formula.right)

        elif formula.op == '<left>' or formula.op == '<H>':
            sol = False
            neighbors = self.get_neighbours(s)
            for w2 in neighbors:
                if self.check_formula(w2, t_list, formula.right):
                    sol = True
                    break
            return sol

        elif formula.op[:2] == '<S':
            sol = False
            i = int(formula.op[2:-1])
            neighbors = self.get_neighbours(t_list[i-1])
            for w2 in neighbors:
                temp_list = t_list[:i-1] + [w2] + t_list[i:]
                if self.check_formula(s, temp_list, formula.right):
                    sol = True
                    break
            return sol

        elif formula.op == '[left]' or formula.op == '[H]':
            sol = True
            neighbors = self.get_neighbours(s)
            for w2 in neighbors:
                if not self.check_formula(w2, t_list, formula.right):
                    sol = False
                    break
            return sol

        elif formula.op[:2] == '[S':
            sol = True
            i = int(formula.op[2:-1])
            neighbors = self.get_neighbours(t_list[i - 1])
            for w2 in neighbors:
                temp_list = t_list[:i - 1] + [w2] + t_list[i:]
                if self.check_formula(s, temp_list, formula.right):
                    sol = False
                    break
            return sol

        else:
            print(f'Invalid Operator {formula.op}')

    def get_neighbours(self, w):
        w_dict = {i: True if i in self.V[w] else False for i in self.P}
        neighbor_formula = self.bdd.let(w_dict, self.relation_formula)
        neighbors = []
        for iteration in self.bdd.pick_iter(neighbor_formula):
            vw = [i[:-1] for i in iteration.keys() if iteration[i]]
            for world in self.V.keys():
                if sorted(vw) == sorted(self.V[world]):
                    neighbors.append(world)
        return neighbors

    def draw_formula(self, s, t, formula):
        flag = self.check_formula(s, t, formula)
        if isinstance(t, str):
            t = [t]
        dot = graphviz.Digraph(comment=f'Modal Logic Model', engine='neato', format='png')
        for world in self.V:
            if s == world:
                dot.node(world, world, color='green')
            if world in t:
                dot.node(world, world, color='red')
            else:
                dot.node(world, world)

        for world in self.V:
            neighbors = self.get_neighbours(world)
            for w2 in neighbors:
                dot.edge(world, w2)
        
        formula = str(formula).replace('\/', '\u2228').replace('/\\', '\u2227')
        if flag:
            dot.attr(label=f'\nM, {s}, {t} \u22A8 {formula}', fontname="Sans Not-Rotated 14")
        else:
            dot.attr(label=f'\nM, {s}, {t} \u22AD {formula}', fontname="Sans Not-Rotated 14")
        dot.view()


class Sabotage:
    def __init__(self, model_yml: Dict = None):
        self.P = None
        self.V = None
        self.bdd = None
        self.world_formula = None
        self.relation_formula = None

        if model_yml is not None:
            self.create_model_from_file(model_yml)

    def create_model_from_file(self, model_yml: Dict):

        # Prop symbols
        self.P = set(model_yml['P'])
        self.V = model_yml['V']

        for w in self.V.keys():
            for w2 in self.V.keys():
                if w != w2:
                    if sorted(self.V[w]) == sorted(self.V[w2]):
                        new_letter = list(letters - self.P)[0]
                        self.V[w].append(new_letter)
                        self.P.add(new_letter)

        # Valuations
        self.bdd = BDD()
        for p in self.P:
            self.bdd.add_var(p)
            self.bdd.add_var(f"{p}'")

        formulas = []
        for w in self.V.keys():
            var_list = self.V[w] + [f'~{i}' for i in self.P if i not in self.V[w]]
            formulas.append('/\\'.join(var_list))
        formula = '\\/'.join([f'({i})' for i in formulas])
        self.world_formula = self.bdd.add_expr(formula)

        # Relations
        formulas = []
        for w in model_yml['R'].keys():
            source = '/\\'.join([i if i in self.V[w] else f'~{i}' for i in self.P])
            for w2 in model_yml['R'][w]:
                dest = '/\\'.join([i + "'" if i in self.V[w2] else f"~{i}'" for i in self.P])
                formulas.append(source + '/\\' + dest)
        formula = '\\/'.join([f'({i})' for i in formulas])
        self.relation_formula = self.bdd.add_expr(formula)

    def check_formula(self, w, formula, relation=None):
        if relation is None:
            relation = self.relation_formula

        # prop
        if formula.order == 0:
            if formula.op in self.V[w]:
                return True
            else:
                return False

        if formula.op == '/\\':
            return self.check_formula(w, formula.left, relation) and self.check_formula(w, formula.right, relation)

        elif formula.op == '\\/':
            return self.check_formula(w, formula.left, relation) or self.check_formula(w, formula.right, relation)

        elif formula.op == '~':
            return not self.check_formula(w, formula.right, relation)

        elif formula.op == '<>':
            sol = False
            neighbors = self.get_neighbours(w, relation)
            for w2 in neighbors:
                if self.check_formula(w2, formula.right, relation):
                    sol = True
                    break
            return sol

        elif formula.op == '<.>':
            sol = False
            for iteration in self.bdd.pick_iter(self.relation_formula):
                neg_edge = [f'(~{i})' if iteration[i] else f'({i})' for i in iteration]
                new_relation = self.relation_formula & self.bdd.add_expr('\\/'.join(neg_edge))
                if self.check_formula(w, formula.right, new_relation):
                    sol = True
                    break
            return sol

        elif formula.op == '[]':
            sol = True
            neighbors = self.get_neighbours(w)
            for w2 in neighbors:
                if self.check_formula(w2, formula.right, relation):
                    sol = False
                    break
            return sol

        elif formula.op == '[.]':
            sol = True
            for iteration in self.bdd.pick_iter(self.relation_formula):
                neg_edge = [f'(~{i})' if iteration[i] else f'({i})' for i in iteration]
                node_eq = "\\/".join(neg_edge)
                new_relation = self.relation_formula & self.bdd.add_expr(f'({node_eq})')
                if not self.check_formula(w, formula.right, new_relation):
                    sol = False
                    break
            return sol

        else:
            print(f'Invalid Operator {formula.op}')

    def get_neighbours(self, w, formula=None):
        if formula is None:
            formula = self.relation_formula
        w_dict = {i: True if i in self.V[w] else False for i in self.P}
        neighbor_formula = self.bdd.let(w_dict, formula)
        neighbors = []
        for iteration in self.bdd.pick_iter(neighbor_formula):
            vw = [i[:-1] for i in iteration.keys() if iteration[i]]
            for world in self.V.keys():
                if sorted(vw) == sorted(self.V[world]):
                    neighbors.append(world)
        return neighbors

    def draw_formula(self, w, formula):
        flag = self.check_formula(w, formula)

        dot = graphviz.Digraph(comment=f'Modal Logic Model', engine='neato', format='png')
        for world in self.V:
            if w == world:
                dot.node(world, world, shape='square')
            else:
                dot.node(world, world)

        for world in self.V:
            neighbors = self.get_neighbours(world)
            for w2 in neighbors:
                dot.edge(world, w2)
        if flag:
            dot.attr(label=f'\nM, {w} \u22A8 {formula}', fontname="Sans Not-Rotated 14")
        else:
            dot.attr(label=f'\nM, {w} \u22AD {formula}', fontname="Sans Not-Rotated 14")
        dot.view()
