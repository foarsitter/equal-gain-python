from decimal import *

import calculations
from objects.Actor import Actor


class Exchange:
    def __init__(self, i: Actor, j: Actor, p: str, q: str, m, groups):
        self.model = m
        self.gain = 0
        self.is_valid = True
        self.re_calc = False
        self.p = p
        self.q = q

        self.dp = 0
        self.dq = 0

        self.updates = {p: dict(), q: dict()}
        # c.	If (1) holds, i shifts his position on issue p in the direction of j,
        # whereas j shifts his position on issue q in the direction of i.
        # Issue p is then called the supply issue of i and the demand issue of j,
        # whereas issue q is the demand issue of i and the supply issue of j.
        # If (2) holds,
        # issue q is the supply issue of i and issue p is the supply issue of j.
        # if ( (model$s_matrix[p, i] / model$s_matrix[q, i]) < (model$s_matrix[p, j] / model$s_matrix[q, j]))
        if (m.get(i, p, "s") / m.get(i, q, "s")) < (m.get(j, p, "s") / m.get(j, q, "s")):
            self.i = ExchangeActor(m, j, supply=q, demand=p, group=groups[0])
            self.j = ExchangeActor(m, i, supply=p, demand=q, group=groups[1])
        else:
            self.i = ExchangeActor(m, i, supply=q, demand=p, group=groups[0])
            self.j = ExchangeActor(m, j, supply=p, demand=q, group=groups[1])

        self.j.opposite_actor = self.i
        self.i.opposite_actor = self.j

    def calculate(self):
        # first we try to move j to the position of i on issue p
        # we start with the calculation for j
        self.dp = calculations.by_absolute_move(self.model.ActorIssues[self.j.supply], self.j)
        self.dq = calculations.by_exchange_ratio(self.j, self.dp)

        self.i.move = calculations.reverse_move(self.model.ActorIssues[self.i.supply], self.i, self.dq)
        self.j.move = abs(self.i.x_demand - self.j.x)

        if abs(self.i.move) > abs(self.j.x_demand - self.i.x):
            self.dq = calculations.by_absolute_move(self.model.ActorIssues[self.i.supply], self.i)
            self.dp = calculations.by_exchange_ratio(self.i, self.dq)

            self.i.move = abs(self.j.x_demand - self.i.x)
            self.j.move = calculations.reverse_move(self.model.ActorIssues[self.j.supply], self.j, self.dp)

        # TODO add check of NBS.
        # this check is only necessary for the smallest exchange,
        # because if the smallest exchange exceeds the limit the larger one will definitely do so

        if self.i.x > self.j.x_demand:
            self.i.move *= -1

        if self.j.x > self.i.x_demand:
            self.j.move *= -1

        self.i.moves.append(self.i.move)
        self.j.moves.append(self.j.move)

        self.i.y = self.i.x + self.i.move
        self.j.y = self.j.x + self.j.move

        eui = calculations.gain(self.i, self.dq, self.dp)
        euj = calculations.gain(self.j, self.dp, self.dq)

        if abs(eui - euj) > 0.0001:
            raise Exception("Expected equal gain")
        else:
            self.gain = abs(eui)

        b1 = self.i.is_move_valid(self.i.move)
        b2 = self.j.is_move_valid(self.j.move)

        self.is_valid = b1 and b2

        if self.gain < 1e-10:
            self.is_valid = False

        if self.is_valid:  # TODO and self.re_calc:

            self.j.nbs_0 = self.model.nbs[self.j.supply]
            self.j.nbs_1 = calculations.calc_adjusted_nbs(self.model.ActorIssues[self.j.supply],
                                                          self.updates[self.j.supply],
                                                          self.j.actor, self.j.y,
                                                          self.model.nbs_denominators[self.j.supply])

            if self.i.x_demand >= self.j.nbs_0 and self.i.x_demand >= self.j.nbs_1:
                pass
            elif self.i.x_demand <= self.j.nbs_0 and self.i.x_demand <= self.j.nbs_1:
                pass
            else:

                new_pos = calculations.calc_adjusted_nbs_by_position(self.model.ActorIssues[self.j.supply],
                                                                     self.updates[self.j.supply],
                                                                     self.j.actor, self.j.x, self.i.x_demand,
                                                                     self.model.nbs_denominators[self.j.supply])

                self.dp = (abs(new_pos - self.j.x) * self.j.s * self.j.c) / self.model.nbs_denominators[
                    self.j.supply]
                self.dq = calculations.by_exchange_ratio(self.j, self.dp)

                self.i.move = calculations.reverse_move(self.model.ActorIssues[self.i.supply], self.i, self.dq)
                self.j.move = abs(new_pos - self.j.x)

                if self.i.x > self.j.x_demand:
                    self.i.move *= -1

                if self.j.x > self.i.x_demand:
                    self.j.move *= -1

                self.i.moves.pop()
                self.j.moves.pop()
                self.i.moves.append(self.i.move)
                self.j.moves.append(self.j.move)

                self.i.y = self.i.x + self.i.move
                self.j.y = self.j.x + self.j.move

                nbs_1 = calculations.calc_adjusted_nbs(self.model.ActorIssues[self.j.supply],
                                                       self.updates[self.j.supply],
                                                       self.j.actor, self.j.y,
                                                       self.model.nbs_denominators[self.j.supply])

                if abs(nbs_1 - self.i.x_demand) > 0.000001:
                    new_pos = calculations.calc_adjusted_nbs_by_position(self.model.ActorIssues[self.j.supply],
                                                                         self.updates[self.j.supply],
                                                                         self.j.actor, self.j.x, self.i.x_demand,
                                                                         self.model.nbs_denominators[self.j.supply])

                    # self.is_valid = False
                    self.gain = 0.001
                    return

                eui = calculations.gain(self.i, self.dq, self.dp)
                euj = calculations.gain(self.j, self.dp, self.dq)

                if abs(eui - euj) > 0.0001:
                    raise Exception("Expected equal gain")
                else:
                    self.gain = abs(eui)

                b1 = self.i.is_move_valid(self.i.move)
                b2 = self.j.is_move_valid(self.j.move)

                self.is_valid = b1 and b2

            # TODO garbage code, korsakov code or something like that
            # Need sto be methodical approached
            self.i.nbs_0 = self.model.nbs[self.i.supply]

            self.i.nbs_1 = calculations.calc_adjusted_nbs(self.model.ActorIssues[self.i.supply],
                                                          self.updates[self.i.supply],
                                                          self.i.actor, self.i.y,
                                                          self.model.nbs_denominators[self.i.supply])

            if self.j.x_demand >= self.i.nbs_0 and self.j.x_demand >= self.i.nbs_1:
                pass
            elif self.j.x_demand <= self.i.nbs_0 and self.j.x_demand <= self.i.nbs_1:
                pass
            else:
                new_pos = calculations.calc_adjusted_nbs_by_position(self.model.ActorIssues[self.i.supply],
                                                                     self.updates[self.i.supply],
                                                                     self.i.actor, self.i.x, self.j.x_demand,
                                                                     self.model.nbs_denominators[self.i.supply])

                self.dq = (abs(new_pos - self.i.x) * self.i.s * self.i.c) / self.model.nbs_denominators[self.i.supply]
                self.dp = calculations.by_exchange_ratio(self.i, self.dq)

                self.i.move = abs(new_pos - self.i.x)
                self.j.move = calculations.reverse_move(self.model.ActorIssues[self.j.supply], self.j, self.dp)

                if self.i.x > self.j.x_demand:
                    self.i.move *= -1

                if self.j.x > self.i.x_demand:
                    self.j.move *= -1

                self.i.moves.pop()
                self.j.moves.pop()
                self.i.moves.append(self.i.move)
                self.j.moves.append(self.j.move)

                self.i.y = self.i.x + self.i.move
                self.j.y = self.j.x + self.j.move

                nbs_1 = calculations.calc_adjusted_nbs(self.model.ActorIssues[self.i.supply],
                                                       self.updates[self.i.supply],
                                                       self.i.actor, self.i.y,
                                                       self.model.nbs_denominators[self.i.supply])

                if abs(nbs_1 - self.j.x_demand) > 0.000001:
                    new_pos = calculations.calc_adjusted_nbs_by_position(self.model.ActorIssues[self.i.supply],
                                                                         self.updates[self.i.supply],
                                                                         self.i.actor, self.i.x, self.j.x_demand,
                                                                         self.model.nbs_denominators[self.i.supply])
                    self.gain = 0.001
                    # self.is_valid = False
                    return

                eui = calculations.gain(self.i, self.dq, self.dp)
                euj = calculations.gain(self.j, self.dp, self.dq)

                if abs(eui - euj) > 0.0001:
                    raise Exception("Expected equal gain")
                else:
                    self.gain = abs(eui)

                b1 = self.i.is_move_valid(self.i.move)
                b2 = self.j.is_move_valid(self.j.move)

                self.is_valid = b1 and b2

    def equals(self, i, j, p, q):

        return self.i.equals(i, q) and self.j.equals(j, p) or self.i.equals(j, p) and self.j.equals(i, q)

    def recalculate(self, exchange: 'Exchange'):
        # update supply positions

        self.re_calc = False

        # TODO create a method inside ExchangeActor for comparison, gets ugly.

        if self.i.actor.Name == exchange.i.actor.Name and self.i.supply == exchange.i.supply:
            self.i.x = exchange.i.y
            self.i.moves.pop()
            self.j.moves.pop()
            self.i.moves.append(exchange.i.moves[-1])
            self.re_calc = True
            # self.updates[exchange.i.supply][exchange.i.actor.Name] = exchange.i.y
        elif self.i.actor.Name == exchange.j.actor.Name and self.i.supply == exchange.j.supply:
            self.i.x = exchange.j.y
            self.i.moves.pop()
            self.j.moves.pop()
            self.i.moves.append(exchange.j.moves[-1])
            self.re_calc = True
            # self.updates[exchange.j.supply][exchange.j.actor.Name] = exchange.j.y
        if self.j.actor.Name == exchange.i.actor.Name and self.j.supply == exchange.i.supply:
            self.j.x = exchange.i.y
            self.i.moves.pop()
            self.j.moves.pop()
            self.j.moves.append(exchange.i.moves[-1])
            self.re_calc = True
            # self.updates[exchange.i.supply][exchange.i.actor.Name] = exchange.i.y
        elif self.j.actor.Name == exchange.j.actor.Name and self.j.supply == exchange.j.supply:
            self.j.x = exchange.j.y
            self.i.moves.pop()
            self.j.moves.pop()
            self.j.moves.append(exchange.j.moves[-1])
            self.re_calc = True

        # update the positions for the demand actors...

        if (self.j.actor.Name == exchange.j.actor.Name and self.j.demand == exchange.j.demand) or (
                        self.i.actor.Name == exchange.j.actor.Name and self.i.demand == exchange.j.demand):

            if exchange.i.actor.Name in self.updates[exchange.j.demand]:

                exchangeActor = exchange.i
                demand = exchange.j.demand
                x_updated = self.updates[exchange.j.demand][exchangeActor.actor.Name]

                if exchangeActor.start_position <= x_updated:
                    if x_updated < exchangeActor.y:
                        self.updates[demand][exchangeActor.actor.Name] = x_updated
                    else:
                        self.updates[demand][exchangeActor.actor.Name] = exchangeActor.y
                else:
                    if x_updated > exchangeActor.y:
                        self.updates[demand][exchangeActor.actor.Name] = x_updated
                    else:
                        self.updates[demand][exchangeActor.actor.Name] = exchangeActor.y
            else:
                self.updates[exchange.j.demand][exchange.i.actor.Name] = exchange.i.y

            if not self.re_calc:
                self.i.moves.pop()
                self.j.moves.pop()
                self.re_calc = True

        if (self.i.actor.Name == exchange.i.actor.Name and self.i.demand == exchange.i.demand) or (
                        self.j.actor.Name == exchange.i.actor.Name and self.j.demand == exchange.i.demand):

            if exchange.j.actor.Name in self.updates[exchange.i.demand]:

                exchangeActor = exchange.j
                demand = exchange.i.demand
                x_updated = self.updates[exchange.i.demand][exchangeActor.actor.Name]

                if exchangeActor.start_position <= x_updated:
                    if x_updated < exchangeActor.y:
                        self.updates[demand][exchangeActor.actor.Name] = x_updated
                    else:
                        self.updates[demand][exchangeActor.actor.Name] = exchangeActor.y
                else:
                    if x_updated > exchangeActor.y:
                        self.updates[demand][exchangeActor.actor.Name] = x_updated
                    else:
                        self.updates[demand][exchangeActor.actor.Name] = exchangeActor.y

            else:
                self.updates[exchange.i.demand][exchange.j.actor.Name] = exchange.j.y

            if not self.re_calc:
                self.i.moves.pop()
                self.j.moves.pop()
                self.re_calc = True

        # if self.i.actor.Name == exchange.j.actor.Name and self.i.demand == exchange.j.demand:
        #
        #     if exchange.i.actor.Name in self.updates[exchange.j.demand]:
        #         exchangeActor = exchange.i
        #         demand = exchange.j.demand
        #         x_updated = self.updates[exchange.j.demand][exchangeActor.actor.Name]
        #
        #         if exchangeActor.start_position <= x_updated:
        #             if x_updated < exchangeActor.y:
        #                 self.updates[demand][exchangeActor.actor.Name] = x_updated
        #             else:
        #                 self.updates[demand][exchangeActor.actor.Name] = exchangeActor.y
        #         else:
        #             if x_updated > exchangeActor.y:
        #                 self.updates[demand][exchangeActor.actor.Name] = x_updated
        #             else:
        #                 self.updates[demand][exchangeActor.actor.Name] = exchangeActor.y
        #     else:
        #         self.updates[exchange.j.demand][exchange.i.actor.Name] = exchange.i.y
        #
        #     if not self.re_calc:
        #         self.i.moves.pop()
        #         self.j.moves.pop()
        #         self.re_calc = True

        if self.re_calc:
            self.calculate()

    def __str__(self):
        return "{0}: {1}, {2}".format(round(self.gain, 9), str(self.i), str(self.j))


class ExchangeActor:
    def __init__(self, model, actor: Actor, demand: str, supply: str, group: str):
        self.c = model.get(actor, supply, "c")
        self.s = model.get(actor, supply, "s")
        self.x = model.get(actor, supply, "x")
        self.y = 0

        self.c_demand = model.get(actor, demand, "c")
        self.s_demand = model.get(actor, demand, "s")
        self.x_demand = model.get(actor, demand, "x")

        self.start_position = self.x

        self.demand = demand
        self.supply = supply

        self.group = group

        self.actor = actor

        self.opposite_actor = None
        self.move = 0
        self.moves = []

        self.nbs_0 = 0
        self.nbs_1 = 0

    def is_move_valid(self, move):
        # a move cannot exceed the interval [0,100]
        if abs(move) > 100 or abs(move) <= 1e-10:
            return False

        # if an exchange is on the edges there is no move posible
        if self.x + move < 0 or self.x + move > 100:
            return False

        if len(self.moves) == 1:
            return True

        if sum(self.moves) > 100:
            return False

        moves_min = min(self.moves)
        moves_max = max(self.moves)

        if moves_min < 0 and moves_max < 0 or moves_min > 0 and moves_max > 0:
            return True
            # newMoves < - c(self$moves, move) < 0
            #
            # return (isTRUE(all.equal(min(newMoves), max(newMoves))))

    def __str__(self):
        return "{0} {1} {2} {3} ({4})".format(self.actor.Name, self.supply, self.x, self.y,
                                              self.opposite_actor.x_demand)

    def new_start_position(self):

        sw = Decimal(0.4)
        fw = Decimal(0.1)
        swv = (1 - self.s) * sw * self.y
        fwv = fw * self.y
        pv = (1 - (1 - self.s) * sw - fw) * self.start_position
        x_t1 = swv + fwv + pv

        return x_t1
        # i.swv = (1 - s) * sw * y
        # ii.fwv = fw * y
        # iii.pv = (1 – (1 – s)*sw –fw)*x(t)
        # iv.x(t + 1) = swv + fwv + pv

    def equals(self, name, supply):

        if self.actor.Name == name and self.supply == supply:
            return True

        return False
